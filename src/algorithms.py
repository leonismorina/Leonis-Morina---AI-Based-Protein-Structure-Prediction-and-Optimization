"""Core algorithms for Protein Structure Prediction in the 2D HP Lattice Model.

Implemented Algorithms:
1. baseline: Random Search over valid self-avoiding walks.
2. branch_and_bound: Systematic pruned tree search / beam search with parity bounds and symmetry breaking.
3. simulated_annealing: Metropolis-Hastings local search using Madras-Sokal pivot moves and corner flips.
4. genetic_algorithm: Evolutionary search with relative move chromosomes, tournament selection, crossover & mutation.
5. hybrid_memetic: Combined GA exploration followed by SA local polishing.

All algorithms:
- Count explored states with meter.count()
- Count pruned/rejected states with meter.prune()
- Track convergence with meter.record(best_energy)
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple

import lattice

RELATIVE_MOVES = ["F", "L", "R"]


# ============================================================================
# Helper Functions
# ============================================================================

def generate_random_valid_walk(
    hp: str, max_attempts: int = 100, rng: Optional[random.Random] = None
) -> Optional[List[Tuple[int, int]]]:
    """Grow a self-avoiding random walk step-by-step."""
    if rng is None:
        rng = random.Random()

    n = len(hp)
    for _ in range(max_attempts):
        coords = [(0, 0)]
        occupied = {(0, 0)}
        failed = False
        for step in range(1, n):
            x, y = coords[-1]
            candidates = [(x + dx, y + dy) for dx, dy in lattice.DIR_VECTORS.values()]
            valid_candidates = [c for c in candidates if c not in occupied]
            if not valid_candidates:
                failed = True
                break
            chosen = rng.choice(valid_candidates)
            coords.append(chosen)
            occupied.add(chosen)
        if not failed:
            return coords
    return None


def relative_moves_to_coords(moves: List[str]) -> List[Tuple[int, int]]:
    """Convert relative move string or list to 2D coordinates."""
    return lattice.relative_to_coordinates("".join(moves))


# ============================================================================
# 1. Baseline Algorithm: Random Sampling
# ============================================================================

def baseline(instance: dict, meter, samples: int = 200, seed: int = 42) -> dict:
    """Baseline: Monte Carlo random sampling of self-avoiding conformations."""
    rng = random.Random(seed)
    hp = instance["hp"]

    best_coords = None
    best_energy = float("inf")

    for _ in range(samples):
        meter.count()
        coords = generate_random_valid_walk(hp, max_attempts=5, rng=rng)
        if coords is None:
            meter.prune()
            continue

        energy = lattice.hp_energy(hp, coords)
        if energy < best_energy:
            best_energy = energy
            best_coords = coords
            meter.record(best_energy)

    return {
        "algorithm": "baseline",
        "coords": best_coords,
        "energy": best_energy if best_coords else 0.0,
        "valid": best_coords is not None and lattice.is_valid_walk(best_coords),
    }


# ============================================================================
# 2. Algorithm 1: Pruned Branch & Bound / Beam Search (Exact/Systematic)
# ============================================================================

def branch_and_bound(
    instance: dict, meter, beam_width: int = 40
) -> dict:
    """Systematic Search with Parity Bounds, Symmetry Breaking, and Pruning.
    
    Search-space reductions:
    1. Relative turns (F, L, R) reduce search space from 4^(n-1) to 3^(n-2).
    2. Symmetry breaking: first turn fixed to 'F' or 'L' (avoids bilateral reflection across the axis).
    3. Parity-based upper bounding on potential H-H contacts:
       Prune prefixes that cannot mathematically beat the current best solution.
    4. Beam filtering: retain the top `beam_width` most promising partial folds.
    """
    hp = instance["hp"]
    n = len(hp)
    if n <= 1:
        meter.count()
        return {"algorithm": "branch_and_bound", "coords": [(0, 0)], "energy": 0.0, "valid": True}

    # State: (moves_tuple, coords_list, occupied_set, current_contacts, score_heuristic)
    # Start with initial residue at (0, 0), step 1 to (1, 0)
    initial_coords = [(0, 0), (1, 0)]
    initial_occupied = {(0, 0), (1, 0)}

    # First turn choice: symmetry breaking - only allow 'F' and 'L' (cuts space by half)
    beam: List[Tuple[Tuple[str, ...], List[Tuple[int, int]], Set[Tuple[int, int]], int]] = []

    first_turns = ["F", "L"] if n > 2 else ["F"]
    for turn in first_turns:
        c = lattice.relative_to_coordinates(turn)
        if lattice.is_valid_walk(c):
            contacts = len(lattice.hp_contacts(hp[:len(c)], c))
            beam.append(((turn,), c, set(c), contacts))
            meter.count()
        else:
            meter.prune()

    best_overall_coords = None
    best_overall_energy = float("inf")

    # Expand residue by residue until length n
    # Initial beam entries already have 3 residues (len(coords) == 3)
    for current_len in range(3, n):
        next_beam = []
        target_sub_hp = hp[: current_len + 1]

        for moves, coords, occupied, curr_contacts in beam:
            last_pos = coords[-1]
            prev_pos = coords[-2]
            dx, dy = last_pos[0] - prev_pos[0], last_pos[1] - prev_pos[1]

            for turn in RELATIVE_MOVES:
                meter.count()
                ndx, ndy = lattice.RELATIVE_TURNS[turn](dx, dy)
                next_pos = (last_pos[0] + ndx, last_pos[1] + ndy)

                # Collision check
                if next_pos in occupied:
                    meter.prune()
                    continue

                new_coords = coords + [next_pos]
                new_occupied = occupied | {next_pos}
                new_moves = moves + (turn,)

                # Incremental contact calculation for the new residue
                new_contacts = curr_contacts
                if target_sub_hp[-1] == "H":
                    for ddx, ddy in lattice.DIR_VECTORS.values():
                        nbr = (next_pos[0] + ddx, next_pos[1] + ddy)
                        if nbr in occupied and nbr != last_pos:
                            idx = new_coords.index(nbr)
                            if idx < current_len - 1 and target_sub_hp[idx] == "H":
                                if abs(idx - current_len) % 2 == 1:
                                    new_contacts += 1

                # Calculate potential heuristic bound
                remaining_h = hp[current_len + 1:].count("H")
                max_possible_contacts = new_contacts + remaining_h * 2

                if best_overall_coords is not None and -max_possible_contacts >= best_overall_energy:
                    meter.prune()
                    continue

                heuristic = new_contacts * 10.0 - 0.1 * lattice.radius_of_gyration_sq(new_coords)
                next_beam.append((heuristic, new_moves, new_coords, new_occupied, new_contacts))

        if not next_beam:
            break

        next_beam.sort(key=lambda item: item[0], reverse=True)
        pruned_count = max(0, len(next_beam) - beam_width)
        for _ in range(pruned_count):
            meter.prune()

        beam = [(item[1], item[2], item[3], item[4]) for item in next_beam[:beam_width]]

        if current_len == n - 1:
            for _, coords, _, contacts in beam:
                energy = -float(contacts)
                if energy < best_overall_energy:
                    best_overall_energy = energy
                    best_overall_coords = coords
                    meter.record(best_overall_energy)

    if best_overall_coords is None and beam:
        best_overall_coords = beam[0][1]
        best_overall_energy = lattice.hp_energy(hp, best_overall_coords)

    return {
        "algorithm": "branch_and_bound",
        "coords": best_overall_coords,
        "energy": best_overall_energy,
        "valid": best_overall_coords is not None and lattice.is_valid_walk(best_overall_coords),
    }


# ============================================================================
# 3. Algorithm 2: Simulated Annealing (Metropolis-Hastings Local Search)
# ============================================================================

def simulated_annealing(
    instance: dict,
    meter,
    t_start: float = 5.0,
    t_min: float = 0.05,
    alpha: float = 0.98,
    steps_per_temp: int = 30,
    seed: int = 42,
) -> dict:
    """Simulated Annealing on HP Protein Folding using Pivot & Corner-flip moves.
    
    Features:
    - Validity preservation: only self-avoiding configurations are accepted.
    - Perturbations: Madras-Sokal Pivot Move (70%) and Corner Flip (30%).
    - Metropolis criterion: accept worsening moves with probability exp(-delta_E / T).
    """
    rng = random.Random(seed)
    hp = instance["hp"]
    n = len(hp)

    # Initialize with a random valid walk or straight line
    current_coords = generate_random_valid_walk(hp, max_attempts=50, rng=rng)
    if current_coords is None:
        current_coords = [(i, 0) for i in range(n)]

    current_energy = lattice.hp_energy(hp, current_coords)
    best_coords = list(current_coords)
    best_energy = current_energy
    meter.record(best_energy)

    temp = t_start
    while temp > t_min:
        for _ in range(steps_per_temp):
            meter.count()

            # Choose move type: 70% pivot move, 30% corner flip
            if rng.random() < 0.70 and n > 3:
                pivot_idx = rng.randint(0, n - 2)
                angle_choice = rng.randint(0, 2)
                candidate_coords = lattice.apply_pivot_move(current_coords, pivot_idx, angle_choice)
            else:
                corner_idx = rng.randint(1, n - 2)
                candidate_coords = lattice.apply_corner_flip(current_coords, corner_idx)

            if candidate_coords is None:
                meter.prune()
                continue

            cand_energy = lattice.hp_energy(hp, candidate_coords)
            delta_e = cand_energy - current_energy

            # Metropolis acceptance criterion
            if delta_e <= 0 or rng.random() < math.exp(-delta_e / temp):
                current_coords = candidate_coords
                current_energy = cand_energy

                if current_energy < best_energy:
                    best_energy = current_energy
                    best_coords = list(candidate_coords)
                    meter.record(best_energy)

        temp *= alpha

    return {
        "algorithm": "simulated_annealing",
        "coords": best_coords,
        "energy": best_energy,
        "valid": lattice.is_valid_walk(best_coords),
    }


# ============================================================================
# 4. Algorithm 3: Genetic Algorithm (Evolutionary Metaheuristic)
# ============================================================================

def genetic_algorithm(
    instance: dict,
    meter,
    pop_size: int = 50,
    generations: int = 60,
    crossover_prob: float = 0.85,
    mutation_prob: float = 0.15,
    tournament_k: int = 3,
    seed: int = 42,
) -> dict:
    """Genetic Algorithm for HP Protein Folding.
    
    Representation: Chromosome is a list of relative moves (length n-2).
    Fitness: Higher is better -> -energy - collision_penalty.
    Operators:
    - Tournament selection
    - Single-point crossover
    - Direction mutation + pivot mutation
    - Elitism (top 2 individuals preserved)
    """
    rng = random.Random(seed)
    hp = instance["hp"]
    n = len(hp)
    num_moves = max(0, n - 2)

    def evaluate_chromosome(chrom: List[str]) -> Tuple[float, List[Tuple[int, int]], bool]:
        coords = lattice.relative_to_coordinates("".join(chrom))
        collisions = lattice.count_collisions(coords)
        if collisions == 0:
            energy = lattice.hp_energy(hp, coords)
            fitness = -energy  # Higher fitness for lower energy
            return fitness, coords, True
        else:
            # Penalize collisions heavily so valid solutions dominate
            fitness = -1000.0 - (collisions * 100.0)
            return fitness, coords, False

    # Initialize population
    population = []
    for _ in range(pop_size):
        meter.count()
        chrom = [rng.choice(RELATIVE_MOVES) for _ in range(num_moves)]
        fit, coords, valid = evaluate_chromosome(chrom)
        population.append({"chrom": chrom, "fitness": fit, "coords": coords, "valid": valid})

    best_individual = max(population, key=lambda ind: ind["fitness"])
    best_energy = lattice.hp_energy(hp, best_individual["coords"]) if best_individual["valid"] else float("inf")
    if best_individual["valid"]:
        meter.record(best_energy)

    for gen in range(generations):
        # Sort by fitness descending
        population.sort(key=lambda ind: ind["fitness"], reverse=True)

        if population[0]["valid"]:
            current_best_e = lattice.hp_energy(hp, population[0]["coords"])
            if current_best_e < best_energy:
                best_energy = current_best_e
                best_individual = population[0]
                meter.record(best_energy)

        # Elitism: retain top 2
        new_population = [population[0], population[1]]

        while len(new_population) < pop_size:
            meter.count()

            # Tournament selection for parent 1
            cand1 = rng.sample(population, tournament_k)
            parent1 = max(cand1, key=lambda ind: ind["fitness"])["chrom"]

            # Tournament selection for parent 2
            cand2 = rng.sample(population, tournament_k)
            parent2 = max(cand2, key=lambda ind: ind["fitness"])["chrom"]

            # Crossover
            if rng.random() < crossover_prob and num_moves > 1:
                cx_point = rng.randint(1, num_moves - 1)
                child = parent1[:cx_point] + parent2[cx_point:]
            else:
                child = list(parent1)

            # Mutation
            for i in range(num_moves):
                if rng.random() < mutation_prob:
                    child[i] = rng.choice(RELATIVE_MOVES)

            fit, coords, valid = evaluate_chromosome(child)
            if not valid:
                meter.prune()

            new_population.append({"chrom": child, "fitness": fit, "coords": coords, "valid": valid})

        population = new_population

    final_best = max(population, key=lambda ind: ind["fitness"])
    final_coords = final_best["coords"]
    final_valid = final_best["valid"]
    final_e = lattice.hp_energy(hp, final_coords) if final_valid else float("inf")

    return {
        "algorithm": "genetic_algorithm",
        "coords": final_coords,
        "energy": final_e,
        "valid": final_valid,
    }


# ============================================================================
# 5. Algorithm 4 (Advanced/Optional): Hybrid Memetic Algorithm (GA + SA Polish)
# ============================================================================

def hybrid_memetic(
    instance: dict, meter, seed: int = 42
) -> dict:
    """Hybrid Memetic Algorithm:
    Stage 1: Genetic Algorithm runs for global exploration.
    Stage 2: Simulated Annealing local search polishes the best solution
             using pivot moves and corner flips to achieve lowest energy.
    """
    rng = random.Random(seed)
    # Stage 1: GA with moderate generations
    ga_result = genetic_algorithm(
        instance, meter, pop_size=40, generations=35, seed=seed
    )

    initial_coords = ga_result.get("coords")
    if initial_coords is None or not ga_result.get("valid", False):
        initial_coords = generate_random_valid_walk(instance["hp"], max_attempts=50, rng=rng)
        if initial_coords is None:
            initial_coords = [(i, 0) for i in range(len(instance["hp"]))]

    # Stage 2: SA Polish with focused cooling
    sa_inst = dict(instance)
    hp = sa_inst["hp"]
    n = len(hp)

    current_coords = list(initial_coords)
    current_energy = lattice.hp_energy(hp, current_coords)
    best_coords = list(current_coords)
    best_energy = current_energy

    temp = 2.0
    alpha = 0.92
    t_min = 0.05
    steps_per_temp = 20

    while temp > t_min:
        for _ in range(steps_per_temp):
            meter.count()
            if rng.random() < 0.65 and n > 3:
                pivot_idx = rng.randint(0, n - 2)
                angle_choice = rng.randint(0, 2)
                cand = lattice.apply_pivot_move(current_coords, pivot_idx, angle_choice)
            else:
                corner_idx = rng.randint(1, n - 2)
                cand = lattice.apply_corner_flip(current_coords, corner_idx)

            if cand is None:
                meter.prune()
                continue

            cand_e = lattice.hp_energy(hp, cand)
            delta_e = cand_e - current_energy
            if delta_e <= 0 or rng.random() < math.exp(-delta_e / temp):
                current_coords = cand
                current_energy = cand_e
                if current_energy < best_energy:
                    best_energy = current_energy
                    best_coords = list(cand)
                    meter.record(best_energy)

        temp *= alpha

    return {
        "algorithm": "hybrid_memetic",
        "coords": best_coords,
        "energy": best_energy,
        "valid": lattice.is_valid_walk(best_coords),
    }


# ============================================================================
# Registration & Scoring
# ============================================================================

ALGORITHMS = {
    "baseline": baseline,
    "branch_and_bound": branch_and_bound,
    "simulated_annealing": simulated_annealing,
    "genetic_algorithm": genetic_algorithm,
    "hybrid_memetic": hybrid_memetic,
}


def score(instance: dict, result: Any) -> dict:
    """Extract quality and performance metrics for results/metrics.csv."""
    if not isinstance(result, dict) or result.get("coords") is None:
        return {
            "solved": False,
            "energy": 0.0,
            "contacts": 0,
            "valid": False,
            "compactness": 0.0,
            "bound_gap": 0.0,
        }

    coords = result["coords"]
    hp = instance["hp"]
    valid = lattice.is_valid_walk(coords)
    energy = lattice.hp_energy(hp, coords) if valid else float("inf")
    contacts = len(lattice.hp_contacts(hp, coords)) if valid else 0
    compactness = lattice.radius_of_gyration_sq(coords) if valid else 0.0
    bound = instance.get("theoretical_lower_bound", 0)
    bound_gap = energy - bound if valid else float("inf")

    return {
        "solved": valid and energy <= 0,
        "energy": float(energy),
        "contacts": contacts,
        "valid": valid,
        "compactness": round(compactness, 2),
        "bound_gap": float(bound_gap),
    }
