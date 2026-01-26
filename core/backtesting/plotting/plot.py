import plotly.graph_objects as go
import pandas as pd
import matplotlib.pyplot as plt
from plotly.subplots import make_subplots
import os


class TradePlotter:
    def __init__(
        self,
        df: pd.DataFrame,
        trades: pd.DataFrame,
        bullish_zones=None,
        bearish_zones=None,
        extra_series=None,
        bool_series=None,
        title: str = "Trades plot"
    ):
        self.df = df
        self.trades = trades
        self.bullish_zones = bullish_zones or []
        self.bearish_zones = bearish_zones or []
        self.extra_series = extra_series or []
        self.bool_series = bool_series or []
        self.title = title

        self.fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.02,
            row_heights=[0.9, 0.1],
        )

        self._legend_flags = {
            "Entry": False,
            "TP1": False,
            "custom_SL": False,
            "custom_TP": False,
            "manual_exit": False,
        }



    # -------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------
    def plot(self):
        self._add_candles()
        self._add_pivots()

        if self.trades is not None and not self.trades.empty:
            self._add_trades()

        self._add_zones()
        self._add_extra_series()
        self._add_bool_series()
        self._layout()
        return self.fig

    def save(self, path: str):
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        try:
            self.fig.write_image(path)
        except Exception:
            self.fig.write_html(path.replace(".png", ".html"))

    def show(self):
        self.fig.show(renderer="browser")

    # -------------------------------------------------
    # INTERNALS
    # -------------------------------------------------
    def _add_pivots(self):
        pivot_sources = [
            ('pivot', {
                3: {'color': 'red', 'label': 'HH'},
                4: {'color': 'green', 'label': 'LL'},
                5: {'color': 'red', 'label': 'LH'},
                6: {'color': 'green', 'label': 'HL'},
            })
        ]

        df = self.df.reset_index(drop=True)

        for pivot_col, pivot_map in pivot_sources:
            if pivot_col not in df.columns:
                continue

            for i, row in df.iterrows():
                pivot_val = row.get(pivot_col)
                if pivot_val not in pivot_map:
                    continue

                info = pivot_map[pivot_val]
                start_idx = max(i - 15, 0)
                end_idx = min(start_idx + 30, len(df) - 1)
                x_values = [df['time'].iloc[start_idx], df['time'].iloc[end_idx]]

                y_value = None
                if pivot_val == 3:
                    y_value = row.get('HH')
                elif pivot_val == 4:
                    y_value = row.get('LL')
                elif pivot_val == 5:
                    y_value = row.get('LH')
                elif pivot_val == 6:
                    y_value = row.get('HL')

                if pd.isna(y_value):
                    continue

                self.fig.add_trace(go.Scatter(
                    x=x_values,
                    y=[y_value, y_value],
                    mode='lines+text',
                    line=dict(color=info['color'], width=1.5, dash='dash'),
                    name=info['label'],
                    text=[info['label'], None],
                    textposition='top right',
                    showlegend=False,
                    hoverinfo='text'
                ))

    def _add_candles(self):
        self.fig.add_trace(
            go.Candlestick(
                x=self.df["time"],
                open=self.df["open"],
                high=self.df["high"],
                low=self.df["low"],
                close=self.df["close"],
                name="Price",
            ),
            row=1,
            col=1,
        )

    def _add_trade_marker(
        self,
        x,
        y,
        trade,
        marker_type,
        color,
        symbol,
        showlegend=False,
        pnl=None,
        exit_reason=None,
    ):

        hover = (
            f"Entry tag: {trade.get('entry_tag')}<br>"
            f"Exit tag: {trade.get('exit_tag')}<br>"
            f"Size: {trade['position_size']:.4f}<br>"
            f"PnL: {(pnl if pnl is not None else trade['pnl_usd']):.4f}<br>"
            f"Price: {y:.2f}<br>"
            f"Time: {x}<br>"
        )
        if exit_reason:
            hover += f"Reason: {exit_reason}<br>"

        self.fig.add_trace(
            go.Scatter(
                x=[x],
                y=[y],
                mode="markers",
                name=marker_type,
                marker=dict(color=color, symbol=symbol, size=10),
                showlegend=showlegend,
                hovertemplate=hover + "<extra></extra>",
            ),
            row=1,
            col=1,
        )

    def _connect(self, t0, p0, t1, p1):
        if pd.notna(t0) and pd.notna(t1) and pd.notna(p0) and pd.notna(p1):
            self.fig.add_trace(
                go.Scatter(
                    x=[t0, t1],
                    y=[p0, p1],
                    mode="lines",
                    line=dict(color="gray", dash="dot"),
                    showlegend=False,
                ),
                row=1,
                col=1,
            )

    def _add_trades(self):

        def connect(t0, p0, t1, p1):
            if pd.notna(t0) and pd.notna(t1) and pd.notna(p0) and pd.notna(p1):
                self.fig.add_trace(
                    go.Scatter(
                        x=[t0, t1],
                        y=[p0, p1],
                        mode="lines",
                        line=dict(color="gray", dash="dot"),
                        showlegend=False,
                    ),
                    row=1,
                    col=1,
                )

        for _, t in self.trades.iterrows():

            # =========================
            # ENTRY
            # =========================
            self._add_trade_marker(
                x=t["entry_time"],
                y=t["entry_price"],
                trade=t,
                marker_type="Entry",
                color="black",
                symbol="circle",
                showlegend=not self._legend_flags["Entry"],
            )
            self._legend_flags["Entry"] = True

            # =========================
            # TP1 (jeśli istnieje)
            # =========================
            has_tp1 = pd.notna(t.get("tp1_time")) and pd.notna(t.get("tp1_price"))

            if has_tp1:
                # ENTRY -> TP1
                connect(
                    t["entry_time"], t["entry_price"],
                    t["tp1_time"], t["tp1_price"]
                )

                self._add_trade_marker(
                    x=t["tp1_time"],
                    y=t["tp1_price"],
                    trade=t,
                    marker_type="TP1",
                    color="blue",
                    symbol="square",
                    showlegend=not self._legend_flags["TP1"],
                    pnl=t.get("tp1_pnl"),
                    exit_reason=t.get("tp1_exit_reason"),
                )
                self._legend_flags["TP1"] = True

            # =========================
            # FINAL EXIT (TP2 / SL / BE)
            # =========================
            exit_tag = str(t.get("exit_tag", "")).upper()

            if "TP" in exit_tag:
                color, symbol, key = "blue", "triangle-down", "custom_TP"
            elif "SL" in exit_tag:
                color, symbol, key = "orange", "triangle-up", "custom_SL"
            else:
                color, symbol, key = "gray", "x", "manual_exit"

            # TP1 -> EXIT  OR  ENTRY -> EXIT
            if has_tp1:
                connect(
                    t["tp1_time"], t["tp1_price"],
                    t["exit_time"], t["exit_price"]
                )
            else:
                connect(
                    t["entry_time"], t["entry_price"],
                    t["exit_time"], t["exit_price"]
                )

            self._add_trade_marker(
                x=t["exit_time"],
                y=t["exit_price"],
                trade=t,
                marker_type=key,
                color=color,
                symbol=symbol,
                showlegend=not self._legend_flags[key],
            )
            self._legend_flags[key] = True

    def _add_zones(self):
        for zones, default_color in [
            (self.bullish_zones, "rgba(33,150,243,0.3)"),
            (self.bearish_zones, "rgba(255,152,0,0.3)"),
        ]:
            if not zones:
                continue

            for zone in zones:
                # OBSŁUGA OBU FORMATÓW
                if len(zone) == 2:
                    zone_name, zdf = zone
                    fillcolor = default_color
                elif len(zone) == 3:
                    zone_name, zdf, fillcolor = zone
                else:
                    raise ValueError(f"Invalid zone format: {zone}")

                if zdf is None or zdf.empty:
                    continue

                for i, r in zdf.iterrows():
                    x0 = r["time"]
                    x1 = (
                        r["validate_till_time"]
                        if pd.notna(r.get("validate_till_time"))
                        else self.df["time"].iloc[-1]
                    )

                    self.fig.add_trace(
                        go.Scatter(
                            x=[x0, x1, x1, x0, x0],
                            y=[
                                r["low_boundary"],
                                r["low_boundary"],
                                r["high_boundary"],
                                r["high_boundary"],
                                r["low_boundary"],
                            ],
                            fill="toself",
                            fillcolor=fillcolor,
                            line=dict(width=0),
                            mode="lines",
                            name=zone_name if i == 0 else None,
                            showlegend=(i == 0),
                            opacity=0.4,
                            hoverinfo="skip",
                        ),
                        row=1,
                        col=1,
                    )

    def _add_extra_series(self):
        if self.extra_series:
            for extra in self.extra_series:
                if len(extra) == 4:
                    name, series, color, dash = extra
                    line_style = dict(color=color, dash=dash)
                elif len(extra) == 3:
                    name, series, color = extra
                    line_style = dict(color=color)
                else:
                    name, series = extra
                    line_style = dict()

                self.fig.add_trace(
                    go.Scatter(
                        x=self.df["time"],
                        y=series,
                        mode="lines",
                        name=name,
                        line=line_style,
                    ),
                    row=1,
                    col=1,
                )

    def _add_bool_series(self):
        for name, series, color in self.bool_series:
            self.fig.add_trace(
                go.Bar(
                    x=self.df["time"],
                    y=series.astype(int),
                    name=name,
                    marker_color=color,
                    opacity=0.5,
                ),
                row=2,
                col=1,
            )

    def _add_pivots(self):
        if "pivot_15" not in self.df.columns:
            return
        # (tu możesz wkleić swoją logikę pivotów praktycznie 1:1)

    def _layout(self):
        self.fig.update_layout(
            title=self.title,
            xaxis_rangeslider_visible=False,
            height=800,
        )
