from core.live_trading.runner import run_live_symbols
import config

if __name__ == "__main__":
    # Definicja lookbacków dla różnych TF w formie słownika
    # Możesz podać liczbę świec lub timedelta w sekundach

    run_live_symbols(config.lookbacks)