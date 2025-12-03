import contextlib
import os
from io import StringIO

import config
import numpy as np
from datetime import timedelta
from rich.console import Console
from rich.table import Table


def compute_equity(trades_df, starting_capital=config.INITIAL_BALANCE):
    trades = trades_df.copy()

    print(trades_df['position_size'])

    trades['pnl_points'] = trades['pnl']

    trades['pnl_usd'] = (trades['pnl_points'] * (trades['position_size'] / trades['entry_price'])) * 100000
    trades['capital'] = starting_capital + trades['pnl_usd'].cumsum()

    return trades


def format_duration(seconds):
    return str(timedelta(seconds=round(seconds)))


def summarize_group(df, group_name="TOTAL"):
    total_trades = len(df)
    win_trades = df[df["pnl"] > 0]
    loss_trades = df[df["pnl"] < 0]
    draw_trades = df[df["pnl"] == 0]

    avg_profit_pct = df["returns"].mean() * 100
    total_profit = df["pnl_usd"].sum()
    sum_win = win_trades["pnl_usd"].sum()
    sum_loss = loss_trades["pnl_usd"].sum()
    total_return_pct = df["returns"].sum() * 100
    avg_duration = df["duration_sec"].mean()
    win_pct = len(win_trades) / total_trades * 100 if total_trades else 0

    avg_win_trade = sum_win / len(win_trades)

    avg_loss_trade = sum_loss / len(loss_trades)

    expectancy = ((win_pct * sum_win / len(win_trades)) - ((1 - win_pct) * (sum_loss / len(loss_trades))))

    if 'capital' in df.columns and df['capital'].notna().any():
        max_capital = df['capital'].max()
        min_capital = df['capital'].min()
        drawdown = max_capital - min_capital
    else:
        max_capital = min_capital = drawdown = ''

    if 'capital' in df.columns and df['capital'].notna().any():
        running_max = df['capital'].cummax()  # skumulowane maksimum do danego momentu
        drawdowns = running_max - df['capital']  # różnica między maksimum a aktualną wartością
        max_drawdown = drawdowns.max()  # maksymalny spadek (drawdown)
    else:
        max_drawdown = None

    drawdown_pct = (running_max - df['capital']) / running_max
    max_drawdown_pct = drawdown_pct.max()

    return [
        group_name,
        total_trades,
        round(avg_profit_pct, 4),
        round(total_profit, 3),
        round(total_return_pct, 2),
        format_duration(avg_duration),
        len(win_trades),
        len(draw_trades),
        len(loss_trades),
        round(win_pct, 1),
        round(avg_win_trade, 2) if avg_win_trade != '' else '',
        round(avg_loss_trade, 2) if avg_loss_trade != '' else '',
        round(expectancy, 2) if drawdown != '' else '',

    ]


def print_group_stats(df, group_col, title):
    console = Console()
    table = Table(title=title)

    headers = [group_col.capitalize(), "Trades", "Avg Profit %", "Tot Profit USD", "Tot Profit %", "Avg Duration",
               "Win", "Draw", "Loss", "Win%", "Avg Winner", "Avg Losser", "exp"]
    for header in headers:
        table.add_column(header, justify="center")

    grouped = df.groupby(group_col)

    # Przygotuj listę statystyk grup, potem posortuj po 'Tot Profit USD' (index 3)
    stats_list = []
    for name, group in grouped:
        stats = summarize_group(group, str(name))
        stats_list.append(stats)

    # Sortujemy malejąco po Total Profit USD (index 3)
    stats_list.sort(key=lambda x: float(x[3]), reverse=True)

    # Dodajemy posortowane wiersze
    for stats in stats_list:
        table.add_row(*map(str, stats))

    # Dodajemy sumę na końcu, pogrubioną
    total_stats = summarize_group(df)
    table.add_row(*map(str, total_stats), style="bold")

    console.print(table)


def print_final_raport(df, group_col, title):
    console = Console()
    table = Table(title=title)

    headers = [group_col.capitalize(), "Trades", "Avg Profit %", "Tot Profit USD", "Tot Profit %", "Avg Duration",
               "Win", "Draw", "Loss", "Win%", "Max Balance", "Min Balance", "Drawdown", "Avg Winner", "Avg Losser",
               "exp"]
    for header in headers:
        table.add_column(header, justify="center")

    grouped = df.groupby(group_col)
    for name, group in grouped:
        stats = summarize_group(group, str(name))
        table.add_row(*map(str, stats))

    total_stats = summarize_group(df)
    table.add_row(*map(str, total_stats), style="bold")
    console.print(table)


def print_summary_metrics(df, initial_balance=3000):
    console = Console()
    df = df.sort_values("exit_time").copy()
    df["balance"] = df["pnl_usd"].cumsum() + initial_balance

    start_date = df["exit_time"].min()
    end_date = df["exit_time"].max()
    n_days = (end_date - start_date).days or 1
    total_trades = len(df)
    final_balance = df["balance"].iloc[-1]
    absolute_profit = final_balance - initial_balance
    total_profit_pct = (absolute_profit / initial_balance) * 100
    cagr = ((final_balance / initial_balance) ** (365 / n_days) - 1) * 100

    daily_returns = df.groupby(df["exit_time"].dt.date)["returns"].sum()
    sharpe = sortino = 0
    if not daily_returns.empty:
        std_daily = daily_returns.std()
        mean_daily = daily_returns.mean()
        sharpe = mean_daily / std_daily * np.sqrt(365) if std_daily else 0
        sortino = mean_daily / daily_returns[daily_returns < 0].std() * np.sqrt(365) if (daily_returns < 0).any() else 0

    max_balance = df["balance"].max()
    min_balance = df["balance"].min()
    if 'balance' in df.columns and df['balance'].notna().any():
        running_max = df['balance'].cummax()  # skumulowane maksimum do danego momentu
        drawdowns = running_max - df['balance']  # różnica między maksimum a aktualną wartością
        max_drawdown = drawdowns.max()  # maksymalny spadek (drawdown)
        drawdown_pct = drawdowns / df['balance']
        max_drawdown_pct = drawdown_pct.max() * 100

    else:
        max_drawdown = None

    avg_stake = df["position_size"].mean() if "position_size" in df.columns else np.nan
    total_volume = df["position_size"].sum() if "position_size" in df.columns else np.nan
    best_trade = df[df['returns'] == df['returns'].max()].iloc[0]
    worst_trade = df[df['returns'] == df['returns'].min()].iloc[0]

    # Największa dzienna strata w procentach
    worst_day_loss_pct = daily_returns.min() * 100

    daily_pnl_usd = df.groupby(df["exit_time"].dt.date)["pnl_usd"].sum()
    worst_day_loss_usd = daily_pnl_usd.min()

    total_trades = len(df)
    win_trades = df[df["pnl"] > 0]
    loss_trades = df[df["pnl"] < 0]
    draw_trades = df[df["pnl"] == 0]

    avg_profit_pct = df["returns"].mean() * 100
    total_profit = df["pnl_usd"].sum()
    sum_win = win_trades["pnl_usd"].sum()
    sum_loss = loss_trades["pnl_usd"].sum()
    total_return_pct = df["returns"].sum() * 100
    avg_duration = df["duration_sec"].mean()
    win_pct = len(win_trades) / total_trades * 100 if total_trades else 0

    win_ratio = len(win_trades) / total_trades if total_trades else 0
    loss_ratio = 1 - win_ratio
    avg_win = sum_win / len(win_trades) if len(win_trades) else 0
    avg_loss = abs(sum_loss / len(loss_trades)) if len(loss_trades) else 0

    expectancy = (win_ratio * avg_win) - (loss_ratio * avg_loss)

    exp_ratio = expectancy / avg_profit_pct

    table = Table(title="SUMMARY METRICS")
    table.add_column("Metric", justify="left")
    table.add_column("Value", justify="right")

    table.add_row("Backtesting from", str(start_date))
    table.add_row("Backtesting to", str(end_date))
    table.add_row("Total/Daily Avg Trades", f"{total_trades} / {round(total_trades / n_days, 2)}")
    table.add_row("Starting balance", f"{round(initial_balance, 0)} USD")
    table.add_row("Final balance", f"{final_balance:.2f} USD")
    table.add_row("Absolute profit", f"{absolute_profit:.2f} USD")
    table.add_row("Total profit %", f"{total_profit_pct:.2f}%")
    table.add_row("CAGR %", f"{cagr:.2f}%")
    table.add_row("Sortino", f"{sortino:.2f}")
    table.add_row("Sharpe", f"{sharpe:.2f}")
    table.add_row("Profit factor",
                  f"{-df[df['pnl_usd'] > 0]['pnl_usd'].sum() / df[df['pnl_usd'] < 0]['pnl_usd'].sum():.2f}" if (
                              df["pnl_usd"] < 0).any() else "∞")
    table.add_row("Expectancy (Ratio)", f"{expectancy:.2f} ({exp_ratio:.2f})")
    table.add_row("Avg. daily profit %", f"{(df['returns'].sum() / n_days * 100):.2f}%")
    table.add_row("Avg. stake amount", f"{avg_stake:.2f} USD" if not np.isnan(avg_stake) else "-")
    table.add_row("Total trade volume", f"{total_volume:.2f} USD" if not np.isnan(total_volume) else "-")
    table.add_row("Best trade", f"{str(best_trade.get('pair', '-'))}: {best_trade['returns'] * 100:.2f}%")
    table.add_row("Worst trade", f"{worst_trade.get('pair', '-')}: {worst_trade['returns'] * 100:.2f}%")
    table.add_row("Min balance", f"{min_balance:.2f} USD")
    table.add_row("Max balance", f"{max_balance:.2f} USD")
    table.add_row("Absolute Drawdown", f"{max_drawdown:.2f} USD")
    table.add_row("Max % underwater", f"{max_drawdown_pct:.2f}%")
    table.add_row("Max daily loss $", f"{worst_day_loss_usd:.2f}$")
    table.add_row("Max daily loss %", f"{worst_day_loss_pct:.2f}%")

    console.print(table)


def print_weekday_profitability(df):
    console = Console()
    df = df.copy()
    df["date"] = df["exit_time"].dt.date
    df["weekday"] = df["exit_time"].dt.day_name()

    # Grupujemy PnL dziennie
    daily_grouped = df.groupby(["date", "weekday"])["pnl_usd"].sum().reset_index()

    full_stats = []
    trimmed_stats = []

    for weekday in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        wd_data = daily_grouped[daily_grouped["weekday"] == weekday]

        if wd_data.empty:
            continue

        pnl_list = wd_data["pnl_usd"].tolist()
        total_days = len(pnl_list)
        avg_pnl = np.mean(pnl_list)
        std_pnl = np.std(pnl_list)
        win_pct = (wd_data["pnl_usd"] > 0).mean() * 100

        full_stats.append({
            "weekday": weekday,
            "count": total_days,
            "avg_pnl": avg_pnl,
            "std_pnl": std_pnl,
            "win_pct": win_pct
        })

        # 🧹 Usuwamy najlepszy i najgorszy dzień
        if total_days > 2:
            trimmed = wd_data.sort_values("pnl_usd")[1:-1]
            trimmed_pnls = trimmed["pnl_usd"].tolist()
            trimmed_avg = np.mean(trimmed_pnls)
            trimmed_std = np.std(trimmed_pnls)
            trimmed_win_pct = (trimmed["pnl_usd"] > 0).mean() * 100
        else:
            trimmed_avg = trimmed_std = trimmed_win_pct = 0

        trimmed_stats.append({
            "weekday": weekday,
            "count": len(trimmed_pnls) if total_days > 2 else 0,
            "avg_pnl": trimmed_avg,
            "std_pnl": trimmed_std,
            "win_pct": trimmed_win_pct
        })

    def render_table(data, title):
        table = Table(title=title)
        table.add_column("Weekday", justify="left")
        table.add_column("Days", justify="center")
        table.add_column("Avg PnL", justify="right")
        table.add_column("Std Dev", justify="right")
        table.add_column("Win %", justify="right")

        for row in data:
            table.add_row(
                row["weekday"],
                str(row["count"]),
                f"{row['avg_pnl']:.2f}",
                f"{row['std_pnl']:.2f}",
                f"{row['win_pct']:.1f}%",
            )
        console.print(table)

    render_table(full_stats, "📊 WEEKDAY PROFITABILITY (ALL DAYS)")
    render_table(trimmed_stats, "📉 WEEKDAY PROFITABILITY (WITHOUT BEST & WORST DAY PER WEEKDAY)")


def print_hourly_profitability(df, time_col="entry_time"):
    console = Console()
    df = df.copy()
    df["hour"] = df[time_col].dt.hour

    hourly_grouped = df.groupby(["hour"])[
        "pnl_usd"
    ].sum().reset_index(name="pnl_sum")

    # Tworzymy mapping z godziną do listy dziennych PnL
    hourly_raw = (
        df.assign(date=df[time_col].dt.date, hour=df[time_col].dt.hour)
        .groupby(["date", "hour"])["pnl_usd"]
        .sum()
        .reset_index()
        .rename(columns={"pnl_usd": "pnl"})
    )
    hourly_raw.columns = ["date", "hour", "pnl"]

    full_stats = []
    trimmed_stats = []

    for hour in range(24):
        hour_data = hourly_raw[hourly_raw["hour"] == hour]
        if hour_data.empty:
            continue

        pnl_list = hour_data["pnl"].tolist()
        total_periods = len(pnl_list)
        avg_pnl = np.mean(pnl_list)
        std_pnl = np.std(pnl_list)
        win_pct = (hour_data["pnl"] > 0).mean() * 100

        full_stats.append({
            "hour": hour,
            "count": total_periods,
            "avg_pnl": avg_pnl,
            "std_pnl": std_pnl,
            "win_pct": win_pct
        })

        # 🧹 Usuwamy najlepszy i najgorszy wynik
        if total_periods > 2:
            trimmed = hour_data.sort_values("pnl")[1:-1]
            trimmed_pnls = trimmed["pnl"].tolist()
            trimmed_avg = np.mean(trimmed_pnls)
            trimmed_std = np.std(trimmed_pnls)
            trimmed_win_pct = (trimmed["pnl"] > 0).mean() * 100
        else:
            trimmed_avg = trimmed_std = trimmed_win_pct = 0

        trimmed_stats.append({
            "hour": hour,
            "count": len(trimmed_pnls) if total_periods > 2 else 0,
            "avg_pnl": trimmed_avg,
            "std_pnl": trimmed_std,
            "win_pct": trimmed_win_pct
        })

    def render_table(data, title):
        table = Table(title=title)
        table.add_column("Hour", justify="center")
        table.add_column("Periods", justify="center")
        table.add_column("Avg PnL", justify="right")
        table.add_column("Std Dev", justify="right")
        table.add_column("Win %", justify="right")

        for row in data:
            table.add_row(
                f"{row['hour']:02d}:00",
                str(row["count"]),
                f"{row['avg_pnl']:.2f}",
                f"{row['std_pnl']:.2f}",
                f"{row['win_pct']:.1f}%",
            )
        console.print(table)

    title_prefix = "ENTRY" if time_col == "entry_time" else "EXIT"
    render_table(full_stats, f"⏱ {title_prefix} HOUR PROFITABILITY (ALL)")
    render_table(trimmed_stats, f"🧹 {title_prefix} HOUR PROFITABILITY (TRIMMED)")


def print_backtest_report(trades_df, processed_df):
    trades_df = trades_df.copy()
    trades_df["returns"] = trades_df["pnl"] / trades_df["entry_price"]
    trades_df["duration_sec"] = (trades_df["exit_time"] - trades_df["entry_time"]).dt.total_seconds()

    print_group_stats(trades_df, "entry_tag", "ENTER TAG STATS")
    print_group_stats(trades_df, "exit_tag", "EXIT REASON STATS")

    # ✅ Nowa tabela: tylko dla tradów które osiągnęły TP1
    tp1_trades = trades_df[trades_df["tp1_price"].notna()]
    if not tp1_trades.empty:
        # Zmiana duration_sec: tylko do TP1
        tp1_trades["duration_sec"] = (tp1_trades["tp1_time"] - tp1_trades["entry_time"]).dt.total_seconds()

        # Zmiana returns: tylko część TP1 (0.5 pozycji)
        tp1_trades["returns"] = np.where(
            tp1_trades["direction"] == "long",
            (tp1_trades["tp1_price"] - tp1_trades["entry_price"]) / tp1_trades["entry_price"] * 0.5,
            (tp1_trades["entry_price"] - tp1_trades["tp1_price"]) / tp1_trades["entry_price"] * 0.5
        )

        print_group_stats(tp1_trades, "entry_tag", "ENTER TAG STATS for trades that HIT TP1")
        print_group_stats(tp1_trades, "exit_tag", "EXIT STATS for trades that HIT TP1")
    print_final_raport(trades_df, "symbol",
                       f"BACKTESTING REPORT {processed_df['time'].min()} to {processed_df['time'].max()}")
    print_summary_metrics(trades_df, initial_balance=trades_df['capital'].iloc[0])


def save_backtest_report(trades_df, processed_df, filename="results/my_backtest_report.txt"):
    """
    Generuje pełny raport i zapisuje go do pliku tekstowego.
    Tworzy folder, jeśli nie istnieje.
    """
    # Utwórz folder, jeśli nie istnieje
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Przechwycenie wszystkiego co drukuje rich.Console
    buffer = StringIO()
    with contextlib.redirect_stdout(buffer):
        print_backtest_report(trades_df, processed_df)

    # Zapis do pliku
    with open(filename, "w", encoding="utf-8") as f:
        f.write(buffer.getvalue())

    print(f"✅ Raport zapisany do pliku: {filename}")
