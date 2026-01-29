from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import json
import shutil


class DashboardRenderer:
    """
    Renders RiskReport output into a single-page HTML dashboard.
    NO computations. Layout handled in HTML/CSS.
    """

    def __init__(self):
        base = Path(__file__).parent
        self.template_dir = base / "templates"
        self.static_dir = base / "static"
        self.output_dir = Path("dashboard_output")
        self.output_dir.mkdir(exist_ok=True)

        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True,
        )

    def render(self, report_data: dict, ctx) -> Path:
        template = self.env.get_template("dashboard.html")

        html = template.render(
            report=report_data,
            report_json=json.dumps(
                {
                    **report_data,
                    "__equity__": {
                        "time": ctx.trades["entry_time"].astype(str).tolist(),
                        "equity": ctx.trades["equity"].tolist(),
                        "drawdown": ctx.trades["drawdown"].tolist(),
                    }
                },
                default=str
            ),
        )

        out = self.output_dir / "dashboard.html"
        out.write_text(html, encoding="utf-8")

        self._copy_static()
        return out

    def _copy_static(self):

        target = self.output_dir / "static"
        if target.exists():
            shutil.rmtree(target)

        shutil.copytree(self.static_dir, target)
