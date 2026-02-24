"""
Permission Tier Enforcement — Constitutional permission boundary middleware.

This module enforces the bounded autonomy principle (Art. II §2) and the
permission tier system. Every agent action passes through this middleware
before execution. Actions are classified as:

- AUTONOMOUS: within the agent's tier → proceed with logging
- REQUIRES_APPROVAL: above tier → escalate to Legislative/Judicial review
- FORBIDDEN: absolutely prohibited for this tier → deny immediately

The permission check happens at the tool/action level, not the prompt level.
This is critical: LLMs cannot truly be "prevented" from generating outputs,
but we CAN prevent those outputs from being executed.

References:
    Article II §2 — Bounded Autonomy
    Amendment III — No Unconsented Irreversible Execution
    Article V §2 — Separation of Powers (structural invariant)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Callable
from uuid import UUID

from nova_syntheia.constitution.schema import (
    ActionType,
    FOUNDING_PERMISSION_TIERS,
    PermissionTier,
)

logger = logging.getLogger(__name__)


class PermissionDecision(str, Enum):
    """Result of a permission check."""

    AUTHORIZED = "authorized"
    REQUIRES_APPROVAL = "requires_approval"
    FORBIDDEN = "forbidden"
    EXCEEDS_IRREVERSIBLE_THRESHOLD = "exceeds_irreversible_threshold"


@dataclass
class PermissionCheckResult:
    """Result of checking an action against a permission tier."""

    decision: PermissionDecision
    action_type: ActionType
    tier_id: str
    tier_name: str
    reason: str
    dollar_amount: Decimal | None = None
    threshold: Decimal | None = None

    @property
    def is_allowed(self) -> bool:
        return self.decision == PermissionDecision.AUTHORIZED


class PermissionEngine:
    """
    Central permission enforcement engine.

    Loads permission tiers from configuration (Legislative standing orders)
    and checks every proposed action against the acting agent's tier.

    This engine is the enforcement mechanism for Art. II §2: agents may not
    self-expand their own permissions or operational authority.
    """

    def __init__(self, tiers: dict[str, PermissionTier] | None = None) -> None:
        """
        Initialize with permission tiers.

        Args:
            tiers: Permission tier definitions. Defaults to Founding Era tiers.
        """
        self.tiers = tiers or dict(FOUNDING_PERMISSION_TIERS)

    def get_tier(self, tier_id: str) -> PermissionTier | None:
        """Retrieve a permission tier by ID."""
        return self.tiers.get(tier_id)

    def check_permission(
        self,
        tier_id: str,
        action_type: ActionType,
        dollar_amount: Decimal | None = None,
    ) -> PermissionCheckResult:
        """
        Check whether an action is permitted under a given tier.

        This is the core enforcement function. Every agent action MUST
        pass through this check before execution.

        Args:
            tier_id: The agent's assigned permission tier ID.
            action_type: The type of action being attempted.
            dollar_amount: Dollar amount for irreversible action threshold check.

        Returns:
            PermissionCheckResult with decision and reasoning.
        """
        tier = self.tiers.get(tier_id)
        if tier is None:
            return PermissionCheckResult(
                decision=PermissionDecision.FORBIDDEN,
                action_type=action_type,
                tier_id=tier_id,
                tier_name="UNKNOWN",
                reason=f"Unknown permission tier: {tier_id}",
            )

        # Check forbidden first (highest priority)
        if action_type in tier.forbidden_actions:
            return PermissionCheckResult(
                decision=PermissionDecision.FORBIDDEN,
                action_type=action_type,
                tier_id=tier_id,
                tier_name=tier.name,
                reason=(
                    f"Action {action_type.value} is FORBIDDEN for tier "
                    f"'{tier.name}'. This is a constitutional constraint "
                    f"under Art. II §2 and Art. V §2 (separation of powers)."
                ),
            )

        # Check if action requires approval
        if action_type in tier.requires_approval:
            return PermissionCheckResult(
                decision=PermissionDecision.REQUIRES_APPROVAL,
                action_type=action_type,
                tier_id=tier_id,
                tier_name=tier.name,
                reason=(
                    f"Action {action_type.value} requires prior approval "
                    f"under tier '{tier.name}'. Must be escalated to "
                    f"Legislative Assembly or appropriate authority "
                    f"(Art. II §2)."
                ),
            )

        # Check irreversible action threshold (Amendment III)
        if dollar_amount is not None and tier.irreversible_threshold > 0:
            if dollar_amount > tier.irreversible_threshold:
                return PermissionCheckResult(
                    decision=PermissionDecision.EXCEEDS_IRREVERSIBLE_THRESHOLD,
                    action_type=action_type,
                    tier_id=tier_id,
                    tier_name=tier.name,
                    reason=(
                        f"Action amount ${dollar_amount} exceeds irreversible "
                        f"action threshold of ${tier.irreversible_threshold} "
                        f"for tier '{tier.name}'. Prior authorization required "
                        f"(Amendment III)."
                    ),
                    dollar_amount=dollar_amount,
                    threshold=tier.irreversible_threshold,
                )

        # Check autonomous actions
        if action_type in tier.autonomous_actions:
            return PermissionCheckResult(
                decision=PermissionDecision.AUTHORIZED,
                action_type=action_type,
                tier_id=tier_id,
                tier_name=tier.name,
                reason=(
                    f"Action {action_type.value} is authorized as autonomous "
                    f"under tier '{tier.name}' (Art. II §2)."
                ),
            )

        # Action not explicitly listed — default to requires approval
        return PermissionCheckResult(
            decision=PermissionDecision.REQUIRES_APPROVAL,
            action_type=action_type,
            tier_id=tier_id,
            tier_name=tier.name,
            reason=(
                f"Action {action_type.value} is not explicitly listed in "
                f"tier '{tier.name}'. Defaulting to requires_approval per "
                f"constitutional precaution (Art. II §2)."
            ),
        )

    def update_tier(self, tier_id: str, tier: PermissionTier) -> None:
        """
        Update a permission tier (Legislative standing order change).

        This must be accompanied by a ledger entry recording the change.
        """
        self.tiers[tier_id] = tier
        logger.info("Permission tier updated: %s", tier_id)

    def list_tiers(self) -> dict[str, PermissionTier]:
        """Return all active permission tiers."""
        return dict(self.tiers)


# Global permission engine instance (initialized with Founding Era defaults)
permission_engine = PermissionEngine()
