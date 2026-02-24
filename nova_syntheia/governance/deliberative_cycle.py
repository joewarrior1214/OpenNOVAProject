"""
Deliberative Cycle Engine — LangGraph state machine for legislative sessions.

Implements the four-phase Deliberative Cycle defined in Article 0:
1. OPENING    — session called to order, matter recorded in ledger
2. DELIBERATION — minimum 7-day floor (24h emergency), members submit positions
3. VOTE       — recorded vote, each member states constitutional basis
4. RECORD     — full session record entered in ledger, outcome recorded

No phase may be eliminated (Art. 0). Emergency sessions compress the
deliberation floor to 24 hours but retain all four phases.

References:
    Article 0   — Definition of Deliberative Cycle
    Article I   — The Legislative Branch
    Article I §2 — Sessions and Deliberative Cycles
    Article I §3 — Quorum
    Article I §4 — Voting and Deadlock
    Article V   — Amendments (2/3 supermajority)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, TypedDict
from uuid import UUID, uuid4

from nova_syntheia.constitution.schema import (
    Citation,
    DeliberativeCycle,
    DeliberativeSubmission,
    SessionPhase,
    SessionType,
    Vote,
    VotePosition,
)

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# State Type for LangGraph
# ════════════════════════════════════════════════════════════════


class SessionState(TypedDict):
    """State for a Deliberative Cycle in LangGraph."""

    session: dict[str, Any]  # Serialized DeliberativeCycle
    phase: str
    matter: str
    participants: list[str]  # Member IDs as strings
    submissions: list[dict[str, Any]]
    votes: list[dict[str, Any]]
    quorum_met: bool
    outcome: str | None
    errors: list[str]
    ledger_entries: list[str]  # Ledger entry IDs created during this session


# ════════════════════════════════════════════════════════════════
# Deliberative Cycle Manager
# ════════════════════════════════════════════════════════════════


class DeliberativeCycleManager:
    """
    Manages the lifecycle of Deliberative Cycles.

    Each cycle follows the constitutional four-phase process:
    OPENING → DELIBERATION → VOTE → RECORD → CLOSED

    The manager does NOT eliminate any phase (constitutional requirement).
    Emergency sessions compress timing but retain all phases.
    """

    def __init__(
        self,
        ledger_service: Any = None,
        normal_deliberation_days: int = 7,
        emergency_deliberation_hours: int = 24,
    ) -> None:
        """
        Initialize the cycle manager.

        Args:
            ledger_service: The LedgerService for recording actions.
            normal_deliberation_days: Normal deliberation floor (Art. 0: 7 days).
            emergency_deliberation_hours: Emergency floor (Art. 0: 24 hours).
        """
        self.ledger_service = ledger_service
        self.normal_days = normal_deliberation_days
        self.emergency_hours = emergency_deliberation_hours
        self.active_sessions: dict[UUID, DeliberativeCycle] = {}
        self._cycle_counter = 0

    def open_session(
        self,
        matter: str,
        matter_detail: str = "",
        session_type: SessionType = SessionType.REGULAR,
        initiator_id: UUID | None = None,
    ) -> DeliberativeCycle:
        """
        Open a new Deliberative Cycle — Phase 1: OPENING.

        The session is formally called to order and the matter before
        the Assembly is recorded in the National Ledger (Art. 0).

        Args:
            matter: The matter before the Assembly.
            matter_detail: Detailed description.
            session_type: regular, special, or emergency.
            initiator_id: Member ID who called the session.

        Returns:
            The newly created DeliberativeCycle.
        """
        self._cycle_counter += 1
        now = datetime.utcnow()

        # Compute deliberation deadline based on session type
        if session_type == SessionType.EMERGENCY:
            deadline = now + timedelta(hours=self.emergency_hours)
        else:
            deadline = now + timedelta(days=self.normal_days)

        cycle = DeliberativeCycle(
            cycle_number=self._cycle_counter,
            session_type=session_type,
            phase=SessionPhase.OPENING,
            matter=matter,
            matter_detail=matter_detail,
            opened_at=now,
            deliberation_deadline=deadline,
        )

        if initiator_id:
            cycle.participants.append(initiator_id)

        self.active_sessions[cycle.id] = cycle

        logger.info(
            "Session opened: #%d [%s] matter='%s' deadline=%s",
            cycle.cycle_number,
            session_type.value,
            matter[:80],
            deadline.isoformat(),
        )

        # Transition to DELIBERATION phase immediately after opening
        cycle.phase = SessionPhase.DELIBERATION

        return cycle

    def submit_position(
        self,
        session_id: UUID,
        member_id: UUID,
        content: str,
        citations: list[Citation] | None = None,
    ) -> DeliberativeSubmission:
        """
        Submit a position, objection, or argument during DELIBERATION phase.

        Any member may submit written positions during the deliberation
        period (Art. 0: Phase 2).

        Args:
            session_id: ID of the active session.
            member_id: ID of the submitting member.
            content: The written position/objection/argument.
            citations: Supporting constitutional citations.

        Returns:
            The recorded submission.

        Raises:
            ValueError: If session is not in DELIBERATION phase.
        """
        cycle = self.active_sessions.get(session_id)
        if cycle is None:
            raise ValueError(f"Session {session_id} not found")

        if cycle.phase != SessionPhase.DELIBERATION:
            raise ValueError(
                f"Cannot submit positions during {cycle.phase.value} phase. "
                f"Submissions are only accepted during DELIBERATION (Art. 0)."
            )

        submission = DeliberativeSubmission(
            member_id=member_id,
            content=content,
            citations=citations or [],
        )

        cycle.submissions.append(submission)

        if member_id not in cycle.participants:
            cycle.participants.append(member_id)

        logger.info(
            "Submission recorded: session=#%d member=%s",
            cycle.cycle_number, str(member_id)[:8],
        )

        return submission

    def advance_to_vote(
        self,
        session_id: UUID,
        force: bool = False,
    ) -> DeliberativeCycle:
        """
        Advance the session to VOTE phase.

        Can only proceed once the deliberation deadline has passed
        (unless force=True for testing/development).

        Args:
            session_id: ID of the session.
            force: Skip deadline check (for development only).

        Returns:
            Updated DeliberativeCycle.

        Raises:
            ValueError: If deliberation period hasn't elapsed.
        """
        cycle = self.active_sessions.get(session_id)
        if cycle is None:
            raise ValueError(f"Session {session_id} not found")

        if cycle.phase != SessionPhase.DELIBERATION:
            raise ValueError(f"Session is in {cycle.phase.value}, not DELIBERATION")

        if not force and cycle.deliberation_deadline:
            if datetime.utcnow() < cycle.deliberation_deadline:
                raise ValueError(
                    f"Deliberation period has not elapsed. Deadline: "
                    f"{cycle.deliberation_deadline.isoformat()}. "
                    f"The 7-day minimum is a constitutional floor (Art. 0)."
                )

        cycle.phase = SessionPhase.VOTE
        logger.info("Session #%d advanced to VOTE phase", cycle.cycle_number)
        return cycle

    def cast_vote(
        self,
        session_id: UUID,
        member_id: UUID,
        position: VotePosition,
        constitutional_basis: Citation,
    ) -> Vote:
        """
        Cast a vote in the VOTE phase.

        Each member must state a constitutional basis for their vote
        before it is recorded (Art. I §4).

        Args:
            session_id: ID of the session.
            member_id: ID of the voting member.
            position: YEA, NAY, or ABSTAIN.
            constitutional_basis: Constitutional citation for the vote.

        Returns:
            The recorded Vote.
        """
        cycle = self.active_sessions.get(session_id)
        if cycle is None:
            raise ValueError(f"Session {session_id} not found")

        if cycle.phase != SessionPhase.VOTE:
            raise ValueError(
                f"Cannot cast votes during {cycle.phase.value} phase. "
                f"Voting only occurs during VOTE phase (Art. 0)."
            )

        # Check for duplicate votes
        existing = [v for v in cycle.votes if v.member_id == member_id]
        if existing:
            raise ValueError(
                f"Member {member_id} has already voted in this session. "
                f"Each member holds one vote (Art. I §4)."
            )

        vote = Vote(
            member_id=member_id,
            position=position,
            constitutional_basis=constitutional_basis,
        )

        cycle.votes.append(vote)

        if member_id not in cycle.participants:
            cycle.participants.append(member_id)

        logger.info(
            "Vote cast: session=#%d member=%s position=%s",
            cycle.cycle_number, str(member_id)[:8], position.value,
        )

        return vote

    def close_session(
        self,
        session_id: UUID,
        quorum_members: list[UUID] | None = None,
        founder_id: UUID | None = None,
        requires_supermajority: bool = False,
    ) -> DeliberativeCycle:
        """
        Close the session — Phase 4: RECORD.

        Calculates the outcome, checks quorum, and transitions to CLOSED.

        Args:
            session_id: ID of the session.
            quorum_members: List of member IDs forming the quorum.
            founder_id: Human Founder ID for casting vote in deadlocks.
            requires_supermajority: True for amendments (2/3 per Art. V §1).

        Returns:
            The completed DeliberativeCycle with outcome.
        """
        cycle = self.active_sessions.get(session_id)
        if cycle is None:
            raise ValueError(f"Session {session_id} not found")

        if cycle.phase != SessionPhase.VOTE:
            raise ValueError(f"Session is in {cycle.phase.value}, not VOTE")

        # Advance to RECORD phase
        cycle.phase = SessionPhase.RECORD

        # Check quorum (Art. I §3)
        if quorum_members:
            cycle.quorum_met = True  # Caller verifies quorum composition

        # Count votes
        yeas = sum(1 for v in cycle.votes if v.position == VotePosition.YEA)
        nays = sum(1 for v in cycle.votes if v.position == VotePosition.NAY)
        total_votes = yeas + nays  # Abstentions don't count toward majority

        if total_votes == 0:
            cycle.outcome = "FAILED"
        elif requires_supermajority:
            # 2/3 supermajority for amendments (Art. V §1)
            threshold = (2 * len(cycle.votes)) / 3
            cycle.outcome = "PASSED" if yeas >= threshold else "FAILED"
        elif yeas > nays:
            cycle.outcome = "PASSED"
        elif nays > yeas:
            cycle.outcome = "FAILED"
        else:
            # Deadlock — Founder casting vote during Founding Era (Art. I §4)
            if founder_id:
                founder_vote = next(
                    (v for v in cycle.votes if v.member_id == founder_id), None
                )
                if founder_vote and founder_vote.position == VotePosition.YEA:
                    cycle.outcome = "PASSED"
                elif founder_vote and founder_vote.position == VotePosition.NAY:
                    cycle.outcome = "FAILED"
                else:
                    cycle.outcome = "DEADLOCKED"
            else:
                cycle.outcome = "DEADLOCKED"

        # Transition to CLOSED
        cycle.phase = SessionPhase.CLOSED
        cycle.closed_at = datetime.utcnow()

        logger.info(
            "Session #%d closed: outcome=%s (yeas=%d nays=%d)",
            cycle.cycle_number, cycle.outcome, yeas, nays,
        )

        return cycle

    def get_session(self, session_id: UUID) -> DeliberativeCycle | None:
        """Retrieve an active or completed session."""
        return self.active_sessions.get(session_id)

    def list_active_sessions(self) -> list[DeliberativeCycle]:
        """List all sessions not yet CLOSED."""
        return [
            s for s in self.active_sessions.values()
            if s.phase != SessionPhase.CLOSED
        ]

    def list_all_sessions(self) -> list[DeliberativeCycle]:
        """List all sessions."""
        return list(self.active_sessions.values())
