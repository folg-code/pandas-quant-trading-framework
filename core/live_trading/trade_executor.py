import MetaTrader5 as mt5
from core.live_trading.tg_sender import send_telegram_log


def send_order(symbol, direction, volume, sl, tp1, tp2, comment=""):
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        print(f"❌ Nie można pobrać informacji o symbolu: {symbol}")
        return None

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        print(f"❌ Brak ticków dla {symbol}")
        return None

    order_type = mt5.ORDER_TYPE_BUY if direction == "long" else mt5.ORDER_TYPE_SELL
    price = tick.ask if direction == "long" else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp2,  # TP2 jako limit
        "deviation": 30,
        "magic": 234000,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if not result:
        send_telegram_log(f"❌ Brak odpowiedzi MT5 przy wysyłaniu zlecenia {symbol}")
        return None
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Błąd zlecenia: {result.retcode} - {result.comment}")
    return result

def close_position(position, volume=None):
    if volume is None:
        return None
    direction = position.type
    symbol = position.symbol
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return None
    price = tick.bid if direction == mt5.ORDER_TYPE_BUY else tick.ask
    order_type = mt5.ORDER_TYPE_SELL if direction == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "position": position.ticket,
        "price": price,
        "deviation": 20,
        "magic": 123456,
        "comment": "Auto-close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    return mt5.order_send(request)

def modify_stop_loss(trade_id, new_sl):
    position = mt5.positions_get(ticket=trade_id)
    if not position:
        return False
    position = position[0]
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": trade_id,
        "sl": new_sl,
        "tp": position.tp,
        "symbol": position.symbol,
    }
    result = mt5.order_send(request)
    return result.retcode == mt5.TRADE_RETCODE_DONE

def get_open_positions(symbol):
    positions = mt5.positions_get(symbol=symbol)
    return list(positions) if positions else []
