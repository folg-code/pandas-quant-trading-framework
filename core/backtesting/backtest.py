import pandas as pd
from pandas import DataFrame
import config
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

from Strategies.universal.position_sizer import position_sizer, get_pip_value


def vectorized_backtest(
        df: pd.DataFrame,
        symbol: str,
        slippage: float,
        initial_size: float,
        max_size: float
) -> pd.DataFrame:

    if symbol is not None:
        return _vectorized_backtest_single_symbol(
            df,
            symbol,
            slippage,
            initial_size, max_size
        )

    all_trades = []
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = []
        for sym, group_df in df.groupby('symbol'):
            # Przekazujemy wszystkie argumenty
            futures.append(executor.submit(
                _vectorized_backtest_single_symbol,
                group_df.copy(), sym,
                slippage, initial_size, max_size
            ))

        for future in as_completed(futures):
            try:
                trades = future.result()
                all_trades.append(trades)
            except Exception as e:
                print(f"❌ Błąd w backteście: {e}")

    return pd.concat(all_trades).sort_values(by='exit_time') if all_trades else pd.DataFrame()


def _vectorized_backtest_single_symbol(
        df: pd.DataFrame,
        symbol: str,
        slippage: float,
        initial_size: float,
        max_size: float
) -> pd.DataFrame:

    df = df.copy().reset_index(drop=False)
    trades = []
    blocked_tags = set()
    print("🚀 Init: _vectorized_backtest_single_symbol")

    active_tags = set()

    for direction in ['long', 'short']:

        entries_pos = df.index[
            df['signal_entry'].apply(lambda x: isinstance(x, dict) and x.get('direction') == direction)
        ].tolist()

        exits_pos = df.index[
            df['signal_exit'].apply(lambda x: isinstance(x, dict) and x.get('direction') == direction)
        ].tolist()

        executed_trades = []

        for entry_pos in entries_pos:
            entry_row = df.loc[entry_pos]
            entry_signal = entry_row['signal_entry']
            entry_tag = entry_signal.get("tag") if isinstance(entry_signal, dict) else str(entry_signal)
            entry_time = entry_row['time']
            levels = entry_row.get('levels', None)

            if isinstance(levels, dict):
                sl = levels.get("SL") or levels.get("sl") or levels.get("stop") or levels.get(0)
                tp1 = levels.get("TP1") or levels.get("tp1") or levels.get(1)
                tp2 = levels.get("TP2") or levels.get("tp2") or levels.get(2)



            if any(t['enter_tag'] == entry_tag and t['exit_time'] > entry_time for t in executed_trades):
                continue

            min_time_gap = pd.Timedelta(minutes=30)

            #if any(abs(entry_time - t['entry_time']) < min_time_gap for t in trades if t['direction'] == direction):
            # continue

            # --- Kierunek & cena wejścia ---
            entry_price = (
                entry_row['close'] * (1 + slippage)
                if direction == 'long'
                else entry_row['close'] * (1 - slippage)
            )

            position_size = position_sizer(
                entry_price,
                sl["level"],
                max_risk = 0.005,
                account_size= config.INITIAL_BALANCE,
                symbol=symbol)
            avg_entry_price = entry_price
            current_sl = sl["level"]
            exit_price = None
            exit_time = None
            exit_reason = None
            tp1_price = None
            tp1_time = None
            tp1_executed = False
            tp1_exit_reason = None
            pnl_total = 0

            tp1_pnl = None

            update_sl_next_bar = False

            # --- Pętla po kolejnych świecach ---
            for i in range(entry_pos + 1, len(df)):
                row = df.iloc[i]
                high, low, close = row['high'], row['low'], row['close']
                time = row['time']

                candle_range = row['high'] - row['low']
                lower_shadow = row[['close', 'open']].min() - row['high']
                upper_shadow = row['high'] - row[['close', 'open']].max()
                is_green = row['close'] > row['open']
                is_red = row['close'] < row['open']

                small_upper_shadow = (upper_shadow / candle_range) < 0.35 if candle_range != 0 else False
                small_lower_shadow = (lower_shadow / candle_range) < 0.35 if candle_range != 0 else False

                no_exit_long = is_green & small_upper_shadow
                no_exit_short = is_red & small_lower_shadow

                # Aktualizacja SL po TP1
                if update_sl_next_bar:
                    current_sl = (
                        avg_entry_price + (0.01 * row['atr'])
                        if direction == 'long'
                        else avg_entry_price - (0.01 * row['atr'])
                    )
                    update_sl_next_bar = False

                # --- LONG logic ---
                if direction == 'long':
                    if not tp1_executed and high >= tp1['level'] and not no_exit_long:
                        tp1_price = close
                        tp1_time = time
                        tp1_exit_reason = tp1['tag']
                        tp1_pnl = (tp1_price - avg_entry_price) * (position_size * 0.5)
                        position_size *= 0.5
                        tp1_executed = True
                        sl_exit_tag = tp1['tag']
                        update_sl_next_bar = True

                    if low <= current_sl:
                        exit_price = current_sl
                        exit_time = time
                        if tp1_executed == True:
                            exit_reason = "BE after TP1"
                        else:
                            exit_reason = sl['tag']

                        break

                    if high >= tp2['level'] and not no_exit_long:
                        exit_price = close
                        exit_reason = tp2['tag']
                        exit_time = time
                        break

                # --- SHORT logic ---
                elif direction == 'short':
                    if not tp1_executed and low <= tp1['level'] and not no_exit_short:
                        tp1_price = close
                        tp1_time = time
                        tp1_exit_reason = tp1['tag']
                        tp1_pnl = (avg_entry_price - tp1_price) * (position_size * 0.5)
                        position_size *= 0.5
                        tp1_executed = True
                        sl_exit_tag = tp2['tag']
                        update_sl_next_bar = True

                    if high >= current_sl:
                        exit_price = current_sl
                        exit_reason = sl['tag']
                        exit_time = time
                        break

                    if low <= tp2['level'] and not no_exit_short:
                        exit_price = close
                        exit_reason = tp2['tag']
                        exit_time = time
                        break

            if exit_price is None:
                exit_price = df.iloc[-1]['close'] * (1 - slippage) if direction == 'long' else df.iloc[-1]['close'] * (
                            1 + slippage)
                exit_time = df.iloc[-1]['time']
                exit_reason = 'end_of_data'

            if direction == 'long':
                if tp1_executed:
                    pnl_total = (((tp1['level'] - avg_entry_price) * 0.5) + ((exit_price - avg_entry_price) * 0.5))
                else:
                    pnl_total = exit_price - avg_entry_price
            else:
                if tp1_executed:
                    pnl_total = (((avg_entry_price - tp1['level']) * 0.5) + ((avg_entry_price - exit_price) * 0.5))
                else:
                    pnl_total = (avg_entry_price - exit_price)

            if pnl_total < 0:
                blocked_tags.add(entry_signal['tag'])
            elif pnl_total > 0 and blocked_tags:
                blocked_tags.clear()

            active_tags.discard(entry_signal.get("tag"))

            trades.append({
                'symbol': symbol,
                'direction': direction,
                'entry_time': entry_time,
                'exit_time': exit_time,
                'entry_price': avg_entry_price,
                'exit_price': exit_price,
                'position_size': position_size,
                'pnl': pnl_total,
                'exit_reason': exit_reason,
                'entry_tag': entry_tag,
                'exit_tag': exit_reason,
                'tp1_price': tp1_price,
                'tp1_time': tp1_time,
                'tp1_exit_reason': tp1_exit_reason,
                'tp2_price': tp2 if exit_reason == tp2['tag'] else None,
                'tp2_time': exit_time if exit_reason == tp2['tag'] else None,
                'tp1_pnl': tp1_pnl
            })

            executed_trades.append({
                'enter_tag': entry_tag,
                'exit_time': exit_time
            })

    print(f"✅ Finished backtest for {symbol}, {len(trades)} trades.")

    return pd.DataFrame(trades)