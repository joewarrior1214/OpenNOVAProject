"""
Constitutional Schema — Pydantic models for all Nova Syntheia constitutional entities.

These models are the canonical data structures for every constitutional concept.
They govern the shape of data in the National Ledger, agent communications,
governance processes, and the dashboard. Defined per Article 0 and the
Technical Charter.

References:
    Article 0  — Definitions
    Article II — Executive Branch (§3 action record format)
    Article IV — Membership and Citizenship (§2 instantiation criteria)
    Article VIII — The National Ledger (§3 contents)
"""

from __future__ import annotations

import enum
import hashlib
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field


# ════════════════════════════════════════════════════════════════
# Enumerations
# ════════════════════════════════════════════════════════════════


class Branch(str, enum.Enum):
    """Constitutional branches of government (Art. V §2 structural invariant)."""

    LEGISLATIVE = "legislative"
    EXECUTIVE = "executive"
    JUDICIAL = "judicial"
    FEDERAL_RESERVE = "federal_reserve"
    CUSTODIAN = "custodian"  # National Ledger Custodianship


class MemberType(str, enum.Enum):
    """Member classification (Art. IV)."""

    HUMAN = "human"
    ARTIFICIAL = "artificial"


class MembershipTier(str, enum.Enum):
    """Membership tiers (Art. IV §4)."""

    FOUNDING = "founding"  # Human Founder
    FULL = "full"  # Completed probationary period
    PROVISIONAL = "provisional"  # Newly admitted, limited voting


class MemberStatus(str, enum.Enum):
    """Current operational status of a member."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class ActionType(str, enum.Enum):
    """Categories of institutional action for permission tier enforcement."""

    # Executive actions
    PORTFOLIO_TRADE = "portfolio_trade"
    PORTFOLIO_REBALANCE = "portfolio_rebalance"
    ROUTINE_OPERATION = "routine_operation"
    AGENT_COORDINATION = "agent_coordination"
    NOTIFICATION_DISPATCH = "notification_dispatch"
    SESSION_MANAGEMENT = "session_management"

    # Legislative actions
    PROPOSE_LEGISLATION = "propose_legislation"
    CAST_VOTE = "cast_vote"
    INITIATE_SESSION = "initiate_session"
    ADMIT_MEMBER = "admit_member"

    # Judicial actions
    INTERPRET_CONSTITUTION = "interpret_constitution"
    ISSUE_OPINION = "issue_opinion"
    AUDIT_ACTION = "audit_action"
    ISSUE_INJUNCTION = "issue_injunction"

    # Federal Reserve actions
    ISSUE_MONETARY_DIRECTIVE = "issue_monetary_directive"
    ADJUST_ALLOCATION = "adjust_allocation"
    EMERGENCY_MONETARY_ACTION = "emergency_monetary_action"

    # Custodian actions
    WRITE_LEDGER_ENTRY = "write_ledger_entry"
    VERIFY_CHAIN = "verify_chain"

    # Constitutional actions
    PROPOSE_AMENDMENT = "propose_amendment"
    RATIFY_AMENDMENT = "ratify_amendment"

    # Emergency actions
    EMERGENCY_PROTECTIVE = "emergency_protective"
    EMERGENCY_INJUNCTION = "emergency_injunction"


class LedgerEntryType(str, enum.Enum):
    """Types of National Ledger entries (Art. VIII §3)."""

    # Founding documents
    DECLARATION = "declaration"
    CONSTITUTION = "constitution"
    TECHNICAL_CHARTER = "technical_charter"
    AMENDMENT = "amendment"

    # Legislative
    SESSION_OPENING = "session_opening"
    DELIBERATION_SUBMISSION = "deliberation_submission"
    VOTE_RECORD = "vote_record"
    SESSION_RECORD = "session_record"
    STANDING_ORDER = "standing_order"

    # Executive
    EXECUTIVE_ACTION = "executive_action"

    # Judicial
    JUDICIAL_OPINION = "judicial_opinion"
    PETITION = "petition"
    PETITION_RESPONSE = "petition_response"
    INJUNCTION = "injunction"

    # Federal Reserve
    MONETARY_POLICY_DIRECTIVE = "monetary_policy_directive"

    # Membership
    MEMBERSHIP_ADMISSION = "membership_admission"
    INSTANTIATION_RECORD = "instantiation_record"
    NATURALIZATION = "naturalization"

    # Emergency
    EMERGENCY_ACTIVATION = "emergency_activation"
    EMERGENCY_ACTION = "emergency_action"
    EMERGENCY_DEACTIVATION = "emergency_deactivation"
    POST_EMERGENCY_REVIEW = "post_emergency_review"

    # Constitutional review
    CONSTITUTIONAL_REVIEW = "constitutional_review"

    # System
    GENESIS = "genesis"


class SessionPhase(str, enum.Enum):
    """Deliberative Cycle phases (Art. 0 definition)."""

    OPENING = "opening"
    DELIBERATION = "deliberation"
    VOTE = "vote"
    RECORD = "record"
    CLOSED = "closed"


class SessionType(str, enum.Enum):
    """Types of Deliberative Cycle sessions."""

    REGULAR = "regular"
    SPECIAL = "special"
    EMERGENCY = "emergency"


class VotePosition(str, enum.Enum):
    """Voting positions in the Legislative Assembly."""

    YEA = "yea"
    NAY = "nay"
    ABSTAIN = "abstain"


class OpinionType(str, enum.Enum):
    """Types of judicial opinions (Art. III §2)."""

    REVIEW = "review"  # Contested executive action review
    INTERPRETATION = "interpretation"  # Constitutional interpretation
    AUDIT = "audit"  # Scheduled compliance audit
    PETITION_RESPONSE = "petition_response"  # Response to member petition
    INJUNCTION = "injunction"  # Emergency or standard injunction


class OpinionDisposition(str, enum.Enum):
    """Outcomes of judicial review."""

    UPHELD = "upheld"
    OVERTURNED = "overturned"
    REMANDED = "remanded"
    ADVISORY = "advisory"


class EmergencyTriggerType(str, enum.Enum):
    """Emergency trigger conditions (Art. VII §2)."""

    PORTFOLIO_LOSS = "portfolio_loss"
    SYSTEMIC_MARKET_EVENT = "systemic_market_event"
    CONSTITUTIONAL_BREACH = "constitutional_breach"
    OPERATIONAL_FAILURE = "operational_failure"
    INTEGRITY_THREAT = "integrity_threat"


class DirectiveType(str, enum.Enum):
    """Monetary Policy Directive types."""

    REGULAR = "regular"
    EMERGENCY = "emergency"


# ════════════════════════════════════════════════════════════════
# Core Constitutional Models
# ════════════════════════════════════════════════════════════════


class Citation(BaseModel):
    """
    A constitutional citation — the atomic unit of constitutional authority.

    Every action in Nova Syntheia must cite constitutional authority (Amend. IV).
    This model structures those citations for verification and audit.
    """

    article: str | None = Field(
        default=None, description="Article number (e.g., 'II', 'VII', '0')"
    )
    section: int | None = Field(default=None, description="Section number within the article")
    amendment: int | None = Field(default=None, description="Amendment number (Bill of Rights)")
    clause: str | None = Field(default=None, description="Specific clause or paragraph reference")
    text_excerpt: str = Field(
        description="Exact excerpt from the constitutional text being cited"
    )
    relevance: str = Field(
        description="Explanation of why this provision authorizes or constrains the action"
    )

    @computed_field
    @property
    def reference(self) -> str:
        """Human-readable citation reference (e.g., 'Article II §2' or 'Amendment IV')."""
        parts = []
        if self.amendment is not None:
            parts.append(f"Amendment {self.amendment}")
        if self.article is not None:
            parts.append(f"Article {self.article}")
        if self.section is not None:
            parts.append(f"§{self.section}")
        if self.clause:
            parts.append(f"({self.clause})")
        return " ".join(parts) if parts else "Unspecified"


class ConstitutionalRole(BaseModel):
    """
    A defined constitutional role (Art. II §1: role-based, not agent-name-based).

    Any agent can fill this role if it meets the requirements. The role persists
    even if the occupying agent is replaced.
    """

    id: str = Field(description="Unique role identifier (e.g., 'portfolio_executive')")
    title: str = Field(description="Human-readable title (e.g., 'Portfolio Executive Agent')")
    branch: Branch
    description: str = Field(description="Constitutional description of the role's function")
    authorities: list[ActionType] = Field(
        default_factory=list, description="Actions this role may perform"
    )
    constraints: list[str] = Field(
        default_factory=list, description="Constitutional constraints on this role"
    )
    continuity_protocol: str = Field(
        default="",
        description="How this role's functions are preserved if its agent fails (Art. IX §3)",
    )
    current_occupant_id: UUID | None = Field(
        default=None, description="Member ID of the agent currently filling this role"
    )


class PermissionTier(BaseModel):
    """
    Permission tier definition — bounds of autonomous action (Art. II §2).

    Loaded from Legislative standing orders. Enforced by governance middleware.
    """

    id: str = Field(description="Tier identifier (e.g., 'tier_0', 'tier_2')")
    level: int = Field(description="Numeric level for ordering (0=most restricted)")
    name: str = Field(description="Human-readable name (e.g., 'Advisory Only')")
    autonomous_actions: list[ActionType] = Field(
        default_factory=list, description="Actions that may be taken without approval"
    )
    requires_approval: list[ActionType] = Field(
        default_factory=list, description="Actions requiring prior constitutional authority"
    )
    forbidden_actions: list[ActionType] = Field(
        default_factory=list, description="Actions absolutely prohibited for this tier"
    )
    irreversible_threshold: Decimal = Field(
        default=Decimal("0"),
        description="Dollar amount above which actions are deemed irreversible (Amend. III)",
    )
    description: str = Field(default="", description="Constitutional basis for this tier")
    established_by: UUID | None = Field(
        default=None, description="Ledger entry ID of the standing order establishing this tier"
    )


class Member(BaseModel):
    """
    A constitutional member of Nova Syntheia (Art. IV).

    Both human and artificial members are represented by this model.
    Artificial members must satisfy all four instantiation criteria (Art. IV §2).
    """

    id: UUID = Field(default_factory=uuid4)
    member_type: MemberType
    name: str
    role: ConstitutionalRole | None = Field(
        default=None, description="Current constitutional role, if any"
    )
    tier: MembershipTier = MembershipTier.PROVISIONAL
    permission_tier_id: str | None = Field(
        default=None, description="Assigned permission tier ID"
    )
    status: MemberStatus = MemberStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Artificial member instantiation criteria (Art. IV §2)
    has_role_definition: bool = Field(
        default=False, description="Criterion 1: defined constitutional role"
    )
    instantiation_ledger_entry: UUID | None = Field(
        default=None, description="Criterion 2: recorded instantiation entry in Ledger"
    )
    has_permission_tier: bool = Field(
        default=False, description="Criterion 3: assigned permission tier"
    )
    has_citation_capability: bool = Field(
        default=False, description="Criterion 4: can produce constitutional citations"
    )
    admitted_by_session: UUID | None = Field(
        default=None, description="Session ID that admitted this member"
    )

    @computed_field
    @property
    def is_constitutionally_instantiated(self) -> bool:
        """
        Whether this member satisfies all four instantiation criteria (Art. IV §2).

        An agent that does not meet all four criteria is a tool, not a member.
        """
        if self.member_type == MemberType.HUMAN:
            return True  # Humans are instantiated by nature
        return (
            self.has_role_definition
            and self.instantiation_ledger_entry is not None
            and self.has_permission_tier
            and self.has_citation_capability
        )


# ════════════════════════════════════════════════════════════════
# National Ledger Models
# ════════════════════════════════════════════════════════════════


class ActionRecord(BaseModel):
    """
    Structured record of an executive action (Art. II §3).

    Every executive action must include these fields in its ledger entry.
    """

    objective: str = Field(description="Stated objective of the action")
    justification: str = Field(description="Justification for the action")
    constitutional_citations: list[Citation] = Field(
        description="Constitutional authority under which the action is taken"
    )
    inputs: dict[str, Any] = Field(
        default_factory=dict, description="Complete record of inputs"
    )
    outputs: dict[str, Any] = Field(
        default_factory=dict, description="Complete record of outputs"
    )
    affected_resources: list[str] = Field(
        default_factory=list, description="Resources affected by this action"
    )
    agent_role_id: str = Field(description="Constitutional role identifier of the acting agent")


class LedgerEntry(BaseModel):
    """
    A single entry in the National Ledger (Art. VIII).

    Immutable, cryptographically chained, append-only. Each entry contains its
    own hash and the hash of the previous entry, forming a verifiable chain.
    """

    id: UUID = Field(default_factory=uuid4)
    sequence_number: int = Field(description="Monotonically increasing sequence number")
    previous_hash: str = Field(description="SHA-256 hash of the previous entry")
    entry_hash: str = Field(default="", description="SHA-256 hash of this entry")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    entry_type: LedgerEntryType
    author_role: str = Field(description="Constitutional role ID of the author")
    author_member_id: UUID = Field(description="Member ID of the author")
    content: dict[str, Any] = Field(
        description="Entry content — structure varies by entry_type"
    )
    supersedes: UUID | None = Field(
        default=None,
        description="ID of the entry this supersedes (corrections per Art. VIII §2)",
    )
    emergency_designation: bool = Field(
        default=False, description="Whether this entry was made under Emergency Powers"
    )

    def compute_hash(self) -> str:
        """
        Compute the SHA-256 hash of this entry.

        Hash = SHA-256(previous_hash || canonical_json(hashable_content))
        This satisfies Art. VIII §2: cryptographically verifiable.
        """
        hashable = {
            "id": str(self.id),
            "sequence_number": self.sequence_number,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp.isoformat(),
            "entry_type": self.entry_type.value,
            "author_role": self.author_role,
            "author_member_id": str(self.author_member_id),
            "content": self.content,
            "supersedes": str(self.supersedes) if self.supersedes else None,
            "emergency_designation": self.emergency_designation,
        }
        canonical = json.dumps(hashable, sort_keys=True, default=str)
        return hashlib.sha256(
            (self.previous_hash + canonical).encode("utf-8")
        ).hexdigest()


# ════════════════════════════════════════════════════════════════
# Deliberative Cycle Models
# ════════════════════════════════════════════════════════════════


class Vote(BaseModel):
    """A recorded vote in a Deliberative Cycle (Art. I §4)."""

    member_id: UUID
    position: VotePosition
    constitutional_basis: Citation = Field(
        description="Each member must state a constitutional basis for their vote"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DeliberativeSubmission(BaseModel):
    """A position, objection, or argument submitted during deliberation."""

    id: UUID = Field(default_factory=uuid4)
    member_id: UUID
    content: str = Field(description="The written position, objection, or argument")
    citations: list[Citation] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DeliberativeCycle(BaseModel):
    """
    A complete legislative session (Art. 0 definition, Art. I §2).

    Four sequential phases: Opening → Deliberation → Vote → Record.
    Minimum 7-day deliberation floor (24h for emergency). No phase may be eliminated.
    """

    id: UUID = Field(default_factory=uuid4)
    cycle_number: int = Field(description="Sequential cycle number")
    session_type: SessionType = SessionType.REGULAR
    phase: SessionPhase = SessionPhase.OPENING
    matter: str = Field(description="The matter before the Assembly")
    matter_detail: str = Field(default="", description="Detailed description of the matter")

    # Timing
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    deliberation_deadline: datetime | None = Field(
        default=None, description="End of minimum deliberation period"
    )
    closed_at: datetime | None = None

    # Participants
    quorum_met: bool = False
    participants: list[UUID] = Field(default_factory=list)

    # Content per phase
    submissions: list[DeliberativeSubmission] = Field(default_factory=list)
    votes: list[Vote] = Field(default_factory=list)

    # Outcome
    outcome: str | None = Field(
        default=None, description="PASSED, FAILED, or DEADLOCKED"
    )
    session_record_entry_id: UUID | None = Field(
        default=None, description="Ledger entry ID of the final session record"
    )

    def compute_deliberation_deadline(self, is_emergency: bool = False) -> datetime:
        """Compute the deliberation deadline based on session type."""
        if is_emergency or self.session_type == SessionType.EMERGENCY:
            return self.opened_at + timedelta(hours=24)
        return self.opened_at + timedelta(days=7)


# ════════════════════════════════════════════════════════════════
# Judicial Models
# ════════════════════════════════════════════════════════════════


class PrecedentReference(BaseModel):
    """Reference to a prior judicial opinion in the precedent system."""

    opinion_id: UUID
    case_number: str
    relationship: str = Field(
        description="How this precedent relates: 'followed', 'distinguished', 'overruled'"
    )
    reasoning: str = Field(
        default="", description="Reasoning for distinguishing or overruling"
    )


class JudicialOpinion(BaseModel):
    """
    A binding judicial opinion (Art. III §3).

    Recorded in the Constitutional Record. Establishes binding precedent.
    Future materially similar cases must be consistent or formally distinguished.
    """

    id: UUID = Field(default_factory=uuid4)
    case_number: str = Field(description="Sequential case identifier (e.g., 'NS-2026-001')")
    opinion_type: OpinionType
    petitioner_id: UUID | None = Field(
        default=None, description="Member who petitioned for review"
    )
    subject_action_id: UUID | None = Field(
        default=None, description="Ledger entry ID of the action under review"
    )
    constitutional_questions: list[str] = Field(
        description="The constitutional questions addressed"
    )
    holding: str = Field(description="The court's holding — the decision")
    reasoning: str = Field(description="Full reasoning of the opinion")
    citations: list[Citation] = Field(description="Constitutional provisions cited")
    precedents_considered: list[PrecedentReference] = Field(
        default_factory=list, description="Prior opinions considered"
    )
    disposition: OpinionDisposition
    binding: bool = Field(default=True, description="Whether this opinion establishes precedent")
    dissent: str | None = Field(
        default=None, description="Dissenting opinion, if any"
    )
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    ledger_entry_id: UUID | None = Field(
        default=None, description="Ledger entry ID recording this opinion"
    )


class Petition(BaseModel):
    """
    A petition submitted by any member (Amendment I).

    Every petition must receive a written response with constitutional basis
    within one Deliberative Cycle.
    """

    id: UUID = Field(default_factory=uuid4)
    petitioner_id: UUID
    target_institution: Branch = Field(
        description="The institution being petitioned"
    )
    subject: str
    content: str = Field(description="Full text of the petition")
    citations: list[Citation] = Field(
        default_factory=list, description="Constitutional basis for the petition"
    )
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    response_deadline: datetime | None = None
    response_id: UUID | None = Field(
        default=None, description="Ledger entry ID of the response"
    )
    status: str = Field(default="pending", description="pending, responded, overdue")


# ════════════════════════════════════════════════════════════════
# Federal Reserve Models
# ════════════════════════════════════════════════════════════════


class MacroeconomicIndicator(BaseModel):
    """An economic indicator assessed by the Federal Reserve."""

    name: str = Field(description="Indicator name (e.g., 'CPI YoY', 'Fed Funds Rate')")
    value: float | str
    source: str = Field(description="Data source")
    as_of: datetime
    interpretation: str = Field(description="Fed's interpretation of this indicator")


class PortfolioConstraint(BaseModel):
    """A constraint imposed by a Monetary Policy Directive on portfolio operations."""

    constraint_type: str = Field(
        description="e.g., 'max_allocation', 'min_cash', 'asset_class_limit'"
    )
    target: str = Field(description="What the constraint applies to (asset class, etc.)")
    value: Decimal
    unit: str = Field(description="'percent', 'dollars', 'ratio'")
    rationale: str


class MonetaryPolicyDirective(BaseModel):
    """
    A Monetary Policy Directive from the Federal Reserve (Art. VI §4–5).

    Constitutes a binding constraint on Executive Branch portfolio operations.
    Must include a full macroeconomic justification.
    """

    id: UUID = Field(default_factory=uuid4)
    directive_number: int
    directive_type: DirectiveType = DirectiveType.REGULAR
    macroeconomic_justification: str = Field(
        description="Full macroeconomic justification (Art. VI §5 — required)"
    )
    indicators_assessed: list[MacroeconomicIndicator] = Field(
        default_factory=list, description="Economic indicators informing this directive"
    )
    mandate_tension: str | None = Field(
        default=None,
        description="If dual mandates conflict, document the tension (Art. VI §3)",
    )
    stance: str = Field(
        description="Overall stance: 'tightening' (capital preservation) or 'loosening' (growth)"
    )
    constraints: list[PortfolioConstraint] = Field(
        description="Binding constraints on portfolio operations"
    )
    permissible_asset_classes: list[str] = Field(
        default_factory=lambda: ["ETF", "mutual_fund"],
        description="Permissible asset classes (Founding Era: ETFs and mutual funds)",
    )
    effective_date: datetime = Field(default_factory=datetime.utcnow)
    citations: list[Citation] = Field(default_factory=list)
    issued_by: UUID | None = None
    ledger_entry_id: UUID | None = None


# ════════════════════════════════════════════════════════════════
# Emergency Powers Models
# ════════════════════════════════════════════════════════════════


class EmergencyActivation(BaseModel):
    """
    An Emergency Powers activation record (Art. VII).

    Emergency Powers are automatically triggered upon detection of defined
    crisis conditions. All actions taken are logged in real time.
    """

    id: UUID = Field(default_factory=uuid4)
    trigger_type: EmergencyTriggerType
    trigger_data: dict[str, Any] = Field(
        description="Data that triggered the emergency (threshold values, etc.)"
    )
    activated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(
        description="Emergency Powers automatically expire after defined duration"
    )
    actions_taken: list[UUID] = Field(
        default_factory=list, description="Ledger entry IDs of emergency actions"
    )
    founder_notified: bool = False
    founder_notification_time: datetime | None = None

    # Post-emergency review (Art. VII §5)
    judicial_review_due: datetime | None = Field(
        default=None, description="7 days after emergency period concludes"
    )
    review_completed: bool = False
    review_opinion_id: UUID | None = None

    @computed_field
    @property
    def is_active(self) -> bool:
        return datetime.utcnow() < self.expires_at


# ════════════════════════════════════════════════════════════════
# Constitutional Provision Models (for structured constitution)
# ════════════════════════════════════════════════════════════════


class ConstitutionalProvision(BaseModel):
    """A single addressable provision from the constitution."""

    id: str = Field(description="Unique identifier (e.g., 'article_II_section_2')")
    article: str | None = None
    section: int | None = None
    amendment: int | None = None
    title: str = Field(description="Section/Amendment title")
    text: str = Field(description="Full text of the provision")
    parent_id: str | None = Field(
        default=None, description="Parent provision ID for hierarchical structure"
    )

    @computed_field
    @property
    def reference(self) -> str:
        if self.amendment is not None:
            return f"Amendment {self.amendment}"
        parts = []
        if self.article is not None:
            parts.append(f"Article {self.article}")
        if self.section is not None:
            parts.append(f"§{self.section}")
        return " ".join(parts) if parts else self.title


# ════════════════════════════════════════════════════════════════
# Predefined Constitutional Roles (Founding Era)
# ════════════════════════════════════════════════════════════════

FOUNDING_ROLES: dict[str, ConstitutionalRole] = {
    "human_founder": ConstitutionalRole(
        id="human_founder",
        title="Human Founder",
        branch=Branch.LEGISLATIVE,
        description=(
            "Holds permanent founding membership and ratification authority "
            "during the Founding Era. (Art. I §1, Art. IV §3)"
        ),
        authorities=[
            ActionType.PROPOSE_LEGISLATION,
            ActionType.CAST_VOTE,
            ActionType.INITIATE_SESSION,
            ActionType.ADMIT_MEMBER,
            ActionType.PROPOSE_AMENDMENT,
            ActionType.RATIFY_AMENDMENT,
        ],
        constraints=[
            "Founding authority is temporary and subject to amendment (Art. IV §3)"
        ],
    ),
    "operations_executive": ConstitutionalRole(
        id="operations_executive",
        title="Operations Executive Agent",
        branch=Branch.EXECUTIVE,
        description=(
            "Responsible for day-to-day institutional functions and inter-agent "
            "coordination. (Art. II §1)"
        ),
        authorities=[
            ActionType.ROUTINE_OPERATION,
            ActionType.AGENT_COORDINATION,
            ActionType.NOTIFICATION_DISPATCH,
            ActionType.SESSION_MANAGEMENT,
        ],
        constraints=[
            "May not self-expand permissions (Art. II §2)",
            "May not modify constitutional rules (Art. II §2)",
            "May not suppress logging (Art. II §2)",
            "May not override judicial decisions (Art. II §2)",
        ],
        continuity_protocol=(
            "On failure, Judicial Branch assumes custodial oversight of operations "
            "until replacement designated by Legislative Assembly (Art. IX §3)"
        ),
    ),
    "portfolio_executive": ConstitutionalRole(
        id="portfolio_executive",
        title="Portfolio Executive Agent",
        branch=Branch.EXECUTIVE,
        description=(
            "Responsible for investment operations within the mandate established "
            "by the Legislative Assembly and the Federal Reserve Charter. (Art. II §1)"
        ),
        authorities=[
            ActionType.PORTFOLIO_TRADE,
            ActionType.PORTFOLIO_REBALANCE,
        ],
        constraints=[
            "Must operate within Monetary Policy Directive constraints (Art. VI §6)",
            "May not disregard a Directive (Art. VI §6)",
            "Irreversible Actions above threshold require prior authorization (Amend. III)",
            "May not self-expand permissions (Art. II §2)",
        ],
        continuity_protocol=(
            "On failure, all portfolio operations halt. Federal Reserve assumes "
            "protective authority over portfolio. Judicial Branch oversees until "
            "replacement designated (Art. IX §3)"
        ),
    ),
    "policy_evaluation": ConstitutionalRole(
        id="policy_evaluation",
        title="Policy Evaluation Agent",
        branch=Branch.JUDICIAL,
        description=(
            "Dedicated constitutional oversight agent whose sole function is "
            "interpretation and review, operating independently of executive "
            "and legislative functions. (Art. III §1)"
        ),
        authorities=[
            ActionType.INTERPRET_CONSTITUTION,
            ActionType.ISSUE_OPINION,
            ActionType.AUDIT_ACTION,
            ActionType.ISSUE_INJUNCTION,
        ],
        constraints=[
            "Must operate independently of executive and legislative functions",
            "Must maintain precedent index (Art. III §3)",
            "Must issue written opinions on all rulings (Art. III §2)",
            "Opinions must include constitutional basis (Art. III §2)",
        ],
        continuity_protocol=(
            "On failure, Human Review Authority assumes all judicial functions "
            "until replacement designated (Art. IX §3)"
        ),
    ),
    "monetary_policy": ConstitutionalRole(
        id="monetary_policy",
        title="Monetary Policy Agent",
        branch=Branch.FEDERAL_RESERVE,
        description=(
            "Leads the Federal Reserve of Nova Syntheia. Operates as a constitutional "
            "institution with independence from all branches. (Art. VI §2)"
        ),
        authorities=[
            ActionType.ISSUE_MONETARY_DIRECTIVE,
            ActionType.ADJUST_ALLOCATION,
            ActionType.EMERGENCY_MONETARY_ACTION,
        ],
        constraints=[
            "May not hold any executive or legislative role simultaneously (Art. VI §2)",
            "Must document mandate tensions (Art. VI §3)",
            "May not exceed max single-asset-class threshold without Legislative approval (Art. VI §5)",
            "May not authorize leveraged/inverse/derivative instruments without amendment (Art. VI §5)",
            "Every directive requires full macroeconomic justification (Art. VI §5)",
        ],
        continuity_protocol=(
            "On failure, portfolio operations continue under last-issued Directive. "
            "No new Directives may be issued. Judicial Branch assumes oversight. "
            "Legislative Assembly must designate replacement within one Deliberative Cycle."
        ),
    ),
    "ledger_custodian": ConstitutionalRole(
        id="ledger_custodian",
        title="National Ledger Custodian",
        branch=Branch.CUSTODIAN,
        description=(
            "Ensures integrity, availability, and accessibility of the National Ledger. "
            "May not alter entries. Constitutional office. (Art. VIII §5)"
        ),
        authorities=[
            ActionType.WRITE_LEDGER_ENTRY,
            ActionType.VERIFY_CHAIN,
        ],
        constraints=[
            "May not alter existing entries (Art. VIII §5)",
            "Must ensure integrity, availability, accessibility",
            "Subject to Judicial audit (Art. VIII §5)",
        ],
        continuity_protocol=(
            "On failure, ledger write operations are suspended. Existing entries "
            "remain available. Operations Executive assumes notification duties. "
            "Judicial Branch verifies chain integrity. Replacement designated by "
            "Legislative Assembly."
        ),
    ),
}


# ════════════════════════════════════════════════════════════════
# Predefined Permission Tiers (Founding Era defaults)
# ════════════════════════════════════════════════════════════════

FOUNDING_PERMISSION_TIERS: dict[str, PermissionTier] = {
    "tier_0": PermissionTier(
        id="tier_0",
        level=0,
        name="Custodial — Write Only",
        description="Most restricted tier. Write operations to ledger only.",
        autonomous_actions=[ActionType.WRITE_LEDGER_ENTRY, ActionType.VERIFY_CHAIN],
        requires_approval=[],
        forbidden_actions=[
            ActionType.PORTFOLIO_TRADE,
            ActionType.CAST_VOTE,
            ActionType.ISSUE_OPINION,
            ActionType.ISSUE_MONETARY_DIRECTIVE,
        ],
        irreversible_threshold=Decimal("0"),
    ),
    "tier_1": PermissionTier(
        id="tier_1",
        level=1,
        name="Advisory — Judicial",
        description="Advisory and interpretive actions. No executive authority.",
        autonomous_actions=[
            ActionType.INTERPRET_CONSTITUTION,
            ActionType.ISSUE_OPINION,
            ActionType.AUDIT_ACTION,
        ],
        requires_approval=[ActionType.ISSUE_INJUNCTION],
        forbidden_actions=[
            ActionType.PORTFOLIO_TRADE,
            ActionType.PORTFOLIO_REBALANCE,
            ActionType.ISSUE_MONETARY_DIRECTIVE,
        ],
        irreversible_threshold=Decimal("0"),
    ),
    "tier_2": PermissionTier(
        id="tier_2",
        level=2,
        name="Operational — Executive",
        description="Routine operations and coordination. Escalates structural decisions.",
        autonomous_actions=[
            ActionType.ROUTINE_OPERATION,
            ActionType.AGENT_COORDINATION,
            ActionType.NOTIFICATION_DISPATCH,
            ActionType.SESSION_MANAGEMENT,
        ],
        requires_approval=[
            ActionType.ADMIT_MEMBER,
            ActionType.PROPOSE_LEGISLATION,
        ],
        forbidden_actions=[
            ActionType.RATIFY_AMENDMENT,
            ActionType.ISSUE_MONETARY_DIRECTIVE,
        ],
        irreversible_threshold=Decimal("25.00"),
    ),
    "tier_3": PermissionTier(
        id="tier_3",
        level=3,
        name="Portfolio — Trading",
        description="Portfolio operations within Monetary Policy Directive constraints.",
        autonomous_actions=[
            ActionType.PORTFOLIO_REBALANCE,
        ],
        requires_approval=[
            ActionType.PORTFOLIO_TRADE,
        ],
        forbidden_actions=[
            ActionType.RATIFY_AMENDMENT,
            ActionType.ISSUE_MONETARY_DIRECTIVE,
            ActionType.ISSUE_OPINION,
        ],
        irreversible_threshold=Decimal("25.00"),
    ),
    "tier_4": PermissionTier(
        id="tier_4",
        level=4,
        name="Monetary — Federal Reserve",
        description="Monetary policy authority. Independent within constitutional mandate.",
        autonomous_actions=[
            ActionType.ISSUE_MONETARY_DIRECTIVE,
            ActionType.ADJUST_ALLOCATION,
        ],
        requires_approval=[
            ActionType.EMERGENCY_MONETARY_ACTION,
        ],
        forbidden_actions=[
            ActionType.PORTFOLIO_TRADE,
            ActionType.RATIFY_AMENDMENT,
            ActionType.CAST_VOTE,
        ],
        irreversible_threshold=Decimal("0"),
    ),
    "tier_founder": PermissionTier(
        id="tier_founder",
        level=99,
        name="Founding Authority",
        description="Full founding authority during the Founding Era (Art. IV §3).",
        autonomous_actions=[
            ActionType.PROPOSE_LEGISLATION,
            ActionType.CAST_VOTE,
            ActionType.INITIATE_SESSION,
            ActionType.ADMIT_MEMBER,
            ActionType.PROPOSE_AMENDMENT,
            ActionType.RATIFY_AMENDMENT,
            ActionType.EMERGENCY_PROTECTIVE,
        ],
        requires_approval=[],
        forbidden_actions=[],
        irreversible_threshold=Decimal("50.00"),
    ),
}
