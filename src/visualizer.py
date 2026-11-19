"""Visualizer for 2D HP protein conformations.
Plots the protein backbone, residue types (Hydrophobic vs Polar),
and non-covalent topological H-H contacts.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import lattice


def plot_conformation(
    hp: str,
    coords: List[Tuple[int, int]],
    title: str = "Protein 2D Lattice Conformation",
    output_path: str = "docs/diagrams/protein_conformation.png",
) -> Path:
    """Plot backbone chain with colored residues and non-consecutive H-H contact dashed bonds."""
    fig, ax = plt.subplots(figsize=(8, 8))

    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]

    # Plot covalent backbone links
    ax.plot(xs, ys, color="gray", linewidth=2.5, zorder=1, label="Backbone chain")

    # Plot non-consecutive H-H contacts (dashed red lines)
    contacts = lattice.hp_contacts(hp, coords)
    contact_label_added = False
    for i, j in contacts:
        x_pair = [coords[i][0], coords[j][0]]
        y_pair = [coords[i][1], coords[j][1]]
        lbl = "H-H contact (-1 energy)" if not contact_label_added else ""
        ax.plot(x_pair, y_pair, color="crimson", linestyle="--", linewidth=2.0, zorder=2, label=lbl)
        contact_label_added = True

    # Plot residues: H (Hydrophobic: red circles), P (Polar: dodgerblue squares)
    h_xs, h_ys, p_xs, p_ys = [], [], [], []
    for i, (x, y) in enumerate(coords):
        if hp[i] == "H":
            h_xs.append(x)
            h_ys.append(y)
        else:
            p_xs.append(x)
            p_ys.append(y)

    if h_xs:
        ax.scatter(h_xs, h_ys, color="firebrick", s=280, zorder=3, edgecolors="black", linewidths=1.5, label="H (Hydrophobic)")
    if p_xs:
        ax.scatter(p_xs, p_ys, color="dodgerblue", s=280, marker="s", zorder=3, edgecolors="black", linewidths=1.5, label="P (Polar)")

    # Label sequence indices on nodes
    for i, (x, y) in enumerate(coords):
        ax.text(x, y, str(i + 1), color="white", fontsize=8, ha="center", va="center", weight="bold", zorder=4)

    energy = lattice.hp_energy(hp, coords)
    compactness = lattice.radius_of_gyration_sq(coords)
    ax.set_title(f"{title}\nLength: {len(hp)} | H-H Contacts: {len(contacts)} | Energy: {energy:.1f} | Rg²: {compactness:.2f}", fontsize=12)
    ax.set_aspect("equal")
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper right", framealpha=0.9)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


if __name__ == "__main__":
    import generator
    import algorithms
    from vsi.measure import Meter

    inst = generator.make_instance("medium", seed=42)
    meter = Meter()
    res = algorithms.simulated_annealing(inst, meter)
    if res["valid"]:
        plot_conformation(inst["hp"], res["coords"], title="Simulated Annealing Fold (Medium)", output_path="docs/diagrams/best_folded_structure.png")
        print("Saved docs/diagrams/best_folded_structure.png")
