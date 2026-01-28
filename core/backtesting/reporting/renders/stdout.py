from rich.console import Console
from rich.pretty import Pretty
from rich.table import Table
from rich.panel import Panel


# ==================================================
# COLUMN ALIASES
# ==================================================

TAG_TABLE_COLUMN_ALIASES = {
    # Common
    "Tag": "Tag",
    "Context": "Ctx",

    # Performance
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

    # Exit / Drawdown
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
    "Win rate": "WR",
    "Total PnL": "PnL",
}


# ==================================================
# STDOUT RENDERER
# ==================================================

class StdoutRenderer:
    """
    Generic section-based stdout renderer.

    Contract:
    - Section returns either:
        * dict (Pretty-printed)
        * { "rows": [...], "sorted_by": ... }  -> tag table
        * { key: { "rows": [...] }, ... }      -> conditional tables
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

        # --- Tag-style tables (entry / exit / drawdown rows) ---
        if name in {
            "Performance by Entry Tag",
            "Exit Logic Diagnostics",
        }:
            self._render_tag_table(payload)

        elif name == "Drawdown Structure & Failure Modes":

            self._render_drawdown_section(payload)

        elif name == "Capital & Exposure Analysis":

            self._render_capital_exposure_section(payload)

        # --- Conditional multi-tables ---
        elif name in {
            "Conditional Expectancy Analysis",
            "Conditional Entry Tag Performance",
        }:
            self._render_conditional_tables(payload)

        # --- Fallback ---
        else:
            self.console.print(Pretty(payload, expand_all=True))

    # ==================================================
    # TAG TABLE RENDERER
    # ==================================================

    def _render_tag_table(self, payload: dict):

        rows = payload.get("rows", [])
        if not rows:
            self.console.print("[italic]No data[/italic]")
            return

        table = Table(
            show_header=True,
            header_style="bold magenta",
            box=None,
            show_lines=False
        )

        raw_columns = list(rows[0].keys())

        # Apply aliases
        columns = [
            TAG_TABLE_COLUMN_ALIASES.get(col, col)
            for col in raw_columns
        ]

        # Columns
        for col in columns:
            table.add_column(
                col,
                justify="right",
                no_wrap=True
            )

        # Rows
        for row in rows:
            table.add_row(
                *[self._fmt(row[col]) for col in raw_columns]
            )

        self.console.print(table)

        sorted_by = payload.get("sorted_by")
        if sorted_by:
            alias = TAG_TABLE_COLUMN_ALIASES.get(sorted_by, sorted_by)
            self.console.print(f"[italic]Sorted by: {alias}[/italic]")

    # ==================================================
    # CONDITIONAL TABLES RENDERER
    # ==================================================

    def _render_capital_exposure_section(self, payload: dict):

        # ==========================
        # SUMMARY
        # ==========================
        summary = payload.get("Summary", {})
        if summary:
            self.console.print("\n[bold]Summary[/bold]")
            for k, v in summary.items():
                self.console.print(f"{k}: {self._fmt(v)}")

        # ==========================
        # OVERTRADING TABLE
        # ==========================
        over = payload.get("Overtrading diagnostics")
        if not over:
            return

        rows = over.get("rows", [])
        if not rows:
            return

        self.console.print("\n[bold]Overtrading diagnostics[/bold]")

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
        # SUMMARY
        # ==========================
        summary = payload.get("Summary", {})
        if summary:
            self.console.print("\n[bold]Summary[/bold]")
            for k, v in summary.items():
                self.console.print(f"{k}: {self._fmt(v)}")

        # ==========================
        # FAILURE MODES TABLE
        # ==========================
        failure = payload.get("Failure modes")
        if not failure:
            return

        rows = failure.get("rows", [])
        if not rows:
            return

        self.console.print("\n[bold]Failure modes[/bold]")

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
        """
        Renders multiple conditional expectancy tables.
        Each key in payload is a separate condition block.
        """

        for title, block in payload.items():
            rows = block.get("rows", [])
            if not rows:
                continue

            self.console.print(f"\n[bold]{title}[/bold]")

            table = Table(
                show_header=True,
                header_style="bold magenta",
                box=None
            )

            raw_columns = list(rows[0].keys())

            # Apply aliases
            columns = [
                CONDITIONAL_COLUMN_ALIASES.get(col, col)
                for col in raw_columns
            ]

            for col in columns:
                table.add_column(col, justify="right", no_wrap=True)

            for row in rows:
                table.add_row(
                    *[self._fmt(row[col]) for col in raw_columns]
                )

            self.console.print(table)

            sorted_by = block.get("sorted_by")
            if sorted_by:
                alias = CONDITIONAL_COLUMN_ALIASES.get(sorted_by, sorted_by)
                self.console.print(f"[italic]Sorted by: {alias}[/italic]")

    # ==================================================
    # FORMATTER
    # ==================================================

    def _fmt(self, v):
        if v is None:
            return "-"
        if isinstance(v, float):
            return f"{v:,.4f}"
        return str(v)