from datetime import datetime

def market_data_provider_mock():
    return {
        "price": 1.1000,
        "time": datetime.utcnow(),
    }


def signal_provider_mock_once():
    """
    Zwraca jeden sygnał, potem pustą listę
    """
    yielded = {"done": False}

    def _provider():
        if yielded["done"]:
            return []
        yielded["done"] = True
        return [{
            "symbol": "EURUSD",
            "direction": "long",
            "volume": 0.1,
            "entry_price": 1.1000,
            "sl": 1.0950,
            "tp1": 1.1020,
            "tp2": 1.1050,
            "entry_tag": "entry_test",
        }]

    return _provider