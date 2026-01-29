import plotly.graph_objects as go


class PlotRenderer:
    """
    Lowest-level rendering primitives.
    No layout, no dispatch, no logic.
    """

    def metric_table(self, payload: dict) -> go.Table:
        return go.Table(
            header=dict(values=["Metric", "Value"]),
            cells=dict(
                values=[
                    list(payload.keys()),
                    [self._fmt(v, "%" in k) for k, v in payload.items()],
                ]
            ),
        )

    def kv_table(self, payload: dict) -> go.Table:
        sections, keys, values = [], [], []

        for section, params in payload.items():
            for k, v in params.items():
                sections.append(section)
                keys.append(k)
                values.append(self._fmt(v))

        return go.Table(
            header=dict(values=["Section", "Parameter", "Value"]),
            cells=dict(values=[sections, keys, values]),
        )

    def generic_table(self, rows: list[dict]) -> go.Table:
        if not rows:
            return go.Table(header=dict(values=["No data"]), cells=dict(values=[[]]))

        columns = list(rows[0].keys())
        values = [[self._fmt(row[c]) for row in rows] for c in columns]

        return go.Table(
            header=dict(values=columns),
            cells=dict(values=values),
        )

    # ------------------------------
    # FORMATTER (1:1 ze STDOUT)
    # ------------------------------

    def _fmt(self, v, pct: bool = False):
        if isinstance(v, dict) and "display" in v:
            return v["display"]

        # legacy fallback
        if v is None:
            return "-"

        if isinstance(v, float):
            if pct:
                return f"{v * 100:,.2f}%"
            return f"{v:,.4f}"

        if isinstance(v, int):
            return f"{v:,d}"

        return str(v)