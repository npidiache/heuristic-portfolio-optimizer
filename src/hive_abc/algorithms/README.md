# hive_abc.algorithms

![module](https://img.shields.io/badge/module-algorithms-00e5ff?style=flat-square&labelColor=1a1a2e)

The ABC family. One shared template (`base.BeeHive`) implements the
employed → onlooker → scout choreography of Karaboga's Artificial Bee
Colony; each variant overrides exactly one behavioral hook, so the frozen
thesis semantics live in a single place.

| Class | Thesis name | Overridden hook | Extra parameters | Reference |
| --- | --- | --- | --- | --- |
| `ABCOriginal` | ABC | — | — | Karaboga (2005), TR-06 |
| `ABCFABacanin` | ABC-FA | `_neighbor_candidate` (firefly move, all dimensions) | `b0`, `gamma`, `alpha` | Tuba & Bacanin (2014) — original implementation credited |
| `ABCFAEM` | ABC-FAEM | `_scout_move` (firefly move toward softmax elite) | `b0`, `gamma`, `alpha`, `k_top`, `softmax_tau`, `p_fa` | this thesis |
| `ABCGSA` | ABC-GSA | `_scout_move` (swarm net gravitational force) | `g_constant`, `epsilon`, `alpha` | this thesis; Rashedi et al. (2009) |
| `ABCEpsilonScout` | (annex) | `_scout_move` (ε-greedy restart / best-guided) | `epsilon` | this thesis (annex) |

## Usage

```python
from hive_abc import ABCFAEM, Bounds

result = ABCFAEM(colony_size=25, max_iterations=60, p_fa=1.0).optimize(
    objective, Bounds.box(n_assets), seed=42
)
```

## Fidelity notes

Behavior deliberately preserved from the thesis implementation (see the
`base` module docstring): onlooker roulette probabilities frozen at
initialization, a single strictly-greater-than scout trigger per iteration,
and Karaboga's fitness transform for greedy selection. Seeding uses
`numpy.random.default_rng(seed)` — the legacy per-class hash derivation was
platform-dependent; statistical reproduction (Tier-2 bands) is the contract.

`p_fa` on `ABCFAEM` is the probabilistic trigger of committee task 9:
probability that a stalled bee performs the firefly elite move instead of a
random restart. The default `1.0` reproduces the frozen thesis behavior;
see `docs/analysis/pfa_sensitivity.md` for the sweep.
