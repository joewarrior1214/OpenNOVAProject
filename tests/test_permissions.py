"""
Tests for the Permission Engine — Art. II §2.

Validates:
- Permission tier enforcement
- Escalation paths
- Founder override authority
"""

from __future__ import annotations

import pytest

from nova_syntheia.governance.permissions import (
    PermissionDecision,
    PermissionEngine,
    permission_engine,
)
from nova_syntheia.constitution.schema import (
    ActionType,
    FOUNDING_PERMISSION_TIERS,
    FOUNDING_ROLES,
)


class TestPermissionEngine:
    """Test the constitutional permission engine."""

    def setup_method(self):
        self.engine = PermissionEngine()

    def test_custodian_allowed_ledger_operations(self):
        """Ledger Custodian should be allowed to write ledger entries."""
        result = self.engine.check_permission(
            tier_id="tier_0",
            action_type=ActionType.WRITE_LEDGER_ENTRY,
        )
        assert result.decision == PermissionDecision.AUTHORIZED

    def test_custodian_denied_executive_actions(self):
        """Ledger Custodian should NOT be allowed to execute trades."""
        result = self.engine.check_permission(
            tier_id="tier_0",
            action_type=ActionType.PORTFOLIO_TRADE,
        )
        assert result.decision in (
            PermissionDecision.FORBIDDEN,
            PermissionDecision.REQUIRES_APPROVAL,
        )

    def test_portfolio_executive_can_trade(self):
        """Portfolio Executive should be authorized or require approval to trade."""
        result = self.engine.check_permission(
            tier_id="tier_3",
            action_type=ActionType.PORTFOLIO_TRADE,
        )
        # Tier 3 may require approval for trades (constitutional safeguard)
        assert result.decision in (
            PermissionDecision.AUTHORIZED,
            PermissionDecision.REQUIRES_APPROVAL,
        )

    def test_advisory_cannot_trade(self):
        """Advisory tier (judicial) should not be able to trade."""
        result = self.engine.check_permission(
            tier_id="tier_1",
            action_type=ActionType.PORTFOLIO_TRADE,
        )
        assert result.decision != PermissionDecision.AUTHORIZED

    def test_founder_can_legislate(self):
        """Founder tier should be authorized for legislative actions."""
        result = self.engine.check_permission(
            tier_id="tier_founder",
            action_type=ActionType.PROPOSE_LEGISLATION,
        )
        assert result.decision == PermissionDecision.AUTHORIZED

    def test_global_permission_engine_exists(self):
        """The global permission_engine should be initialized."""
        assert permission_engine is not None
        assert isinstance(permission_engine, PermissionEngine)


class TestPermissionTiers:
    """Test that all founding permission tiers are properly defined."""

    def test_all_tiers_exist(self):
        expected = ["tier_0", "tier_1", "tier_2", "tier_3", "tier_4", "tier_founder"]
        for tier_id in expected:
            assert tier_id in FOUNDING_PERMISSION_TIERS

    def test_tier_ordering(self):
        """Lower tiers should have fewer permissions than higher tiers."""
        tier_0 = FOUNDING_PERMISSION_TIERS["tier_0"]
        tier_4 = FOUNDING_PERMISSION_TIERS["tier_4"]
        # tier_0 (Custodial) should have fewer autonomous actions than tier_4 (Monetary)
        assert len(tier_0.autonomous_actions) <= len(tier_4.autonomous_actions)

    def test_founder_tier_level_highest(self):
        """Founder tier should have the highest level."""
        founder = FOUNDING_PERMISSION_TIERS["tier_founder"]
        assert founder.level == 99
