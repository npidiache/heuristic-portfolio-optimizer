# hive_abc.calibration

![module](https://img.shields.io/badge/module-calibration-00e5ff?style=flat&labelColor=1a1a2e)

The production path for tuning optimizer hyper-parameters, replacing the
unrunnable `legacy/` tuners. Four pieces, one flow: enumerate candidates
(`grid`), cut leak-free windows (`splits`), evaluate every candidate over
every window and seed (`runner`), and select a configuration while pricing
in the multiple testing behind the search (`selection`).

| Module | Provides |
| --- | --- |
| `grid` | `ParameterGrid` (cartesian candidates), `sample_candidates`, `candidate_label` |
| `splits` | `WalkForwardSplit`, `walk_forward_splits` (train / embargo / test windows) |
| `runner` | `run_calibration` → `CalibrationStudy` of per-(candidate, split) `TrialResult`s |
| `selection` | `select_configuration` → frozen `SelectionReport` |

## Usage

```python
from hive_abc.algorithms import ABCAdaptiveScout
from hive_abc.calibration import (
    ParameterGrid,
    candidate_label,
    run_calibration,
    select_configuration,
    walk_forward_splits,
)

grid = ParameterGrid({"colony_size": (15, 25), "max_trials_factor": (0.3, 0.6)})
splits = walk_forward_splits(prices.index, train_days=252, test_days=63)

study = run_calibration(
    build_optimizer=lambda c: ABCAdaptiveScout(
        colony_size=int(c["colony_size"]),
        max_trials_factor=float(c["max_trials_factor"]),
        max_iterations=60,
    ),
    prices=prices,
    candidates=grid.candidates(),
    splits=splits,
    seeds=range(10),
)
report = select_configuration(
    study, baseline=candidate_label({"colony_size": 25, "max_trials_factor": 0.6})
)
print(report.recommended, report.significant, report.deflated_sharpe)
```

## Discipline notes

- **Leak-free by construction.** Every split satisfies
  `max(train) < min(test)` with an embargo gap in between (property-tested);
  the runner builds the utility objective from the TRAIN window's log-return
  moments only and scores out-of-sample Sortino on the TEST window's
  pct-change returns — the `backtest.engine` metric-input convention.
- **Multiple testing is priced in.** Challengers are Wilcoxon-tested against
  the baseline, corrected with Holm's step-down, and the winner's estimate is
  deflated against the whole candidate set (DSR). A study where nothing beats
  the baseline is a valid, reportable negative: `significant == False`.
- **Independent of the frozen thesis path.** The runner never imports
  `backtest.engine` — no `DEFAULT_MODELS`, no per-model seed offsets; seeds
  are applied exactly as given. Calibration studies cannot disturb the
  Tier-2/Tier-3 reproduction guarantees.
