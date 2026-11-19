"""Lattice representation, validity checking, energy calculation,
and local moves for 2D HP Protein Folding.

Key concepts:
- Relative moves: 'F' (Forward), 'L' (Left), 'R' (Right).
  Using relative moves automatically eliminates rigid rotational symmetries!
- Absolute moves: 'U' (Up), 'D' (Down), 'L' (Left), 'R' (Right).
- Coordinate representation: list of (x, y) integer tuples.
- Self-avoiding walk (SAW): coordinates must all be unique.
- Energy: HP contact energy (-1 for each pair of non-consecutive H residues
  at Manhattan distance 1) + optional compactness / collision penalties.
- Bipartite Parity Property: on a 2D square lattice, two residues i and j
  can be adjacent if and only if |i - j| is ODD (i.e. (x+y) parity alternates).
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Set, Tuple

# Absolute 2D cardinal directions
DIR_VECTORS: Dict[str, Tuple[int, int]] = {
    "U": (0, 1),
    "D": (0, -1),
    "L": (-1, 0),
    "R": (1, 0),
}

# Relative move transitions given current facing direction
# Turn Left: (dx, dy) -> (-dy, dx)
# Turn Right: (dx, dy) -> (dy, -dx)
# Go Forward: (dx, dy) -> (dx, dy)
RELATIVE_TURNS = {
    "F": lambda dx, dy: (dx, dy),
    "L": lambda dx, dy: (-dy, dx),
    "R": lambda dx, dy: (dy, -dx),
}


def relative_to_coordinates(
    moves: str, start: Tuple[int, int] = (0, 0), initial_dir: Tuple[int, int] = (1, 0)
) -> List[Tuple[int, int]]:
    """Convert relative moves ('F', 'L', 'R') of length n-1 into (x, y) coordinates.
    First step from start is always along initial_dir (default Right = (1, 0)).
    """
    coords = [start]
    curr_pos = start
    curr_dir = initial_dir

    # First move from start
    next_pos = (curr_pos[0] + curr_dir[0], curr_pos[1] + curr_dir[1])
    coords.append(next_pos)
    curr_pos = next_pos

    for turn in moves:
        curr_dir = RELATIVE_TURNS[turn](curr_dir[0], curr_dir[1])
        curr_pos = (curr_pos[0] + curr_dir[0], curr_pos[1] + curr_dir[1])
        coords.append(curr_pos)

    return coords


def absolute_to_coordinates(
    moves: str, start: Tuple[int, int] = (0, 0)
) -> List[Tuple[int, int]]:
    """Convert absolute moves ('U', 'D', 'L', 'R') of length n-1 into coordinates."""
    pos = [start]
    for m in moves:
        dx, dy = DIR_VECTORS[m]
        x, y = pos[-1]
        pos.append((x + dx, y + dy))
    return pos


def is_valid_walk(coords: List[Tuple[int, int]]) -> bool:
    """Check self-avoiding walk (no duplicate lattice points)."""
    return len(set(coords)) == len(coords)


def count_collisions(coords: List[Tuple[int, int]]) -> int:
    """Number of duplicate coordinate visits (0 means strictly valid walk)."""
    return len(coords) - len(set(coords))


def hp_contacts(hp: str, coords: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Return all topological non-consecutive H-H contact pairs (i, j) with i < j."""
    if not is_valid_walk(coords):
        return []

    index = {c: i for i, c in enumerate(coords)}
    contacts = []
    n = len(coords)

    for i in range(n):
        if hp[i] != "H":
            continue
        x, y = coords[i]
        for dx, dy in DIR_VECTORS.values():
            neighbor = (x + dx, y + dy)
            j = index.get(neighbor)
            if j is not None and j > i + 1 and hp[j] == "H":
                contacts.append((i, j))
    return contacts


def hp_energy(
    hp: str,
    coords: List[Tuple[int, int]],
    collision_penalty: float = 1000.0,
    contact_strength: float = -1.0,
) -> float:
    """Calculate the energy of a protein conformation.
    
    E(S) = E_contacts + E_collisions
    - E_contacts = contact_strength * (number of non-covalent H-H contacts)
    - E_collisions = collision_penalty * (number of collisions)
    
    If coords are self-avoiding, collisions = 0 and energy = -1.0 * contacts.
    """
    collisions = count_collisions(coords)
    if collisions > 0:
        return float(collisions * collision_penalty)

    contacts = hp_contacts(hp, coords)
    return float(len(contacts) * contact_strength)


def radius_of_gyration_sq(coords: List[Tuple[int, int]]) -> float:
    """Measure structural compactness (squared radius of gyration)."""
    if not coords:
        return 0.0
    n = len(coords)
    mean_x = sum(c[0] for c in coords) / n
    mean_y = sum(c[1] for c in coords) / n
    return sum((c[0] - mean_x) ** 2 + (c[1] - mean_y) ** 2 for c in coords) / n


def bounding_box_area(coords: List[Tuple[int, int]]) -> int:
    """Area of minimal enclosing rectangle around coordinates."""
    if not coords:
        return 0
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    width = max(xs) - min(xs) + 1
    height = max(ys) - min(ys) + 1
    return width * height


def theoretical_energy_lower_bound(hp: str) -> int:
    """Theoretical lower bound on energy based on bipartite lattice parity.
    
    On a 2D square lattice, vertices can be 2-colored (even parity vs odd parity).
    Residues can only contact if one has even sequence index and the other has odd index!
    Each lattice node has degree 4 (at most 2 non-covalent contacts, since 2 are covalent
    chain links, and end points have at most 3 non-covalent contacts).
    
    Therefore, the maximum number of contacts between Even H's and Odd H's is:
    UpperBound_contacts <= min(sum(max_contacts(H_even)), sum(max_contacts(H_odd)))
    """
    n = len(hp)
    even_h = [i for i in range(n) if hp[i] == "H" and i % 2 == 0]
    odd_h = [i for i in range(n) if hp[i] == "H" and i % 2 == 1]

    def capacity(idx: int) -> int:
        # Endpoints of the chain have 1 covalent bond -> up to 3 non-covalent neighbors
        # Internal nodes have 2 covalent bonds -> up to 2 non-covalent neighbors
        return 3 if (idx == 0 or idx == n - 1) else 2

    cap_even = sum(capacity(i) for i in even_h)
    cap_odd = sum(capacity(i) for i in odd_h)

    max_contacts = min(cap_even, cap_odd)
    # Energy is negative of contacts
    return -max_contacts


# ============================================================================
# Local Improvement Moves (Validity Preserving)
# ============================================================================

def rotate_point_90(
    p: Tuple[int, int], pivot: Tuple[int, int], clockwise: bool = True
) -> Tuple[int, int]:
    """Rotate point p around pivot by 90 degrees."""
    dx = p[0] - pivot[0]
    dy = p[1] - pivot[1]
    if clockwise:
        return (pivot[0] + dy, pivot[1] - dx)
    else:
        return (pivot[0] - dy, pivot[1] + dx)


def rotate_point_180(p: Tuple[int, int], pivot: Tuple[int, int]) -> Tuple[int, int]:
    """Rotate point p around pivot by 180 degrees."""
    dx = p[0] - pivot[0]
    dy = p[1] - pivot[1]
    return (pivot[0] - dx, pivot[1] - dy)


def apply_pivot_move(
    coords: List[Tuple[int, int]], pivot_idx: int, angle_choice: int
) -> Optional[List[Tuple[int, int]]]:
    """Madras-Sokal Pivot Move:
    Select residue at pivot_idx (0 <= pivot_idx < len-1).
    Rotate the suffix (all residues from pivot_idx + 1 to end) around coords[pivot_idx].
    angle_choice: 0 -> 90 deg CW, 1 -> 90 deg CCW, 2 -> 180 deg.
    
    Returns the new coordinate list if it remains a strictly valid Self-Avoiding Walk,
    or None if a self-collision occurred.
    """
    n = len(coords)
    if pivot_idx < 0 or pivot_idx >= n - 1:
        return None

    pivot = coords[pivot_idx]
    prefix = coords[: pivot_idx + 1]
    occupied_prefix = set(prefix)

    new_suffix = []
    for i in range(pivot_idx + 1, n):
        pt = coords[i]
        if angle_choice == 0:
            rotated = rotate_point_90(pt, pivot, clockwise=True)
        elif angle_choice == 1:
            rotated = rotate_point_90(pt, pivot, clockwise=False)
        else:
            rotated = rotate_point_180(pt, pivot)

        if rotated in occupied_prefix:
            return None  # Collision with prefix
        occupied_prefix.add(rotated)
        new_suffix.append(rotated)

    return prefix + new_suffix


def apply_corner_flip(
    coords: List[Tuple[int, int]], corner_idx: int
) -> Optional[List[Tuple[int, int]]]:
    """Crankshaft / Corner-flip Move:
    If residues (i-1, i, i+1) form a right-angle corner (diagonal distance is sqrt(2)),
    flip residue i to the opposite diagonal point: p' = p_{i-1} + p_{i+1} - p_i.
    
    Returns the new coordinate list if p' is empty and walk remains valid, else None.
    """
    n = len(coords)
    if corner_idx <= 0 or corner_idx >= n - 1:
        return None

    p_prev = coords[corner_idx - 1]
    p_curr = coords[corner_idx]
    p_next = coords[corner_idx + 1]

    # Check if they form a corner (Manhattan distance 2, Euclidean distance sqrt(2))
    dx1, dy1 = p_curr[0] - p_prev[0], p_curr[1] - p_prev[1]
    dx2, dy2 = p_next[0] - p_curr[0], p_next[1] - p_curr[1]

    # Must be orthogonal: dot product == 0
    if dx1 * dx2 + dy1 * dy2 != 0:
        return None

    flipped = (p_prev[0] + p_next[0] - p_curr[0], p_prev[1] + p_next[1] - p_curr[1])

    # Check if flipped position is already occupied by any other residue
    occupied = set(coords)
    occupied.remove(p_curr)
    if flipped in occupied:
        return None

    new_coords = list(coords)
    new_coords[corner_idx] = flipped
    return new_coords


# ============================================================================
# Visualisation
# ============================================================================

def format_ascii_lattice(hp: str, coords: List[Tuple[int, int]]) -> str:
    """Render 2D lattice structure as clear ASCII grid showing residues and bonds."""
    if not coords:
        return "(empty structure)"

    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    width = (max_x - min_x) * 2 + 1
    height = (max_y - min_y) * 2 + 1

    grid = [[" " for _ in range(width)] for _ in range(height)]

    def grid_coords(x: int, y: int) -> Tuple[int, int]:
        gx = (x - min_x) * 2
        # Invert y so top is max_y
        gy = (max_y - y) * 2
        return gx, gy

    # Place covalent bonds between consecutive residues
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        gx1, gy1 = grid_coords(x1, y1)
        gx2, gy2 = grid_coords(x2, y2)
        mid_gx = (gx1 + gx2) // 2
        mid_gy = (gy1 + gy2) // 2
        if x1 == x2:
            grid[mid_gy][mid_gx] = "|"
        else:
            grid[mid_gy][mid_gx] = "-"

    # Place residues
    for i, (x, y) in enumerate(coords):
        gx, gy = grid_coords(x, y)
        res_char = hp[i] if i < len(hp) else "*"
        grid[gy][gx] = res_char

    return "\n".join("".join(row) for row in grid)
