class InformativeStrategyMixin:
    @classmethod
    def get_required_informatives(cls):
        tfs = set()
        for attr in dir(cls):
            fn = getattr(cls, attr)
            if callable(fn) and getattr(fn, "_informative", False):
                tfs.add(fn._informative_timeframe)
        return sorted(tfs)


class ExternalDataMixin:
    def merge_external(self, base_df, *dfs):
        df = base_df
        for ext in dfs:
            df = df.merge(ext, on="time", how="left", validate="1:1")
        return df