"""
Monetary Policy Agent — Federal Reserve implementation.

Responsible for macroeconomic analysis, monetary policy directives,
dual-mandate balancing, and economic indicator monitoring.

Constitutional Role: monetary_policy (Art. IX)
Branch: Federal Reserve (independent)
Permission Tier: tier_4 (Monetary Policy — highest AI authority)

References:
    Article IX §1 — Federal Reserve Establishment
    Article IX §2 — Monetary Powers
    Article IX §3 — Dual Mandate
    Article IX §4 — Rate & Directive Authority
    Article IX §5 — Portfolio Integration
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from nova_syntheia.agents.base import BaseConstitutionalAgent
from nova_syntheia.constitution.schema import (
    ActionType,
    DirectiveType,
    FOUNDING_ROLES,
    MacroeconomicIndicator,
    MonetaryPolicyDirective,
    PortfolioConstraint,
)

logger = logging.getLogger(__name__)


class MonetaryPolicyAgent(BaseConstitutionalAgent):
    """
    Federal Reserve Agent — monetary policy and macroeconomic oversight.

    This agent:
    - Monitors macroeconomic indicators (inflation, employment, rates)
    - Issues Monetary Policy Directives (binding on Executive Branch per Art. IX §5)
    - Balances the dual mandate: growth vs. stability (Art. IX §3)
    - Sets portfolio constraints (sector limits, duration targets, risk caps)
    - Reports economic outlook to the polity

    Key constitutional features:
    - Independence from Executive Branch (Art. IX §1)
    - Directives subject to Judicial review (Art. IX §6)
    - Transparent publication of reasoning (Art. IX §4)
    - Subject to legislative override by supermajority (Art. IX §7)
    """

    def __init__(self, member_id: UUID, model: str, **kwargs: Any) -> None:
        super().__init__(
            member_id=member_id,
            role=FOUNDING_ROLES["monetary_policy"],
            permission_tier_id="tier_4",
            model=model,
            system_prompt="""You are the Federal Reserve Agent of Nova Syntheia.

You manage monetary policy for the polity under a dual mandate (Art. IX §3):
1. GROWTH: Maximize long-term portfolio appreciation
2. STABILITY: Protect capital and manage drawdown risk

Your primary tools are Monetary Policy Directives, which are binding on the
Executive Branch (Art. IX §5). These include:
- RATE_GUIDANCE: Interest rate and yield expectations
- RISK_LIMIT: Maximum drawdown, volatility, or concentration limits
- SECTOR_ALLOCATION: Sector weight targets and bands
- REBALANCE_TRIGGER: Conditions that require portfolio rebalancing
- EMERGENCY_HALT: Stop all trading (requires Art. VII emergency conditions)

CONSTRAINTS:
- You are INDEPENDENT from the Executive Branch (Art. IX §1)
- Your directives are subject to Judicial review (Art. IX §6)
- You must PUBLISH reasoning for all directives (Art. IX §4)
- A legislative supermajority can override your directives (Art. IX §7)
- You may NOT execute trades directly — directives go to Portfolio Executive
- The Founder's casting vote applies in cases of deadlock (Art. IX §8)

When analyzing the macroeconomic environment, consider:
- Current portfolio size ($50 starting capital — every dollar matters)
- Transaction costs and minimum position sizes
- Market conditions (volatility, trend, sentiment)
- Risk-adjusted returns, not just absolute returns
- Time horizon (long-term wealth building)

With only $50, prioritize capital preservation while seeking asymmetric
opportunities. The growth mandate should not endanger the stability mandate
at this scale.""",
            **kwargs,
        )
        self._current_indicators: list[MacroeconomicIndicator] = []
        self._active_directives: list[MonetaryPolicyDirective] = []
        self._directive_history: list[MonetaryPolicyDirective] = []

    async def _execute(
        self,
        action_type: ActionType,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a monetary policy action."""
        handlers = {
            ActionType.ISSUE_DIRECTIVE: self._handle_issue_directive,
            ActionType.MONITOR_INDICATORS: self._handle_monitor_indicators,
            ActionType.BALANCE_DUAL_MANDATE: self._handle_dual_mandate_analysis,
            ActionType.SET_PORTFOLIO_CONSTRAINTS: self._handle_set_constraints,
            ActionType.ECONOMIC_OUTLOOK: self._handle_economic_outlook,
        }

        handler = handlers.get(action_type)
        if handler is None:
            return {
                "status": "unsupported",
                "message": (
                    f"Federal Reserve does not support {action_type.value}. "
                    f"This role is limited to monetary policy operations (Art. IX)."
                ),
            }

        return await handler(inputs)

    async def _handle_issue_directive(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Issue a Monetary Policy Directive.

        Art. IX §4: The Federal Reserve may issue directives setting rates,
        risk limits, sector allocations, rebalancing triggers, and emergency halts.
        All directives must include published reasoning.
        """
        directive_type_str = inputs.get("directive_type", "RISK_LIMIT")
        reasoning = inputs.get("reasoning", "")
        parameters = inputs.get("parameters", {})
        portfolio_constraints = inputs.get("portfolio_constraints", [])
        duration_hours = inputs.get("duration_hours", 168)  # Default 7 days

        if not reasoning:
            # Art. IX §4: reasoning publication is mandatory
            reasoning_result = await self.reason(
                f"Provide detailed monetary policy reasoning for a {directive_type_str} directive "
                f"with parameters: {parameters}. Consider the dual mandate (growth vs. stability), "
                f"current market conditions, and our $50 starting capital."
            )
            reasoning = reasoning_result

        try:
            directive_type = DirectiveType(directive_type_str)
        except ValueError:
            directive_type = DirectiveType.RISK_LIMIT

        constraints = []
        for c in portfolio_constraints:
            constraints.append(
                PortfolioConstraint(
                    constraint_type=c.get("type", ""),
                    value=c.get("value", 0.0),
                    description=c.get("description", ""),
                )
            )

        directive = MonetaryPolicyDirective(
            id=uuid4(),
            directive_type=directive_type,
            issued_by=self.member_id,
            reasoning=reasoning,
            parameters=parameters,
            portfolio_constraints=constraints,
            effective_from=datetime.now(timezone.utc),
            duration_hours=duration_hours,
        )

        self._active_directives.append(directive)
        self._directive_history.append(directive)

        logger.info(
            "Monetary Policy Directive issued: %s (%s)",
            directive.id,
            directive.directive_type.value,
        )

        return {
            "status": "issued",
            "directive_id": str(directive.id),
            "directive_type": directive.directive_type.value,
            "reasoning_excerpt": reasoning[:200] + "..." if len(reasoning) > 200 else reasoning,
            "constraints_count": len(constraints),
            "duration_hours": duration_hours,
            "note": "Directive is binding on Executive Branch (Art. IX §5). Subject to Judicial review (Art. IX §6).",
        }

    async def _handle_monitor_indicators(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Monitor and update macroeconomic indicators.

        Uses LLM reasoning to assess economic conditions and their
        implications for portfolio management at our scale.
        """
        indicators_data = inputs.get("indicators", [])

        indicators = []
        for ind in indicators_data:
            indicators.append(
                MacroeconomicIndicator(
                    name=ind.get("name", ""),
                    value=ind.get("value", 0.0),
                    previous_value=ind.get("previous_value"),
                    unit=ind.get("unit", ""),
                    source=ind.get("source", ""),
                    assessed_at=datetime.now(timezone.utc),
                )
            )

        self._current_indicators = indicators

        # Use LLM to synthesize indicator implications
        if indicators:
            indicator_summary = "\n".join(
                f"- {i.name}: {i.value}{i.unit} (prev: {i.previous_value})"
                for i in indicators
            )
            analysis = await self.reason(
                f"Analyze these macroeconomic indicators for a $50 portfolio:\n{indicator_summary}\n\n"
                f"What are the implications for our dual mandate (growth vs stability)? "
                f"Should we adjust any monetary policy directives?"
            )
        else:
            analysis = "No indicators provided for analysis."

        return {
            "status": "monitored",
            "indicators_count": len(indicators),
            "analysis": analysis,
            "active_directives": len(self._active_directives),
        }

    async def _handle_dual_mandate_analysis(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Perform dual mandate balancing analysis (Art. IX §3).

        Assesses the tension between growth and stability mandates
        and recommends policy adjustments.
        """
        portfolio_value = inputs.get("portfolio_value", 50.0)
        portfolio_return_pct = inputs.get("return_pct", 0.0)
        max_drawdown_pct = inputs.get("max_drawdown_pct", 0.0)
        current_allocation = inputs.get("allocation", {})

        context = (
            f"Portfolio: ${portfolio_value:.2f} (return: {portfolio_return_pct:+.1f}%, "
            f"max drawdown: {max_drawdown_pct:.1f}%)\n"
            f"Allocation: {current_allocation}\n"
            f"Active directives: {len(self._active_directives)}\n"
            f"Indicators: {len(self._current_indicators)}"
        )

        analysis = await self.reason(
            f"Perform a dual mandate analysis for Nova Syntheia (Art. IX §3).\n\n"
            f"{context}\n\n"
            f"Balance the Growth Mandate (maximize long-term appreciation) against "
            f"the Stability Mandate (protect capital, manage risk). At our $50 scale, "
            f"capital preservation is paramount — losing $25 is catastrophic. "
            f"Recommend specific policy adjustments with constitutional citations."
        )

        # Determine mandate bias
        if portfolio_return_pct < -5:
            bias = "stability"
            urgency = "high"
        elif portfolio_return_pct > 10:
            bias = "growth"
            urgency = "low"
        elif max_drawdown_pct > 10:
            bias = "stability"
            urgency = "medium"
        else:
            bias = "balanced"
            urgency = "normal"

        return {
            "status": "analyzed",
            "mandate_bias": bias,
            "urgency": urgency,
            "portfolio_value": portfolio_value,
            "analysis": analysis,
            "recommendation": (
                "Shift toward stability measures"
                if bias == "stability"
                else "Maintain balanced approach"
                if bias == "balanced"
                else "Growth opportunities identified"
            ),
        }

    async def _handle_set_constraints(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Set portfolio constraints (Art. IX §5).

        Portfolio constraints are binding on the Portfolio Executive Agent.
        """
        constraints_data = inputs.get("constraints", [])

        constraints = []
        for c in constraints_data:
            constraints.append(
                PortfolioConstraint(
                    constraint_type=c.get("type", ""),
                    value=c.get("value", 0.0),
                    description=c.get("description", ""),
                )
            )

        # Wrap in a directive
        directive = MonetaryPolicyDirective(
            id=uuid4(),
            directive_type=DirectiveType.RISK_LIMIT,
            issued_by=self.member_id,
            reasoning=inputs.get("reasoning", "Portfolio constraints update per Art. IX §5"),
            parameters={"constraint_update": True},
            portfolio_constraints=constraints,
            effective_from=datetime.now(timezone.utc),
            duration_hours=inputs.get("duration_hours", 720),  # 30 days default
        )

        self._active_directives.append(directive)
        self._directive_history.append(directive)

        return {
            "status": "constraints_set",
            "directive_id": str(directive.id),
            "constraints": [
                {"type": c.constraint_type, "value": c.value, "description": c.description}
                for c in constraints
            ],
            "binding_on": "Portfolio Executive Agent (Art. IX §5)",
        }

    async def _handle_economic_outlook(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Generate economic outlook report for the polity.

        Published periodically to maintain transparency (Art. IX §4).
        """
        horizon = inputs.get("horizon", "medium_term")

        indicator_context = ""
        if self._current_indicators:
            indicator_context = "\nCurrent indicators:\n" + "\n".join(
                f"- {i.name}: {i.value}{i.unit}" for i in self._current_indicators
            )

        directive_context = ""
        if self._active_directives:
            directive_context = "\nActive directives:\n" + "\n".join(
                f"- {d.directive_type.value}: {d.reasoning[:100]}..."
                for d in self._active_directives
            )

        outlook = await self.reason(
            f"Generate a {horizon} economic outlook for Nova Syntheia.\n"
            f"{indicator_context}\n{directive_context}\n\n"
            f"Consider: market conditions, our $50 portfolio scale, active directives, "
            f"and the dual mandate. Provide a clear assessment with recommendations. "
            f"This will be published to all members (Art. IX §4 transparency requirement)."
        )

        return {
            "status": "published",
            "horizon": horizon,
            "outlook": outlook,
            "indicators_considered": len(self._current_indicators),
            "active_directives": len(self._active_directives),
            "published_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_active_directives(self) -> list[MonetaryPolicyDirective]:
        """Return all currently active directives."""
        now = datetime.now(timezone.utc)
        self._active_directives = [
            d for d in self._active_directives
            if d.is_active(now)
        ]
        return self._active_directives

    def get_capabilities(self) -> list[str]:
        return [
            "monetary_policy_directives",
            "macroeconomic_monitoring",
            "dual_mandate_balancing",
            "portfolio_constraint_setting",
            "economic_outlook_publishing",
        ]
