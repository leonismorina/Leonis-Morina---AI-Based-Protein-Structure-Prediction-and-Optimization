"""Tests for core search algorithms."""

import pytest
from vsi.measure import Meter

import generator
import algorithms
import lattice


@pytest.fixture
def small_instance():
    return generator.make_instance("small", seed=42)


@pytest.mark.parametrize(
    "algo_name",
    [
        "baseline",
        "branch_and_bound",
        "simulated_annealing",
        "genetic_algorithm",
        "hybrid_memetic",
    ],
)
def test_all_algorithms_run_and_valid(algo_name, small_instance):
    meter = Meter()
    algo_fn = algorithms.ALGORITHMS[algo_name]
    result = algo_fn(small_instance, meter)

    assert result is not None
    assert "coords" in result
    assert result["coords"] is not None
    assert len(result["coords"]) == small_instance["length"]
    assert result["valid"] is True
    assert lattice.is_valid_walk(result["coords"])

    # Verify meter tracked steps
    assert meter.evaluated > 0

    # Verify score function
    scored = algorithms.score(small_instance, result)
    assert scored["valid"] is True
    assert scored["energy"] <= 0
