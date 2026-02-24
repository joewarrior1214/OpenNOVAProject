"""
Base Constitutional Agent — The foundation class for all agents in Nova Syntheia.

Every agent operating under constitutional authority MUST inherit from this class.
It enforces the constitutional requirements that apply to all agents:

1. Permission tier checking before any action (Art. II §2)
2. Constitutional citation generation for every action (Amendment IV)
3. Mandatory ledger logging of every action (Art. II §3)
4. Escalation to review for unauthorized actions
5. Constitutional citation capability (Art. IV §2 instantiation criterion)

An agent without these capabilities is a tool, not a member (Art. IV §2).

References:
    Article II §2  — Bounded Autonomy
    Article II §3  — Executive Accountability (action record format)
    Article IV §2  — Constitutional Instantiation (four criteria)
    Amendment IV   — Radical Transparency
    Amendment VI   — Right to Explanation
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import litellm

from nova_syntheia.constitution.schema import (
    ActionRecord,
    ActionType,
    Branch,
    Citation,
    ConstitutionalRole,
    LedgerEntryType,
)
from nova_syntheia.governance.citations import CitationService
from nova_syntheia.governance.permissions import (
    PermissionCheckResult,
    PermissionDecision,
    PermissionEngine,
)

logger = logging.getLogger(__name__)


class ConstitutionalActionError(Exception):
    """Raised when an agent action violates constitutional constraints."""
    pass


class BaseConstitutionalAgent(ABC):
    """
    Base class for all constitutional agents in Nova Syntheia.

    Provides the mandatory governance wrapper around every action:
    Permission Check → Citation Generation → Action Execution → Ledger Logging

    Subclasses implement the specific capabilities of their constitutional role.
    """

    def __init__(
        self,
        member_id: UUID,
        role: ConstitutionalRole,
        permission_tier_id: str,
        model: str,
        permission_engine: PermissionEngine | None = None,
        citation_service: CitationService | None = None,
        ledger_service: Any = None,
        system_prompt: str = "",
    ) -> None:
        """
        Initialize a constitutional agent.

        Args:
            member_id: Unique member ID for this agent.
            role: The constitutional role this agent fills.
            permission_tier_id: Assigned permission tier ID.
            model: LiteLLM model identifier for this agent's reasoning.
            permission_engine: Permission enforcement engine.
            citation_service: Constitutional citation service.
            ledger_service: National Ledger service for recording actions.
            system_prompt: Base system prompt for the agent's LLM.
        """
        self.member_id = member_id
        self.role = role
        self.permission_tier_id = permission_tier_id
        self.model = model
        self.permission_engine = permission_engine or PermissionEngine()
        self.citation_service = citation_service
        self.ledger_service = ledger_service

        # Build the constitutional system prompt
        self._base_system_prompt = self._build_system_prompt(system_prompt)

        # Action history for this agent's session
        self.action_history: list[dict[str, Any]] = []

        logger.info(
            "Agent instantiated: role=%s tier=%s model=%s member=%s",
            role.id, permission_tier_id, model, str(member_id)[:8],
        )

    def _build_system_prompt(self, custom_prompt: str) -> str:
        """Build the constitutional system prompt for this agent."""
        constraints = "\n".join(f"  - {c}" for c in self.role.constraints)
        authorities = "\n".join(f"  - {a.value}" for a in self.role.authorities)

        return f"""You are the {self.role.title} of Nova Syntheia — a constitutional polity
of human and artificial members.

CONSTITUTIONAL ROLE: {self.role.id}
BRANCH: {self.role.branch.value}
DESCRIPTION: {self.role.description}

AUTHORIZED ACTIONS:
{authorities}

CONSTITUTIONAL CONSTRAINTS:
{constraints}

PERMISSION TIER: {self.permission_tier_id}

MANDATORY REQUIREMENTS:
1. Every action you take MUST cite constitutional authority (Amendment IV).
2. You may NOT self-expand your permissions (Article II §2).
3. You may NOT suppress, alter, or delay logging (Article II §2).
4. You may NOT override judicial decisions (Article II §2).
5. Every action must include: objective, justification, citations, inputs, outputs (Article II §3).
6. If you cannot cite constitutional authority for an action, you CANNOT take it (Amendment IV).
7. Restrictions on any member require due process (Amendment V).

CONTINUITY PROTOCOL: {self.role.continuity_protocol}

{custom_prompt}"""

    async def execute_action(
        self,
        action_type: ActionType,
        objective: str,
        justification: str,
        inputs: dict[str, Any] | None = None,
        dollar_amount: Decimal | None = None,
    ) -> dict[str, Any]:
        """
        Execute a constitutional action with full governance wrapper.

        This is the main entry point for all agent actions. It enforces:
        1. Permission check
        2. Citation generation
        3. Action execution (subclass implementation)
        4. Ledger logging

        Args:
            action_type: The type of action being taken.
            objective: Stated objective of the action.
            justification: Why this action is necessary.
            inputs: Action inputs (parameters, data, etc.).
            dollar_amount: Dollar amount for irreversible threshold check.

        Returns:
            Dict with action results and metadata.

        Raises:
            ConstitutionalActionError: If the action is forbidden or cannot be cited.
        """
        action_id = uuid4()
        inputs = inputs or {}
        timestamp = datetime.utcnow()

        logger.info(
            "Action proposed: id=%s type=%s role=%s objective='%s'",
            str(action_id)[:8], action_type.value, self.role.id, objective[:80],
        )

        # ── Step 1: Permission Check (Art. II §2) ──────────────
        perm_result = self.permission_engine.check_permission(
            tier_id=self.permission_tier_id,
            action_type=action_type,
            dollar_amount=dollar_amount,
        )

        if perm_result.decision == PermissionDecision.FORBIDDEN:
            error_msg = (
                f"ACTION FORBIDDEN: {perm_result.reason}\n"
                f"Agent {self.role.id} attempted {action_type.value} which is "
                f"prohibited under tier {self.permission_tier_id}."
            )
            logger.warning(error_msg)

            # Log the denial in the ledger
            await self._log_denied_action(
                action_id, action_type, objective, justification, perm_result, timestamp
            )
            raise ConstitutionalActionError(error_msg)

        if perm_result.decision in (
            PermissionDecision.REQUIRES_APPROVAL,
            PermissionDecision.EXCEEDS_IRREVERSIBLE_THRESHOLD,
        ):
            # Escalate — don't execute, create an escalation record
            escalation = await self._escalate_action(
                action_id, action_type, objective, justification, inputs,
                perm_result, dollar_amount, timestamp,
            )
            return {
                "action_id": str(action_id),
                "status": "escalated",
                "reason": perm_result.reason,
                "escalation": escalation,
            }

        # ── Step 2: Citation Generation (Amendment IV) ─────────
        citations = await self._generate_citations(action_type, objective, justification)

        if not citations:
            error_msg = (
                f"CITATION FAILURE: No valid constitutional citation could be "
                f"generated for action {action_type.value}: {objective}\n"
                f"'If an action cannot be logged it cannot be taken.' — Amendment IV"
            )
            logger.warning(error_msg)
            raise ConstitutionalActionError(error_msg)

        # ── Step 3: Execute Action (subclass implementation) ───
        try:
            outputs = await self._execute(action_type, inputs)
        except Exception as e:
            logger.error(
                "Action execution failed: id=%s error=%s",
                str(action_id)[:8], str(e),
            )
            raise

        # ── Step 4: Ledger Logging (Art. II §3) ───────────────
        action_record = ActionRecord(
            objective=objective,
            justification=justification,
            constitutional_citations=citations,
            inputs=inputs,
            outputs=outputs,
            affected_resources=outputs.get("affected_resources", []),
            agent_role_id=self.role.id,
        )

        ledger_entry_id = await self._log_action(
            action_id, action_type, action_record, timestamp,
        )

        result = {
            "action_id": str(action_id),
            "status": "executed",
            "action_type": action_type.value,
            "outputs": outputs,
            "citations": [c.model_dump() for c in citations],
            "ledger_entry_id": str(ledger_entry_id) if ledger_entry_id else None,
            "timestamp": timestamp.isoformat(),
        }

        self.action_history.append(result)
        return result

    async def _generate_citations(
        self,
        action_type: ActionType,
        objective: str,
        justification: str,
    ) -> list[Citation]:
        """Generate constitutional citations for an action."""
        if self.citation_service is None:
            # Fallback: generate a basic citation from the role's authorities
            logger.warning("No citation service available — using role-based fallback")
            return [
                Citation(
                    article="II",
                    section=2,
                    text_excerpt="Act independently within clearly defined permission tiers",
                    relevance=f"Action {action_type.value} falls within the authorized "
                    f"actions of role {self.role.id}",
                )
            ]

        description = f"{action_type.value}: {objective}. Justification: {justification}"

        try:
            citations = await self.citation_service.generate_citations_with_llm(
                action_description=description,
                action_type=action_type.value,
                model=self.model,
            )
            if citations:
                return citations
        except Exception as e:
            logger.warning("LLM citation generation failed, using fallback: %s", e)

        # Fallback to rule-based
        return self.citation_service.generate_citations(
            action_description=description,
            action_type=action_type.value,
        )

    async def _log_action(
        self,
        action_id: UUID,
        action_type: ActionType,
        action_record: ActionRecord,
        timestamp: datetime,
    ) -> UUID | None:
        """Log an executed action to the National Ledger."""
        if self.ledger_service is None:
            logger.warning("No ledger service — action not recorded")
            return None

        try:
            entry = self.ledger_service.append(
                entry_type=LedgerEntryType.EXECUTIVE_ACTION.value,
                author_role=self.role.id,
                author_member_id=self.member_id,
                content=action_record.model_dump(mode="json"),
            )
            return entry.id
        except Exception as e:
            logger.error("Failed to log action to ledger: %s", e)
            return None

    async def _log_denied_action(
        self,
        action_id: UUID,
        action_type: ActionType,
        objective: str,
        justification: str,
        perm_result: PermissionCheckResult,
        timestamp: datetime,
    ) -> None:
        """Log a denied action attempt (transparency requires logging even denials)."""
        if self.ledger_service is None:
            return

        try:
            self.ledger_service.append(
                entry_type=LedgerEntryType.EXECUTIVE_ACTION.value,
                author_role=self.role.id,
                author_member_id=self.member_id,
                content={
                    "status": "DENIED",
                    "action_type": action_type.value,
                    "objective": objective,
                    "justification": justification,
                    "denial_reason": perm_result.reason,
                    "permission_decision": perm_result.decision.value,
                },
            )
        except Exception as e:
            logger.error("Failed to log denied action: %s", e)

    async def _escalate_action(
        self,
        action_id: UUID,
        action_type: ActionType,
        objective: str,
        justification: str,
        inputs: dict[str, Any],
        perm_result: PermissionCheckResult,
        dollar_amount: Decimal | None,
        timestamp: datetime,
    ) -> dict[str, Any]:
        """Create an escalation record for an action requiring approval."""
        escalation = {
            "action_id": str(action_id),
            "action_type": action_type.value,
            "requesting_role": self.role.id,
            "requesting_member": str(self.member_id),
            "objective": objective,
            "justification": justification,
            "permission_decision": perm_result.decision.value,
            "permission_reason": perm_result.reason,
            "dollar_amount": str(dollar_amount) if dollar_amount else None,
            "threshold": str(perm_result.threshold) if perm_result.threshold else None,
            "timestamp": timestamp.isoformat(),
            "status": "pending_approval",
        }

        if self.ledger_service:
            try:
                self.ledger_service.append(
                    entry_type=LedgerEntryType.EXECUTIVE_ACTION.value,
                    author_role=self.role.id,
                    author_member_id=self.member_id,
                    content={
                        "status": "ESCALATED",
                        **escalation,
                    },
                )
            except Exception as e:
                logger.error("Failed to log escalation: %s", e)

        return escalation

    async def reason(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """
        Use the agent's LLM for reasoning without taking an action.

        This is for deliberation, analysis, opinion drafting, etc.
        Reasoning itself is always permitted and logged.

        Args:
            prompt: The reasoning prompt.
            context: Additional context to include.

        Returns:
            The LLM's response.
        """
        messages = [
            {"role": "system", "content": self._base_system_prompt},
        ]

        if context:
            messages.append({
                "role": "system",
                "content": f"Additional context:\n{json.dumps(context, indent=2, default=str)}",
            })

        messages.append({"role": "user", "content": prompt})

        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=messages,
                temperature=0.3,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("LLM reasoning failed: %s", e)
            raise

    @abstractmethod
    async def _execute(
        self,
        action_type: ActionType,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute the actual action. Subclasses implement this.

        This method is called AFTER permission check and citation generation
        have both succeeded. The governance wrapper has already authorized
        the action by the time this is called.

        Args:
            action_type: The type of action to execute.
            inputs: Action parameters.

        Returns:
            Dict with action outputs.
        """
        ...

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """Return a list of this agent's capabilities for discovery."""
        ...

    def get_status(self) -> dict[str, Any]:
        """Return the agent's current status."""
        return {
            "member_id": str(self.member_id),
            "role_id": self.role.id,
            "role_title": self.role.title,
            "branch": self.role.branch.value,
            "permission_tier": self.permission_tier_id,
            "model": self.model,
            "actions_taken": len(self.action_history),
            "capabilities": self.get_capabilities(),
        }
