import os
import contextlib
from io import StringIO
from datetime import timedelta
import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table

import pandas as pd
from rich.console import Console
from rich.table import Table
from datetime import timedelta

from config import BACKTEST_MODE


class BacktestReporter:

    def __init__(self, trades: pd.DataFrame, signals: pd.DataFrame, initial_balance: float):
        self.console = Console()
        self.trades = trades.copy()
        self.signals = signals
        self.initial_balance = initial_balance

        self._compute_equity_curve()
        self._prepare_trades()

    # ------------------------------------------------------------------
    # PREPARE
    # ------------------------------------------------------------------
    def _prepare_trades(self):
        required_cols = [
            "symbol", "entry_time", "exit_time",
            "entry_tag", "exit_tag",
            "pnl_usd", "returns",
            "duration"
        ]
        for c in required_cols:
            if c not in self.trades.columns:
                raise ValueError(f"Missing column in trades: {c}")

        # safety
        self.trades["entry_tag"] = self.trades["entry_tag"].fillna("UNKNOWN")
        self.trades["exit_tag"] = self.trades["exit_tag"].fillna("UNKNOWN")


    def _compute_equity_curve(self):
        # Sortowanie po czasie wyjścia
        self.trades = self.trades.sort_values(by="exit_time").reset_index(drop=True)

        # Equity curve wektorowo
        self.trades["equity"] = self.initial_balance + self.trades["pnl_usd"].cumsum()

        # Maksimum, minimum i drawdown
        self.trades["running_max"] = self.trades["equity"].cummax()
        self.trades["drawdown"] = self.trades["running_max"] - self.trades["equity"]
        self.max_balance = self.trades["equity"].max()
        self.min_balance = self.trades["equity"].min()
        self.max_drawdown = self.trades["drawdown"].max()

    def _aggregate_entry_tag(self, df: pd.DataFrame) -> dict:
        trades = len(df)
        if trades == 0:
            return None

        # equity curve per tag
        equity = self.initial_balance + df["pnl_usd"].cumsum()
        running_max = equity.cummax()
        drawdown = (running_max - equity).max()

        wins = df[df["pnl_usd"] > 0]
        losses = df[df["pnl_usd"] < 0]

        win_rate = len(wins) / trades if trades else 0
        avg_win = wins["pnl_usd"].mean() if not wins.empty else 0
        avg_loss = losses["pnl_usd"].mean() if not losses.empty else 0
        expectancy = win_rate * avg_win - (1 - win_rate) * abs(avg_loss)

        # --- TP / SL logic ---

        def parse_exit_tag(tag: str):
            """
            Supports both legacy tags (SL_xxx, TP1_xxx_yyy)
            and new domain tags (SL, TP2, BE, TIMEOUT).
            """

            if not isinstance(tag, str):
                return "UNKNOWN", None, None

            parts = tag.split("_")

            if tag == "SL":
                return "SL", None, "final"

            if tag == "TP2":
                return "TP2", None, "final"

            if tag == "BE":
                return "BE", None, "final"

            if tag == "TIMEOUT":
                return "TIMEOUT", None, "final"

            # ---- legacy fallback ----
            if tag.startswith("SL") and len(parts) >= 2:
                return "SL", parts[1], "final"

            if tag.startswith("TP1") and len(parts) >= 3:
                return "TP1", parts[2], "partial"

            if tag.startswith("TP2") and len(parts) >= 3:
                return "TP2", parts[2], "final"

            return "UNKNOWN", None, None

        df[["exit_event", "sl_source", "exit_stage"]] = df["exit_tag"].apply(
            lambda t: pd.Series(parse_exit_tag(t))
        )

        pct_sl = (df["exit_event"] == "SL").mean() * 100
        pct_be = (df["exit_event"] == "TP1").mean() * 100
        pct_tp2 = (df["exit_event"] == "TP2").mean() * 100

        profit_pct = (equity.iloc[-1] / self.initial_balance - 1) * 100

        return {
            "trades": trades,
            "profit_pct": profit_pct,
            "pct_be": pct_be,
            "pct_tp2": pct_tp2,
            "pct_sl": pct_sl,
            "exp": expectancy,
            "drawdown": drawdown,
        }

    # ------------------------------------------------------------------
    # CORE AGGREGATION LOGIC
    # ------------------------------------------------------------------
    def _aggregate_trades(self, df: pd.DataFrame) -> dict:
        if df.empty:
            return {
                "trades": 0,
                "avg_profit_pct": 0,
                "tot_profit_usd": 0,
                "tot_profit_pct": 0,
                "avg_duration": timedelta(0),
                "win": 0,
                "draw": 0,
                "loss": 0,
                "win_pct": 0,
                "avg_winner": 0,
                "avg_losser": 0,
                "exp": 0,
            }

        wins = df[df["pnl_usd"] > 0]
        losses = df[df["pnl_usd"] < 0]
        draws = df[df["pnl_usd"] == 0]

        effective_trades = len(wins) + len(losses)
        win_rate = (len(wins) / effective_trades) if effective_trades > 0 else 0

        avg_win = wins["pnl_usd"].mean() if not wins.empty else 0
        avg_loss = losses["pnl_usd"].mean() if not losses.empty else 0

        expectancy = win_rate * avg_win - (1 - win_rate) * abs(avg_loss)

        return {
            "trades": len(df),
            "avg_profit_pct": df["returns"].mean() * 100,
            "tot_profit_usd": df["pnl_usd"].sum(),
            "tot_profit_pct": df["returns"].sum() * 100,
            "avg_duration": df["duration"].mean(),
            "win": len(wins),
            "draw": len(draws),
            "loss": len(losses),
            "win_pct": win_rate * 100,
            "avg_winner": avg_win,
            "avg_losser": avg_loss,
            "exp": expectancy,
        }

    # ------------------------------------------------------------------
    # GENERIC GROUP TABLE
    # ------------------------------------------------------------------
    def _print_group_table(self, title: str, group_col: str, df: pd.DataFrame):
        self.console.rule(f"[bold yellow]{title}[/bold yellow]")

        total_df = []
        stats_list = []

        # grupowanie i agregacja
        for name, g in df.groupby(group_col):
            stats = self._aggregate_trades(g)
            stats["name"] = name
            stats_list.append(stats)
            total_df.append(g)

        if not stats_list:
            print("⚠️ Brak danych do wyświetlenia.")
            return

        # sortowanie po tot_profit_usd malejąco
        stats_list = sorted(stats_list, key=lambda x: x["tot_profit_usd"], reverse=True)

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column(str(group_col))
        table.add_column("Trades", justify="right")
        table.add_column("Tot Profit USD", justify="right")
        table.add_column("Tot Profit %", justify="right")
        table.add_column("Avg Duration", justify="center")
        table.add_column("Win", justify="right")
        table.add_column("Draw", justify="right")
        table.add_column("Loss", justify="right")
        table.add_column("Win %", justify="right")
        table.add_column("Avg Winner", justify="right")
        table.add_column("Avg Losser", justify="right")
        table.add_column("Exp", justify="right")

        # dodanie wierszy do tabeli
        for stats in stats_list:
            # formatowanie avg_duration w HH:MM:SS
            avg_duration_str = str(pd.to_timedelta(stats["avg_duration"], unit='s')).split('.')[0]

            table.add_row(
                str(stats["name"]),
                f"{stats['trades']}",
                f"{stats['tot_profit_usd']:.3f}",
                f"{stats['tot_profit_pct']:.2f}",
                avg_duration_str,
                f"{stats['win']}",
                f"{stats['draw']}",
                f"{stats['loss']}",
                f"{stats['win_pct']:.1f}",
                f"{stats['avg_winner']:.2f}",
                f"{stats['avg_losser']:.2f}",
                f"{stats['exp']:.2f}"
            )

        self.console.print(table)

    def _print_summary_metrics(self):
        t = self.trades.sort_values("exit_time")

        start = t["entry_time"].min()
        end = t["exit_time"].max()

        total_trades = len(t)
        days = max((end - start).days, 1)
        trades_per_day = total_trades / days

        final_balance = t["equity"].iloc[-1]
        absolute_profit = final_balance - self.initial_balance
        total_profit_pct = (final_balance / self.initial_balance - 1) * 100
        cagr = ((final_balance / self.initial_balance) ** (365 / days) - 1) * 100

        daily_returns = t.groupby(t["exit_time"].dt.date)["pnl_usd"].sum()
        max_daily_loss = daily_returns.min()
        max_daily_loss_pct = max_daily_loss / self.initial_balance * 100

        equity = t["equity"]
        max_balance = equity.cummax()
        drawdown = max_balance - equity
        max_dd = drawdown.max()
        max_dd_pct = (drawdown / max_balance).max() * 100

        wins = t[t["pnl_usd"] > 0]
        losses = t[t["pnl_usd"] < 0]

        profit_factor = wins["pnl_usd"].sum() / abs(losses["pnl_usd"].sum()) if not losses.empty else float("inf")

        expectancy = self._aggregate_trades(t)["exp"]

        table = Table(title="SUMMARY METRICS", show_header=False)
        table.add_column("Metric")
        table.add_column("Value", justify="right")

        rows = [
            ("Backtesting from", str(start)),
            ("Backtesting to", str(end)),
            ("Total/Daily Avg Trades", f"{total_trades} / {trades_per_day:.1f}"),
            ("Starting balance", f"{self.initial_balance:.2f} USD"),
            ("Final balance", f"{final_balance:.2f} USD"),
            ("Absolute profit", f"{absolute_profit:.2f} USD"),
            ("Total profit %", f"{total_profit_pct:.2f}%"),
            ("CAGR %", f"{cagr:.2f}%"),
            ("Profit factor", f"{profit_factor:.2f}"),
            ("Expectancy", f"{expectancy:.2f}"),
            ("Max balance", f"{max_balance.max():.2f} USD"),
            ("Min balance", f"{equity.min():.2f} USD"),
            ("Absolute Drawdown", f"{max_dd:.2f} USD"),
            ("Max % underwater", f"{max_dd_pct:.2f}%"),
            ("Max daily loss $", f"{max_daily_loss:.2f} USD"),
            ("Max daily loss %", f"{max_daily_loss_pct:.2f}%"),
        ]

        for r in rows:
            table.add_row(*r)

        self.console.print(table)

    # ------------------------------------------------------------------
    # PUBLIC REPORTS
    # ------------------------------------------------------------------
    def print_entry_tag_stats(self):
        self.console.rule("[bold yellow]ENTER TAG STATS[/bold yellow]")

        rows = []

        for tag, g in self.trades.groupby("entry_tag"):
            stats = self._aggregate_entry_tag(g)
            if stats is None:
                continue

            rows.append({
                "entry_tag": tag,
                **stats
            })

        if not rows:
            self.console.print("⚠️ No entry tag data.")
            return

        # 🔑 SORTOWANIE PO TOTAL PROFIT %
        rows = sorted(rows, key=lambda x: x["profit_pct"], reverse=True)

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Entry Tag")
        table.add_column("Trades", justify="right")
        table.add_column("TOT Profit %", justify="right")
        table.add_column("%BE", justify="right")
        table.add_column("%TP2", justify="right")
        table.add_column("%SL", justify="right")
        table.add_column("Exp $", justify="right")
        table.add_column("Max DD $", justify="right")

        for r in rows:
            table.add_row(
                str(r["entry_tag"]),
                f"{r['trades']}",
                f"{r['profit_pct']:.2f}",
                f"{r['pct_be']:.1f}",
                f"{r['pct_tp2']:.1f}",
                f"{r['pct_sl']:.1f}",
                f"{r['exp']:.2f}",
                f"{r['drawdown']:.2f}",
            )

        self.console.print(table)

    def print_exit_reason_stats(self):
        self._print_group_table("EXIT REASON STATS", "exit_tag", self.trades)

    def print_tp1_entry_stats(self):
        df = self.trades[self.trades['tp1_price'].notna()]
        self._print_group_table(
            "ENTER TAG STATS for trades that HIT TP1",
            "entry_tag",
            df
        )

    def print_tp1_exit_stats(self):
        df = self.trades[self.trades['tp1_price'].notna()]
        self._print_group_table(
            "EXIT STATS for trades that HIT TP1",
            "exit_tag",
            df
        )

    def print_symbol_report(self):
        self._print_group_table(
            "BACKTESTING REPORT",
            "symbol",
            self.trades
        )

    def print_entry_tag_split_table(self, mode: str = "filtered"):
        """
        mode:
            - 'filtered' : tylko stabilne / decyzyjne tagi (default)
            - 'all'      : wszystkie tagi (diagnostyka)
        """

        if "window" not in self.trades.columns:
            self.console.print("⚠️ Split report requires 'window' column in trades.")
            return

        self.console.rule(
            "[bold yellow]ENTRY TAG — STABILITY FILTERED[/bold yellow]"
            if mode == "filtered"
            else "[bold yellow]ENTRY TAG — FULL DIAGNOSTIC VIEW[/bold yellow]"
        )

        # --- aggregate ---
        grouped = self.trades.groupby(["entry_tag", "window"])
        data = {}

        for (tag, window), g in grouped:
            stats = self._aggregate_entry_tag(g)
            if stats is None:
                continue
            data.setdefault(tag, {})[window] = stats

        rows = []

        # --- scoring ---
        def score_window(opt, val, fin):
            score = 0.0

            # trades (data reliability)
            if opt and opt["trades"] >= 50:
                score += 1
            if val and val["trades"] >= 30:
                score += 1
            if fin and fin["trades"] >= 30:
                score += 1

            # EV persistence
            if opt and opt["exp"] > 0:
                score += 2
            if val and val["exp"] > 0:
                score += 2
            if fin and fin["exp"] > 0:
                score += 1

            return score

        # --- collect rows ---
        for tag, windows in data.items():
            opt = windows.get("OPT")
            val = windows.get("VAL")
            fin = windows.get("FINAL")

            if not opt:
                continue

            score = score_window(opt, val, fin)

            if mode == "filtered":
                if opt["trades"] < 50:
                    continue
                if val and val["trades"] < 30:
                    continue
                if opt["exp"] <= 0:
                    continue
                if score <= 4:
                    continue

            rows.append((tag, score, opt, val, fin))

        if not rows:
            self.console.print("⚠️ No entry tags to display.")
            return

        # --- sorting ---
        if mode == "filtered":
            rows.sort(key=lambda r: r[1], reverse=True)
        else:
            rows.sort(
                key=lambda r: (
                    -(r[4]["exp"] if r[4] else -1e9),  # FINAL EV first
                    -r[1]  # then stability score
                )
            )

        # --- table ---
        table = Table(show_header=True, header_style="bold magenta")

        table.add_column("Entry Tag", style="bold")
        table.add_column("Score", justify="right")
        table.add_column("Trades OPT", justify="right")
        table.add_column("Trades VAL", justify="right")
        table.add_column("Trades FINAL", justify="right")

        metrics = [
            ("%TP2", "pct_tp2", True),
            ("%SL", "pct_sl", True),
            ("Exp $", "exp", False),
        ]

        for name, _, _ in metrics:
            table.add_column(f"{name} OPT", justify="right")
            table.add_column(f"{name} VAL", justify="right")
            table.add_column(f"{name} FINAL", justify="right")

        def fmt(w, key, pct=False):
            if not w:
                return "—"
            v = w[key]
            return f"{v:.1f}" if pct else f"{v:.2f}"

        # --- render rows ---
        for tag, score, opt, val, fin in rows:
            row = [
                tag,
                f"{score:.1f}",
                str(opt["trades"]),
                str(val["trades"]) if val else "—",
                str(fin["trades"]) if fin else "—",
            ]

            for _, key, pct in metrics:
                row.extend([
                    fmt(opt, key, pct),
                    fmt(val, key, pct),
                    fmt(fin, key, pct),
                ])

            table.add_row(*row)

        self.console.print(table)

    def print_entry_tag_split_report(self):
        """
        ENTRY TAG performance per backtest window (OPT / VAL / FINAL)
        """

        if "window" not in self.trades.columns:
            self.console.print("⚠️ Split report requires 'window' column in trades.")
            return

        self.console.rule("[bold yellow]ENTRY TAG SPLIT PERFORMANCE[/bold yellow]")

        rows = []

        grouped = self.trades.groupby(["entry_tag", "window"])

        # { entry_tag: { window: stats } }
        data = {}

        for (tag, window), g in grouped:
            stats = self._aggregate_entry_tag(g)
            if stats is None:
                continue

            data.setdefault(tag, {})[window] = stats

        for tag, windows in data.items():
            opt = windows.get("OPT")
            val = windows.get("VAL")
            fin = windows.get("FINAL")

            if not opt:
                continue  # bez OPT tag nie istnieje

            row = {
                "entry_tag": tag,
                "opt": opt["profit_pct"],
                "val": val["profit_pct"] if val else None,
                "final": fin["profit_pct"] if fin else None,
                "delta_opt_val": (
                    (val["profit_pct"] - opt["profit_pct"]) if val else None
                ),
                "delta_val_final": (
                    (fin["profit_pct"] - val["profit_pct"]) if fin and val else None
                ),
                "trades": opt["trades"],
            }

            rows.append(row)

        if not rows:
            self.console.print("⚠️ No split entry tag data.")
            return

        # sort: najlepsze OPT na górze
        rows = sorted(rows, key=lambda x: x["opt"], reverse=True)

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Entry Tag")
        table.add_column("OPT %", justify="right")
        table.add_column("VAL %", justify="right")
        table.add_column("FINAL %", justify="right")
        table.add_column("Δ OPT→VAL", justify="right")
        table.add_column("Δ VAL→FINAL", justify="right")
        table.add_column("Trades", justify="right")

        for r in rows:
            table.add_row(
                r["entry_tag"],
                f"{r['opt']:.2f}",
                f"{r['val']:.2f}" if r["val"] is not None else "—",
                f"{r['final']:.2f}" if r["final"] is not None else "—",
                f"{r['delta_opt_val']:.2f}" if r["delta_opt_val"] is not None else "—",
                f"{r['delta_val_final']:.2f}" if r["delta_val_final"] is not None else "—",
                f"{r['trades']}",
            )

        self.console.print(table)

    # ------------------------------------------------------------------
    # RUN ALL REPORTS
    # ------------------------------------------------------------------
    def run(self):

        if BACKTEST_MODE == "single":
            self.console.rule("[bold cyan]SUMMARY METRICS[/bold cyan]")

            self._print_summary_metrics()

            #self.console.rule("[bold cyan]DETAILED REPORTS[/bold cyan]")

            self.print_entry_tag_stats()
            self.print_exit_reason_stats()

            # self.print_tp1_entry_stats()
            # self.print_tp1_exit_stats()
            self.print_symbol_report()
        elif BACKTEST_MODE == "split":
            self.console.rule("[bold cyan]SUMMARY METRICS[/bold cyan]")

            self._print_summary_metrics()

            if "window" in self.trades.columns:
                self.print_entry_tag_split_table(mode="all")

            self.print_exit_reason_stats()
            self.print_symbol_report()


    def save(self, filename: str):
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        buffer = StringIO()
        with contextlib.redirect_stdout(buffer):
            self.run()

        with open(filename, "w", encoding="utf-8") as f:
            f.write(buffer.getvalue())

        print(f"✅ Raport zapisany do pliku: {filename}")
