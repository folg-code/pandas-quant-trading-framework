# TechnicalAnalysis/PriceStructureZones/reaction.py

import pandas as pd
import numpy as np
from .models import ZoneSet


class ZoneReactionEngine:
    """
    Computes price reactions to zones.
    """

    def react(self, zones: ZoneSet, df: pd.DataFrame) -> dict[str, np.ndarray]:
        """
        Returns per-bar reaction signals.

        Output example:
        {
            "active_zones": np.ndarray[list[str]],
            "reacted_zones": np.ndarray[list[str]],
        }
        """
        raise NotImplementedError("Zone reaction logic not implemented")