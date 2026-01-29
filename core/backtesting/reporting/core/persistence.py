from pathlib import Path
from datetime import datetime
import json
import pandas as pd


class ReportPersistence:
    """
    Persist report outputs for dashboards / post-analysis.
    """

    def __init__(self, base_dir: Path = Path("results/reports")):
        self.base_dir = base_dir

    def persist(
        self,
        *,
        trades: pd.DataFrame,
        equity: pd.Series,
        report_data: dict,
        meta: dict | None = None,
    ) -> Path:

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        run_dir = self.base_dir / f"run_{ts}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # ----------------------------
        # trades snapshot
        # ----------------------------
        trades.to_parquet(run_dir / "trades.parquet", index=False)

        # ----------------------------
        # equity snapshot
        # ----------------------------
        equity.to_frame(name="equity").to_parquet(
            run_dir / "equity.parquet"
        )

        # ----------------------------
        # report (JSON)
        # ----------------------------
        with open(run_dir / "report.json", "w") as f:
            json.dump(report_data, f, indent=2, default=str)

        # ----------------------------
        # meta
        # ----------------------------
        meta_payload = meta or {}
        meta_payload["timestamp_utc"] = ts

        with open(run_dir / "meta.json", "w") as f:
            json.dump(meta_payload, f, indent=2)

        return run_dir
