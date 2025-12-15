def prepare_strategy(strategy, main_df, informative_dfs):
    strategy.df = main_df.copy()
    strategy._informative_results = informative_dfs.copy()