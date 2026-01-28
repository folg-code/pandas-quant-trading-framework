from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


class StdoutRenderer:
    def __init__(self):
        self.console = Console()

    def render(self, report_data: dict):

        self._render_global(report_data["global"])
        self._render_by_context(report_data["by_context"])

    # ==================================================
    # GLOBAL METRICS
    # ==================================================

    def _render_global(self, metrics: dict):

        table = Table(
            title="Global Risk Metrics",
            show_header=True,
            header_style="bold cyan",
            box=None
        )

        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        for name, value in metrics.items():
            table.add_row(
                name,
                self._fmt(value)
            )

        self.console.print()
        self.console.print(Panel(table, title="GLOBAL", expand=False))

    # ==================================================
    # CONTEXTUAL METRICS
    # ==================================================

    def _render_by_context(self, contexts: dict):

        for ctx_name, ctx_data in contexts.items():

            if not ctx_data:
                continue

            self.console.print()
            self.console.print(
                Panel(
                    Text(ctx_name.upper(), justify="center", style="bold"),
                    title="RISK BY CONTEXT",
                    expand=False
                )
            )

            table = Table(
                show_header=True,
                header_style="bold magenta",
                box=None
            )

            table.add_column("Context Value", style="bold")
            for metric_name in next(iter(ctx_data.values())).keys():
                table.add_column(metric_name, justify="right")

            for value, metrics in ctx_data.items():
                table.add_row(
                    str(value),
                    *[self._fmt(v) for v in metrics.values()]
                )

            self.console.print(table)

    # ==================================================
    # FORMATTERS
    # ==================================================

    def _fmt(self, value):

        if value is None:
            return "-"

        if isinstance(value, float):
            return f"{value:,.4f}"

        return str(value)