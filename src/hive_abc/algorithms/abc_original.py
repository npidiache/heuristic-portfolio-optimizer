"""ABC original (Karaboga, 2005) — the unmodified base algorithm."""

# --------------------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------------------
from hive_abc.algorithms.base import BeeHive


# --------------------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------------------
class ABCOriginal(BeeHive):
    """
    Artificial Bee Colony as proposed by Karaboga (2005).

    Reference: D. Karaboga, "An idea based on honey bee swarm for numerical
    optimization", Technical Report TR-06, Erciyes University, 2005. The
    thesis used this variant unchanged (legacy class `ABC_BeeHive`); both
    behavioral hooks keep their base-class implementations.
    """
