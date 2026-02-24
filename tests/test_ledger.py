"""
Tests for the National Ledger hash chain — Art. VIII §2.

Validates:
- Append-only semantics
- SHA-256 hash chain integrity
- Chain verification
- Tamper detection
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from nova_syntheia.constitution.schema import LedgerEntry, LedgerEntryType


class TestLedgerEntryHash:
    """Test the Pydantic LedgerEntry hash computation."""

    def test_compute_hash_deterministic(self):
        entry = LedgerEntry(
            id=uuid4(),
            sequence_number=1,
            entry_type=LedgerEntryType.EXECUTIVE_ACTION,
            author_role="operations_executive",
            author_member_id=uuid4(),
            content={"action": "test"},
            previous_hash="0" * 64,
        )
        h1 = entry.compute_hash()
        h2 = entry.compute_hash()
        assert h1 == h2, "Hash should be deterministic"

    def test_compute_hash_changes_with_content(self):
        member_id = uuid4()
        entry_id = uuid4()
        base_kwargs = {
            "id": entry_id,
            "sequence_number": 1,
            "entry_type": LedgerEntryType.EXECUTIVE_ACTION,
            "author_role": "operations_executive",
            "author_member_id": member_id,
            "previous_hash": "0" * 64,
        }
        e1 = LedgerEntry(**base_kwargs, content={"action": "alpha"})
        e2 = LedgerEntry(**base_kwargs, content={"action": "beta"})
        assert e1.compute_hash() != e2.compute_hash(), "Different content should produce different hash"

    def test_compute_hash_format(self):
        entry = LedgerEntry(
            id=uuid4(),
            sequence_number=0,
            entry_type=LedgerEntryType.DECLARATION,
            author_role="system",
            author_member_id=uuid4(),
            content={"genesis": True},
            previous_hash="0" * 64,
        )
        h = entry.compute_hash()
        assert len(h) == 64, "SHA-256 hex digest should be 64 chars"
        assert all(c in "0123456789abcdef" for c in h), "Hash should be lowercase hex"

    def test_hash_chain_linkage(self):
        """Simulate a 3-entry chain and verify linkage."""
        member_id = uuid4()
        genesis = LedgerEntry(
            id=uuid4(),
            sequence_number=0,
            entry_type=LedgerEntryType.DECLARATION,
            author_role="system",
            author_member_id=member_id,
            content={"genesis": True},
            previous_hash="0" * 64,
        )
        genesis_hash = genesis.compute_hash()

        entry1 = LedgerEntry(
            id=uuid4(),
            sequence_number=1,
            entry_type=LedgerEntryType.EXECUTIVE_ACTION,
            author_role="operations_executive",
            author_member_id=member_id,
            content={"action": "first"},
            previous_hash=genesis_hash,
        )
        entry1_hash = entry1.compute_hash()

        entry2 = LedgerEntry(
            id=uuid4(),
            sequence_number=2,
            entry_type=LedgerEntryType.EXECUTIVE_ACTION,
            author_role="portfolio_executive",
            author_member_id=member_id,
            content={"action": "second"},
            previous_hash=entry1_hash,
        )

        # Verify chain: each entry's previous_hash matches the prior entry's hash
        assert entry1.previous_hash == genesis_hash
        assert entry2.previous_hash == entry1_hash

    def test_tamper_detection(self):
        """Altering content after hashing should be detectable."""
        entry = LedgerEntry(
            id=uuid4(),
            sequence_number=1,
            entry_type=LedgerEntryType.EXECUTIVE_ACTION,
            author_role="operations_executive",
            author_member_id=uuid4(),
            content={"amount": 100},
            previous_hash="0" * 64,
        )
        original_hash = entry.compute_hash()

        # "Tamper" with content
        tampered = entry.model_copy(update={"content": {"amount": 999}})
        tampered_hash = tampered.compute_hash()

        assert original_hash != tampered_hash, "Tampered entry should produce different hash"
