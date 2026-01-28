from numba import njit


EXIT_NONE = 0
EXIT_SL = 1
EXIT_TP1_BE = 2
EXIT_TP2 = 3
EXIT_EOD = 9


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
    slippage_abs,
):
    """
    Returns:
        exit_price: float
        exit_time: datetime
        exit_code: int
        tp1_executed: bool
        tp1_price: float
        tp1_time: datetime
    """
    exit_code = EXIT_NONE
    tp1_executed = False
    tp1_price = 0.0
    tp1_time = time_arr[0]

    sl = sl_level
    n = len(close_arr)

    for i in range(entry_pos + 1, n):
        high = high_arr[i]
        low = low_arr[i]
        t = time_arr[i]

        # -------------------------------------------------
        # MOVE SL TO BE AFTER TP1
        # -------------------------------------------------
        if tp1_executed:
            sl = entry_price

        if direction == 1:  # LONG
            # TP1 (no slippage, partial logic)
            if (not tp1_executed) and high >= tp1_level:
                tp1_executed = True
                tp1_price = tp1_level
                tp1_time = t

            # SL HIT
            if low <= sl:
                if tp1_executed:
                    exit_code = EXIT_TP1_BE
                else:
                    exit_code = EXIT_SL
                exit_price = sl - slippage_abs
                return exit_price, t, exit_code, tp1_executed, tp1_price, tp1_time

            # TP2 HIT (NO slippage for now)
            if high >= tp2_level:
                exit_code = EXIT_TP2
                exit_price = tp2_level
                return exit_price, t, exit_code, tp1_executed, tp1_price, tp1_time

        else:  # SHORT
            # TP1
            if (not tp1_executed) and low <= tp1_level:
                tp1_executed = True
                tp1_price = tp1_level
                tp1_time = t

            # SL HIT
            if high >= sl:
                if tp1_executed:
                    exit_code = EXIT_TP1_BE
                else:
                    exit_code = EXIT_SL
                exit_price = sl + slippage_abs
                return exit_price, t, exit_code, tp1_executed, tp1_price, tp1_time

            # TP2 HIT
            if low <= tp2_level:
                exit_code = EXIT_TP2
                exit_price = tp2_level
                return exit_price, t, exit_code, tp1_executed, tp1_price, tp1_time

    # -------------------------------------------------
    # END OF DATA
    # -------------------------------------------------
    exit_code = EXIT_EOD
    return close_arr[-1], time_arr[-1], exit_code, tp1_executed, tp1_price, tp1_time
