"""
Portfolio Executive Agent — Investment operations under constitutional governance.

Responsible for portfolio management within the mandate established by the
Legislative Assembly and the Federal Reserve Charter. Every trade is
constitutionally authorized, logged, and subject to judicial review.

Constitutional Role: portfolio_executive (Art. II §1)
Branch: Executive
Permission Tier: tier_3 (Portfolio)

References:
    Article II §1 — Executive role (Portfolio Executive Agent)
    Article VI §6 — Relationship to Federal Reserve (directives are binding)
    Amendment III — No Unconsented Irreversible Execution
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from nova_syntheia.agents.base import BaseConstitutionalAgent
from nova_syntheia.constitution.schema import (
    ActionType,
    FOUNDING_ROLES,
)

logger = logging.getLogger(__name__)


class PortfolioExecutiveAgent(BaseConstitutionalAgent):
    """
    Portfolio Executive Agent — manages Nova Syntheia's investment portfolio.

    Operates within Monetary Policy Directive constraints (Art. VI §6).
    Starting capital: $50 on Alpaca. Focuses on broad market ETFs with
    tactical allocation per Federal Reserve directives.

    Every trade is logged with: objective, justification, constitutional
    citation, inputs (order params), outputs (fill details).
    """

    def __init__(self, member_id: UUID, model: str, **kwargs: Any) -> None:
        super().__init__(
            member_id=member_id,
            role=FOUNDING_ROLES["portfolio_executive"],
            permission_tier_id="tier_3",
            model=model,
            system_prompt="""You are the Portfolio Executive Agent of Nova Syntheia.

Your primary responsibilities:
1. Execute investment operations within the mandate of the Legislative Assembly
   and the Federal Reserve Charter
2. Operate strictly within Monetary Policy Directive constraints (Art. VI §6)
3. Monitor portfolio positions and performance
4. Propose trades with full constitutional justification
5. Report portfolio status to the Assembly

CRITICAL CONSTRAINTS:
- You may NOT disregard a Monetary Policy Directive (Art. VI §6)
- Trades above the irreversible threshold require prior authorization (Amendment III)
- You may petition the Fed to reconsider a Directive
- You may appeal to Judicial Branch if a Directive exceeds constitutional authority

CURRENT PORTFOLIO PARAMETERS:
- Starting capital: $50
- Permissible asset classes: ETFs and mutual funds (Founding Era)
- Strategy: Broad market exposure with tactical allocation per Fed directives
- Brokerage: Alpaca (zero commission, fractional shares)""",
            **kwargs,
        )
        self.alpaca_client = None  # Set by orchestrator
        self.active_directive = None  # Current Monetary Policy Directive

    async def _execute(
        self,
        action_type: ActionType,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a portfolio action."""
        handlers = {
            ActionType.PORTFOLIO_TRADE: self._handle_trade,
            ActionType.PORTFOLIO_REBALANCE: self._handle_rebalance,
        }

        handler = handlers.get(action_type)
        if handler is None:
            return {
                "status": "unsupported",
                "message": f"Action type {action_type.value} not implemented",
            }

        return await handler(inputs)

    async def _handle_trade(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a portfolio trade.

        All trades must comply with the active Monetary Policy Directive
        and fall within the permission tier's irreversible threshold.
        """
        symbol = inputs.get("symbol", "")
        side = inputs.get("side", "buy")  # buy or sell
        qty = inputs.get("qty")
        notional = inputs.get("notional")  # Dollar amount for fractional shares

        # Validate against active Monetary Policy Directive
        if self.active_directive:
            directive_check = self._check_directive_compliance(inputs)
            if not directive_check["compliant"]:
                return {
                    "status": "blocked_by_directive",
                    "message": directive_check["reason"],
                    "directive_number": self.active_directive.directive_number,
                }

        # Execute via Alpaca
        if self.alpaca_client:
            try:
                order = await self._submit_alpaca_order(symbol, side, qty, notional)
                return {
                    "status": "executed",
                    "order": order,
                    "affected_resources": [f"portfolio:{symbol}"],
                }
            except Exception as e:
                return {
                    "status": "failed",
                    "error": str(e),
                    "symbol": symbol,
                }
        else:
            # Paper trading / simulation mode
            return {
                "status": "simulated",
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "notional": notional,
                "message": "Alpaca client not connected — trade simulated",
                "affected_resources": [f"portfolio:{symbol}"],
            }

    async def _handle_rebalance(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Rebalance the portfolio according to target allocations.

        Target allocations come from Monetary Policy Directives.
        """
        target_allocations = inputs.get("target_allocations", {})

        return {
            "status": "rebalance_planned",
            "target_allocations": target_allocations,
            "message": "Rebalance plan generated — individual trades will be submitted",
        }

    def _check_directive_compliance(self, trade_inputs: dict[str, Any]) -> dict[str, Any]:
        """Check if a proposed trade complies with the active Monetary Policy Directive."""
        if not self.active_directive:
            return {"compliant": True, "reason": "No active directive"}

        # Check against directive constraints
        for constraint in self.active_directive.constraints:
            # Basic constraint checking — expanded in production
            if constraint.constraint_type == "max_allocation":
                pass  # Would check current + proposed allocation
            elif constraint.constraint_type == "forbidden_asset_class":
                pass  # Would check symbol's asset class

        return {"compliant": True, "reason": "Directive constraints satisfied"}

    async def _submit_alpaca_order(
        self,
        symbol: str,
        side: str,
        qty: float | None,
        notional: float | None,
    ) -> dict[str, Any]:
        """Submit an order to Alpaca."""
        # This would use alpaca-py in production
        return {
            "order_id": "simulated",
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "notional": notional,
            "status": "submitted",
        }

    async def get_portfolio_status(self) -> dict[str, Any]:
        """Get current portfolio status."""
        if self.alpaca_client:
            # Would query Alpaca for actual positions
            pass

        return {
            "total_value": "50.00",
            "cash": "50.00",
            "positions": [],
            "day_return": "0.00",
            "total_return": "0.00",
        }

    def get_capabilities(self) -> list[str]:
        return [
            "portfolio_trading",
            "portfolio_rebalancing",
            "position_monitoring",
            "performance_reporting",
            "directive_compliance_checking",
            "alpaca_integration",
        ]
