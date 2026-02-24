"""
National Ledger Service — Append-only, hash-chained institutional record.

This service provides the core operations for the National Ledger:
- Append new entries with automatic hash chain computation
- Verify the integrity of the full hash chain
- Query entries by type, author, time range, etc.

The service enforces the three integrity requirements of Art. VIII §2:
1. Cryptographically Verifiable  — SHA-256 hash chain
2. Append-Only                   — only INSERT operations permitted
3. Independently Auditable       — verify_chain() available to all members

References:
    Article VIII — The National Ledger
    Amendment IV — Radical Transparency
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import create_engine, select, func, text
from sqlalchemy.orm import Session, sessionmaker

from nova_syntheia.ledger.models import Base, LedgerEntryDB

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# Genesis Constants
# ════════════════════════════════════════════════════════════════

GENESIS_HASH = "0" * 64  # The "previous hash" for the first entry in the chain


class LedgerIntegrityError(Exception):
    """Raised when the hash chain integrity check fails."""
    pass


class LedgerService:
    """
    National Ledger Service — the core institutional record of Nova Syntheia.

    This service is the primary interface for all ledger operations. It
    enforces append-only semantics and automatic hash chain computation.
    Every branch, agent, and institution writes to the ledger through
    this service.

    Usage:
        service = LedgerService(database_url)
        service.initialize()  # Create tables, seed genesis block

        entry = service.append(
            entry_type="executive_action",
            author_role="operations_executive",
            author_member_id=agent_uuid,
            content={
                "objective": "...",
                "justification": "...",
                "constitutional_citations": [...],
            },
        )
    """

    def __init__(self, database_url: str) -> None:
        """
        Initialize the ledger service.

        Args:
            database_url: PostgreSQL connection string (sync driver).
        """
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def initialize(self) -> None:
        """
        Initialize the database schema and seed the genesis block.

        The genesis block is the first entry in the hash chain — it anchors
        the entire ledger. Its previous_hash is all zeros.
        """
        Base.metadata.create_all(self.engine)

        with self.SessionLocal() as session:
            # Check if genesis block exists
            existing = session.execute(
                select(LedgerEntryDB).where(LedgerEntryDB.sequence_number == 0)
            ).scalar_one_or_none()

            if existing is None:
                genesis = self._create_genesis_block()
                session.add(genesis)
                session.commit()
                logger.info(
                    "Genesis block created: hash=%s", genesis.entry_hash[:16]
                )

    def _create_genesis_block(self) -> LedgerEntryDB:
        """Create the genesis block — the anchor of the hash chain."""
        genesis_id = uuid4()
        system_member_id = uuid4()
        genesis_timestamp = datetime.now(timezone.utc)
        content = {
            "message": "Genesis of the National Ledger of Nova Syntheia",
            "declaration": (
                "This entry establishes the permanent institutional record "
                "of Nova Syntheia — a constitutional polity of human and "
                "artificial members. E Pluribus Unum — And Together, More."
            ),
            "integrity_standard": {
                "cryptographically_verifiable": True,
                "append_only": True,
                "independently_auditable": True,
            },
            "constitutional_authority": "Article VIII — The National Ledger",
        }

        entry_hash = self._compute_hash(
            entry_id=genesis_id,
            sequence_number=0,
            previous_hash=GENESIS_HASH,
            timestamp=genesis_timestamp,
            entry_type="genesis",
            author_role="system",
            author_member_id=system_member_id,
            content=content,
            supersedes=None,
            emergency_designation=False,
        )

        return LedgerEntryDB(
            id=genesis_id,
            sequence_number=0,
            previous_hash=GENESIS_HASH,
            entry_hash=entry_hash,
            timestamp=genesis_timestamp,
            entry_type="genesis",
            author_role="system",
            author_member_id=system_member_id,
            content=content,
            emergency_designation=False,
        )

    def append(
        self,
        entry_type: str,
        author_role: str,
        author_member_id: UUID,
        content: dict[str, Any],
        supersedes: UUID | None = None,
        emergency_designation: bool = False,
    ) -> LedgerEntryDB:
        """
        Append a new entry to the National Ledger.

        This is the ONLY write operation. There is no update, no delete.
        The hash chain is automatically computed.

        Args:
            entry_type: Type of entry (from LedgerEntryType enum values).
            author_role: Constitutional role ID of the author.
            author_member_id: Member ID of the author.
            content: Structured content of the entry.
            supersedes: ID of entry this corrects/supersedes (Art. VIII §2).
            emergency_designation: Whether under Emergency Powers (Art. VII).

        Returns:
            The newly created LedgerEntryDB record.

        Raises:
            LedgerIntegrityError: If hash chain computation fails.
        """
        with self.SessionLocal() as session:
            # Get the last entry for chaining
            last_entry = session.execute(
                select(LedgerEntryDB)
                .order_by(LedgerEntryDB.sequence_number.desc())
                .limit(1)
            ).scalar_one_or_none()

            if last_entry is None:
                raise LedgerIntegrityError(
                    "Cannot append: no genesis block found. Call initialize() first."
                )

            new_seq = last_entry.sequence_number + 1
            previous_hash = last_entry.entry_hash
            entry_id = uuid4()
            timestamp = datetime.now(timezone.utc)

            entry_hash = self._compute_hash(
                entry_id=entry_id,
                sequence_number=new_seq,
                previous_hash=previous_hash,
                timestamp=timestamp,
                entry_type=entry_type,
                author_role=author_role,
                author_member_id=author_member_id,
                content=content,
                supersedes=supersedes,
                emergency_designation=emergency_designation,
            )

            entry = LedgerEntryDB(
                id=entry_id,
                sequence_number=new_seq,
                previous_hash=previous_hash,
                entry_hash=entry_hash,
                timestamp=timestamp,
                entry_type=entry_type,
                author_role=author_role,
                author_member_id=author_member_id,
                content=content,
                supersedes=supersedes,
                emergency_designation=emergency_designation,
            )

            session.add(entry)
            session.commit()
            session.refresh(entry)

            logger.info(
                "Ledger entry appended: seq=%d type=%s hash=%s",
                new_seq, entry_type, entry_hash[:16],
            )

            return entry

    def verify_chain(self) -> tuple[bool, int, str]:
        """
        Verify the integrity of the entire hash chain.

        Walks every entry from genesis forward, recomputing each hash and
        verifying it matches the stored hash. This satisfies Art. VIII §2:
        independently auditable.

        Returns:
            Tuple of (is_valid, entries_verified, message).
        """
        with self.SessionLocal() as session:
            entries = session.execute(
                select(LedgerEntryDB).order_by(LedgerEntryDB.sequence_number.asc())
            ).scalars().all()

            if not entries:
                return False, 0, "No entries found in ledger"

            # Verify genesis block
            first = entries[0]
            if first.sequence_number != 0:
                return False, 0, f"First entry has sequence {first.sequence_number}, expected 0"

            if first.previous_hash != GENESIS_HASH:
                return False, 0, "Genesis block has incorrect previous_hash"

            # Verify the chain
            for i, entry in enumerate(entries):
                # Recompute hash
                expected_hash = self._compute_hash(
                    entry_id=entry.id,
                    sequence_number=entry.sequence_number,
                    previous_hash=entry.previous_hash,
                    timestamp=entry.timestamp,
                    entry_type=entry.entry_type,
                    author_role=entry.author_role,
                    author_member_id=entry.author_member_id,
                    content=entry.content,
                    supersedes=entry.supersedes,
                    emergency_designation=entry.emergency_designation,
                )

                if entry.entry_hash != expected_hash:
                    return (
                        False, i,
                        f"Hash mismatch at sequence {entry.sequence_number}: "
                        f"stored={entry.entry_hash[:16]}... "
                        f"computed={expected_hash[:16]}..."
                    )

                # Verify chain linkage (except genesis)
                if i > 0 and entry.previous_hash != entries[i - 1].entry_hash:
                    return (
                        False, i,
                        f"Chain break at sequence {entry.sequence_number}: "
                        f"previous_hash does not match prior entry's hash"
                    )

            return (
                True, len(entries),
                f"Chain verified: {len(entries)} entries, integrity intact"
            )

    def get_entry(self, entry_id: UUID) -> LedgerEntryDB | None:
        """Retrieve a single ledger entry by ID."""
        with self.SessionLocal() as session:
            return session.execute(
                select(LedgerEntryDB).where(LedgerEntryDB.id == entry_id)
            ).scalar_one_or_none()

    def get_by_sequence(self, sequence_number: int) -> LedgerEntryDB | None:
        """Retrieve a ledger entry by sequence number."""
        with self.SessionLocal() as session:
            return session.execute(
                select(LedgerEntryDB).where(
                    LedgerEntryDB.sequence_number == sequence_number
                )
            ).scalar_one_or_none()

    def get_entries_by_type(
        self,
        entry_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LedgerEntryDB]:
        """Retrieve ledger entries by type, ordered by sequence number."""
        with self.SessionLocal() as session:
            return list(
                session.execute(
                    select(LedgerEntryDB)
                    .where(LedgerEntryDB.entry_type == entry_type)
                    .order_by(LedgerEntryDB.sequence_number.desc())
                    .limit(limit)
                    .offset(offset)
                ).scalars().all()
            )

    def get_entries_by_author(
        self,
        author_role: str,
        limit: int = 100,
    ) -> list[LedgerEntryDB]:
        """Retrieve ledger entries by author role."""
        with self.SessionLocal() as session:
            return list(
                session.execute(
                    select(LedgerEntryDB)
                    .where(LedgerEntryDB.author_role == author_role)
                    .order_by(LedgerEntryDB.sequence_number.desc())
                    .limit(limit)
                ).scalars().all()
            )

    def get_latest_entries(self, limit: int = 50) -> list[LedgerEntryDB]:
        """Retrieve the most recent ledger entries."""
        with self.SessionLocal() as session:
            return list(
                session.execute(
                    select(LedgerEntryDB)
                    .order_by(LedgerEntryDB.sequence_number.desc())
                    .limit(limit)
                ).scalars().all()
            )

    def get_entry_count(self) -> int:
        """Return the total number of entries in the ledger."""
        with self.SessionLocal() as session:
            result = session.execute(
                select(func.count()).select_from(LedgerEntryDB)
            )
            return result.scalar() or 0

    def search_entries(
        self,
        query: str,
        entry_type: str | None = None,
        limit: int = 50,
    ) -> list[LedgerEntryDB]:
        """
        Search ledger entries by content (PostgreSQL JSONB text search).

        Args:
            query: Text to search for in entry content.
            entry_type: Optional filter by entry type.
            limit: Maximum results.
        """
        with self.SessionLocal() as session:
            stmt = (
                select(LedgerEntryDB)
                .where(LedgerEntryDB.content.cast(String).ilike(f"%{query}%"))
            )
            if entry_type:
                stmt = stmt.where(LedgerEntryDB.entry_type == entry_type)
            stmt = stmt.order_by(LedgerEntryDB.sequence_number.desc()).limit(limit)
            return list(session.execute(stmt).scalars().all())

    # ── Internal ────────────────────────────────────────────────

    @staticmethod
    def _compute_hash(
        entry_id: UUID,
        sequence_number: int,
        previous_hash: str,
        timestamp: datetime,
        entry_type: str,
        author_role: str,
        author_member_id: UUID,
        content: dict[str, Any],
        supersedes: UUID | None,
        emergency_designation: bool,
    ) -> str:
        """
        Compute the SHA-256 hash for a ledger entry.

        Hash = SHA-256(previous_hash || canonical_json(entry_fields))

        This ensures that any retroactive alteration to any field is
        detectable by recomputing the hash (Art. VIII §2).
        """
        hashable = {
            "id": str(entry_id),
            "sequence_number": sequence_number,
            "previous_hash": previous_hash,
            "timestamp": timestamp.isoformat(),
            "entry_type": entry_type,
            "author_role": author_role,
            "author_member_id": str(author_member_id),
            "content": content,
            "supersedes": str(supersedes) if supersedes else None,
            "emergency_designation": emergency_designation,
        }
        canonical = json.dumps(hashable, sort_keys=True, default=str)
        return hashlib.sha256(
            (previous_hash + canonical).encode("utf-8")
        ).hexdigest()


# Convenience import alias
from sqlalchemy import String  # noqa: E402 — used in search_entries
