"""
National Ledger — SQLAlchemy models for the immutable institutional record.

The National Ledger is a constitutional institution (Art. VIII §1). Its integrity
is a constitutional requirement. These models implement the three integrity
requirements of Art. VIII §2:

1. Cryptographically Verifiable — SHA-256 hash chain
2. Append-Only — no UPDATE or DELETE; corrections via superseding entries
3. Independently Auditable — hash chain can be verified by any member

References:
    Article VIII — The National Ledger
    Article 0 — Definition of National Ledger
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ledger models."""
    pass


class LedgerEntryTypeDB(str, enum.Enum):
    """Ledger entry types — mirrors schema.LedgerEntryType for DB enum."""

    GENESIS = "genesis"
    DECLARATION = "declaration"
    CONSTITUTION = "constitution"
    TECHNICAL_CHARTER = "technical_charter"
    AMENDMENT = "amendment"
    SESSION_OPENING = "session_opening"
    DELIBERATION_SUBMISSION = "deliberation_submission"
    VOTE_RECORD = "vote_record"
    SESSION_RECORD = "session_record"
    STANDING_ORDER = "standing_order"
    EXECUTIVE_ACTION = "executive_action"
    JUDICIAL_OPINION = "judicial_opinion"
    PETITION = "petition"
    PETITION_RESPONSE = "petition_response"
    INJUNCTION = "injunction"
    MONETARY_POLICY_DIRECTIVE = "monetary_policy_directive"
    MEMBERSHIP_ADMISSION = "membership_admission"
    INSTANTIATION_RECORD = "instantiation_record"
    NATURALIZATION = "naturalization"
    EMERGENCY_ACTIVATION = "emergency_activation"
    EMERGENCY_ACTION = "emergency_action"
    EMERGENCY_DEACTIVATION = "emergency_deactivation"
    POST_EMERGENCY_REVIEW = "post_emergency_review"
    CONSTITUTIONAL_REVIEW = "constitutional_review"


class LedgerEntryDB(Base):
    """
    A single entry in the National Ledger — the permanent institutional record.

    This table is APPEND-ONLY. No rows may be updated or deleted.
    Corrections are made by new entries with `supersedes` pointing to the
    original (Art. VIII §2).

    The hash chain: each entry stores the SHA-256 hash of
    (previous_hash || canonical_json(content)), ensuring that any retroactive
    alteration is detectable by any member (Art. VIII §2).
    """

    __tablename__ = "ledger_entries"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Chain ordering
    sequence_number = Column(
        Integer, nullable=False, unique=True, index=True,
        comment="Monotonically increasing sequence number",
    )

    # Hash chain (Art. VIII §2 — cryptographically verifiable)
    previous_hash = Column(
        String(64), nullable=False,
        comment="SHA-256 hash of the previous entry",
    )
    entry_hash = Column(
        String(64), nullable=False, unique=True,
        comment="SHA-256 hash of this entry",
    )

    # Timestamp
    timestamp = Column(
        DateTime(timezone=True), nullable=False, default=func.now(),
        comment="When this entry was recorded",
    )

    # Entry classification
    entry_type = Column(
        String(50), nullable=False, index=True,
        comment="Type of ledger entry (Art. VIII §3)",
    )

    # Authorship (Art. II §3 — role identifier)
    author_role = Column(
        String(100), nullable=False,
        comment="Constitutional role ID of the author",
    )
    author_member_id = Column(
        UUID(as_uuid=True), nullable=False,
        comment="Member ID of the author",
    )

    # Content — JSONB for structured, queryable content
    content = Column(
        JSONB, nullable=False,
        comment="Entry content — structure varies by entry_type",
    )

    # Superseding chain (Art. VIII §2 — corrections)
    supersedes = Column(
        UUID(as_uuid=True), ForeignKey("ledger_entries.id"), nullable=True,
        comment="ID of entry this supersedes (original preserved)",
    )

    # Emergency designation (Art. VII §3)
    emergency_designation = Column(
        Boolean, nullable=False, default=False,
        comment="Whether entry was made under Emergency Powers",
    )

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_ledger_entry_type_timestamp", "entry_type", "timestamp"),
        Index("ix_ledger_author_role", "author_role"),
        Index("ix_ledger_author_member", "author_member_id"),
        Index("ix_ledger_emergency", "emergency_designation"),
        {
            "comment": (
                "National Ledger of Nova Syntheia — permanent, immutable, "
                "cryptographically verifiable institutional record (Art. VIII)"
            ),
        },
    )

    def __repr__(self) -> str:
        return (
            f"<LedgerEntry seq={self.sequence_number} "
            f"type={self.entry_type} hash={self.entry_hash[:12]}...>"
        )


class MemberDB(Base):
    """
    Members of Nova Syntheia — human and artificial (Art. IV).

    Membership records are also recorded in the National Ledger,
    but this table provides efficient querying for operational purposes.
    """

    __tablename__ = "members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    member_type = Column(
        String(20), nullable=False,
        comment="'human' or 'artificial' (Art. IV)",
    )
    name = Column(String(200), nullable=False)
    role_id = Column(
        String(100), nullable=True,
        comment="Constitutional role ID",
    )
    membership_tier = Column(
        String(20), nullable=False, default="provisional",
        comment="founding, full, or provisional (Art. IV §4)",
    )
    permission_tier_id = Column(
        String(50), nullable=True,
        comment="Assigned permission tier ID",
    )
    status = Column(
        String(20), nullable=False, default="active",
        comment="active, suspended, or inactive",
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=func.now(),
    )

    # Instantiation criteria (Art. IV §2)
    has_role_definition = Column(Boolean, nullable=False, default=False)
    instantiation_ledger_entry_id = Column(
        UUID(as_uuid=True), nullable=True,
        comment="Criterion 2: ledger entry recording instantiation",
    )
    has_permission_tier = Column(Boolean, nullable=False, default=False)
    has_citation_capability = Column(Boolean, nullable=False, default=False)
    admitted_by_session_id = Column(
        UUID(as_uuid=True), nullable=True,
        comment="Session ID that admitted this member",
    )

    __table_args__ = (
        Index("ix_member_role", "role_id"),
        Index("ix_member_status", "status"),
    )


class SessionDB(Base):
    """
    Deliberative Cycle sessions (Art. 0, Art. I §2).

    Tracks the lifecycle of each legislative session through its phases.
    """

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    cycle_number = Column(Integer, nullable=False, unique=True)
    session_type = Column(
        String(20), nullable=False, default="regular",
        comment="regular, special, or emergency",
    )
    phase = Column(
        String(20), nullable=False, default="opening",
        comment="Current phase: opening, deliberation, vote, record, closed",
    )
    matter = Column(Text, nullable=False, comment="Matter before the Assembly")
    matter_detail = Column(Text, nullable=True)

    opened_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    deliberation_deadline = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    quorum_met = Column(Boolean, nullable=False, default=False)
    outcome = Column(
        String(20), nullable=True,
        comment="PASSED, FAILED, or DEADLOCKED",
    )
    session_record_entry_id = Column(
        UUID(as_uuid=True), nullable=True,
        comment="Ledger entry ID of final session record",
    )


class JudicialOpinionDB(Base):
    """
    Judicial opinions in the Constitutional Record (Art. III §3).

    Establishes binding precedent. Part of the living legal tradition.
    """

    __tablename__ = "judicial_opinions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_number = Column(String(50), nullable=False, unique=True)
    opinion_type = Column(
        String(30), nullable=False,
        comment="review, interpretation, audit, petition_response, injunction",
    )
    petitioner_id = Column(UUID(as_uuid=True), nullable=True)
    subject_action_id = Column(UUID(as_uuid=True), nullable=True)
    constitutional_questions = Column(
        JSONB, nullable=False, default=list,
        comment="Questions addressed in this opinion",
    )
    holding = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=False)
    citations = Column(JSONB, nullable=False, default=list)
    precedents_considered = Column(JSONB, nullable=False, default=list)
    disposition = Column(
        String(20), nullable=False,
        comment="upheld, overturned, remanded, advisory",
    )
    binding = Column(Boolean, nullable=False, default=True)
    dissent = Column(Text, nullable=True)
    issued_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    ledger_entry_id = Column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        Index("ix_opinion_type", "opinion_type"),
        Index("ix_opinion_disposition", "disposition"),
    )


class MonetaryDirectiveDB(Base):
    """
    Monetary Policy Directives from the Federal Reserve (Art. VI §4).

    Constitutes binding constraints on Executive Branch portfolio operations.
    """

    __tablename__ = "monetary_directives"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    directive_number = Column(Integer, nullable=False, unique=True)
    directive_type = Column(
        String(20), nullable=False, default="regular",
    )
    macroeconomic_justification = Column(Text, nullable=False)
    indicators_assessed = Column(JSONB, nullable=False, default=list)
    mandate_tension = Column(Text, nullable=True)
    stance = Column(
        String(30), nullable=False,
        comment="tightening or loosening",
    )
    constraints = Column(
        JSONB, nullable=False, default=list,
        comment="Binding portfolio constraints",
    )
    permissible_asset_classes = Column(
        JSONB, nullable=False, default=lambda: ["ETF", "mutual_fund"],
    )
    effective_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    citations = Column(JSONB, nullable=False, default=list)
    issued_by = Column(UUID(as_uuid=True), nullable=True)
    ledger_entry_id = Column(UUID(as_uuid=True), nullable=True)


class EmergencyActivationDB(Base):
    """
    Emergency Powers activation records (Art. VII).
    """

    __tablename__ = "emergency_activations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    trigger_type = Column(String(30), nullable=False)
    trigger_data = Column(JSONB, nullable=False)
    activated_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    founder_notified = Column(Boolean, nullable=False, default=False)
    founder_notification_time = Column(DateTime(timezone=True), nullable=True)
    judicial_review_due = Column(DateTime(timezone=True), nullable=True)
    review_completed = Column(Boolean, nullable=False, default=False)
    review_opinion_id = Column(UUID(as_uuid=True), nullable=True)
