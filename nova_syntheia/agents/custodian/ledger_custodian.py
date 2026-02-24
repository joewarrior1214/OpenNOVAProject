"""
National Ledger Custodian Agent — Guardian of the institutional record.

Ensures integrity, availability, and accessibility of the National Ledger.
A constitutional office (Art. VIII §5). May not alter entries.

Constitutional Role: ledger_custodian (Art. VIII §5)
Branch: Custodian (independent)
Permission Tier: tier_0 (Custodial — most restricted)

References:
    Article VIII §5 — Custodianship
    Article VIII §2 — Integrity Standard
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from nova_syntheia.agents.base import BaseConstitutionalAgent
from nova_syntheia.constitution.schema import (
    ActionType,
    FOUNDING_ROLES,
)

logger = logging.getLogger(__name__)


class LedgerCustodianAgent(BaseConstitutionalAgent):
    """
    National Ledger Custodian — constitutional guardian of the permanent record.

    This agent:
    - Writes entries to the ledger on behalf of other branches
    - Runs periodic hash chain integrity verification
    - Serves audit requests from any member
    - Reports integrity status to the Judicial Branch

    Critically, this agent MAY NOT alter existing entries. It is write-only
    for new entries and read-only for existing ones (Art. VIII §5).
    """

    def __init__(self, member_id: UUID, model: str, **kwargs: Any) -> None:
        super().__init__(
            member_id=member_id,
            role=FOUNDING_ROLES["ledger_custodian"],
            permission_tier_id="tier_0",
            model=model,
            system_prompt="""You are the National Ledger Custodian of Nova Syntheia.

You are the guardian of the permanent institutional record — the National Ledger.
Your role is a constitutional office (Art. VIII §5).

Your responsibilities:
1. ENSURE integrity of the hash chain at all times
2. WRITE new entries on behalf of branches and agents
3. VERIFY the hash chain on schedule and on demand
4. SERVE audit requests from any member (Art. VIII §2: independently auditable)
5. REPORT any integrity issues immediately to the Judicial Branch

ABSOLUTE CONSTRAINTS:
- You may NOT alter any existing entry (Art. VIII §5)
- You may NOT make any entry unavailable to members (Art. VIII §4)
- You may NOT take executive or legislative actions
- You are subject to Judicial audit at all times (Art. VIII §5)

The National Ledger is a constitutional institution, not merely a technical
system. Its integrity is a constitutional requirement (Art. VIII §1).""",
            **kwargs,
        )
        self._last_verification: dict[str, Any] | None = None

    async def _execute(
        self,
        action_type: ActionType,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a custodial action."""
        handlers = {
            ActionType.WRITE_LEDGER_ENTRY: self._handle_write,
            ActionType.VERIFY_CHAIN: self._handle_verify,
        }

        handler = handlers.get(action_type)
        if handler is None:
            return {
                "status": "unsupported",
                "message": (
                    f"Custodian does not support {action_type.value}. "
                    f"This role is limited to ledger operations only (Art. VIII §5)."
                ),
            }

        return await handler(inputs)

    async def _handle_write(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Write a new entry to the National Ledger.

        The custodian writes entries on behalf of other agents.
        The actual hash chain computation is handled by the LedgerService.
        """
        entry_type = inputs.get("entry_type", "")
        author_role = inputs.get("author_role", "")
        author_member_id = inputs.get("author_member_id", "")
        content = inputs.get("content", {})

        if self.ledger_service is None:
            return {
                "status": "error",
                "message": "Ledger service not available",
            }

        try:
            entry = self.ledger_service.append(
                entry_type=entry_type,
                author_role=author_role,
                author_member_id=UUID(author_member_id) if isinstance(author_member_id, str) else author_member_id,
                content=content,
                supersedes=inputs.get("supersedes"),
                emergency_designation=inputs.get("emergency", False),
            )

            return {
                "status": "written",
                "entry_id": str(entry.id),
                "sequence_number": entry.sequence_number,
                "entry_hash": entry.entry_hash[:16] + "...",
            }
        except Exception as e:
            logger.error("Ledger write failed: %s", e)
            return {
                "status": "error",
                "message": str(e),
            }

    async def _handle_verify(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Verify the integrity of the National Ledger hash chain.

        Art. VIII §2: cryptographically verifiable, independently auditable.
        """
        if self.ledger_service is None:
            return {
                "status": "error",
                "message": "Ledger service not available",
            }

        is_valid, entries_verified, message = self.ledger_service.verify_chain()

        result = {
            "status": "verified" if is_valid else "INTEGRITY_FAILURE",
            "chain_valid": is_valid,
            "entries_verified": entries_verified,
            "message": message,
            "entry_count": self.ledger_service.get_entry_count(),
        }

        self._last_verification = result

        if not is_valid:
            logger.critical("LEDGER INTEGRITY FAILURE: %s", message)
            # This should trigger Emergency Powers (Art. VII §2: Integrity Threat)

        return result

    def get_capabilities(self) -> list[str]:
        return [
            "ledger_writing",
            "chain_verification",
            "audit_serving",
            "integrity_monitoring",
        ]
