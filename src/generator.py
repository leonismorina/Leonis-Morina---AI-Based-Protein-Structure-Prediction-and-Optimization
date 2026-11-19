"""Protein sequences + HP-model helpers and benchmarks.

The HP model (hydrophobic / polar) is the classic simplified folding model: each amino acid is H or P;
a fold is a self-avoiding walk on a lattice; every pair of H residues that are lattice neighbours but not
consecutive in the chain contributes -1 to the energy.
"""

from __future__ import annotations

import random
from typing import Dict, List, Tuple

import lattice

AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"
HYDROPHOBIC = set("AVILMFWC")  # Standard classification

SIZES = {"small": 12, "medium": 24, "large": 36, "huge": 50}

# Standard literature HP benchmark sequences (Dill et al.)
BENCHMARKS = {
    12: "HPHPPHHPHPPH",
    18: "HPHPPHHPHPPHPHHPPH",
    20: "HPPHPPHPPHPPHPPHPPHP",
    24: "HHPPHPPHPPHPPHPPHPPHPPHH",
    25: "PPHPPHHPPPPHHPPPPHHPPPHHH",
    36: "PPPPPPHHPPHPPHPPHPPHPPHPPHHPPPPHPHHP",
}


def to_hp(sequence: str) -> str:
    """Convert amino acid sequence to HP string."""
    return "".join("H" if aa in HYDROPHOBIC else "P" for aa in sequence)


def make_instance(size: str, seed: int = 0) -> dict:
    """Generate an instance with protein sequence, HP representation, and size metadata."""
    length = SIZES[size]
    # If standard benchmark exists for this length, use it; otherwise generate random
    if length in BENCHMARKS:
        hp_seq = BENCHMARKS[length]
        # Reconstruct representative AA sequence matching the HP pattern
        rng = random.Random(seed)
        h_pool = list("AVILMFWC")
        p_pool = [aa for aa in AMINO_ACIDS if aa not in HYDROPHOBIC]
        seq = "".join(rng.choice(h_pool) if c == "H" else rng.choice(p_pool) for c in hp_seq)
    else:
        rng = random.Random(seed)
        seq = "".join(rng.choice(AMINO_ACIDS) for _ in range(length))
        hp_seq = to_hp(seq)

    theoretical_bound = lattice.theoretical_energy_lower_bound(hp_seq)
    return {
        "size": size,
        "length": length,
        "sequence": seq,
        "hp": hp_seq,
        "theoretical_lower_bound": theoretical_bound,
    }


def coordinates(moves: str, start: Tuple[int, int] = (0, 0)) -> List[Tuple[int, int]]:
    """Relative 2D moves ('F', 'L', 'R') or absolute ('U', 'D', 'L', 'R') -> coordinates."""
    if set(moves).issubset({"F", "L", "R"}):
        return lattice.relative_to_coordinates(moves, start)
    return lattice.absolute_to_coordinates(moves, start)


def is_valid(coords: List[Tuple[int, int]]) -> bool:
    """Self-avoiding walk check."""
    return lattice.is_valid_walk(coords)


def hp_energy(hp: str, coords: List[Tuple[int, int]]) -> int:
    """Standard HP energy (lower is better). Penalty 10^6 for invalid folds."""
    return int(lattice.hp_energy(hp, coords, collision_penalty=1_000_000.0))
