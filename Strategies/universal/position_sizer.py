
def position_sizer(close, sl, max_risk, account_size, pip_value_per_lot=10, risk_is_percent=True):
    """
    Oblicza wielkość pozycji (loty), aby ryzyko na trade nie przekraczało max_risk.

    Parameters
    ----------
    close : float
        Cena wejścia w pozycję.
    sl : float
        Poziom stop loss.
    max_risk : float
        Maksymalne ryzyko — procent (np. 0.01 = 1%) lub wartość nominalna (np. 100).
    account_size : float
        Wartość kapitału.
    pip_value_per_lot : float, default=10
        Wartość 1 pipsa dla 1 lota.
    risk_is_percent : bool, default=True
        Czy max_risk jest w procentach (True) czy w kwocie (False).

    Returns
    -------
    float
        Wielkość pozycji w lotach.
    """
    # różnica w pipsach między wejściem a SL

    if isinstance(close, dict) or isinstance(sl, dict):
        print("❗Błąd: close albo sl jest dict:")
        print("close =", close)
        print("sl =", sl)

    pip_distance = abs(close - sl) * 10000  # dla par typu EURUSD

    if pip_distance == 0:
        return 0

    # oblicz kwotę ryzyka
    risk_amount = max_risk * account_size if risk_is_percent else max_risk

    # oblicz wielkość pozycji
    lot_size = risk_amount / (pip_distance * pip_value_per_lot)
    return round(lot_size, 3)