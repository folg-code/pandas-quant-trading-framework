from rich.console import Console
from rich.pretty import Pretty
from rich.table import Table
from rich.panel import Panel


# ==================================================
# COLUMN ALIASES
# ==================================================

TAG_TABLE_COLUMN_ALIASES = {
    "Tag": "Tag",
    "Context": "Ctx",

    "Trades": "N",
    "Expectancy (USD)": "EXP",
    "Win rate": "WR [%]",
    "Average win": "AvgWin [USD]",
    "Average loss": "AvgLoss [USD]",
    "Max consecutive wins": "MaxW",
    "Max consecutive losses": "MaxL",
    "Total PnL": "PnL",
    "Contribution to total PnL (%)": "PnL%",
    "Max internal drawdown (USD)": "DD",

    "Depth": "Depth",
    "Duration (trades)": "Dur",
    "Recovery (trades)": "Rec",
    "Trades during DD": "N",
    "PnL during DD": "PnL",
    "Start": "Start",
    "End": "End",
    "DD #": "DD",
}

CONDITIONAL_COLUMN_ALIASES = {
    "hour": "Hour",
    "weekday": "Day",
    "Trades": "N",
    "Expectancy (USD)": "EXP",
    "Win rate": "WR [%]",
    "Total PnL": "PnL",
}


# ==================================================
# STDOUT RENDERER
# ==================================================

class StdoutRenderer:
    """
    Generic section-based stdout renderer.

    NOTE:
    This commit only unifies formatting.
    Section logic and dispatch are unchanged.
    """

    def __init__(self):
        self.console = Console()

    # ==================================================
    # PUBLIC API
    # ==================================================

    def render(self, report_data: dict):
        for section_name, section_payload in report_data.items():
            self._render_section(section_name, section_payload)

    # ==================================================
    # SECTION DISPATCH
    # ==================================================

    def _render_section(self, name: str, payload: dict):

        self.console.print()
        self.console.print(
            Panel.fit(
                f"[bold cyan]{name}[/bold cyan]",
                border_style="cyan"
            )
        )

        if name in {
            "Performance by Entry Tag",
            "Exit Logic Diagnostics",
        }:
            self._render_tag_table(payload)

        elif name == "Drawdown Structure & Failure Modes":
            self._render_drawdown_section(payload)

        elif name == "Capital & Exposure Analysis":
            self._render_capital_exposure_section(payload)

        elif name == "Tail Risk Analysis":
            self._render_tail_risk_section(payload)

        elif name in {
            "Conditional Expectancy Analysis",
            "Conditional Entry Tag Performance",
        }:
            self._render_conditional_tables(payload)

        elif name == "Backtest Configuration & Assumptions":
            self._render_kv_table(payload)

        elif name == "Core Performance Metrics":
            self._render_metric_table(payload)

        elif name == "Trade Distribution & Payoff Geometry":
            self._render_trade_distribution_section(payload)

        else:
            # temporary fallback for sections not yet migrated
            self.console.print(Pretty(payload, expand_all=True))

    # ==================================================
    # TAG TABLE RENDERER
    # ==================================================

    def _render_tag_table(self, payload: dict):

        rows = payload.get("rows", [])
        if not rows:
            self.console.print("[italic]No data[/italic]")
            return

        table = Table(show_header=True, header_style="bold magenta", box=None)

        raw_columns = list(rows[0].keys())
        columns = [TAG_TABLE_COLUMN_ALIASES.get(c, c) for c in raw_columns]

        for col in columns:
            table.add_column(col, justify="right", no_wrap=True)

        for row in rows:
            table.add_row(*[self._fmt(row[c]) for c in raw_columns])

        self.console.print(table)

        sorted_by = payload.get("sorted_by")
        if sorted_by:
            alias = TAG_TABLE_COLUMN_ALIASES.get(sorted_by, sorted_by)
            self.console.print(f"[italic]Sorted by: {alias}[/italic]")

    # ==================================================
    # OTHER RENDERERS
    # ==================================================

    def _render_summary_table(self, summary: dict):

        if not summary:
            return

        table = Table(
            show_header=True,
            header_style="bold magenta",
            box=None,
            show_lines=False,
        )

        # kolumny = klucze
        for col in summary.keys():
            table.add_column(col, justify="right", no_wrap=True)

        # jeden wiersz
        table.add_row(
            *[self._fmt(v) for v in summary.values()]
        )

        self.console.print(table)

    def _render_trade_distribution_section(self, payload: dict):

        for title, block in payload.items():
            rows = block.get("rows", [])
            if not rows:
                continue

            percent_columns = block.get("percent_columns", set())

            self.console.print(f"\n[bold]{title}[/bold]")

            table = Table(box=None, show_header=True)
            columns = list(rows[0].keys())

            for col in columns:
                table.add_column(col, justify="right", no_wrap=True)

            for row in rows:
                table.add_row(
                    *[
                        self._fmt(
                            row[col],
                            pct=col in percent_columns
                        )
                        for col in columns
                    ]
                )

            self.console.print(table)

    def _render_metric_table(self, payload: dict):
        """
        Render flat metric dict as:
        Metric | Value
        """
        table = Table(box=None, show_header=True)
        table.add_column("Metric")
        table.add_column("Value", justify="right")

        for metric, value in payload.items():
            is_pct = "%" in metric
            table.add_row(
                metric,
                self._fmt(value, pct=is_pct)
            )

        self.console.print(table)

    def _render_kv_table(self, payload: dict):
        """
        Render nested dict as a key-value table:
        Section | Parameter | Value
        """
        table = Table(box=None, show_header=True)
        table.add_column("Section", style="bold")
        table.add_column("Parameter")
        table.add_column("Value", justify="right")

        for section, params in payload.items():
            for key, value in params.items():
                table.add_row(
                    section,
                    key,
                    self._fmt(value)
                )

        self.console.print(table)

    def _render_tail_risk_section(self, payload: dict):
        rows = []

        for name, data in payload.items():
            if not isinstance(data, dict):
                continue

            rows.append({
                "Tail": name.replace(" tails", "").replace(" 5%", ""),
                "Q": data.get("Quantile"),
                "Trades": data.get("Trades count"),
                "Average trade PnL": data.get("Average trade PnL"),
                "Total PnL": data.get("Total PnL"),
                "Contribution to total PnL (%)": data.get("Contribution to total PnL (%)"),
                "Worst trade": data.get("Worst trade"),
            })

        self._render_generic_table(rows)

    def _render_capital_exposure_section(self, payload: dict):

        # ==========================
        # SUMMARY TABLE
        # ==========================
        summary = payload.get("Summary", {})
        if summary:
            self.console.print("\n[bold]Summary[/bold]")
            self._render_summary_table(summary)

        # ---- visual spacing ----
        self.console.print()

        # ==========================
        # OVERTRADING TABLE
        # ==========================
        over = payload.get("Overtrading diagnostics")
        if not over:
            return

        rows = over.get("rows", [])
        if not rows:
            return

        self.console.print("[bold]Overtrading diagnostics[/bold]")

        table = Table(
            show_header=True,
            header_style="bold magenta",
            box=None,
            show_lines=False
        )

        raw_columns = list(rows[0].keys())
        columns = [
            TAG_TABLE_COLUMN_ALIASES.get(col, col)
            for col in raw_columns
        ]

        for col in columns:
            table.add_column(col, justify="right", no_wrap=True)

        for row in rows:
            table.add_row(
                *[self._fmt(row[col]) for col in raw_columns]
            )

        self.console.print(table)

        sorted_by = over.get("sorted_by")
        if sorted_by:
            alias = TAG_TABLE_COLUMN_ALIASES.get(sorted_by, sorted_by)
            self.console.print(f"[italic]Sorted by: {alias}[/italic]")

    def _render_drawdown_section(self, payload: dict):

        # ==========================
        # SUMMARY TABLE
        # ==========================
        summary = payload.get("Summary", {})
        if summary:
            self.console.print("\n[bold]Summary[/bold]")
            self._render_summary_table(summary)

        # ---- visual spacing ----
        self.console.print()

        # ==========================
        # FAILURE MODES TABLE
        # ==========================
        failure = payload.get("Failure modes")
        if not failure:
            return

        rows = failure.get("rows", [])
        if not rows:
            return

        self.console.print("[bold]Failure modes[/bold]")

        table = Table(
            show_header=True,
            header_style="bold magenta",
            box=None,
            show_lines=False
        )

        raw_columns = list(rows[0].keys())
        columns = [
            TAG_TABLE_COLUMN_ALIASES.get(col, col)
            for col in raw_columns
        ]

        for col in columns:
            table.add_column(col, justify="right", no_wrap=True)

        for row in rows:
            table.add_row(
                *[self._fmt(row[col]) for col in raw_columns]
            )

        self.console.print(table)

        sorted_by = failure.get("sorted_by")
        if sorted_by:
            alias = TAG_TABLE_COLUMN_ALIASES.get(sorted_by, sorted_by)
            self.console.print(f"[italic]Sorted by: {alias}[/italic]")

    def _render_conditional_tables(self, payload: dict):
        for title, block in payload.items():
            rows = block.get("rows", [])
            if not rows:
                continue

            self.console.print(f"\n[bold]{title}[/bold]")
            self._render_generic_table(rows)

    # ==================================================
    # GENERIC TABLE
    # ==================================================

    def _render_generic_table(self, rows: list[dict]):
        if not rows:
            self.console.print("[italic]No data[/italic]")
            return

        table = Table(show_header=True, header_style="bold magenta", box=None)
        columns = list(rows[0].keys())

        for col in columns:
            table.add_column(col, justify="right", no_wrap=True)

        for row in rows:
            table.add_row(*[self._fmt(row[col]) for col in columns])

        self.console.print(table)

    # ==================================================
    # GLOBAL FORMATTER (SINGLE SOURCE OF TRUTH)
    # ==================================================

    def _fmt(self, v, *, pct: bool = False):
        """
        Backward compatible:
        - if v is materialized dict: return v["display"]
        - else fallback to legacy behavior (temporary during migration)
        """
        if isinstance(v, dict) and "display" in v:
            return v["display"]

        if v is None:
            return "-"

        if isinstance(v, float):
            if pct:
                return f"{v * 100:,.2f}%"
            return f"{v:,.4f}"

        if isinstance(v, int):
            return f"{v:,d}"

        return str(v)
