from typing import Dict, Any

import MetaTrader5 as mt5


class MT5Adapter:
    """
    Real MetaTrader5 execution adapter.
    Thin wrapper over MT5 API.
    """

    def __init__(
        self,
        *,
        login: int | None = None,
        password: str | None = None,
        server: str | None = None,
        dry_run: bool = False,
    ):
        self.dry_run = dry_run

        if self.dry_run:
            print("⚠ MT5Adapter running in DRY-RUN mode")
            return

        if not mt5.terminal_info():
            raise RuntimeError("MT5 terminal not initialized")

        print("🟢 MT5 initialized")

    # ==================================================
    # Execution API
    # ==================================================

    def open_position(
            self,
            *,
            symbol: str,
            direction: str,
            volume: float,
            price: float,
            sl: float,
            tp: float | None = None,
    ) -> Dict[str, Any]:

        if self.dry_run:
            print(
                f"[DRY-RUN] OPEN {symbol} {direction} "
                f"vol={volume} price={price} sl={sl} tp={tp}"
            )
            return {"ticket": f"MOCK_{symbol}", "price": price}

        # --------------------------------------------------
        # SYMBOL + TICK
        # --------------------------------------------------
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            raise RuntimeError(f"Symbol not found: {symbol}")

        if not symbol_info.visible:
            mt5.symbol_select(symbol, True)

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"No tick data for {symbol}")

        market_price = tick.ask if direction == "long" else tick.bid

        # --------------------------------------------------
        # VALIDATE SL / TP (ABSOLUTELY REQUIRED)
        # --------------------------------------------------
        stops_level = symbol_info.trade_stops_level * symbol_info.point

        if direction == "long":
            if sl >= market_price:
                raise RuntimeError(f"Invalid SL for long: sl={sl}, price={market_price}")
            if tp is not None and tp <= market_price:
                raise RuntimeError(f"Invalid TP for long: tp={tp}, price={market_price}")

            if (market_price - sl) < stops_level:
                raise RuntimeError(f"SL too close: {market_price - sl} < {stops_level}")
            if tp is not None and (tp - market_price) < stops_level:
                raise RuntimeError(f"TP too close: {tp - market_price} < {stops_level}")

            order_type = mt5.ORDER_TYPE_BUY

        else:  # short
            if sl <= market_price:
                raise RuntimeError(f"Invalid SL for short: sl={sl}, price={market_price}")
            if tp is not None and tp >= market_price:
                raise RuntimeError(f"Invalid TP for short: tp={tp}, price={market_price}")

            if (sl - market_price) < stops_level:
                raise RuntimeError(f"SL too close: {sl - market_price} < {stops_level}")
            if tp is not None and (market_price - tp) < stops_level:
                raise RuntimeError(f"TP too close: {market_price - tp} < {stops_level}")

            order_type = mt5.ORDER_TYPE_SELL

        # --------------------------------------------------
        # SEND ORDER
        # --------------------------------------------------
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": market_price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 100001,
            "comment": "live_engine",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"MT5 order_send failed: {result}")

        return {
            "ticket": result.order,
            "price": market_price,
        }

    def close_position(
        self,
        *,
        ticket: str,
        price: float | None = None,
    ) -> None:

        if self.dry_run:
            print(f"[DRY-RUN] CLOSE ticket={ticket} price={price}")
            return

        positions = mt5.positions_get(ticket=int(ticket))
        if not positions:
            raise RuntimeError(f"No open position with ticket {ticket}")

        pos = positions[0]

        order_type = (
            mt5.ORDER_TYPE_SELL
            if pos.type == mt5.POSITION_TYPE_BUY
            else mt5.ORDER_TYPE_BUY
        )

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": pos.ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": order_type,
            "price": mt5.symbol_info_tick(pos.symbol).bid
            if order_type == mt5.ORDER_TYPE_SELL
            else mt5.symbol_info_tick(pos.symbol).ask,
            "deviation": 10,
            "magic": 100001,
            "comment": "live_engine_close",
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"MT5 close failed: {result}")

    def close_partial(self, *, ticket: str, volume: float, price: float):
        if self.dry_run:
            print(f"[DRY-RUN] PARTIAL CLOSE ticket={ticket} vol={volume} price={price}")
            return

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "volume": volume,
            "price": price,
            "type": mt5.ORDER_TYPE_SELL,  # dla long
            "deviation": 10,
            "comment": "tp1_partial",
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"Partial close failed: {result}")

    def modify_sl(self, *, ticket: str, new_sl: float):
        if self.dry_run:
            print(f"[DRY-RUN] MODIFY SL ticket={ticket} sl={new_sl}")
            return

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": new_sl,
            "tp": 0.0,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"SL modify failed: {result}")

    def init_mt5(self):
        if not mt5.initialize():
            raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")

        info = mt5.account_info()
        print(
            "🟢 MT5 initialized | "
            f"Account={info.login} "
            f"Balance={info.balance} "
            f"Server={info.server}"
        )

    def shutdown(self):
        if not self.dry_run:
            mt5.shutdown()
            print("🔴 MT5 shutdown")
