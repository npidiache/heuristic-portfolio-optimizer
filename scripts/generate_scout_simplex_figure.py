"""Generates the ternary-simplex schematic for the scout-activation annex.

Produces a print-ready PNG (300 dpi, Obsidian Aqua palette, Spanish labels)
under `docs/figures/`, illustrating why the recovery move's geometry matters:
on a three-asset simplex it contrasts where each scout policy relocates a
stagnant bee — uniform restart (dispersed), firefly attraction (barely moves),
and the proposed elite-conditioned Dirichlet restart (concentrated on the
elite direction). The figure is schematic (a fixed-seed illustration of the
operators), not derived from the frozen data; it accompanies
`docs/analysis/anexo_activacion_scout.md` as Figura A.1.

Requires the optional dependency group:  uv sync --group figures
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# noqa comments: imports must follow the sys.path bootstrap in scripts.
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from numpy.typing import NDArray  # noqa: E402

# --------------------------------------------------------------------------------------
# Global Variables
# --------------------------------------------------------------------------------------
FIGURES_DIR = REPO_ROOT / "docs" / "figures"
SEED = 7
N_POINTS = 130

INK = "#1A1A2E"
MUTED = "#64748B"
AQUA = "#0097A7"
CORAL = "#E05252"

# Barycentric vertices of the 2-simplex: asset A (top), B (left), C (right).
VERTICES = np.array([[0.5, np.sqrt(3.0) / 2.0], [0.0, 0.0], [1.0, 0.0]])
ELITE_MEAN = np.array([0.56, 0.30, 0.14])
STAGNANT = np.array([0.10, 0.18, 0.72])


# --------------------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------------------
def apply_brand_style() -> None:
    """Applies the Obsidian Aqua look to matplotlib."""
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Outfit", "Segoe UI", "Helvetica Neue", "Arial"],
            "text.color": INK,
            "axes.titlecolor": INK,
            "axes.titleweight": "bold",
            "figure.facecolor": "#FFFFFF",
            "axes.facecolor": "#FFFFFF",
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
        }
    )


def to_xy(weights: NDArray[np.float64]) -> NDArray[np.float64]:
    """Maps simplex weight vectors to 2-D barycentric coordinates."""
    return np.asarray(weights @ VERTICES, dtype=np.float64)


def draw_triangle(ax: Axes) -> None:
    """Draws the simplex edges, gridlines, and vertex labels on an axis."""
    closed = np.vstack([VERTICES, VERTICES[0]])
    ax.plot(closed[:, 0], closed[:, 1], color=INK, linewidth=1.6, zorder=2)
    for fraction in (0.25, 0.5, 0.75):
        for i, j, k in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
            p1 = VERTICES[i] + (VERTICES[j] - VERTICES[i]) * fraction
            p2 = VERTICES[i] + (VERTICES[k] - VERTICES[i]) * fraction
            ax.plot(
                [p1[0], p2[0]], [p1[1], p2[1]], color="#E2E8F0", linewidth=0.6, zorder=1
            )
    labels = ["Activo A", "Activo B", "Activo C"]
    offsets = [(0.0, 0.045), (-0.04, -0.045), (0.04, -0.045)]
    aligns = ["center", "right", "left"]
    for vertex, label, (dx, dy), ha in zip(
        VERTICES, labels, offsets, aligns, strict=True
    ):
        ax.annotate(
            label,
            (vertex[0] + dx, vertex[1] + dy),
            ha=ha,
            va="center",
            fontsize=9,
            color=MUTED,
        )
    ax.set_aspect("equal")
    ax.axis("off")


def dirichlet_cloud(
    rng: np.random.Generator, alpha: NDArray[np.float64]
) -> NDArray[np.float64]:
    """Samples `N_POINTS` portfolios from a Dirichlet and maps them to 2-D."""
    return to_xy(rng.dirichlet(alpha, size=N_POINTS))


def firefly_cloud(rng: np.random.Generator) -> NDArray[np.float64]:
    """Samples the near-stationary firefly move around the stagnant bee.

    At portfolio dimensionality the attraction `exp(-gamma * r**2)` collapses,
    so the schematic keeps the candidates clustered on the stalled position
    with only a small jitter.
    """
    jitter = rng.normal(0.0, 0.02, size=(N_POINTS, 3))
    weights = np.clip(STAGNANT + jitter, 1e-6, None)
    weights /= weights.sum(axis=1, keepdims=True)
    return to_xy(weights)


def draw_panel(
    ax: Axes, title: str, cloud: NDArray[np.float64], *, show_bee: bool
) -> None:
    """Renders one policy panel: triangle, elite mean, cloud, optional bee."""
    draw_triangle(ax)
    ax.set_title(title, fontsize=11, pad=10)
    ax.scatter(cloud[:, 0], cloud[:, 1], s=14, color=AQUA, alpha=0.45, zorder=3)
    elite = to_xy(ELITE_MEAN)
    ax.scatter(
        [elite[0]],
        [elite[1]],
        marker="*",
        s=240,
        color=AQUA,
        edgecolor="white",
        linewidth=0.8,
        zorder=5,
    )
    ax.annotate(
        "media élite",
        (elite[0], elite[1] + 0.055),
        ha="center",
        fontsize=8.5,
        color=INK,
        fontweight="bold",
    )
    if show_bee:
        bee = to_xy(STAGNANT)
        ax.scatter(
            [bee[0]],
            [bee[1]],
            marker="o",
            s=90,
            facecolor="none",
            edgecolor=CORAL,
            linewidth=2.0,
            zorder=5,
        )
        ax.annotate(
            "abeja estancada",
            (bee[0], bee[1] - 0.06),
            ha="center",
            fontsize=8.5,
            color=CORAL,
        )


def build_figure() -> None:
    """Assembles the three-panel simplex schematic and writes it to PNG."""
    rng = np.random.default_rng(SEED)
    uniform = dirichlet_cloud(rng, np.ones(3))
    firefly = firefly_cloud(rng)
    dirichlet = dirichlet_cloud(rng, 20.0 * ELITE_MEAN + 0.01)

    fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.4))
    draw_panel(
        axes[0],
        "Reinicio uniforme (ABC original)",
        uniform,
        show_bee=False,
    )
    draw_panel(
        axes[1],
        "Movimiento luciérnaga (ABC-FAEM)",
        firefly,
        show_bee=True,
    )
    draw_panel(
        axes[2],
        "Reinicio Dirichlet élite (propuesto)",
        dirichlet,
        show_bee=False,
    )
    # No baked-in figure title: the caption is supplied by the document that
    # embeds the image (the annex Markdown or the Word caption), avoiding a
    # duplicated "Figura A.1" when inserted into the thesis.
    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / "fig_simplex_scout.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"wrote {path.relative_to(REPO_ROOT)}")


def main() -> None:
    """Applies the brand style and builds the figure."""
    apply_brand_style()
    build_figure()


if __name__ == "__main__":
    main()
