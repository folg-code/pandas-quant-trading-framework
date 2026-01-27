import numpy as np


def generate_price_action_context(self, df):
    """
    Priority-aware PA event generator.

    Rules:
    - BOS has absolute priority
    - MSS is ignored for N bars after BOS
    """

    df['pa_event_type'] = None
    df['pa_event_dir'] = None
    df['pa_event_idx'] = np.nan
    df['pa_level'] = np.nan

    bos_bull = df['bos_bull_event']
    bos_bear = df['bos_bear_event']

    # ==========================
    # BOS (ABSOLUTE PRIORITY)
    # ==========================
    df.loc[bos_bull, 'pa_event_type'] = 'bos'
    df.loc[bos_bull, 'pa_event_dir'] = 'bull'
    df.loc[bos_bull, 'pa_event_idx'] = df.loc[bos_bull, 'bos_bull_event_idx']
    df.loc[bos_bull, 'pa_level'] = df.loc[bos_bull, 'bos_bull_level']

    df.loc[bos_bear, 'pa_event_type'] = 'bos'
    df.loc[bos_bear, 'pa_event_dir'] = 'bear'
    df.loc[bos_bear, 'pa_event_idx'] = df.loc[bos_bear, 'bos_bear_event_idx']
    df.loc[bos_bear, 'pa_level'] = df.loc[bos_bear, 'bos_bear_level']

    # ==========================
    # MSS (ONLY IF NO RECENT BOS)
    # ==========================
    NO_RECENT_BOS = df['bars_since_bos'] > 2  # ← kluczowy parametr

    mss_bull = df['mss_bull_event'] & NO_RECENT_BOS & df['pa_event_type'].isna()
    mss_bear = df['mss_bear_event'] & NO_RECENT_BOS & df['pa_event_type'].isna()

    df.loc[mss_bull, 'pa_event_type'] = 'mss'
    df.loc[mss_bull, 'pa_event_dir'] = 'bull'
    df.loc[mss_bull, 'pa_event_idx'] = df.loc[mss_bull, 'mss_bull_event_idx']
    df.loc[mss_bull, 'pa_level'] = df.loc[mss_bull, 'mss_bull_level']

    df.loc[mss_bear, 'pa_event_type'] = 'mss'
    df.loc[mss_bear, 'pa_event_dir'] = 'bear'
    df.loc[mss_bear, 'pa_event_idx'] = df.loc[mss_bear, 'mss_bear_event_idx']
    df.loc[mss_bear, 'pa_level'] = df.loc[mss_bear, 'mss_bear_level']

    df['pa_event_idx'] = df['pa_event_idx'].ffill()
    df['pa_event_type'] = df['pa_event_type'].ffill()
    df['pa_event_dir'] = df['pa_event_dir'].ffill()
    df['pa_level'] = df['pa_level'].ffill()

    return df
