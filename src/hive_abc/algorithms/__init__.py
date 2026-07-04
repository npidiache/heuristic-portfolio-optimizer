"""The ABC algorithm family: original, published hybrid, and thesis variants.

| Public class      | Thesis name | Legacy class              | Reference          |
| ----------------- | ----------- | ------------------------- | ------------------ |
| `ABCOriginal`     | ABC         | `ABC_BeeHive`             | Karaboga (2005)    |
| `ABCFABacanin`    | ABC-FA      | `ABC_FA_Bacanin`          | Tuba-Bacanin (2014)|
| `ABCFAEM`         | ABC-FAEM    | `ABC_FA_Scout`            | thesis proposal    |
| `ABCGSA`          | ABC-GSA     | `ABC_Scout_Gravitacional` | thesis; Rashedi 09 |
| `ABCEpsilonScout` | (annex)     | `ABC_Probabilistic_Scout` | thesis annex       |
"""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from hive_abc.algorithms.abc_epsilon import ABCEpsilonScout
from hive_abc.algorithms.abc_fa_bacanin import ABCFABacanin
from hive_abc.algorithms.abc_faem import ABCFAEM
from hive_abc.algorithms.abc_gsa import ABCGSA
from hive_abc.algorithms.abc_original import ABCOriginal
from hive_abc.algorithms.base import BeeHive

__all__ = [
    "ABCEpsilonScout",
    "ABCFABacanin",
    "ABCFAEM",
    "ABCGSA",
    "ABCOriginal",
    "BeeHive",
]
