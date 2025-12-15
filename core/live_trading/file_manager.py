import json
import os
from datetime import datetime, timedelta, timezone
import MetaTrader5 as mt5

ACTIVE_TRADES_FILE = "active_trades.json"
BLOCKED_TAGS_FILE = "blocked_tags.json"
EXECUTED_TRADES_FILE = "executed_trades.json"

# --- ACTIVE TRADES ---
def load_active_trades():
    try:
        with open(ACTIVE_TRADES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_active_trades(trades):
    with open(ACTIVE_TRADES_FILE, "w") as f:
        json.dump(trades, f, indent=4)

# --- BLOCKED TAGS ---
def load_blocked_tags():
    try:
        with open(BLOCKED_TAGS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_blocked_tags(tags):
    with open(BLOCKED_TAGS_FILE, 'w') as f:
        json.dump(tags, f, indent=2)

# --- EXECUTED TRADES ---
def load_executed_trades():
    if not os.path.exists(EXECUTED_TRADES_FILE):
        return {}
    try:
        with open(EXECUTED_TRADES_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
    except json.JSONDecodeError:
        return {}

def save_executed_trades(trades):
    with open(EXECUTED_TRADES_FILE, "w") as f:
        json.dump(trades, f, indent=4)

# --- TRADE ENTRY/EXIT ---
def record_trade_entry(tag, symbol, direction, price, volume, entry_time, sl, tp1, tp2, trade_id, open_price):
    trades = load_executed_trades()
    trades[str(trade_id)] = {
        "tag": tag,
        "symbol": symbol,
        "direction": direction,
        "entry_price": price,
        "open_price": open_price,
        "entry_time": entry_time,
        "volume": volume,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp1_hit": False,
        "exit_price": None,
        "exit_time": None,
        "exit_reason": None,
        "exit_tag": None,
        "trade_id": trade_id
    }
    save_executed_trades(trades)

def record_trade_exit(trade_id, price, time, reason, exit_tag):
    trades = load_executed_trades()
    trade_id = str(trade_id)
    if trade_id in trades:
        trades[trade_id]["exit_price"] = price
        trades[trade_id]["exit_time"] = time
        trades[trade_id]["exit_reason"] = reason
        trades[trade_id]["exit_tag"] = exit_tag
        save_executed_trades(trades)

def mark_tp1_hit(trade_id):
    trades = load_executed_trades()
    trade_id = str(trade_id)
    if trade_id in trades:
        trades[trade_id]["tp1_hit"] = True
        save_executed_trades(trades)

def find_deal_by_order(trade_id):
    utc_to = datetime.utcnow()
    utc_from = utc_to - timedelta(days=30)
    deals = mt5.history_deals_get(utc_from, utc_to)
    if not deals:
        return None
    for deal in deals:
        if deal.order == trade_id:
            return deal
    return None