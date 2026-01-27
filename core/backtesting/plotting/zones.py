import pandas as pd


class ZoneView:
    """
    Adapter: filtruje zones DataFrame pod potrzeby rysowania.
    """

    def __init__(self, zones: pd.DataFrame):
        self.zones = zones if zones is not None else pd.DataFrame()

    def select(
        self,
        direction: str,
        zone_type: str,
        tf: str | None = None
    ) -> pd.DataFrame:
        if self.zones.empty:
            return self.zones

        z = self.zones
        z = z[(z["direction"] == direction) & (z["zone_type"] == zone_type)]

        if tf is not None:
            z = z[z["tf"] == tf]

        return z
