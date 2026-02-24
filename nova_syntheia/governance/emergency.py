"""
Emergency Powers — Crisis detection and constitutional emergency response.

Implements Art. VII: automatic trigger detection, scoped emergency powers,
time-limited activation, and mandatory post-emergency judicial review.

Emergency Powers are a last resort, not a convenience (Art. VII §1).
They never suspend Bill of Rights protections (Art. VII §4).

References:
    Article VII — Emergency Powers
    Amendment III — No Unconsented Irreversible Execution
    Amendment V — Due Process (emergency restrictions subject to review)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from nova_syntheia.constitution.schema import (
    EmergencyActivation,
    EmergencyTriggerType,
)

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# Emergency Trigger Thresholds (Legislative Standing Orders)
# ════════════════════════════════════════════════════════════════

DEFAULT_TRIGGER_THRESHOLDS = {
    EmergencyTriggerType.PORTFOLIO_LOSS: {
        "threshold_percent": Decimal("15.0"),  # 15% decline
        "measurement_period_hours": 24,
    },
    EmergencyTriggerType.SYSTEMIC_MARKET_EVENT: {
        "circuit_breaker_level": 1,  # Level 1 or higher
    },
    EmergencyTriggerType.CONSTITUTIONAL_BREACH: {
        "auto_detect": True,  # Any structural invariant violation
    },
    EmergencyTriggerType.OPERATIONAL_FAILURE: {
        "max_agent_downtime_minutes": 30,
    },
    EmergencyTriggerType.INTEGRITY_THREAT: {
        "hash_chain_verification_failures": 1,  # Any failure
    },
}

DEFAULT_EMERGENCY_DURATION_HOURS = 48


class EmergencyPowersManager:
    """
    Emergency Powers Manager — detects, activates, and manages emergency powers.

    Automatic trigger conditions are defined in Art. VII §2.
    Emergency scope and limits are defined in Art. VII §3–4.
    Duration and review are defined in Art. VII §5.
    """

    def __init__(
        self,
        thresholds: dict | None = None,
        emergency_duration_hours: int = DEFAULT_EMERGENCY_DURATION_HOURS,
        ledger_service: Any = None,
    ) -> None:
        self.thresholds = thresholds or dict(DEFAULT_TRIGGER_THRESHOLDS)
        self.emergency_duration_hours = emergency_duration_hours
        self.ledger_service = ledger_service
        self.active_emergencies: dict[UUID, EmergencyActivation] = {}
        self.history: list[EmergencyActivation] = []

    def check_portfolio_loss(
        self,
        current_value: Decimal,
        reference_value: Decimal,
    ) -> EmergencyActivation | None:
        """
        Check if portfolio decline triggers Emergency Powers.

        Art. VII §2: Portfolio Loss Threshold — a decline exceeding the
        defined threshold within the defined measurement period.
        """
        if reference_value <= 0:
            return None

        decline_pct = ((reference_value - current_value) / reference_value) * 100
        threshold = self.thresholds.get(
            EmergencyTriggerType.PORTFOLIO_LOSS, {}
        ).get("threshold_percent", Decimal("15.0"))

        if decline_pct >= threshold:
            return self._activate(
                trigger_type=EmergencyTriggerType.PORTFOLIO_LOSS,
                trigger_data={
                    "current_value": str(current_value),
                    "reference_value": str(reference_value),
                    "decline_percent": str(decline_pct),
                    "threshold_percent": str(threshold),
                },
            )
        return None

    def check_integrity_threat(
        self,
        chain_valid: bool,
        details: str = "",
    ) -> EmergencyActivation | None:
        """
        Check if a ledger integrity failure triggers Emergency Powers.

        Art. VII §2: Integrity Threat — detection of an attempt to compromise
        the integrity of the National Ledger.
        """
        if not chain_valid:
            return self._activate(
                trigger_type=EmergencyTriggerType.INTEGRITY_THREAT,
                trigger_data={
                    "chain_valid": False,
                    "details": details,
                },
            )
        return None

    def check_operational_failure(
        self,
        agent_role: str,
        downtime_minutes: int,
    ) -> EmergencyActivation | None:
        """
        Check if agent downtime triggers Emergency Powers.

        Art. VII §2: Operational Failure — failure of a critical institutional
        agent rendering a constitutional branch unable to perform its functions.
        """
        max_downtime = self.thresholds.get(
            EmergencyTriggerType.OPERATIONAL_FAILURE, {}
        ).get("max_agent_downtime_minutes", 30)

        if downtime_minutes >= max_downtime:
            return self._activate(
                trigger_type=EmergencyTriggerType.OPERATIONAL_FAILURE,
                trigger_data={
                    "agent_role": agent_role,
                    "downtime_minutes": downtime_minutes,
                    "max_allowed_minutes": max_downtime,
                },
            )
        return None

    def check_constitutional_breach(
        self,
        violation_description: str,
        violating_action_id: UUID | None = None,
    ) -> EmergencyActivation | None:
        """
        Trigger Emergency Powers on constitutional breach detection.

        Art. VII §2: Constitutional Breach — detection of an executive action
        that violates a structural invariant without prior authorization.
        """
        return self._activate(
            trigger_type=EmergencyTriggerType.CONSTITUTIONAL_BREACH,
            trigger_data={
                "violation_description": violation_description,
                "violating_action_id": str(violating_action_id) if violating_action_id else None,
            },
        )

    def _activate(
        self,
        trigger_type: EmergencyTriggerType,
        trigger_data: dict[str, Any],
    ) -> EmergencyActivation:
        """
        Activate Emergency Powers.

        Art. VII §3: Upon activation:
        - Federal Reserve may issue emergency directives (24h compressed deliberation)
        - Executive Branch may take protective actions within emergency tier
        - Judicial Branch assumes continuous monitoring
        - Human Founder is notified immediately
        - All actions logged in real time with emergency designation
        """
        now = datetime.utcnow()
        expires = now + timedelta(hours=self.emergency_duration_hours)
        review_due = expires + timedelta(days=7)

        activation = EmergencyActivation(
            trigger_type=trigger_type,
            trigger_data=trigger_data,
            activated_at=now,
            expires_at=expires,
            judicial_review_due=review_due,
        )

        self.active_emergencies[activation.id] = activation
        self.history.append(activation)

        logger.critical(
            "EMERGENCY POWERS ACTIVATED: type=%s expires=%s trigger=%s",
            trigger_type.value,
            expires.isoformat(),
            str(trigger_data)[:200],
        )

        return activation

    def record_emergency_action(
        self,
        emergency_id: UUID,
        action_ledger_entry_id: UUID,
    ) -> None:
        """Record an action taken under Emergency Powers."""
        emergency = self.active_emergencies.get(emergency_id)
        if emergency:
            emergency.actions_taken.append(action_ledger_entry_id)

    def notify_founder(
        self,
        emergency_id: UUID,
    ) -> None:
        """Record that the Human Founder has been notified."""
        emergency = self.active_emergencies.get(emergency_id)
        if emergency:
            emergency.founder_notified = True
            emergency.founder_notification_time = datetime.utcnow()

    def deactivate(self, emergency_id: UUID) -> EmergencyActivation | None:
        """
        Deactivate an emergency (either by expiry or explicit deactivation).

        Art. VII §5: All actions taken under Emergency Powers are subject
        to full judicial review within 7 days of the emergency period concluding.
        """
        emergency = self.active_emergencies.pop(emergency_id, None)
        if emergency:
            logger.info(
                "Emergency Powers deactivated: id=%s type=%s actions_taken=%d",
                str(emergency.id)[:8],
                emergency.trigger_type.value,
                len(emergency.actions_taken),
            )
        return emergency

    def get_active_emergencies(self) -> list[EmergencyActivation]:
        """Return all currently active emergencies."""
        now = datetime.utcnow()
        active = []
        expired_ids = []

        for eid, emergency in self.active_emergencies.items():
            if now >= emergency.expires_at:
                expired_ids.append(eid)
            else:
                active.append(emergency)

        # Auto-expire (Art. VII §5)
        for eid in expired_ids:
            self.deactivate(eid)

        return active

    def is_emergency_active(self) -> bool:
        """Check if any Emergency Powers are currently active."""
        return len(self.get_active_emergencies()) > 0

    def get_pending_reviews(self) -> list[EmergencyActivation]:
        """
        Get emergencies awaiting post-emergency judicial review.

        Art. VII §5: Full judicial review within 7 days of emergency concluding.
        """
        return [
            e for e in self.history
            if not e.review_completed and not e.is_active
        ]
