"""
Nova Syntheia — Alpaca brokerage integration.

Provides a thin wrapper over the Alpaca API for the Portfolio Executive Agent.
Supports paper and live trading. All trades are logged to the National Ledger.

References:
    Article IX §5 — Portfolio integration
    Art. V §1 — Executive branch powers
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class TimeInForce(str, Enum):
    DAY = "day"  # (default for market orders)
    GTC = "gtc"  # good-til-cancelled
    IOC = "ioc"  # immediate-or-cancel


@dataclass(frozen=True)
class AlpacaPosition:
    symbol: str
    qty: float
    market_value: float
    avg_entry_price: float
    unrealized_pl: float
    unrealized_plpc: float
    current_price: float


@dataclass(frozen=True)
class AlpacaOrder:
    id: str
    symbol: str
    qty: float
    side: str
    type: str
    status: str
    filled_qty: float
    filled_avg_price: float | None
    submitted_at: str
    filled_at: str | None


@dataclass(frozen=True)
class AlpacaAccount:
    id: str
    status: str
    cash: float
    portfolio_value: float
    buying_power: float
    equity: float
    last_equity: float
    currency: str


class AlpacaClient:
    """
    Async Alpaca REST client.

    Uses httpx for async HTTP. Supports both paper and live endpoints.
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        base_url: str = "https://paper-api.alpaca.markets",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
            "Content-Type": "application/json",
        }
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers,
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ── Account ────────────────────────────────────────────────

    async def get_account(self) -> AlpacaAccount:
        """Get account details."""
        client = await self._ensure_client()
        resp = await client.get("/v2/account")
        resp.raise_for_status()
        data = resp.json()
        return AlpacaAccount(
            id=data["id"],
            status=data["status"],
            cash=float(data["cash"]),
            portfolio_value=float(data["portfolio_value"]),
            buying_power=float(data["buying_power"]),
            equity=float(data["equity"]),
            last_equity=float(data["last_equity"]),
            currency=data["currency"],
        )

    # ── Positions ──────────────────────────────────────────────

    async def get_positions(self) -> list[AlpacaPosition]:
        """Get all open positions."""
        client = await self._ensure_client()
        resp = await client.get("/v2/positions")
        resp.raise_for_status()
        return [
            AlpacaPosition(
                symbol=p["symbol"],
                qty=float(p["qty"]),
                market_value=float(p["market_value"]),
                avg_entry_price=float(p["avg_entry_price"]),
                unrealized_pl=float(p["unrealized_pl"]),
                unrealized_plpc=float(p["unrealized_plpc"]),
                current_price=float(p["current_price"]),
            )
            for p in resp.json()
        ]

    # ── Orders ─────────────────────────────────────────────────

    async def submit_order(
        self,
        symbol: str,
        qty: float | None = None,
        notional: float | None = None,
        side: OrderSide = OrderSide.BUY,
        order_type: OrderType = OrderType.MARKET,
        time_in_force: TimeInForce = TimeInForce.DAY,
        limit_price: float | None = None,
    ) -> AlpacaOrder:
        """
        Submit a new order.

        Use `qty` for share count or `notional` for dollar amount (fractional shares).
        At $50 scale, `notional` is preferred.
        """
        payload: dict[str, Any] = {
            "symbol": symbol,
            "side": side.value,
            "type": order_type.value,
            "time_in_force": time_in_force.value,
        }

        if notional is not None:
            payload["notional"] = str(round(notional, 2))
        elif qty is not None:
            payload["qty"] = str(qty)
        else:
            raise ValueError("Either qty or notional must be provided")

        if order_type == OrderType.LIMIT and limit_price is not None:
            payload["limit_price"] = str(round(limit_price, 2))

        client = await self._ensure_client()
        resp = await client.post("/v2/orders", json=payload)
        resp.raise_for_status()
        data = resp.json()

        logger.info(
            "Order submitted: %s %s %s (status: %s)",
            side.value,
            symbol,
            notional or qty,
            data["status"],
        )

        return AlpacaOrder(
            id=data["id"],
            symbol=data["symbol"],
            qty=float(data.get("qty") or 0),
            side=data["side"],
            type=data["type"],
            status=data["status"],
            filled_qty=float(data.get("filled_qty") or 0),
            filled_avg_price=float(data["filled_avg_price"]) if data.get("filled_avg_price") else None,
            submitted_at=data["submitted_at"],
            filled_at=data.get("filled_at"),
        )

    async def get_orders(
        self,
        status: str = "all",
        limit: int = 50,
    ) -> list[AlpacaOrder]:
        """Get orders."""
        client = await self._ensure_client()
        resp = await client.get("/v2/orders", params={"status": status, "limit": limit})
        resp.raise_for_status()
        return [
            AlpacaOrder(
                id=o["id"],
                symbol=o["symbol"],
                qty=float(o.get("qty") or 0),
                side=o["side"],
                type=o["type"],
                status=o["status"],
                filled_qty=float(o.get("filled_qty") or 0),
                filled_avg_price=float(o["filled_avg_price"]) if o.get("filled_avg_price") else None,
                submitted_at=o["submitted_at"],
                filled_at=o.get("filled_at"),
            )
            for o in resp.json()
        ]

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        client = await self._ensure_client()
        resp = await client.delete(f"/v2/orders/{order_id}")
        return resp.status_code == 204

    # ── Market Data ────────────────────────────────────────────

    async def get_latest_quote(self, symbol: str) -> dict[str, Any]:
        """Get the latest quote for a symbol (uses data API)."""
        client = await self._ensure_client()
        # Alpaca data API uses a different base URL
        data_url = "https://data.alpaca.markets/v2"
        resp = await client.get(
            f"{data_url}/stocks/{symbol}/quotes/latest",
            headers=self._headers,
        )
        resp.raise_for_status()
        return resp.json()

    async def get_bars(
        self,
        symbol: str,
        timeframe: str = "1Day",
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """Get historical bars."""
        client = await self._ensure_client()
        data_url = "https://data.alpaca.markets/v2"
        resp = await client.get(
            f"{data_url}/stocks/{symbol}/bars",
            params={"timeframe": timeframe, "limit": limit},
            headers=self._headers,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("bars", [])

    # ── Portfolio Summary ──────────────────────────────────────

    async def get_portfolio_summary(self) -> dict[str, Any]:
        """Get a complete portfolio summary for dashboard display."""
        account = await self.get_account()
        positions = await self.get_positions()

        total_unrealized = sum(p.unrealized_pl for p in positions)

        return {
            "account_status": account.status,
            "cash": account.cash,
            "portfolio_value": account.portfolio_value,
            "equity": account.equity,
            "buying_power": account.buying_power,
            "last_equity": account.last_equity,
            "daily_change": account.equity - account.last_equity,
            "daily_change_pct": (
                ((account.equity - account.last_equity) / account.last_equity * 100)
                if account.last_equity > 0
                else 0.0
            ),
            "total_unrealized_pl": total_unrealized,
            "positions_count": len(positions),
            "positions": [
                {
                    "symbol": p.symbol,
                    "qty": p.qty,
                    "market_value": p.market_value,
                    "avg_entry_price": p.avg_entry_price,
                    "current_price": p.current_price,
                    "unrealized_pl": p.unrealized_pl,
                    "unrealized_plpc": p.unrealized_plpc * 100,
                }
                for p in positions
            ],
            "as_of": datetime.now(timezone.utc).isoformat(),
        }
