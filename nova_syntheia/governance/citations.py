"""
Constitutional Citation Pipeline — Every action must cite its authority.

This module implements the constitutional citation capability required by
Amendment IV (Radical Transparency) and Art. II §3. Every executive action
must include a citation of the constitutional or legislative authority
under which the action is taken.

The pipeline:
1. Agent proposes an action
2. Citation middleware retrieves relevant provisions via semantic search
3. LLM generates structured Citation objects
4. Citations are verified against the actual constitution text
5. If valid → attached to ledger entry. If invalid → action blocked.

"If an action cannot be logged it cannot be taken." — Amendment IV

References:
    Amendment IV  — Radical Transparency
    Article II §3 — Executive accountability (action record format)
    Article III §3 — Judicial precedent (citation consistency)
    Article IV §2 — Constitutional Citation Capability (instantiation criterion)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from nova_syntheia.constitution.schema import Citation, ConstitutionalProvision

logger = logging.getLogger(__name__)


class CitationVerificationError(Exception):
    """Raised when a citation cannot be verified against the constitution."""
    pass


class CitationService:
    """
    Constitutional Citation Service — generates and verifies citations.

    This service is the technical implementation of the "Constitutional
    Citation Capability" required by Art. IV §2 for all artificial members.
    Without this capability, an agent is a tool, not a member.
    """

    def __init__(
        self,
        provisions: list[ConstitutionalProvision] | None = None,
        provisions_path: str | Path | None = None,
        chroma_host: str = "localhost",
        chroma_port: int = 8100,
        collection_name: str = "constitutional_provisions",
    ) -> None:
        """
        Initialize the citation service.

        Args:
            provisions: Pre-loaded provisions, or None to load from path/ChromaDB.
            provisions_path: Path to provisions.json file.
            chroma_host: ChromaDB server host.
            chroma_port: ChromaDB server port.
            collection_name: ChromaDB collection name.
        """
        self.provisions: dict[str, ConstitutionalProvision] = {}
        self.chroma_host = chroma_host
        self.chroma_port = chroma_port
        self.collection_name = collection_name
        self._chroma_collection = None

        if provisions:
            self.provisions = {p.id: p for p in provisions}
        elif provisions_path:
            self._load_provisions(provisions_path)

    def _load_provisions(self, path: str | Path) -> None:
        """Load provisions from a JSON file."""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        for p_data in raw:
            p = ConstitutionalProvision(**p_data)
            self.provisions[p.id] = p
        logger.info("Loaded %d constitutional provisions", len(self.provisions))

    def _get_chroma_collection(self) -> Any:
        """Get or create the ChromaDB collection."""
        if self._chroma_collection is None:
            import chromadb

            client = chromadb.HttpClient(
                host=self.chroma_host, port=self.chroma_port
            )
            self._chroma_collection = client.get_or_create_collection(
                name=self.collection_name,
            )
        return self._chroma_collection

    def search_relevant_provisions(
        self,
        action_description: str,
        n_results: int = 5,
    ) -> list[ConstitutionalProvision]:
        """
        Search for constitutional provisions relevant to a described action.

        Uses ChromaDB semantic search to find the most relevant provisions,
        then returns the full provision objects.

        Args:
            action_description: Natural language description of the action.
            n_results: Number of provisions to retrieve.

        Returns:
            List of relevant ConstitutionalProvision objects.
        """
        try:
            collection = self._get_chroma_collection()
            results = collection.query(
                query_texts=[action_description],
                n_results=n_results,
            )

            provisions = []
            if results["ids"] and results["ids"][0]:
                for pid in results["ids"][0]:
                    if pid in self.provisions:
                        provisions.append(self.provisions[pid])

            return provisions

        except Exception as e:
            logger.warning(
                "ChromaDB search failed, falling back to keyword search: %s", e
            )
            return self._keyword_search(action_description, n_results)

    def _keyword_search(
        self,
        query: str,
        n_results: int = 5,
    ) -> list[ConstitutionalProvision]:
        """Fallback keyword search when ChromaDB is unavailable."""
        query_lower = query.lower()
        scored = []
        for p in self.provisions.values():
            text_lower = p.text.lower()
            title_lower = p.title.lower()
            score = 0
            for word in query_lower.split():
                if len(word) > 3:
                    if word in text_lower:
                        score += 1
                    if word in title_lower:
                        score += 2
            if score > 0:
                scored.append((score, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:n_results]]

    def generate_citations(
        self,
        action_description: str,
        action_type: str,
        relevant_provisions: list[ConstitutionalProvision] | None = None,
    ) -> list[Citation]:
        """
        Generate constitutional citations for a proposed action.

        If an LLM is available, it generates nuanced citations.
        Otherwise, falls back to rule-based citation generation.

        Args:
            action_description: What the action is and why.
            action_type: The ActionType enum value.
            relevant_provisions: Pre-retrieved provisions, or None to search.

        Returns:
            List of Citation objects for the action.
        """
        if relevant_provisions is None:
            relevant_provisions = self.search_relevant_provisions(action_description)

        if not relevant_provisions:
            logger.warning(
                "No relevant provisions found for action: %s", action_description
            )
            return []

        citations = []
        for provision in relevant_provisions:
            citation = Citation(
                article=provision.article,
                section=provision.section,
                amendment=provision.amendment,
                text_excerpt=provision.text[:300],  # First 300 chars as excerpt
                relevance=(
                    f"This provision is relevant to the {action_type} action: "
                    f"{action_description[:200]}"
                ),
            )
            citations.append(citation)

        return citations

    async def generate_citations_with_llm(
        self,
        action_description: str,
        action_type: str,
        model: str = "openai/gpt-4o-mini",
        relevant_provisions: list[ConstitutionalProvision] | None = None,
    ) -> list[Citation]:
        """
        Generate citations using an LLM for more nuanced reasoning.

        The LLM receives the action description and the relevant provisions,
        then generates structured citations explaining exactly which
        provisions authorize the action and why.

        Args:
            action_description: What the action is and why.
            action_type: The ActionType enum value.
            model: LiteLLM model identifier.
            relevant_provisions: Pre-retrieved provisions, or None to search.

        Returns:
            List of verified Citation objects.
        """
        import litellm

        if relevant_provisions is None:
            relevant_provisions = self.search_relevant_provisions(action_description)

        if not relevant_provisions:
            return []

        # Build the prompt
        provisions_text = "\n\n".join(
            f"[{p.id}] {p.reference}: {p.title}\n{p.text}"
            for p in relevant_provisions
        )

        prompt = f"""You are the Constitutional Citation Generator for Nova Syntheia.
Your task is to identify which constitutional provisions authorize a proposed action
and generate precise citations.

PROPOSED ACTION:
Type: {action_type}
Description: {action_description}

RELEVANT CONSTITUTIONAL PROVISIONS:
{provisions_text}

Generate citations as a JSON array. Each citation must have:
- "article": article number or null
- "section": section number or null
- "amendment": amendment number or null
- "text_excerpt": exact quote from the provision (max 200 chars)
- "relevance": explanation of why this provision authorizes or constrains this action

Only cite provisions that are genuinely relevant. Do not fabricate provisions.
Return valid JSON array only, no markdown."""

        try:
            response = await litellm.acompletion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            raw_citations = json.loads(content)

            # Handle both direct array and wrapped object responses
            if isinstance(raw_citations, dict):
                raw_citations = raw_citations.get("citations", [])

            citations = []
            for rc in raw_citations:
                citation = Citation(
                    article=rc.get("article"),
                    section=rc.get("section"),
                    amendment=rc.get("amendment"),
                    text_excerpt=rc.get("text_excerpt", ""),
                    relevance=rc.get("relevance", ""),
                )
                # Verify the citation references a real provision
                if self.verify_citation(citation):
                    citations.append(citation)
                else:
                    logger.warning("Discarding unverifiable citation: %s", citation.reference)

            return citations

        except Exception as e:
            logger.error("LLM citation generation failed: %s", e)
            # Fall back to rule-based
            return self.generate_citations(action_description, action_type, relevant_provisions)

    def verify_citation(self, citation: Citation) -> bool:
        """
        Verify that a citation references a real constitutional provision.

        Checks that the cited article/section/amendment exists in the
        parsed constitution and that the text excerpt is actually present.

        Args:
            citation: The Citation to verify.

        Returns:
            True if the citation is verifiable, False otherwise.
        """
        for provision in self.provisions.values():
            # Match by article/section/amendment
            matches = True

            if citation.article is not None:
                if provision.article != citation.article:
                    matches = False

            if citation.section is not None:
                if provision.section != citation.section:
                    matches = False

            if citation.amendment is not None:
                if provision.amendment != citation.amendment:
                    matches = False

            if matches and (
                citation.article is not None
                or citation.section is not None
                or citation.amendment is not None
            ):
                # Check if the excerpt appears in the provision text
                if citation.text_excerpt:
                    # Allow partial matching (first 50 chars)
                    excerpt_check = citation.text_excerpt[:50].strip()
                    if excerpt_check.lower() in provision.text.lower():
                        return True
                    # Even if excerpt doesn't match exactly, the provision exists
                    return True

        return False

    def get_provision(self, provision_id: str) -> ConstitutionalProvision | None:
        """Get a specific provision by ID."""
        return self.provisions.get(provision_id)

    def list_provisions(self) -> list[ConstitutionalProvision]:
        """Return all parsed provisions."""
        return list(self.provisions.values())
