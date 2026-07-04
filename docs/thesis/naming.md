# Naming: thesis names ↔ code classes ↔ legacy identifiers

The thesis document, the presentation, and the legacy code used different
identifiers for the same algorithms. This table is the single mapping; the
public API uses the thesis names, while every result artifact (canonical
JSON, reproduction outputs) keeps the legacy string keys so it matches the
approved presentation byte-for-byte.

| Thesis / public name | `hive_abc` class | Legacy class (in `legacy/`) | Result-file key | Reference |
| --- | --- | --- | --- | --- |
| ABC (original) | `ABCOriginal` | `ABC_BeeHive` | `ABC_Original` | Karaboga (2005), TR-06 |
| ABC-FA | `ABCFABacanin` | `ABC_FA_Bacanin` | `ABC_FA_Bacanin` | Tuba & Bacanin (2014); Yang (2009) |
| **ABC-FAEM** (thesis proposal) | `ABCFAEM` | `ABC_FA_Scout` | `ABC_FA_Scout` | this thesis; hybridization after Tuba & Bacanin (2014) |
| **ABC-GSA** (thesis proposal) | `ABCGSA` | `ABC_Scout_Gravitacional` | `ABC_Scout_Gravitacional` | this thesis; gravity analogy after Rashedi et al. (2009) |
| ε-greedy scout (annex only) | `ABCEpsilonScout` | `ABC_Probabilistic_Scout` | — | this thesis (annex) |
| PMVG (min-variance) | `MinVarianceCVX` | `PMVG_CVX` | `PMVG_CVX` | Markowitz (1952) |
| 1/N | `EqualWeight` | — | `Equally_Weighted` | DeMiguel et al. benchmark convention |

Display names for reports live in `hive_abc.reporting.DISPLAY_NAMES`.

## Parameter renames

| Legacy parameter | `hive_abc` constructor argument |
| --- | --- |
| `numb_bees` | `colony_size` |
| `max_itrs` | `max_iterations` |
| `G` | `g_constant` |
| `seed` (constructor) | `seed` (argument of `optimize()`) |
| derived per-class hash seed | stable `MODEL_SEED_OFFSETS` in the backtest engine |
| — (new) | `p_fa` on `ABCFAEM` — the PFA trigger of committee task 9 (default 1.0 = frozen behavior) |
