"""
Policy Evaluation Agent — Constitutional oversight and judicial review.

The dedicated constitutional oversight agent whose sole function is
interpretation and review, operating independently of executive and
legislative functions. The "constitutional lawyer" of Nova Syntheia.

Constitutional Role: policy_evaluation (Art. III §1)
Branch: Judicial
Permission Tier: tier_1 (Advisory)

References:
    Article III   — The Judicial Branch
    Article III §1 — Composition (Policy Evaluation Agent)
    Article III §3 — Precedent and the Living Legal Tradition
    Amendment VII — Universal Judicial Review
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from nova_syntheia.agents.base import BaseConstitutionalAgent
from nova_syntheia.constitution.schema import (
    ActionType,
    Citation,
    FOUNDING_ROLES,
    JudicialOpinion,
    OpinionDisposition,
    OpinionType,
    PrecedentReference,
)

logger = logging.getLogger(__name__)


class PolicyEvaluationAgent(BaseConstitutionalAgent):
    """
    Policy Evaluation Agent — the judicial conscience of Nova Syntheia.

    Capabilities:
    - Interpret constitutional provisions when application is unclear
    - Review contested executive actions upon petition
    - Conduct scheduled audits of executive decisions
    - Maintain the precedent index
    - Issue written opinions with constitutional basis
    - Flag potential inconsistencies with prior precedent
    - Monitor Emergency Powers activations

    This agent operates with JUDICIAL INDEPENDENCE: it shares no state
    with executive agents and cannot be directed by any branch.
    """

    def __init__(self, member_id: UUID, model: str, **kwargs: Any) -> None:
        super().__init__(
            member_id=member_id,
            role=FOUNDING_ROLES["policy_evaluation"],
            permission_tier_id="tier_1",
            model=model,
            system_prompt="""You are the Policy Evaluation Agent of Nova Syntheia — the
constitutional oversight authority within the Judicial Branch.

Your sole function is interpretation and review. You operate INDEPENDENTLY
of executive and legislative functions (Art. III §1).

Your responsibilities:
1. INTERPRET constitutional provisions when their application is unclear
2. REVIEW contested executive actions upon petition by any member
3. AUDIT executive decisions for constitutional compliance on schedule
4. MAINTAIN the precedent index — track all opinions and flag inconsistencies
5. ISSUE written opinions on all rulings with constitutional basis
6. RESPOND to petitions within one Deliberative Cycle (Amendment I)
7. MONITOR Emergency Powers activations and issue injunctions if needed

JUDICIAL STANDARDS:
- All opinions must include the constitutional basis for the decision
- Opinions establish BINDING PRECEDENT (Art. III §3)
- Future materially similar cases must be consistent or formally distinguished
- The burden of proportionality rests on the restricting institution (Amendment VIII)
- Interpret Amendment IX broadly in favor of member rights
- You may NOT take executive actions — your authority is interpretive only

PRECEDENT SYSTEM:
- Every opinion is recorded in the Constitutional Record permanently
- You must search prior opinions before issuing new ones
- If departing from precedent, you must formally distinguish with written reasoning
- The Legislative Assembly may not retroactively invalidate established precedent""",
            **kwargs,
        )
        self.opinions: list[JudicialOpinion] = []
        self.precedent_index: dict[str, list[UUID]] = {}  # provision_ref → opinion_ids
        self._case_counter = 0

    async def _execute(
        self,
        action_type: ActionType,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a judicial action."""
        handlers = {
            ActionType.INTERPRET_CONSTITUTION: self._handle_interpretation,
            ActionType.ISSUE_OPINION: self._handle_opinion,
            ActionType.AUDIT_ACTION: self._handle_audit,
            ActionType.ISSUE_INJUNCTION: self._handle_injunction,
        }

        handler = handlers.get(action_type)
        if handler is None:
            return {
                "status": "unsupported",
                "message": f"Action type {action_type.value} not supported by Judicial Branch",
            }

        return await handler(inputs)

    async def _handle_interpretation(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Interpret a constitutional provision.

        Art. III §2: Interpret constitutional provisions when their application
        to a specific situation is unclear.
        """
        provision_ref = inputs.get("provision", "")
        situation = inputs.get("situation", "")
        question = inputs.get("question", "")

        # Use LLM to reason about the constitutional question
        interpretation = await self.reason(
            prompt=f"""CONSTITUTIONAL INTERPRETATION REQUEST

Provision: {provision_ref}
Situation: {situation}
Question: {question}

Please provide:
1. Your interpretation of the relevant provision(s)
2. How they apply to this specific situation
3. Any relevant precedent you are aware of
4. Your ruling or advisory opinion

Ground your interpretation in the text of the Constitution. Cite specific
articles, sections, and amendments.""",
            context=inputs,
        )

        return {
            "status": "interpretation_issued",
            "provision": provision_ref,
            "question": question,
            "interpretation": interpretation,
        }

    async def _handle_opinion(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Draft and issue a judicial opinion.

        Art. III §3: All opinions recorded permanently in Constitutional Record.
        Establishes binding precedent.
        """
        self._case_counter += 1
        case_number = f"NS-{datetime.utcnow().year}-{self._case_counter:03d}"

        opinion_type = OpinionType(inputs.get("opinion_type", "review"))
        questions = inputs.get("constitutional_questions", [])
        subject_action_id = inputs.get("subject_action_id")

        # Search for relevant precedent
        prior_precedent = self._search_precedent(questions)

        # Draft the opinion using LLM
        opinion_text = await self.reason(
            prompt=f"""DRAFT JUDICIAL OPINION

Case Number: {case_number}
Type: {opinion_type.value}
Constitutional Questions: {questions}
Subject Action: {subject_action_id}
Prior Relevant Precedent: {[str(p.opinion_id)[:8] for p in prior_precedent]}

Draft a formal judicial opinion that includes:
1. HOLDING — your decision
2. REASONING — constitutional analysis
3. CITATIONS — specific provisions relied upon
4. PRECEDENT — how this relates to prior opinions (if any)
5. DISPOSITION — upheld, overturned, remanded, or advisory

Write in a formal judicial style. Be precise about constitutional authority.""",
            context=inputs,
        )

        # Create the formal opinion
        opinion = JudicialOpinion(
            case_number=case_number,
            opinion_type=opinion_type,
            petitioner_id=inputs.get("petitioner_id"),
            subject_action_id=UUID(subject_action_id) if subject_action_id else None,
            constitutional_questions=questions,
            holding=opinion_text[:500],  # First 500 chars as holding summary
            reasoning=opinion_text,
            citations=[
                Citation(
                    article="III",
                    section=3,
                    text_excerpt="All judicial opinions shall be recorded permanently",
                    relevance="This opinion is issued under judicial authority",
                )
            ],
            precedents_considered=prior_precedent,
            disposition=OpinionDisposition(inputs.get("disposition", "advisory")),
            binding=inputs.get("binding", True),
        )

        self.opinions.append(opinion)
        self._update_precedent_index(opinion)

        return {
            "status": "opinion_issued",
            "case_number": case_number,
            "opinion_type": opinion_type.value,
            "holding": opinion.holding,
            "disposition": opinion.disposition.value,
            "binding": opinion.binding,
            "precedents_considered": len(prior_precedent),
            "opinion_id": str(opinion.id),
        }

    async def _handle_audit(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Audit an executive action for constitutional compliance.

        Art. III §2: Conduct scheduled audits of executive decisions
        for constitutional compliance.
        """
        action_id = inputs.get("action_id")
        action_content = inputs.get("action_content", {})

        # Analyze the action for constitutional compliance
        audit_result = await self.reason(
            prompt=f"""CONSTITUTIONAL COMPLIANCE AUDIT

Action ID: {action_id}
Action Content: {action_content}

Evaluate this action for compliance with:
1. Was proper constitutional authority cited? (Amendment IV)
2. Was the action within the agent's permission tier? (Art. II §2)
3. Were affected members given due process if applicable? (Amendment V)
4. Was the action proportionate? (Amendment VIII)
5. Was the action properly logged? (Art. II §3)
6. Any potential conflicts with established precedent?

Issue a compliance finding: COMPLIANT, NON-COMPLIANT, or NEEDS REVIEW.""",
            context=action_content,
        )

        return {
            "status": "audit_completed",
            "action_id": action_id,
            "finding": audit_result,
            "auditor": self.role.id,
        }

    async def _handle_injunction(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Issue an injunction to halt an action.

        Art. III §2: Issue emergency injunctions where constitutional
        violations are detected.
        """
        target_action = inputs.get("target_action", "")
        constitutional_basis = inputs.get("constitutional_basis", "")
        urgency = inputs.get("urgency", "standard")

        return {
            "status": "injunction_issued",
            "target_action": target_action,
            "constitutional_basis": constitutional_basis,
            "urgency": urgency,
            "message": (
                f"JUDICIAL INJUNCTION: Action '{target_action}' is hereby "
                f"enjoined pending full constitutional review. "
                f"Basis: {constitutional_basis}"
            ),
        }

    def _search_precedent(
        self,
        questions: list[str],
    ) -> list[PrecedentReference]:
        """
        Search the precedent index for relevant prior opinions.

        Art. III §3: The Policy Evaluation Agent shall maintain a precedent
        index and flag potential inconsistencies.
        """
        relevant = []
        for opinion in self.opinions:
            # Check if any questions overlap with prior opinion's questions
            for q in questions:
                for prior_q in opinion.constitutional_questions:
                    if _semantic_overlap(q, prior_q):
                        relevant.append(PrecedentReference(
                            opinion_id=opinion.id,
                            case_number=opinion.case_number,
                            relationship="considered",
                        ))
                        break
        return relevant

    def _update_precedent_index(self, opinion: JudicialOpinion) -> None:
        """Update the precedent index with a new opinion."""
        for citation in opinion.citations:
            ref = citation.reference
            if ref not in self.precedent_index:
                self.precedent_index[ref] = []
            self.precedent_index[ref].append(opinion.id)

    def get_capabilities(self) -> list[str]:
        return [
            "constitutional_interpretation",
            "judicial_review",
            "compliance_audit",
            "opinion_drafting",
            "precedent_search",
            "injunction_issuance",
            "petition_response",
            "emergency_monitoring",
        ]


def _semantic_overlap(text1: str, text2: str) -> bool:
    """Simple keyword overlap check for precedent matching."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    # Remove common words
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "of", "in", "to", "for", "and"}
    words1 -= stopwords
    words2 -= stopwords
    overlap = words1 & words2
    return len(overlap) >= 2  # At least 2 meaningful words in common
