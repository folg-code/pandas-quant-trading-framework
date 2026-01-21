# TechnicalAnalysis/PriceStructureZones/aggregation.py

import pandas as pd
import numpy as np


class ZoneContextAggregator:
    """
    Aggregates raw zone reactions into strategy-level context.
    """

    def aggregate(
        self,
        reactions: dict[str, np.ndarray],
        index: pd.Index
    ) -> dict[str, pd.Series]:
        """
        Converts numpy arrays to pandas Series aligned with DF.

        No filtering, no decisions.
        """
        return {
            key: pd.Series(value, index=index)
            for key, value in reactions.items()
        }