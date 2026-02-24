"""
Tests for the Constitutional Schema — verifies all Pydantic models.

Validates:
- Enum completeness
- Model instantiation
- Founding roles and permission tiers
- Computed fields
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from nova_syntheia.constitution.schema import (
    ActionType,
    Branch,
    Citation,
    ConstitutionalRole,
    FOUNDING_PERMISSION_TIERS,
    FOUNDING_ROLES,
    LedgerEntry,
    LedgerEntryType,
    Member,
    MemberStatus,
    MemberType,
    MembershipTier,
    PermissionTier,
    SessionPhase,
    VotePosition,
)


class TestEnums:
    """Verify constitutional enums are properly defined."""

    def test_branch_values(self):
        assert Branch.EXECUTIVE is not None
        assert Branch.JUDICIAL is not None
        assert Branch.FEDERAL_RESERVE is not None
        assert Branch.CUSTODIAN is not None
        # No FOUNDER branch — founder uses LEGISLATIVE or is special

    def test_member_type(self):
        assert MemberType.HUMAN is not None
        assert MemberType.ARTIFICIAL is not None

    def test_session_phases(self):
        # Actual phases: opening, deliberation, vote, record, closed
        phases = [SessionPhase.OPENING, SessionPhase.DELIBERATION, SessionPhase.VOTE, SessionPhase.RECORD]
        assert len(phases) == 4

    def test_vote_positions(self):
        # Actual values: yea, nay, abstain
        assert VotePosition.YEA is not None
        assert VotePosition.NAY is not None
        assert VotePosition.ABSTAIN is not None

    def test_action_types_comprehensive(self):
        """ActionType should have all major constitutional actions."""
        action_names = [a.value for a in ActionType]
        assert "portfolio_trade" in action_names
        assert "write_ledger_entry" in action_names
        assert "verify_chain" in action_names
        assert "issue_monetary_directive" in action_names


class TestFoundingRoles:
    """Test the predefined Founding Era roles."""

    def test_all_founding_roles_exist(self):
        expected_roles = [
            "human_founder",
            "operations_executive",
            "portfolio_executive",
            "policy_evaluation",
            "monetary_policy",
            "ledger_custodian",
        ]
        for role_name in expected_roles:
            assert role_name in FOUNDING_ROLES, f"Missing founding role: {role_name}"

    def test_founding_roles_have_branches(self):
        for name, role in FOUNDING_ROLES.items():
            assert role.branch is not None, f"Role {name} missing branch"
            assert isinstance(role.branch, Branch)

    def test_founder_is_legislative(self):
        founder = FOUNDING_ROLES["human_founder"]
        assert founder.branch == Branch.LEGISLATIVE

    def test_portfolio_is_executive(self):
        portfolio = FOUNDING_ROLES["portfolio_executive"]
        assert portfolio.branch == Branch.EXECUTIVE


class TestFoundingPermissionTiers:
    """Test the predefined Founding Era permission tiers."""

    def test_all_tiers_have_autonomous_actions(self):
        for tier_id, tier in FOUNDING_PERMISSION_TIERS.items():
            assert isinstance(tier.autonomous_actions, list), f"Tier {tier_id} missing autonomous_actions"

    def test_founder_tier_is_most_permissive(self):
        founder_tier = FOUNDING_PERMISSION_TIERS["tier_founder"]
        for tier_id, tier in FOUNDING_PERMISSION_TIERS.items():
            if tier_id != "tier_founder":
                assert len(founder_tier.autonomous_actions) >= len(tier.autonomous_actions)


class TestCitationModel:
    """Test the Citation Pydantic model."""

    def test_citation_reference_computed(self):
        c = Citation(
            article="VIII",
            section=2,
            text_excerpt="cryptographically verifiable",
            relevance="high",
        )
        assert "VIII" in c.reference
        assert "2" in c.reference

    def test_citation_amendment(self):
        c = Citation(
            amendment=4,
            text_excerpt="right to constitutional citation",
            relevance="high",
        )
        assert "4" in c.reference or "IV" in c.reference


class TestMemberModel:
    """Test the Member model — Art. I §4 constitutional instantiation."""

    def test_create_human_member(self):
        m = Member(
            id=uuid4(),
            name="Alice Founder",
            member_type=MemberType.HUMAN,
            status=MemberStatus.ACTIVE,
            tier=MembershipTier.FOUNDING,
        )
        assert m.member_type == MemberType.HUMAN

    def test_create_artificial_member(self):
        m = Member(
            id=uuid4(),
            name="Operations Agent",
            member_type=MemberType.ARTIFICIAL,
            status=MemberStatus.ACTIVE,
            tier=MembershipTier.FULL,
        )
        assert m.member_type == MemberType.ARTIFICIAL


class TestLedgerEntryModel:
    """Test the LedgerEntry model — Art. VIII."""

    def test_create_declaration_entry(self):
        entry = LedgerEntry(
            id=uuid4(),
            sequence_number=0,
            entry_type=LedgerEntryType.DECLARATION,
            author_role="system",
            author_member_id=uuid4(),
            content={"genesis": True},
            previous_hash="0" * 64,
        )
        assert entry.sequence_number == 0
        assert entry.entry_type == LedgerEntryType.DECLARATION

    def test_entry_hash_is_sha256(self):
        entry = LedgerEntry(
            id=uuid4(),
            sequence_number=1,
            entry_type=LedgerEntryType.EXECUTIVE_ACTION,
            author_role="test",
            author_member_id=uuid4(),
            content={"test": True},
            previous_hash="0" * 64,
        )
        h = entry.compute_hash()
        assert len(h) == 64
