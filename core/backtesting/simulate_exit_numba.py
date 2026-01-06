import numpy as np
from numba import njit


@njit
def simulate_exit_numba(
    direction,          # 1 = long, -1 = short
    entry_pos,
    entry_price,
    sl_level,
    tp1_level,
    tp2_level,
    high_arr,
    low_arr,
    close_arr,
    time_arr,
):
    tp1_executed = False
    tp1_price = 0.0
    tp1_time = time_arr[0]

    sl = sl_level
    n = len(close_arr)

    for i in range(entry_pos + 1, n):
        high = high_arr[i]
        low = low_arr[i]
        close = close_arr[i]
        t = time_arr[i]

        # BE po TP1
        if tp1_executed:
            sl = entry_price

        if direction == 1:  # LONG
            if (not tp1_executed) and high >= tp1_level:
                tp1_executed = True
                tp1_price = close
                tp1_time = t

            if low <= sl:
                return sl, t, tp1_executed, tp1_price, tp1_time

            if high >= tp2_level:
                return close, t, tp1_executed, tp1_price, tp1_time

        else:  # SHORT
            if (not tp1_executed) and low <= tp1_level:
                tp1_executed = True
                tp1_price = close
                tp1_time = t

            if high >= sl:
                return sl, t, tp1_executed, tp1_price, tp1_time

            if low <= tp2_level:
                return close, t, tp1_executed, tp1_price, tp1_time

    return close_arr[-1], time_arr[-1], tp1_executed, tp1_price, tp1_time