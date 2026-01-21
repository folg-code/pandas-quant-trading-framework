# TechnicalAnalysis/PriceStructureZones/detection.py

import pandas as pd
from .models import ZoneSet


class ZoneDetector:
    """
    Detects potential price structure zones.
    No validation, no reactions.
    """

    def detect(self, df: pd.DataFrame) -> ZoneSet:
        """
        Detect raw zones from price structure.

        Returns:
            ZoneSet: detected zones (unvalidated)
        """
        raise NotImplementedError("Zone detection not implemented")