"""
National Ledger Audit Tool — Independent chain integrity verification.

Any member of Nova Syntheia may run this tool to independently verify
the integrity of the National Ledger (Art. VIII §2: independently auditable).

This tool connects directly to the database and recomputes every hash
in the chain, verifying that no entry has been retroactively altered.

Usage:
    python -m nova_syntheia.ledger.audit
    python -m nova_syntheia.ledger.audit --database-url postgresql://...
    python -m nova_syntheia.ledger.audit --verbose

References:
    Article VIII §2 — Independently Auditable
"""

from __future__ import annotations

import argparse
import sys
import time

from rich.console import Console
from rich.table import Table

from nova_syntheia.config import settings
from nova_syntheia.ledger.service import LedgerService

console = Console()


def run_audit(database_url: str, verbose: bool = False) -> bool:
    """
    Run a full hash chain integrity audit.

    Args:
        database_url: PostgreSQL connection string.
        verbose: Print detailed per-entry verification if True.

    Returns:
        True if the chain is valid, False otherwise.
    """
    console.print("\n[bold blue]═══ National Ledger Integrity Audit ═══[/bold blue]")
    console.print(
        "[dim]Article VIII §2: Any member must be able to independently verify "
        "the integrity of the Ledger[/dim]\n"
    )

    service = LedgerService(database_url)

    # Count entries
    count = service.get_entry_count()
    console.print(f"  Entries in ledger: [bold]{count}[/bold]")

    if count == 0:
        console.print("[yellow]⚠ Ledger is empty — no entries to verify[/yellow]")
        return True

    # Run verification
    console.print("  Verifying hash chain...", end=" ")
    start_time = time.time()

    is_valid, entries_verified, message = service.verify_chain()

    elapsed = time.time() - start_time

    if is_valid:
        console.print(f"[bold green]✓ VALID[/bold green]")
        console.print(f"  Entries verified: [bold]{entries_verified}[/bold]")
        console.print(f"  Verification time: {elapsed:.3f}s")
    else:
        console.print(f"[bold red]✗ INVALID[/bold red]")
        console.print(f"  Failure at entry: {entries_verified}")
        console.print(f"  Reason: {message}")

    # Verbose output: show all entries
    if verbose:
        console.print("\n[bold]Detailed Entry Listing:[/bold]")
        table = Table(show_lines=True)
        table.add_column("Seq", style="cyan", width=6)
        table.add_column("Type", style="green", width=25)
        table.add_column("Author", style="yellow", width=25)
        table.add_column("Hash (first 16)", style="dim", width=18)
        table.add_column("Timestamp", width=22)
        table.add_column("Emergency", width=10)

        entries = service.get_latest_entries(limit=count)
        for entry in reversed(entries):
            table.add_row(
                str(entry.sequence_number),
                entry.entry_type,
                entry.author_role,
                entry.entry_hash[:16] + "...",
                str(entry.timestamp)[:19],
                "🚨 YES" if entry.emergency_designation else "—",
            )
        console.print(table)

    console.print(f"\n[bold blue]═══ Audit Complete ═══[/bold blue]\n")
    return is_valid


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Nova Syntheia National Ledger Integrity Auditor (Art. VIII §2)"
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="PostgreSQL connection string (defaults to .env settings)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed entry listing",
    )
    args = parser.parse_args()

    db_url = args.database_url or settings.database_url_sync
    is_valid = run_audit(db_url, verbose=args.verbose)
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
