# TechnicalAnalysis/PriceStructureZones/validation.py

import pandas as pd
from .models import ZoneSet


class ZoneValidator:
    """
    Validates or invalidates existing zones.
    """

    def validate(self, zones: ZoneSet, df: pd.DataFrame) -> ZoneSet:
        """
        Validate zones against price action.

        Rules:
        - may invalidate zones
        - may mutate zone type (e.g. ob -> breaker)
        - MUST NOT create new zones
        """
        raise NotImplementedError("Zone validation not implemented")