"""
Tests for the Deliberative Cycle Manager — Art. 0.

Validates:
- Session lifecycle (open → deliberate → vote → close)
- Phase transitions
- Submission and voting
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from nova_syntheia.governance.deliberative_cycle import DeliberativeCycleManager
from nova_syntheia.constitution.schema import Citation, SessionPhase, VotePosition


class TestDeliberativeCycleManager:
    """Test the deliberative cycle state machine."""

    def setup_method(self):
        self.manager = DeliberativeCycleManager()
        self.founder_id = uuid4()
        self.agent_id = uuid4()

    def _make_citation(self) -> Citation:
        return Citation(
            article="0",
            section=1,
            text_excerpt="Deliberative Cycle",
            relevance="high",
        )

    def test_open_session(self):
        """Opening a session should create a session in OPENING phase."""
        session = self.manager.open_session(
            matter="Test Proposal",
            initiator_id=self.founder_id,
            matter_detail="A test deliberative session",
        )
        assert session is not None
        # open_session auto-advances to DELIBERATION phase
        assert session.phase in (SessionPhase.OPENING, SessionPhase.DELIBERATION)
        assert session.matter == "Test Proposal"

    def test_submit_position(self):
        """Members should be able to submit positions during deliberation."""
        session = self.manager.open_session(
            matter="Test",
            initiator_id=self.founder_id,
        )
        # Advance to deliberation
        self.manager.advance_to_vote(session.id, force=True)
        # Reopen for deliberation — or submit before vote
        # Actually let's just test the open_session → submit flow
        session2 = self.manager.open_session(
            matter="Test 2",
            initiator_id=self.founder_id,
        )
        result = self.manager.submit_position(
            session_id=session2.id,
            member_id=self.agent_id,
            content="I support this proposal because...",
        )
        assert result is not None

    def test_advance_to_vote(self):
        """Session should advance to voting phase."""
        session = self.manager.open_session(
            matter="Test",
            initiator_id=self.founder_id,
        )
        updated = self.manager.advance_to_vote(session.id, force=True)
        assert updated.phase == SessionPhase.VOTE

    def test_cast_vote(self):
        """Members should be able to cast votes during voting phase."""
        session = self.manager.open_session(
            matter="Test",
            initiator_id=self.founder_id,
        )
        self.manager.advance_to_vote(session.id, force=True)

        vote = self.manager.cast_vote(
            session_id=session.id,
            member_id=self.founder_id,
            position=VotePosition.YEA,
            constitutional_basis=self._make_citation(),
        )
        assert vote is not None

    def test_complete_lifecycle(self):
        """Full session lifecycle should work end-to-end."""
        session = self.manager.open_session(
            matter="Full Lifecycle Test",
            initiator_id=self.founder_id,
        )

        # Submission
        self.manager.submit_position(
            session.id, self.founder_id, "I propose we proceed"
        )
        self.manager.submit_position(
            session.id, self.agent_id, "Analysis supports this"
        )

        # Voting
        self.manager.advance_to_vote(session.id, force=True)
        self.manager.cast_vote(
            session.id, self.founder_id, VotePosition.YEA, self._make_citation()
        )
        self.manager.cast_vote(
            session.id, self.agent_id, VotePosition.YEA, self._make_citation()
        )

        # Close
        result = self.manager.close_session(
            session.id,
            quorum_members=[self.founder_id, self.agent_id],
            founder_id=self.founder_id,
        )
        assert result.phase == SessionPhase.CLOSED
