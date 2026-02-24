"""
Due Process Workflows — Constitutional protection for all members.

Implements Art. III §4 and Amendment V: no restriction of a member's rights,
capabilities, or authority without:
1. Clear notice stating the nature and basis of the proposed restriction
2. A documented explanation citing constitutional and legislative authority
3. A minimum response period of 48 hours

Emergency restrictions remain subject to full judicial review within 7 days.

References:
    Article III §4 — Due Process
    Amendment V — Due Process protection
    Amendment VI — Right to Explanation
    Amendment VIII — Proportional Limitation
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from nova_syntheia.constitution.schema import Citation

logger = logging.getLogger(__name__)


class DueProcessNotice(BaseModel):
    """
    A due process notice — required before any restriction of member rights.

    Art. III §4: Clear notice to the affected member stating the nature
    and basis of the proposed restriction.
    """

    id: UUID = Field(default_factory=uuid4)
    affected_member_id: UUID
    issuing_authority: str = Field(description="Role ID of the issuing institution")
    restriction_type: str = Field(description="Nature of the proposed restriction")
    restriction_description: str = Field(description="Detailed description")
    constitutional_basis: list[Citation] = Field(
        description="Constitutional and legislative authority cited"
    )
    proportionality_justification: str = Field(
        default="",
        description="Why the restriction is proportionate to the risk (Amendment VIII)",
    )
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    response_deadline: datetime | None = None
    is_emergency: bool = False
    member_response: str | None = None
    member_response_at: datetime | None = None
    status: str = Field(
        default="pending",
        description="pending, responded, expired, enforced, withdrawn",
    )
    ledger_entry_id: UUID | None = None


class DueProcessManager:
    """
    Manages due process workflows for member rights protection.

    No restriction may be imposed without proper notice, explanation,
    and opportunity for review (Amendment V).
    """

    def __init__(
        self,
        response_period_hours: int = 48,
        ledger_service: Any = None,
    ) -> None:
        self.response_period_hours = response_period_hours
        self.ledger_service = ledger_service
        self.active_notices: dict[UUID, DueProcessNotice] = {}
        self.history: list[DueProcessNotice] = []

    def issue_notice(
        self,
        affected_member_id: UUID,
        issuing_authority: str,
        restriction_type: str,
        restriction_description: str,
        constitutional_basis: list[Citation],
        proportionality_justification: str = "",
        is_emergency: bool = False,
    ) -> DueProcessNotice:
        """
        Issue a due process notice to a member.

        The notice starts the response clock:
        - Normal: 48 hours (Art. III §4)
        - Emergency: immediate restriction but subject to 7-day judicial review

        Args:
            affected_member_id: The member facing restriction.
            issuing_authority: Role ID of the authority proposing restriction.
            restriction_type: Brief description of restriction type.
            restriction_description: Full explanation.
            constitutional_basis: Citations of authority for the restriction.
            proportionality_justification: Amendment VIII compliance.
            is_emergency: If True, restriction can take immediate effect.

        Returns:
            The DueProcessNotice.
        """
        now = datetime.utcnow()
        deadline = now + timedelta(hours=self.response_period_hours)

        notice = DueProcessNotice(
            affected_member_id=affected_member_id,
            issuing_authority=issuing_authority,
            restriction_type=restriction_type,
            restriction_description=restriction_description,
            constitutional_basis=constitutional_basis,
            proportionality_justification=proportionality_justification,
            issued_at=now,
            response_deadline=deadline,
            is_emergency=is_emergency,
        )

        self.active_notices[notice.id] = notice
        self.history.append(notice)

        logger.info(
            "Due process notice issued: member=%s type=%s deadline=%s emergency=%s",
            str(affected_member_id)[:8],
            restriction_type,
            deadline.isoformat(),
            is_emergency,
        )

        return notice

    def submit_response(
        self,
        notice_id: UUID,
        response: str,
    ) -> DueProcessNotice:
        """
        Submit a member's response to a due process notice.

        Art. III §4: The affected member may submit a written response
        during the response period.
        """
        notice = self.active_notices.get(notice_id)
        if notice is None:
            raise ValueError(f"Notice {notice_id} not found")

        if notice.status == "enforced":
            raise ValueError("Restriction already enforced. File a petition for review.")

        notice.member_response = response
        notice.member_response_at = datetime.utcnow()
        notice.status = "responded"

        logger.info(
            "Due process response submitted: notice=%s member=%s",
            str(notice_id)[:8],
            str(notice.affected_member_id)[:8],
        )

        return notice

    def can_enforce(self, notice_id: UUID) -> bool:
        """
        Check whether a restriction can now be enforced.

        Returns True if:
        - Emergency restriction (immediate effect per Art. VII), OR
        - Response period has elapsed, OR
        - Member has already responded
        """
        notice = self.active_notices.get(notice_id)
        if notice is None:
            return False

        if notice.is_emergency:
            return True

        if notice.status == "responded":
            return True

        if notice.response_deadline and datetime.utcnow() >= notice.response_deadline:
            return True

        return False

    def enforce(self, notice_id: UUID) -> DueProcessNotice:
        """Mark a restriction as enforced."""
        notice = self.active_notices.get(notice_id)
        if notice is None:
            raise ValueError(f"Notice {notice_id} not found")

        if not self.can_enforce(notice_id):
            raise ValueError(
                "Cannot enforce: response period has not elapsed and no response "
                "received. Due process requires opportunity for review (Amendment V)."
            )

        notice.status = "enforced"
        logger.info("Restriction enforced: notice=%s", str(notice_id)[:8])
        return notice

    def withdraw(self, notice_id: UUID) -> DueProcessNotice:
        """Withdraw a due process notice."""
        notice = self.active_notices.get(notice_id)
        if notice is None:
            raise ValueError(f"Notice {notice_id} not found")

        notice.status = "withdrawn"
        logger.info("Due process notice withdrawn: %s", str(notice_id)[:8])
        return notice

    def get_pending_notices(self, member_id: UUID | None = None) -> list[DueProcessNotice]:
        """Get all pending (unresolved) due process notices."""
        notices = [
            n for n in self.active_notices.values()
            if n.status in ("pending", "responded")
        ]
        if member_id:
            notices = [n for n in notices if n.affected_member_id == member_id]
        return notices
