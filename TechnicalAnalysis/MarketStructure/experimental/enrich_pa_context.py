def enrich_pa_context(self, df):
    PA_COUNTER_MAX_BARS = 10
    PA_COUNTER_ATR_MULT = 2

    PA_CONT_MIN_BARS = 3
    PA_CONT_MIN_ATR = 0.8
    PA_CONT_MAX_ATR = 2.5

    df['bars_since_pa'] = df['idx'] - df['pa_event_idx']

    df['pa_dist'] = abs(df['close'] - df['pa_level'])
    df['pa_dist_atr'] = df['pa_dist'] / df['atr']

    df['pa_counter_allowed'] = (
            (df['bars_since_pa'] <= PA_COUNTER_MAX_BARS) &
            (df['pa_dist_atr'] <= PA_COUNTER_ATR_MULT)
    )

    df['pa_continuation_allowed'] = (
            (df['bars_since_pa'] >= PA_CONT_MIN_BARS) &
            (df['pa_dist_atr'] >= PA_CONT_MIN_ATR) &
            (df['pa_dist_atr'] <= PA_CONT_MAX_ATR)
    )

    return df
