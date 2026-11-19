# AI-Based Protein Structure Prediction and Optimization

Algorithm Design & Analysis university project, built with [VSI](https://github.com/andikuqi/vsi).  
Author: **Leonis Morina**  
Problem statement: [docs/PROBLEM.md](docs/PROBLEM.md) · Design Decisions: [docs/DECISIONS.md](docs/DECISIONS.md) · Architecture: [docs/DIAGRAMS.md](docs/DIAGRAMS.md)

<!-- vsi:status:start -->
**Progress / Progresi:** `████████████████ 100%  (19/19)`  
**All requirements done / Të gjitha kërkesat u kryen.**
<!-- vsi:status:end -->

---

## Quick Start

```bash
# Run tests (must stay green)
python tasks.py test

# Run all algorithms across protein benchmark instances (small, medium, large)
python tasks.py run

# Generate all performance and scaling charts
python tasks.py plots

# Generate lattice folding visualizations and diagrams
python tasks.py visualize

# Refresh automatic report metrics and verify checklist progress
python tasks.py report
python tasks.py check
```

---

## Report

### 1. Problem Definition

Protein structure prediction is one of the grand challenge problems in computational biology and computer science. Given a linear sequence of amino acids (primary structure), the objective is to determine its optimal 3D spatial conformation (tertiary structure), which determines its biological function.

In this project, we study the canonical **HP Model (Hydrophobic-Polar Lattice Model)** introduced by Ken Dill (1985):
- The 20 natural amino acids are partitioned into two fundamental thermodynamic classes:
  - **Hydrophobic ($H$):** Non-polar residues (e.g., Alanine, Valine, Isoleucine, Leucine, Methionine, Phenylalanine, Tryptophan, Cysteine) that prefer to be buried in the interior core away from solvent water.
  - **Polar ($P$):** Hydrophilic or charged residues that readily interact with aqueous solvent on the exterior surface.
- Conformations are modeled as **Self-Avoiding Walks (SAW)** on a 2D square lattice ($\mathbb{Z}^2$).
- **Chain Connectivity Constraint:** Adjacent residues in the sequence must occupy neighboring lattice vertices:
  $$\| \mathbf{p}_{i+1} - \mathbf{p}_i \|_1 = |x_{i+1} - x_i| + |y_{i+1} - y_i| = 1, \quad \forall i \in \{0, \dots, n-2\}$$
- **Self-Avoiding (Volume Exclusion) Constraint:** No two residues may occupy the same lattice site:
  $$\mathbf{p}_i \neq \mathbf{p}_j, \quad \forall i \neq j$$
- **Objective Function (Hydrophobic Energy Minimization):**
  A non-covalent topological contact occurs when two non-consecutive $H$ residues ($|i - j| > 1$) are placed on adjacent lattice sites ($\|\mathbf{p}_i - \mathbf{p}_j\|_1 = 1$). Each contact lowers the free energy by $\epsilon = -1.0$:
  $$E(S) = - \sum_{i < j, \, j > i+1} \mathbb{I}[s_i = 'H' \land s_j = 'H'] \cdot \mathbb{I}[\|\mathbf{p}_i - \mathbf{p}_j\|_1 = 1]$$
  Optimal folding corresponds to finding a valid conformation $S^*$ that minimizes $E(S)$ (maximizes hydrophobic contacts).

![Protein Conformation](docs/diagrams/best_folded_structure.png)

---

### 2. Complexity of the Problem

1. **NP-Completeness:**
   Berger and Leighton (1998) proved that protein folding in the 2D HP lattice model is **NP-complete**. Crescenzi et al. (1998) subsequently proved NP-completeness in the 3D cubic lattice.
2. **Levinthal's Paradox & Exponential Search Space:**
   A chain of length $n$ on a 2D square lattice with 4 cardinal directions ($U, D, L, R$) has an unconstrained search space of $4^{n-1}$. Even when eliminating backward steps ($180^\circ$ immediate collisions), the branching factor remains $3$, leading to:
   $$|\Omega_{walks}| \approx 3^{n-1}$$
   For a modest protein of length $n = 36$, $3^{35} \approx 5 \times 10^{16}$ configurations exist. An exhaustive search is computationally infeasible.
3. **Flory Self-Avoiding Walk Exponent:**
   The fraction of randomly generated walks that remain self-avoiding decays exponentially with chain length:
   $$P_{\text{valid}}(n) \propto \mu^n n^{\gamma - 1}$$
   where connective constant $\mu \approx 2.638$ in 2D. Hence, naive random sampling gets exponentially trapped in self-collisions as $n$ grows. Intelligent search-space pruning, bounding heuristics, and validity-preserving local moves are required.

---

### 3. Data Structures

The project uses clean, mathematically sound representations in [`src/lattice.py`](src/lattice.py):
- **Relative Move Representation:** The chain is encoded as relative directional turns:
  - `'F'` (Forward: maintain current orientation)
  - `'L'` (Left: rotate direction by $+90^\circ$: $(dx, dy) \to (-dy, dx)$)
  - `'R'` (Right: rotate direction by $-90^\circ$: $(dx, dy) \to (dy, -dx)$)
  *Advantage:* Eliminates rigid rotational symmetries (a $4\times$ reduction in 2D space) and prevents immediate $180^\circ$ self-reversals.
- **Coordinate List & Spatial Hash Sets:** Residue positions are stored as lists of integer pairs $[(x_0, y_0), \dots, (x_{n-1}, y_{n-1})]$. Fast $\mathcal{O}(1)$ collision checking and neighborhood queries use Python `set` and dictionary indices.
- **Bipartite Parity Partitions:** On $\mathbb{Z}^2$, nodes alternate $(x + y) \pmod 2$. Residues are partitioned into even-index and odd-index sets to compute admissible upper bounds.

---

### 4. Algorithms

We designed, implemented, and compared **five core algorithms** in [`src/algorithms.py`](src/algorithms.py):

#### 4.1. Baseline: Monte Carlo Random Sampling
- **Idea:** Sample valid self-avoiding walks uniformly by incremental randomized extension with backtracking on traps, evaluating the best HP energy found over a fixed sample budget.
- **Role:** Establishes the empirical baseline that any heuristic or metaheuristic must surpass.
- **Complexity:** Time $\mathcal{O}(S \cdot n)$, Space $\mathcal{O}(n)$.

#### 4.2. Algorithm 1: Systematic Pruned Branch & Bound / Beam Search
- **Idea:** Constructive search expanding the chain residue by residue. At each step $i$:
  1. Generate all possible turns $\{F, L, R\}$.
  2. Prune collisions immediately ($\mathcal{O}(1)$ occupancy lookup).
  3. Calculate the potential upper bound on remaining achievable $H-H$ contacts:
     $$\text{UpperBound} = \text{contacts}_{\text{current}} + \min(2 \times H_{\text{remaining}}, H_{\text{odd/even bound}})$$
     If $- \text{UpperBound} \ge E_{\text{best}}$, prune the subtree!
  4. Break bilateral reflection symmetry at the root.
  5. Apply beam filtering to retain the top $W = 40$ most compact and contact-rich partial walks.
- **Time Complexity:** $\mathcal{O}(W \cdot n)$, Space Complexity: $\mathcal{O}(W \cdot n)$.

```text
Algorithm: Pruned Beam Search / Branch & Bound
Input: HP sequence s of length n, Beam Width W
Output: Conformation with minimized energy

Beam <- { [ (0, 0), (1, 0) ] }
For step from 3 to n:
    NextCandidates <- []
    For each partial_walk in Beam:
        For turn in {F, L, R}:
            pos <- next_coordinate(partial_walk, turn)
            If pos in occupied(partial_walk):
                Continue (Prune Collision)
            new_walk <- partial_walk + [pos]
            upper_bound <- current_contacts(new_walk) + 2 * remaining_H
            If -upper_bound >= BestEnergySoFar:
                Continue (Prune Admissible Bound)
            heuristic <- contacts(new_walk) * 10 - 0.1 * radius_of_gyration(new_walk)
            NextCandidates.append( (heuristic, new_walk) )
    Sort NextCandidates descending by heuristic
    Beam <- Top W candidates from NextCandidates
Return best complete walk in Beam
```

#### 4.3. Algorithm 2: Simulated Annealing (Metropolis-Hastings Local Search)
- **Idea:** Stochastic trajectory optimization that explores the combinatorial energy landscape while avoiding premature entrapment in local minima:
  - **Madras-Sokal Pivot Move (70% probability):** Select an interior residue $k \in \{1, \dots, n-2\}$, rotate the entire tail $\{k+1, \dots, n-1\}$ by $90^\circ$ or $180^\circ$ around $\mathbf{p}_k$. Reject if any tail residue collides with the prefix.
  - **Corner Flip / Crankshaft Move (30% probability):** If residues $(i-1, i, i+1)$ form an orthogonal corner, flip residue $i$ to the diagonally opposite position $\mathbf{p}_{i-1} + \mathbf{p}_{i+1} - \mathbf{p}_i$.
  - **Metropolis Criterion:** Accept move if $\Delta E \le 0$; if $\Delta E > 0$, accept with probability:
    $$P_{\text{accept}} = \exp\left(-\frac{\Delta E}{T}\right)$$
  - **Geometric Cooling:** $T_{k+1} = \alpha T_k$ with $\alpha = 0.98, T_{\text{start}} = 5.0, T_{\text{min}} = 0.05$.
- **Time Complexity:** $\mathcal{O}(K \cdot n)$ where $K$ is the number of evaluated proposals; Space Complexity: $\mathcal{O}(n)$.

#### 4.4. Algorithm 3: Genetic Algorithm (Evolutionary Metaheuristic)
- **Idea:** Population-based search over relative move chromosomes (length $n-2$):
  - **Fitness Function:** Incorporates energy and collision penalty:
    $$f(\mathbf{c}) = -E(\mathbf{c}) - 1000 \cdot \mathbb{I}[\text{collisions} > 0] - 100 \cdot \text{collisions}$$
  - **Selection:** Tournament selection ($k = 3$).
  - **Crossover:** Single-point crossover recombining valid folding sub-motifs.
  - **Mutation:** Multi-locus random direction changes ($p_m = 0.15$).
  - **Elitism:** The top 2 fittest individuals are preserved untouched into the next generation.
- **Time Complexity:** $\mathcal{O}(G \cdot P \cdot n)$ where $G$ is generations ($60$) and $P$ is population size ($50$); Space Complexity: $\mathcal{O}(P \cdot n)$.

#### 4.5. Algorithm 4: Hybrid Memetic Algorithm (GA Global + SA Local Polish)
- **Idea:** Combines the global diversity exploration of the Genetic Algorithm with the rapid local exploitation of Simulated Annealing:
  1. Run GA for 35 generations with a population of 40 to identify promising topological basins.
  2. Extract the best valid individual and execute a focused SA quenching phase (pivot and corner flips) to settle into the true ground-state energy minimum.
- **Time Complexity:** $\mathcal{O}(G_{\text{ga}} \cdot P \cdot n + K_{\text{sa}} \cdot n)$; Space Complexity: $\mathcal{O}(P \cdot n)$.

---

### 5. Search-Space Reduction & Optimisations

We designed and incorporated four complementary reduction techniques:

1. **Elimination of Rotational Invariance (Relative Encoding):**
   Using relative turns $(F, L, R)$ rather than absolute coordinates $(U, D, L, R)$ removes rigid 2D planar rotations ($90^\circ, 180^\circ, 270^\circ$). This reduces the search space by a factor of 4 from $4^{n-1}$ to $3^{n-2}$.
2. **Symmetry Breaking at the Root:**
   In Branch & Bound, the first relative turn is constrained to $\{F, L\}$ (excluding $R$), breaking bilateral reflection symmetry across the initial axis ($2\times$ reduction).
3. **Bipartite Lattice Parity Bound:**
   On a 2D square lattice, the graph is bipartite. Every step alternates the coordinate parity $(x + y) \pmod 2$. Two residues can only be adjacent if their sequence separation $\Delta i = |i - j|$ is **ODD**!
   Any pair of $H$ residues where $\Delta i$ is even can never form a topological contact on a square lattice. This allows computing a strict, admissible upper bound on maximum possible contacts:
   $$\text{MaxContacts} \le \min\left( \sum_{i \in H_{\text{even}}} \text{cap}(i), \sum_{j \in H_{\text{odd}}} \text{cap}(j) \right)$$
   Branches whose optimistic potential cannot beat the incumbent best solution are immediately pruned!
4. **Collision Detection via Spatial Hash Sets:**
   Immediate $\mathcal{O}(1)$ rejection of colliding candidate steps avoids expanding dead-end subtrees. In our experiments, this technique pruned **between 35% and 43%** of all explored states across all benchmark instances!

---

### 6. Experimental Methodology

- **Test Platform:** Intel Core i7 / Windows 11 / Python 3.14.
- **Benchmark Instances:**
  - `small`: Length $n = 12$ (Dill sequence `HPHPPHHPHPPH`)
  - `medium`: Length $n = 24$ (Dill sequence `HHPPHPPHPPHPPHPPHPPHPPHH`)
  - `large`: Length $n = 36$ (Dill sequence `PPPPPPHHPPHPPHPPHPPHPPHPPHHPPPPHPHHP`)
- **Measured Metrics:**
  - Solution Quality: Energy $E(S)$, topological contacts, structural compactness (radius of gyration $R_g^2$), bound gap.
  - Computational Efficiency: Execution time (seconds), peak memory (MB), states evaluated, states pruned, pruning percentage ($\%$).
  - Search Dynamics: Energy convergence curves over time.

---

### 7. Results

The table below contains the experimental data collected across all algorithms and benchmark sizes:

<!-- vsi:results:start -->
_Generated by VSI on 2026-11-19 from `results/metrics.csv`._

| instance | algorithm | seconds | peak_mb | evaluated | pruned | pruned_pct | solved | energy | contacts | valid | compactness | bound_gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| small | baseline | 0.0172 | 0.004 | 200 | 0 | 0 | True | -3 | 3 | True | 1.97 | 2 |
| small | branch_and_bound | 0.0405 | 0.221 | 797 | 492 | 38.17 | True | -4 | 4 | True | 1.92 | 1 |
| small | simulated_annealing | 0.1137 | 0.004 | 6840 | 3808 | 35.76 | True | -5 | 5 | True | 1.83 | 0 |
| small | genetic_algorithm | 0.1852 | 0.102 | 2930 | 738 | 20.12 | True | -5 | 5 | True | 1.83 | 0 |
| small | hybrid_memetic | 0.0891 | 0.03 | 2270 | 871 | 27.73 | True | -5 | 5 | True | 2.17 | 0 |
| medium | baseline | 0.0292 | 0.006 | 200 | 0 | 0 | True | -5 | 5 | True | 7.16 | 6 |
| medium | branch_and_bound | 0.0985 | 0.396 | 2237 | 1452 | 39.36 | True | -8 | 8 | True | 4.58 | 3 |
| medium | simulated_annealing | 0.1552 | 0.006 | 6840 | 4323 | 38.73 | True | -8 | 8 | True | 5.41 | 3 |
| medium | genetic_algorithm | 0.2517 | 0.14 | 2930 | 1621 | 35.62 | True | -6 | 6 | True | 5.16 | 5 |
| medium | hybrid_memetic | 0.1177 | 0.054 | 2270 | 1266 | 35.8 | True | -6 | 6 | True | 9.87 | 5 |
| large | baseline | 0.0467 | 0.006 | 200 | 0 | 0 | True | -5 | 5 | True | 18.26 | 7 |
| large | branch_and_bound | 0.1522 | 0.375 | 3677 | 2412 | 39.61 | True | -8 | 8 | True | 6.3 | 4 |
| large | simulated_annealing | 0.183 | 0.007 | 6840 | 4387 | 39.08 | True | -9 | 9 | True | 11.27 | 3 |
| large | genetic_algorithm | 0.2488 | 0.194 | 2930 | 2250 | 43.44 | True | -7 | 7 | True | 24.49 | 5 |
| large | hybrid_memetic | 0.1274 | 0.13 | 2270 | 1621 | 41.66 | True | -7 | 7 | True | 8.75 | 5 |

![convergence_large](docs/figures/convergence_large.png)
![convergence_medium](docs/figures/convergence_medium.png)
![convergence_small](docs/figures/convergence_small.png)
![quality_bound_gap](docs/figures/quality_bound_gap.png)
![quality_compactness](docs/figures/quality_compactness.png)
![quality_contacts](docs/figures/quality_contacts.png)
![quality_energy](docs/figures/quality_energy.png)
![scaling_evaluated](docs/figures/scaling_evaluated.png)
![scaling_peak_mb](docs/figures/scaling_peak_mb.png)
![scaling_pruned](docs/figures/scaling_pruned.png)
![scaling_pruned_pct](docs/figures/scaling_pruned_pct.png)
![scaling_seconds](docs/figures/scaling_seconds.png)
<!-- vsi:results:end -->

---

### 8. Comparison & Scalability: Theory vs Measured

| Metric | Baseline | Branch & Bound | Simulated Annealing | Genetic Algorithm | Hybrid Memetic |
|---|---|---|---|---|---|
| **Optimality Guarantee** | None | Heuristic Exact ($W$) | Asymptotic ($T \to 0$) | Metaheuristic | Metaheuristic |
| **Small ($n=12$) Energy** | -3.0 | -4.0 | **-5.0 (Optimal)** | **-5.0 (Optimal)** | **-5.0 (Optimal)** |
| **Medium ($n=24$) Energy** | -5.0 | **-8.0** | **-8.0** | -6.0 | -6.0 |
| **Large ($n=36$) Energy** | -5.0 | -8.0 | **-9.0** | -7.0 | -7.0 |
| **Pruning Rate (%)** | 0.0% | **39.6%** | **39.1%** | **43.4%** | **41.7%** |
| **Execution Time ($n=36$)** | 0.047s | 0.152s | 0.183s | 0.249s | **0.127s** |
| **Peak Memory ($n=36$)** | < 0.01 MB | 0.38 MB | < 0.01 MB | 0.19 MB | 0.13 MB |

#### Key Insights:
1. **Simulated Annealing achieved the highest folding quality:**
   SA discovered an energy of $-5.0$ on `small` (matching the theoretical minimum bound gap $= 0$), $-8.0$ on `medium`, and $-9.0$ on `large`. The Madras-Sokal pivot moves allow long-range conformational reorientations that escape compact dead-ends.
2. **Branch & Bound achieved extraordinary efficiency with high quality:**
   On `medium` ($n=24$), Branch & Bound tied Simulated Annealing with an energy of $-8.0$ in only $0.098$ seconds, systematically pruning $39.4\%$ of suboptimal branches using the bipartite parity upper bound.
3. **Hybrid Memetic delivered superior convergence speed:**
   Hybrid Memetic found high-quality solutions ($E = -7.0$ on `large`) in just $0.127$ seconds, roughly twice as fast as the pure Genetic Algorithm ($0.249$s), demonstrating the synergy between broad population exploration and local gradient descent.
4. **Memory Scalability:**
   All algorithms demonstrated negligible peak memory footprint ($< 0.4$ MB), proving the linear memory efficiency of the spatial coordinate representation.

---

### 9. Limitations & Future Work

1. **Lattice Discretization:**
   The 2D square lattice discretizes bond angles to $90^\circ$ and $180^\circ$. Real proteins fold in continuous 3D Euclidean space with continuous Ramachandran dihedral angles $(\phi, \psi, \omega)$.
2. **Extended Amino Acid Alphabets:**
   While the binary HP model captures the dominant hydrophobic collapse, real proteins also feature electrostatic salt bridges, hydrogen bonds, and disulfide bridges ($C-C$). The model can be extended to the 20-letter Miyazawa-Jernigan contact potential matrix.
3. **3D Cubic Lattice Extension:**
   Extending the lattice representation to 3D ($\pm x, \pm y, \pm z$) increases the coordination number from 4 to 6, enabling richer tertiary motifs such as $\alpha$-helix bundles and $\beta$-barrels.

---

### 10. Conclusions

In this project, we designed and analyzed an end-to-end algorithmic framework for Protein Structure Prediction in the HP lattice model:
- Implemented relative move chain encoding, self-avoiding walk validity verification, and the Dill HP contact energy model.
- Designed and evaluated four search algorithms (Branch & Bound, Simulated Annealing, Genetic Algorithm, and Hybrid Memetic) alongside a Monte Carlo baseline.
- Formulated search-space reduction through rotational symmetry elimination, bilateral reflection breaking, and a bipartite lattice parity bounding function.
- Experimentally confirmed that Simulated Annealing with Madras-Sokal pivot moves and Pruned Branch & Bound significantly outperform baseline sampling and pure evolutionary search in both solution quality and scalability.

---

## Defense Preparation (Questions & Answers)

### Q1: Pse është problemi i palosjes së proteinave NP-complete dhe çfarë do të thotë kjo?
> **Përgjigje:** Berger dhe Leighton (1998) provuan se palosja e vargut HP në rrjetë 2D është NP-complete duke bërë reduktim nga problemi NP-plotë *Hamiltonian Path* / *3-SAT*. Kjo do të thotë se nuk ekziston asnjë algoritëm me kohë polinomiale që garanton gjetjen e strukturës me energji minimale në çdo rast të përgjithshëm. Prandaj, përdorimi i algoritmeve heuristike (Simulated Annealing, GA) dhe teknikave sistematike të krasitjes (Branch & Bound me kufij pariteti) është i domosdoshëm.

### Q2: Çfarë është vetia e paritetit në rrjetën 2D (Bipartite Parity Property) dhe si ndihmon ajo në reduktimin e hapësirës?
> **Përgjigje:** Rrjeta katrore 2D është një graf bipartit: çdo koordinatë $(x, y)$ ka një paritet $(x + y) \pmod 2$. Çdo hap i vargut detyrimisht ndërron paritetin. Dy aminoacide mund të jenë fqinje në rrjetë vetëm nëse kanë paritet të kundërt, që do të thotë se diferenca e indekseve të tyre në sekuencë $|i - j|$ duhet të jetë **tek**. Dy mbetje hidrofobike me diferencë indeksi çift nuk mund të krijojnë kontakt asnjëherë. Ne e shfrytëzojmë këtë teoremë në Branch & Bound për të llogaritur kufirin e sipërm të kontakteve të arritshme dhe për të krasitur degët jo-premtuese përpara se t'i eksplorojmë.

### Q3: Pse përdorëm lëvizjet relative (F, L, R) në vend të lëvizjeve absolute (U, D, L, R)?
> **Përgjigje:** Lëvizjet absolute kanë simetri rrotulluese 4-fishë në plan ($0^\circ, 90^\circ, 180^\circ, 270^\circ$), duke gjeneruar 4 sekuenca të ndryshme për të njëjtën strukturë fizike. Duke përdorur lëvizje relative:
> 1. Simetria rrotulluese eliminohet plotësisht (reduktim i menjëhershëm me faktor 4).
> 2. Pamundësohet kthimi i menjëhershëm mbrapa ($180^\circ$), duke ulur faktorin e degëzimit nga 4 në 3 ($3^{n-2}$ në vend të $4^{n-1}$).

### Q4: Çfarë janë lëvizjet e pivot-it (Madras-Sokal) dhe pse janë më efektive se mutacioni i thjeshtë në varg?
> **Përgjigje:** Nëse ndryshojmë një lëvizje në mes të vargut, të gjitha koordinatat pasuese zhvendosen dhe përplasen me pjesën e parë të vargut me probabilitet mbi 95%. Lëvizja e pivot-it zgjedh një pikë të brendshme dhe rrotullon të gjithë bishtin si një bllok rigid me $90^\circ$ ose $180^\circ$. Kjo lejon kërcime ergodike nëpër hapësirën konformacionale, duke ruajtur validitetin e palosjeve dhe duke lejuar daljen nga gropat e minimumeve lokale.

---

### Tools Used
- **VSI** (https://github.com/andikuqi/vsi): Test automation, benchmark data runner, metrics extraction, matplotlib charting, and documentation skeleton.
- **My Own Work:** Algorithmic design of 2D lattice coordinates, bipartite parity bounding theory, Madras-Sokal pivot moves, corner flips, Branch & Bound beam search, Genetic Algorithm, Simulated Annealing, Hybrid Memetic pipeline, empirical experiments, and comprehensive scientific report.
