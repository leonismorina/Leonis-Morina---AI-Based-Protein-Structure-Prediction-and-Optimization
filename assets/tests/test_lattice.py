"""Unit tests for lattice representation, moves, validity check, and HP energy."""

import pytest
import lattice
import generator


def test_relative_and_absolute_coordinates():
    # Straight line: moves "FF" with start (0, 0)
    coords = lattice.relative_to_coordinates("FF")
    assert coords == [(0, 0), (1, 0), (2, 0), (3, 0)]
    assert lattice.is_valid_walk(coords)

    # Simple 2x2 loop: Right, Up, Left, Down -> (0,0), (1,0), (1,1), (0,1), (0,0)
    loop_coords = lattice.absolute_to_coordinates("ULD", start=(1, 0))
    full_loop = [(0, 0)] + loop_coords
    assert full_loop[0] == full_loop[-1]
    assert not lattice.is_valid_walk(full_loop)
    assert lattice.count_collisions(full_loop) == 1


def test_hp_energy_known_values():
    # Sequence: H-P-P-H forming a 2x2 square:
    # (0, 0): H, (1, 0): P, (1, 1): P, (0, 1): H
    # Non-consecutive H residues at (0, 0) and (0, 1) are adjacent!
    hp = "HPPH"
    coords = [(0, 0), (1, 0), (1, 1), (0, 1)]
    assert lattice.is_valid_walk(coords)
    contacts = lattice.hp_contacts(hp, coords)
    assert len(contacts) == 1
    assert contacts[0] == (0, 3)
    assert lattice.hp_energy(hp, coords) == -1.0


def test_bipartite_parity_bound():
    hp = "HPHPPHHPHPPH"
    bound = lattice.theoretical_energy_lower_bound(hp)
    assert bound < 0  # Negative energy bound


def test_pivot_move_validity():
    # L-shape: (0,0), (1,0), (2,0), (2,1)
    coords = [(0, 0), (1, 0), (2, 0), (2, 1)]
    # Pivot at index 1 ((1,0)): suffix (2,0), (2,1)
    # Rotate 90 deg CW
    new_coords = lattice.apply_pivot_move(coords, pivot_idx=1, angle_choice=0)
    assert new_coords is not None
    assert lattice.is_valid_walk(new_coords)
    assert len(new_coords) == 4


def test_corner_flip_validity():
    # Corner at index 1: (0,0), (1,0), (1,1) -> flipped to (0,1)
    coords = [(0, 0), (1, 0), (1, 1)]
    flipped = lattice.apply_corner_flip(coords, corner_idx=1)
    assert flipped is not None
    assert flipped == [(0, 0), (0, 1), (1, 1)]
    assert lattice.is_valid_walk(flipped)


def test_ascii_visualisation():
    hp = "HPPH"
    coords = [(0, 0), (1, 0), (1, 1), (0, 1)]
    text = lattice.format_ascii_lattice(hp, coords)
    assert "H" in text
    assert "P" in text
