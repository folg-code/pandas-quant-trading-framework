import numpy as np


def detect_microstructure_regime(
        self,
        df,
        atr_short: int = 14,
        atr_long: int = 100,
        range_lookback: int = 20,
        impulse_mult: float = 1.2,
        compression_thr: float = 0.6,
        expansion_thr: float = 1.4,
):

    df['atr_short'] = df['atr'].rolling(atr_short).mean()
    df['atr_long'] = df['atr'].rolling(atr_long).mean()

    df['atr_ratio'] = df['atr_short'] / df['atr_long']

    # ===============================
    # 2️⃣ RANGE / COMPRESSION
    # ===============================
    rolling_high = df['high'].rolling(range_lookback).max()
    rolling_low = df['low'].rolling(range_lookback).min()

    df['rolling_range'] = rolling_high - rolling_low
    df['range_atr_ratio'] = df['rolling_range'] / df['atr_long']

    # ===============================
    # 3️⃣ IMPULSE vs OVERLAP
    # ===============================
    body = (df['close'] - df['open']).abs()
    bar_range = (df['high'] - df['low']).replace(0, np.nan)

    df['body_ratio'] = body / bar_range

    df['impulse_bar'] = (
            (bar_range > impulse_mult * bar_range.rolling(50).median()) &
            (df['body_ratio'] > 0.6)
    )

    df['overlap_bar'] = (
            (bar_range < 0.8 * df['atr']) &
            (df['body_ratio'] < 0.4)
    )

    df['impulse_freq'] = df['impulse_bar'].rolling(10).mean()
    df['overlap_freq'] = df['overlap_bar'].rolling(10).mean()

    # ===============================
    # 4️⃣ REGIME LOGIC
    # ===============================
    regime = np.full(len(df), 'normal', dtype=object)

    range_decay = (
            df['rolling_range'] <
            df['rolling_range'].rolling(50).median() * 0.7
    )

    compression_mask = (
            range_decay &
            (df['overlap_freq'] > 0.55) &
            (df['impulse_freq'] < 0.25)
    )

    expansion_mask = (
            (df['impulse_freq'] > 0.45) &
            (
                    (df['atr_ratio'] > expansion_thr) |
                    (df['impulse_freq'].shift(1) < 0.2)
            )
    )

    exhaustion_mask = (
            (df['atr_ratio'] > expansion_thr) &
            (df['impulse_freq'] < 0.25) &
            (df['overlap_freq'] > 0.4) &
            (df['follow_through_atr'] < 1.2)
    )

    regime[compression_mask] = 'compression'
    regime[expansion_mask] = 'expansion'
    regime[exhaustion_mask] = 'exhaustion'

    df['microstructure_regime'] = regime

    # ===============================
    # 5️⃣ FEATURES POMOCNICZE
    # ===============================

    df['volatility_state'] = np.where(
        df['atr_ratio'] < 0.8, 'low',
        np.where(df['atr_ratio'] > 1.3, 'high', 'normal')
    )

    df['micro_prev'] = df['microstructure_regime'].shift(1)

    df['micro_transition'] = (
            df['micro_prev'].astype(str) +
            '_to_' +
            df['microstructure_regime'].astype(str)
    )

    # =============================================================
    # MICROSTRUCTURE FSM
    # =============================================================

    df['micro_prev'] = df['microstructure_regime'].shift(1)

    df['micro_transition'] = (
            df['micro_prev'].astype(str) +
            '_to_' +
            df['microstructure_regime'].astype(str)
    )

    # =============================================================
    # MICROSTRUCTURE BIAS
    # =============================================================

    df['micro_bias'] = 'balanced'

    df.loc[
        df['micro_transition'].isin({
            'compression_to_expansion',
            'normal_to_expansion',
        }),
        'micro_bias'
    ] = 'momentum_favorable'

    df.loc[
        df['microstructure_regime'] == 'exhaustion',
        'micro_bias'
    ] = 'countertrend_favorable'

    COUNTERTREND_FAVORABLE = {
        'expansion_to_exhaustion',
    }

    df.loc[
        df['micro_transition'].isin(COUNTERTREND_FAVORABLE),
        'micro_bias'
    ] = 'countertrend_favorable'

    # =============================================================
    # FSM
    # =============================================================

    df['micro_bias_block'] = (
        df['micro_bias']
        .ne(df['micro_bias'].shift())
        .cumsum()
    )

    df['bars_in_micro_bias'] = (
            df.groupby(df['micro_bias_block'])
            .cumcount() + 1
    )

    df['bars_since_momentum'] = (
        df['micro_bias'].eq('momentum_favorable')
        .astype(int)
        .groupby(df['micro_bias'].ne('momentum_favorable').cumsum())
        .cumcount()
    )

    df['bars_since_countertrend'] = (
        df['micro_bias']
        .eq('countertrend_favorable')
        .astype(int)
        .groupby(df['micro_bias'].ne('countertrend_favorable').cumsum())
        .cumcount()
    )
    # =============================================================
    # CONTEXT
    # =============================================================

    df['block_momentum'] = (
            df['micro_bias'] == 'countertrend_favorable'
    )

    df['allow_momentum'] = (
            (df['micro_bias'] == 'momentum_favorable') &
            (df['bars_in_micro_bias'] <= 3)
    )

    df['allow_countertrend'] = (
            (df['micro_bias'] == 'countertrend_favorable') &
            (df['bars_in_micro_bias'] <= 2)
    )

    df['block_countertrend'] = (
            (df['micro_bias'] != 'countertrend_favorable') |
            (df['bars_in_micro_bias'] > 2) |
            (df['bars_since_flip'] < 4)
    )

    df['premium_context'] = (
            (df['micro_bias'] == 'momentum_favorable') &
            (df['bars_in_micro_bias'] <= 2)
    )
    return df
