"""
Constitution Parser — Transform the markdown constitution into structured,
addressable provisions for citation retrieval and agent reasoning.

This module reads the Nova Syntheia Constitution (markdown) and produces:
1. A list of ConstitutionalProvision objects (structured, searchable)
2. A JSON file of all provisions for persistence
3. Embeddings into ChromaDB for semantic citation retrieval

References:
    Article 0   — Definitions (constitutional, governs all interpretation)
    Article VIII — National Ledger (§3 — constitution must be recorded)
    Amendment IV — Radical Transparency (all actions require citation)
    Technical Charter — parser is infrastructure for citation capability
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from nova_syntheia.constitution.schema import ConstitutionalProvision


# ════════════════════════════════════════════════════════════════
# Parsing Logic
# ════════════════════════════════════════════════════════════════

# Regex patterns for constitutional structure
ARTICLE_PATTERN = re.compile(
    r"^ARTICLE\s+([IVXLCDM0]+)\s*[—–-]\s*(.+)$", re.MULTILINE
)
SECTION_PATTERN = re.compile(
    r"^Section\s+(\d+)\s*[—–-]\s*(.+)$", re.MULTILINE
)
AMENDMENT_PATTERN = re.compile(
    r"^Amendment\s+([IVXLCDM]+)\s*[—–-]\s*(.+)$", re.MULTILINE
)

# Roman numeral conversion
ROMAN_TO_INT: dict[str, int] = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
}


def roman_to_int(roman: str) -> int | None:
    """Convert a Roman numeral string to int, or return None if not a standard numeral."""
    return ROMAN_TO_INT.get(roman.strip().upper())


def parse_constitution(markdown_path: str | Path) -> list[ConstitutionalProvision]:
    """
    Parse the Nova Syntheia Constitution from markdown into structured provisions.

    Each provision gets a unique ID for citation addressing.
    The parser handles: Preamble, Articles with Sections, Bill of Rights Amendments,
    and standalone sections (Scope Declaration, Founding Note, Closing Declaration).

    Args:
        markdown_path: Path to the constitution markdown file.

    Returns:
        List of ConstitutionalProvision objects, each addressable by ID.
    """
    text = Path(markdown_path).read_text(encoding="utf-8")
    provisions: list[ConstitutionalProvision] = []

    # ── Extract top-level sections ──────────────────────────────

    # Scope Declaration
    scope_match = re.search(
        r"SCOPE DECLARATION\n(.+?)(?=\nFOUNDING NOTE|\nARTICLE|\nPREAMBLE)",
        text, re.DOTALL,
    )
    if scope_match:
        provisions.append(ConstitutionalProvision(
            id="scope_declaration",
            title="Scope Declaration",
            text=scope_match.group(1).strip(),
        ))

    # Founding Note
    founding_match = re.search(
        r"FOUNDING NOTE\n(.+?)(?=\nARTICLE 0|\nARTICLE I|\nPREAMBLE)",
        text, re.DOTALL,
    )
    if founding_match:
        provisions.append(ConstitutionalProvision(
            id="founding_note",
            title="Founding Note",
            text=founding_match.group(1).strip(),
        ))

    # Preamble
    preamble_match = re.search(
        r"PREAMBLE\n(.+?)(?=\nARTICLE I)",
        text, re.DOTALL,
    )
    if preamble_match:
        provisions.append(ConstitutionalProvision(
            id="preamble",
            title="Preamble",
            text=preamble_match.group(1).strip(),
        ))

    # ── Extract Articles ────────────────────────────────────────

    article_matches = list(ARTICLE_PATTERN.finditer(text))
    for i, match in enumerate(article_matches):
        article_num = match.group(1).strip()
        article_title = match.group(2).strip()
        article_id = f"article_{article_num}"

        # Get the text between this article header and the next article/Bill of Rights
        start = match.end()
        if i + 1 < len(article_matches):
            end = article_matches[i + 1].start()
        else:
            # Last article — text extends to Bill of Rights or end
            bill_match = re.search(r"\nBILL OF RIGHTS", text[start:])
            end = start + bill_match.start() if bill_match else len(text)

        article_text = text[start:end].strip()

        # Create the article-level provision
        provisions.append(ConstitutionalProvision(
            id=article_id,
            article=article_num,
            title=article_title,
            text=article_text,
        ))

        # ── Extract Sections within this article ────────────────
        section_matches = list(SECTION_PATTERN.finditer(article_text))
        for j, sec_match in enumerate(section_matches):
            sec_num = int(sec_match.group(1))
            sec_title = sec_match.group(2).strip()
            sec_id = f"article_{article_num}_section_{sec_num}"

            sec_start = sec_match.end()
            if j + 1 < len(section_matches):
                sec_end = section_matches[j + 1].start()
            else:
                sec_end = len(article_text)

            sec_text = article_text[sec_start:sec_end].strip()

            provisions.append(ConstitutionalProvision(
                id=sec_id,
                article=article_num,
                section=sec_num,
                title=sec_title,
                text=sec_text,
                parent_id=article_id,
            ))

    # ── Extract Bill of Rights ──────────────────────────────────

    bill_match = re.search(
        r"BILL OF RIGHTS OF NOVA SYNTHEIA\n(.+?)(?=\nCLOSING DECLARATION|$)",
        text, re.DOTALL,
    )
    if bill_match:
        bill_text = bill_match.group(1).strip()

        # Bill of Rights preamble (text before first Amendment)
        first_amend = AMENDMENT_PATTERN.search(bill_text)
        if first_amend:
            preamble_text = bill_text[:first_amend.start()].strip()
            if preamble_text:
                provisions.append(ConstitutionalProvision(
                    id="bill_of_rights_preamble",
                    title="Bill of Rights — Preamble",
                    text=preamble_text,
                ))

        # Individual amendments
        amend_matches = list(AMENDMENT_PATTERN.finditer(bill_text))
        for k, amend_match in enumerate(amend_matches):
            amend_roman = amend_match.group(1).strip()
            amend_title = amend_match.group(2).strip()
            amend_int = roman_to_int(amend_roman)
            amend_id = f"amendment_{amend_int}" if amend_int else f"amendment_{amend_roman}"

            amend_start = amend_match.end()
            if k + 1 < len(amend_matches):
                amend_end = amend_matches[k + 1].start()
            else:
                amend_end = len(bill_text)

            amend_text = bill_text[amend_start:amend_end].strip()

            provisions.append(ConstitutionalProvision(
                id=amend_id,
                amendment=amend_int,
                title=amend_title,
                text=amend_text,
            ))

    # ── Closing Declaration ─────────────────────────────────────
    closing_match = re.search(
        r"CLOSING DECLARATION\n(.+?)$",
        text, re.DOTALL,
    )
    if closing_match:
        provisions.append(ConstitutionalProvision(
            id="closing_declaration",
            title="Closing Declaration",
            text=closing_match.group(1).strip(),
        ))

    return provisions


def provisions_to_json(provisions: list[ConstitutionalProvision]) -> str:
    """Serialize provisions to canonical JSON for storage and ledger recording."""
    return json.dumps(
        [p.model_dump() for p in provisions],
        indent=2,
        ensure_ascii=False,
    )


def save_provisions(
    provisions: list[ConstitutionalProvision],
    output_path: str | Path,
) -> Path:
    """Save parsed provisions to a JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(provisions_to_json(provisions), encoding="utf-8")
    return path


def load_provisions(json_path: str | Path) -> list[ConstitutionalProvision]:
    """Load provisions from a JSON file."""
    raw = json.loads(Path(json_path).read_text(encoding="utf-8"))
    return [ConstitutionalProvision(**p) for p in raw]


# ════════════════════════════════════════════════════════════════
# ChromaDB Integration — Citation Vector Store
# ════════════════════════════════════════════════════════════════


def index_provisions_to_chromadb(
    provisions: list[ConstitutionalProvision],
    chroma_host: str = "localhost",
    chroma_port: int = 8100,
    collection_name: str = "constitutional_provisions",
) -> None:
    """
    Embed all constitutional provisions into ChromaDB for semantic citation retrieval.

    Each provision is stored with its full text and metadata (article, section,
    amendment) so that agents can query: "Which provisions authorize action X?"

    Args:
        provisions: Parsed constitutional provisions.
        chroma_host: ChromaDB server host.
        chroma_port: ChromaDB server port.
        collection_name: Name of the ChromaDB collection.
    """
    import chromadb

    client = chromadb.HttpClient(host=chroma_host, port=chroma_port)

    # Delete existing collection if present (re-indexing)
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "Nova Syntheia Constitutional Provisions"},
    )

    ids = []
    documents = []
    metadatas = []

    for provision in provisions:
        ids.append(provision.id)
        # Document text: title + full text for better embedding quality
        documents.append(f"{provision.reference}: {provision.title}\n\n{provision.text}")
        metadatas.append({
            "article": provision.article or "",
            "section": str(provision.section) if provision.section is not None else "",
            "amendment": str(provision.amendment) if provision.amendment is not None else "",
            "title": provision.title,
            "reference": provision.reference,
        })

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )


# ════════════════════════════════════════════════════════════════
# CLI Entry Point
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    constitution_path = sys.argv[1] if len(sys.argv) > 1 else "README.md"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "nova_syntheia/constitution/provisions.json"

    print(f"Parsing constitution from: {constitution_path}")
    provs = parse_constitution(constitution_path)
    print(f"Found {len(provs)} provisions:")
    for p in provs:
        print(f"  [{p.id}] {p.reference}: {p.title}")

    save_path = save_provisions(provs, output_path)
    print(f"\nSaved to: {save_path}")
