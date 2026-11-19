# Design decisions log

## 2026-11-19 — Relative Move Chain Representation & Self-Avoiding Walk Model
- **What**: Modeled 2D lattice protein folding using relative directional turns (`F`: Forward, `L`: Turn Left, `R`: Turn Right) rather than absolute directions (`U, D, L, R`).
- **Why**: Absolute direction encoding suffers from 4-fold rigid rotational symmetries in the plane (i.e. rotating the same conformation by 90°, 180°, or 270° yields identical energy but 4 distinct coordinate sequences). Relative moves eliminate rigid rotational degrees of freedom, instantly reducing the theoretical search space from $4^{n-1}$ down to $3^{n-2}$.
- **Complexity**: Time $\mathcal{O}(n)$ to generate coordinates and $\mathcal{O}(n)$ to verify self-avoiding collisions using hash sets. Space $\mathcal{O}(n)$.
- **Alternatives tried / rejected**: Absolute coordinate strings (`U, D, L, R`) were evaluated initially, but produced massive duplicate states and bloated tree branching factors in constructive search.

## 2026-11-19 — Energy Function with Topological H-H Contacts & Bipartite Parity Property
- **What**: Implemented standard Dill HP energy model: $E = -\sum_{(i, j) \in \text{contacts}} 1$, where non-consecutive Hydrophobic residues ($|i - j| > 1$) at Manhattan distance 1 contribute -1.0. Also derived theoretical lower bounds using the bipartite graph property of 2D square lattices (residues on even lattice parity can only contact residues on odd lattice parity).
- **Why**: Accurately reflects hydrophobic collapse, the primary driving force in globular protein folding. The bipartite parity bound provides an admissible heuristic for branch-and-bound pruning.
- **Complexity**: $\mathcal{O}(n)$ contact detection using a spatial hash map index. Parity bound calculation runs in $\mathcal{O}(n)$ time and $\mathcal{O}(1)$ auxiliary space.
- **Alternatives tried / rejected**: Pairwise all-pairs distance checking ($\mathcal{O}(n^2)$) was rejected in favor of coordinate hash indexing ($\mathcal{O}(n)$).

## 2026-11-19 — Algorithm 1: Systematic Pruned Branch & Bound / Beam Search
- **What**: Incremental tree search that builds protein conformations residue-by-residue with symmetry-breaking, dynamic dead-end collision pruning, and parity-based contact upper bounding.
- **Why**: Guarantees systematic exploration without revisiting invalid branches. Incorporating a beam filter ($W = 40$) keeps memory strictly linear and runtime polynomial while preserving high-quality hydrophobic core formation.
- **Complexity**: Time $\mathcal{O}(W \cdot n)$ with beam width $W$; Space $\mathcal{O}(W \cdot n)$ storing current beam frontier states.
- **Alternatives tried / rejected**: Unpruned depth-first search ($\mathcal{O}(3^n)$) blew up exponentially beyond $n = 15$.

## 2026-11-19 — Algorithm 2: Simulated Annealing with Pivot Moves & Corner Flips
- **What**: Stochastic local search using the Metropolis-Hastings criterion ($P(\text{accept}) = e^{-\Delta E / T}$) with 70% Madras-Sokal Pivot moves and 30% local corner flips (crankshaft moves).
- **Why**: Pivot moves provide large ergodic jumps across folding conformational space, preventing the search from getting trapped in shallow local minima, while corner flips perform fine-grained local compactification.
- **Complexity**: Time $\mathcal{O}(K \cdot n)$ where $K$ is total temperature steps; Space $\mathcal{O}(n)$ to store current and candidate coordinates.
- **Alternatives tried / rejected**: Single-locus point mutations on relative move strings frequently break self-avoiding walk validity; pivot moves rotate entire subchains while preserving interior chain topology.

## 2026-11-19 — Algorithm 3: Genetic Algorithm with Elitism & Tournament Selection
- **What**: Population-based metaheuristic maintaining 50 candidate chromosomes, 1-point crossover, direction mutations, and elitism of the top 2 solutions.
- **Why**: Explores multiple distinct basins of attraction simultaneously through recombination of partially folded hydrophobic motifs.
- **Complexity**: Time $\mathcal{O}(G \cdot P \cdot n)$ where $G$ is generations and $P$ is population size; Space $\mathcal{O}(P \cdot n)$.
- **Alternatives tried / rejected**: Pure random walk GA without collision penalties resulted in invalid conformations. Adding heavy collision penalty allowed smooth gradient guidance toward valid compact states.

## 2026-11-19 — Algorithm 4: Hybrid Memetic Algorithm (GA + SA Local Polish)
- **What**: Combined multi-stage pipeline: GA executes broad global exploration across generations to locate optimal topological basins, followed by a low-temperature Simulated Annealing quenching phase that polishes the structure to local optimality.
- **Why**: Directly addresses the exploration vs exploitation trade-off: GA provides robust exploration without premature stagnation, while SA guarantees rapid local descent.
- **Complexity**: Time $\mathcal{O}(G_{eff} \cdot P \cdot n + K_{sa} \cdot n)$; Space $\mathcal{O}(P \cdot n)$.
- **Alternatives tried / rejected**: Pure local search alone often gets stuck in early sub-optimal compact folds with trapped polar residues.
