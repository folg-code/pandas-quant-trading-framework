from datetime import datetime, timedelta

import MetaTrader5 as mt5

from Strategies.universal.position_sizer import position_sizer
from core.live_trading.file_manager import load_active_trades, load_blocked_tags, save_active_trades, mark_tp1_hit
from core.live_trading.trade_executor import send_order, close_position, modify_stop_loss

WARNING_COOLDOWN = timedelta(minutes=15)
last_warning_time = {}

def fetch_signals(strategy):
    signals = strategy.run()
    if signals is None:
        return None, None
    latest_row = strategy.df.iloc[-1]
    previous_row = strategy.df.iloc[-2]
    return previous_row.get("signal_entry"), latest_row.get("signal_exit")

def execute_entry_signal(symbol, strategy, signal_entry, logs, tg_msgs):
    if not isinstance(signal_entry, tuple):
        return
    direction, tag = signal_entry
    entry_tag = str(tag)
    active_trades = load_active_trades()
    blocked_tags = load_blocked_tags()
    now = datetime.utcnow()

    if blocked_tags.get(symbol, {}).get(tag) == "blocked":
        logs.append(f"❌ Tag {tag} dla {symbol} jest zablokowany")
        return

    recent_trade = next((t for t in active_trades.values() if t["symbol"]==symbol), None)
    if recent_trade and (now - datetime.fromisoformat(recent_trade["entry_time"])) < timedelta(minutes=30):
        logs.append(f"⏱️ Ostatnia pozycja <30 min temu dla {symbol}")
        return

    latest_row = strategy.df.iloc[-2]
    levels = latest_row.get("levels")
    if not levels or len(levels)!=3:
        logs.append(f"❌ Nieprawidłowe poziomy wejścia dla {symbol}")
        return

    sl, tp1, tp2 = levels[0][1], levels[1][1], levels[2][1]
    lot_size = position_sizer(latest_row["close"], sl, max_risk=0.01, account_size=10000, symbol=symbol)
    if lot_size<=0:
        logs.append(f"⚠️ Lot=0 dla {symbol}")
        return

    result = send_order(symbol, direction, lot_size, sl, tp1, tp2, comment=entry_tag)
    if result and result.retcode == 0:
        active_trades[str(result.order)] = {
            "symbol": symbol,
            "trade_id": int(result.order),
            "open_price": latest_row["close"],
            "entry_time": now.isoformat(),
            "direction": direction,
            "sl": sl, "tp1": tp1, "tp2": tp2,
            "volume": lot_size, "tp1_hit": False, "entry_tag": entry_tag
        }
        save_active_trades(active_trades)
        tg_msgs.append(f"✅ Wysłano zlecenie {symbol} {direction} (lot {lot_size})")

def manage_active_trades(symbol, strategy, logs, tg_msgs):
    active_trades = load_active_trades()
    open_positions = send_order.get_open_positions(symbol)
    for trade_id, trade in list(active_trades.items()):
        pos = next((p for p in open_positions if p.ticket==int(trade_id)), None)
        if not pos: continue
        if not trade["tp1_hit"] and pos.volume>0:
            tp1_price = trade["tp1"]
            tp1_hit = ((pos.type==mt5.ORDER_TYPE_BUY and pos.price_current>=tp1_price)
                       or (pos.type==mt5.ORDER_TYPE_SELL and pos.price_current<=tp1_price))
            if tp1_hit:
                volume_to_close = round(pos.volume/2,2)
                res = close_position(pos, volume=volume_to_close)
                if res and res.retcode==0:
                    trade["volume"] -= volume_to_close
                    trade["tp1_hit"]=True
                    modify_stop_loss(int(trade_id), trade["open_price"])
                    save_active_trades(active_trades)
                    mark_tp1_hit(trade_id)
                    tg_msgs.append(f"✅ TP1 osiągnięty dla {trade['symbol']}")

def run_strategy_and_manage_position(strategy, symbol, logs, tg_msgs):
    signal_entry, signal_exit = fetch_signals(strategy)
    if signal_entry:
        execute_entry_signal(symbol, strategy, signal_entry, logs, tg_msgs)
    manage_active_trades(symbol, strategy, logs, tg_msgs)
