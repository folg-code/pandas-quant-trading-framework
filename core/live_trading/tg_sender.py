import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_CHANNEL_ID

sent_logs_set = set()
logs_buffer = []

def send_telegram_log(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    payload_channel = {"chat_id": TELEGRAM_CHANNEL_ID, "text": message}
    payload_personal = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=payload_channel)
    requests.post(url, data=payload_personal)

def buffered_send_telegram_log(message):
    if message not in sent_logs_set:
        logs_buffer.append(message)
        sent_logs_set.add(message)

def flush_telegram_logs():
    for msg in logs_buffer:
        send_telegram_log(msg)
    logs_buffer.clear()
    sent_logs_set.clear()

def round_significant(x, sig=5):
    return float(f"{x:.{sig}g}")

def send_position_log(direction, symbol, open_price, entry_tag, sl_exit_tag, sl,
                      tp1_exit_tag, tp1_rr, tp1, tp2_exit_tag, tp2_rr, tp2, candle_formation):
    message = (
        f"✅ Pozycja {direction.upper()} {symbol}\n"
        f"   Cena otwarcia: {round_significant(open_price)}\n"
        f"   Źródło: {entry_tag}\n"
        f"   {sl_exit_tag} : {round_significant(sl)}\n"
        f"   {tp1_exit_tag}): {round_significant(tp1)}\n"
        f"   {tp2_exit_tag}): {round_significant(tp2)}\n"
        f"   Formacja świecowa {candle_formation}"
    )
    return message