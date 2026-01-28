from rich.console import Console
from rich.pretty import Pretty
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


class StdoutRenderer:
    """
    Generic section-based stdout renderer.
    Assumes report_data is a dict of:
        { section_name: section_payload }
    """

    def __init__(self):
        self.console = Console()

    def render(self, report_data: dict):

        for section_name, section_payload in report_data.items():
            self._render_section(section_name, section_payload)

    # ==================================================
    # SECTION RENDERING
    # ==================================================

    def _render_section(self, name: str, payload: dict):

        self.console.print()
        self.console.print(
            Panel.fit(
                f"[bold cyan]{name}[/bold cyan]",
                border_style="cyan"
            )
        )

        # Payload is arbitrary nested dict
        self.console.print(Pretty(payload, expand_all=True))