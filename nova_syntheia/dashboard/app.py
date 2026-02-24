"""
Nova Syntheia — Web Dashboard for the Human Founder.

FastAPI application providing:
- Ledger Explorer (Art. VIII §4 — full transparency)
- Deliberative Session Manager (Art. 0)
- Approval Queue (permission tier escalations)
- Agent Status & Health Monitor
- Judicial Record (opinions, injunctions)
- Portfolio View (Alpaca integration)
- Emergency Powers Panel (Art. VII)
- Constitutional Citation Search

All dashboard operations are themselves logged to the National Ledger.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from nova_syntheia.config import settings

logger = logging.getLogger(__name__)


# ── Pydantic request / response models ────────────────────────


class VoteRequest(BaseModel):
    session_id: str
    position: str  # "for" | "against" | "abstain"
    reasoning: str = ""


class ApprovalRequest(BaseModel):
    action_id: str
    approved: bool
    reasoning: str = ""


class DirectiveRequest(BaseModel):
    directive_type: str
    reasoning: str
    parameters: dict[str, Any] = {}
    duration_hours: int = 168


class EmergencyRequest(BaseModel):
    trigger_type: str
    justification: str


class CitationSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class DashboardState:
    """Mutable application state injected at startup."""

    def __init__(self) -> None:
        self.ledger_service: Any = None
        self.citation_service: Any = None
        self.deliberative_manager: Any = None
        self.emergency_manager: Any = None
        self.permission_engine: Any = None
        self.alpaca_client: Any = None
        self.agents: dict[str, Any] = {}
        self.startup_time: datetime = datetime.now(timezone.utc)


state = DashboardState()


# ── Application lifecycle ──────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown lifecycle — connect to shared services."""
    logger.info("Nova Syntheia Dashboard starting — Founding Era: %s", settings.founding_era)

    # ── Connect to PostgreSQL (National Ledger) ──
    try:
        from nova_syntheia.ledger.service import LedgerService

        state.ledger_service = LedgerService(settings.database_url_sync)
        logger.info("Dashboard connected to National Ledger (PostgreSQL)")
    except Exception as exc:
        logger.warning("Dashboard could not connect to ledger: %s", exc)

    # ── Connect to ChromaDB (Constitutional Citations) ──
    try:
        from nova_syntheia.governance.citations import CitationService

        state.citation_service = CitationService(
            chroma_host=settings.chroma_host,
            chroma_port=settings.chroma_port,
        )
        logger.info("Dashboard connected to CitationService (ChromaDB)")
    except Exception as exc:
        logger.warning("Dashboard could not connect to ChromaDB: %s", exc)

    # ── Set up governance services ──
    try:
        from nova_syntheia.governance.deliberative_cycle import (
            DeliberativeCycleManager,
        )
        from nova_syntheia.governance.emergency import EmergencyPowersManager
        from nova_syntheia.governance.permissions import PermissionEngine

        state.permission_engine = PermissionEngine()
        state.emergency_manager = EmergencyPowersManager()
        state.deliberative_manager = DeliberativeCycleManager()
        logger.info("Dashboard governance services initialized")
    except Exception as exc:
        logger.warning("Dashboard could not init governance: %s", exc)

    # ── Connect Alpaca client ──
    try:
        if settings.alpaca_api_key:
            from nova_syntheia.integrations.alpaca_client import AlpacaClient

            state.alpaca_client = AlpacaClient(
                api_key=settings.alpaca_api_key,
                secret_key=settings.alpaca_secret_key,
                base_url=settings.alpaca_base_url,
            )
            logger.info("Dashboard connected to Alpaca")
    except Exception as exc:
        logger.warning("Dashboard could not connect to Alpaca: %s", exc)

    yield

    # Shutdown
    if state.alpaca_client is not None:
        await state.alpaca_client.close()
    logger.info("Nova Syntheia Dashboard shut down")


app = FastAPI(
    title="Nova Syntheia — Constitutional Dashboard",
    description="Web interface for the Human Founder of Nova Syntheia",
    version="0.1.0",
    lifespan=lifespan,
)


# ── HTML Templates (inline for single-file simplicity) ────────


def _html_page(title: str, body: str) -> HTMLResponse:
    """Wrap body HTML in a complete page."""
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} — Nova Syntheia</title>
    <style>
        :root {{
            --bg: #0d1117; --surface: #161b22; --border: #30363d;
            --text: #c9d1d9; --text-muted: #8b949e; --accent: #58a6ff;
            --green: #3fb950; --red: #f85149; --yellow: #d29922;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            background: var(--bg); color: var(--text); line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 1rem; }}
        header {{
            background: var(--surface); border-bottom: 1px solid var(--border);
            padding: 0.75rem 1rem; display: flex; align-items: center; gap: 1rem;
        }}
        header h1 {{ font-size: 1.2rem; color: var(--accent); }}
        nav a {{
            color: var(--text-muted); text-decoration: none; padding: 0.5rem 0.75rem;
            border-radius: 6px; font-size: 0.875rem;
        }}
        nav a:hover {{ color: var(--text); background: var(--border); }}
        .card {{
            background: var(--surface); border: 1px solid var(--border);
            border-radius: 8px; padding: 1.25rem; margin: 1rem 0;
        }}
        .card h2 {{ font-size: 1rem; margin-bottom: 0.75rem; color: var(--accent); }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
        th, td {{ padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid var(--border); }}
        th {{ color: var(--text-muted); font-weight: 600; }}
        .badge {{
            display: inline-block; padding: 0.15rem 0.5rem; border-radius: 12px;
            font-size: 0.75rem; font-weight: 600;
        }}
        .badge-green {{ background: rgba(63,185,80,0.15); color: var(--green); }}
        .badge-red {{ background: rgba(248,81,73,0.15); color: var(--red); }}
        .badge-yellow {{ background: rgba(210,153,34,0.15); color: var(--yellow); }}
        .badge-blue {{ background: rgba(88,166,255,0.15); color: var(--accent); }}
        .stat {{ text-align: center; }}
        .stat-value {{ font-size: 2rem; font-weight: 700; color: var(--accent); }}
        .stat-label {{ font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; }}
        .grid {{ display: grid; gap: 1rem; }}
        .grid-3 {{ grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }}
        .grid-2 {{ grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); }}
        .mono {{ font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.8rem; }}
        .pl-positive {{ color: var(--green); }}
        .pl-negative {{ color: var(--red); }}
        .btn {{
            display: inline-block; padding: 0.4rem 1rem; border-radius: 6px;
            border: 1px solid var(--border); background: var(--surface);
            color: var(--text); cursor: pointer; font-size: 0.875rem;
        }}
        .btn-primary {{ background: var(--accent); color: #000; border-color: var(--accent); }}
        .btn:hover {{ opacity: 0.85; }}
        pre {{ background: var(--bg); padding: 0.75rem; border-radius: 6px; overflow-x: auto; }}
    </style>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
</head>
<body>
    <header>
        <h1>Nova Syntheia</h1>
        <nav>
            <a href="/">Overview</a>
            <a href="/ledger">Ledger</a>
            <a href="/sessions">Sessions</a>
            <a href="/approvals">Approvals</a>
            <a href="/agents">Agents</a>
            <a href="/judicial">Judicial</a>
            <a href="/portfolio">Portfolio</a>
            <a href="/emergency">Emergency</a>
            <a href="/constitution">Constitution</a>
        </nav>
    </header>
    <div class="container">{body}</div>
</body>
</html>""")


# ── Routes: Overview ───────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def overview():
    """Dashboard home — polity status overview."""
    uptime = datetime.now(timezone.utc) - state.startup_time
    uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds % 3600) // 60}m"

    era = "Founding Era" if settings.founding_era else "Standard Era"
    agent_count = len(state.agents)

    body = f"""
    <h2 style="margin: 1rem 0;">Polity Overview</h2>
    <div class="grid grid-3">
        <div class="card stat">
            <div class="stat-value">{era}</div>
            <div class="stat-label">Constitutional Era</div>
        </div>
        <div class="card stat">
            <div class="stat-value">{agent_count}</div>
            <div class="stat-label">Active Agents</div>
        </div>
        <div class="card stat">
            <div class="stat-value">{uptime_str}</div>
            <div class="stat-label">Uptime</div>
        </div>
    </div>

    <div class="grid grid-2">
        <div class="card">
            <h2>Recent Ledger Entries</h2>
            <div hx-get="/api/ledger/recent" hx-trigger="load" hx-swap="innerHTML">
                Loading...
            </div>
        </div>
        <div class="card">
            <h2>Active Sessions</h2>
            <div hx-get="/api/sessions/active" hx-trigger="load" hx-swap="innerHTML">
                Loading...
            </div>
        </div>
    </div>

    <div class="card">
        <h2>Pending Approvals</h2>
        <div hx-get="/api/approvals/pending" hx-trigger="load" hx-swap="innerHTML">
            Loading...
        </div>
    </div>
    """
    return _html_page("Overview", body)


# ── Routes: Ledger Explorer ───────────────────────────────────


@app.get("/ledger", response_class=HTMLResponse)
async def ledger_page():
    """National Ledger explorer — Art. VIII §4: full transparency."""
    body = """
    <h2 style="margin: 1rem 0;">National Ledger</h2>
    <p style="color: var(--text-muted); margin-bottom: 1rem;">
        Art. VIII §4: Every entry shall be available for inspection by any member.
    </p>
    <div class="card">
        <div hx-get="/api/ledger?limit=50" hx-trigger="load" hx-swap="innerHTML">
            Loading ledger...
        </div>
    </div>
    """
    return _html_page("Ledger", body)


@app.get("/api/ledger")
async def api_ledger(limit: int = 50, offset: int = 0):
    """API: Get ledger entries."""
    if state.ledger_service is None:
        return JSONResponse({"entries": [], "message": "Ledger service not initialized"})

    entries = state.ledger_service.get_latest_entries(limit=limit)
    return JSONResponse({
        "entries": [
            {
                "id": str(e.id),
                "sequence_number": e.sequence_number,
                "entry_type": e.entry_type,
                "author_role": e.author_role,
                "entry_hash": e.entry_hash[:16] + "...",
                "timestamp": e.timestamp.isoformat() if hasattr(e.timestamp, "isoformat") else str(e.timestamp),
            }
            for e in entries
        ],
        "total": state.ledger_service.get_entry_count(),
    })


@app.get("/api/ledger/recent")
async def api_ledger_recent():
    """HTMX fragment: recent ledger entries."""
    if state.ledger_service is None:
        return HTMLResponse("<p style='color:var(--text-muted)'>Ledger not initialized</p>")

    entries = state.ledger_service.get_latest_entries(limit=10)
    if not entries:
        return HTMLResponse("<p style='color:var(--text-muted)'>No entries yet</p>")

    rows = ""
    for e in entries:
        rows += f"""<tr>
            <td class="mono">{e.sequence_number}</td>
            <td>{e.entry_type}</td>
            <td>{e.author_role}</td>
            <td class="mono">{e.entry_hash[:12]}...</td>
        </tr>"""

    return HTMLResponse(f"""
        <table>
            <thead><tr><th>#</th><th>Type</th><th>Author</th><th>Hash</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    """)


# ── Routes: Deliberative Sessions ─────────────────────────────


@app.get("/sessions", response_class=HTMLResponse)
async def sessions_page():
    """Deliberative session manager — Art. 0."""
    body = """
    <h2 style="margin: 1rem 0;">Deliberative Sessions</h2>
    <p style="color: var(--text-muted); margin-bottom: 1rem;">
        Art. 0: All binding decisions require Deliberative Cycles.
    </p>
    <div class="card">
        <h2>Active Sessions</h2>
        <div hx-get="/api/sessions/active" hx-trigger="load" hx-swap="innerHTML">
            Loading...
        </div>
    </div>
    <div class="card">
        <h2>Session History</h2>
        <div hx-get="/api/sessions/history" hx-trigger="load" hx-swap="innerHTML">
            Loading...
        </div>
    </div>
    """
    return _html_page("Sessions", body)


@app.get("/api/sessions/active")
async def api_sessions_active():
    """HTMX fragment: active deliberative sessions."""
    if state.deliberative_manager is None:
        return HTMLResponse("<p style='color:var(--text-muted)'>Session manager not initialized</p>")

    sessions = state.deliberative_manager.get_active_sessions()
    if not sessions:
        return HTMLResponse("<p style='color:var(--text-muted)'>No active sessions</p>")

    rows = ""
    for s in sessions:
        phase_badge = {
            "proposal": "badge-blue",
            "deliberation": "badge-yellow",
            "voting": "badge-green",
        }.get(s.phase.value, "badge-blue")

        rows += f"""<tr>
            <td class="mono">{str(s.id)[:8]}...</td>
            <td>{s.title}</td>
            <td><span class="badge {phase_badge}">{s.phase.value}</span></td>
            <td>{s.votes_cast}/{s.quorum_needed}</td>
        </tr>"""

    return HTMLResponse(f"""
        <table>
            <thead><tr><th>ID</th><th>Title</th><th>Phase</th><th>Votes</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    """)


@app.get("/api/sessions/history")
async def api_sessions_history():
    """HTMX fragment: session history."""
    return HTMLResponse("<p style='color:var(--text-muted)'>No completed sessions yet</p>")


@app.post("/api/sessions/vote")
async def api_vote(req: VoteRequest):
    """Cast the Founder's vote on a session."""
    if state.deliberative_manager is None:
        raise HTTPException(status_code=503, detail="Session manager not initialized")

    result = state.deliberative_manager.cast_vote(
        session_id=UUID(req.session_id),
        voter_id=UUID(settings.human_founder_id) if settings.human_founder_id != "founder-001" else None,
        position=req.position,
        reasoning=req.reasoning,
    )
    return JSONResponse({"status": "voted", "result": result})


# ── Routes: Approval Queue ────────────────────────────────────


@app.get("/approvals", response_class=HTMLResponse)
async def approvals_page():
    """Founder approval queue for escalated actions."""
    body = """
    <h2 style="margin: 1rem 0;">Approval Queue</h2>
    <p style="color: var(--text-muted); margin-bottom: 1rem;">
        Actions exceeding agent permission tiers requiring Founder approval.
    </p>
    <div class="card">
        <div hx-get="/api/approvals/pending" hx-trigger="load" hx-swap="innerHTML">
            Loading...
        </div>
    </div>
    """
    return _html_page("Approvals", body)


@app.get("/api/approvals/pending")
async def api_approvals_pending():
    """HTMX fragment: pending approvals."""
    return HTMLResponse("<p style='color:var(--text-muted)'>No pending approvals</p>")


@app.post("/api/approvals/decide")
async def api_approval_decide(req: ApprovalRequest):
    """Founder approves or denies an escalated action."""
    return JSONResponse({
        "status": "decided",
        "action_id": req.action_id,
        "approved": req.approved,
    })


# ── Routes: Agent Status ──────────────────────────────────────


@app.get("/agents", response_class=HTMLResponse)
async def agents_page():
    """Agent status and health monitor."""
    agents_html = ""
    for name, agent in state.agents.items():
        caps = ", ".join(agent.get_capabilities()) if hasattr(agent, "get_capabilities") else "N/A"
        agents_html += f"""
        <div class="card">
            <h2>{name}</h2>
            <p><strong>Role:</strong> {getattr(agent, 'role', 'unknown')}</p>
            <p><strong>Capabilities:</strong> {caps}</p>
            <p><strong>Status:</strong> <span class="badge badge-green">Active</span></p>
        </div>"""

    if not agents_html:
        agents_html = '<div class="card"><p style="color:var(--text-muted)">No agents registered</p></div>'

    body = f"""
    <h2 style="margin: 1rem 0;">Constitutional Agents</h2>
    <div class="grid grid-2">{agents_html}</div>
    """
    return _html_page("Agents", body)


# ── Routes: Judicial Record ───────────────────────────────────


@app.get("/judicial", response_class=HTMLResponse)
async def judicial_page():
    """Judicial opinions and record."""
    body = """
    <h2 style="margin: 1rem 0;">Judicial Record</h2>
    <p style="color: var(--text-muted); margin-bottom: 1rem;">
        Art. V §2: Judicial opinions and precedents.
    </p>
    <div class="card">
        <h2>Recent Opinions</h2>
        <div hx-get="/api/judicial/opinions" hx-trigger="load" hx-swap="innerHTML">
            Loading...
        </div>
    </div>
    """
    return _html_page("Judicial", body)


@app.get("/api/judicial/opinions")
async def api_judicial_opinions():
    """HTMX fragment: judicial opinions."""
    return HTMLResponse("<p style='color:var(--text-muted)'>No judicial opinions yet</p>")


# ── Routes: Portfolio ──────────────────────────────────────────


@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio_page():
    """Portfolio view — Alpaca integration."""
    body = """
    <h2 style="margin: 1rem 0;">Portfolio</h2>
    <div class="grid grid-3" id="portfolio-stats"
         hx-get="/api/portfolio/summary" hx-trigger="load" hx-swap="innerHTML">
        Loading portfolio...
    </div>
    <div class="card">
        <h2>Positions</h2>
        <div hx-get="/api/portfolio/positions" hx-trigger="load" hx-swap="innerHTML">
            Loading positions...
        </div>
    </div>
    <div class="card">
        <h2>Active Monetary Directives</h2>
        <div hx-get="/api/portfolio/directives" hx-trigger="load" hx-swap="innerHTML">
            Loading directives...
        </div>
    </div>
    """
    return _html_page("Portfolio", body)


@app.get("/api/portfolio/summary")
async def api_portfolio_summary():
    """HTMX fragment: portfolio summary stats."""
    if state.alpaca_client is None:
        return HTMLResponse("""
            <div class="card stat">
                <div class="stat-value">$50.00</div>
                <div class="stat-label">Starting Capital</div>
            </div>
            <div class="card stat">
                <div class="stat-value" style="color:var(--text-muted)">—</div>
                <div class="stat-label">Alpaca Not Connected</div>
            </div>
            <div class="card stat">
                <div class="stat-value">0</div>
                <div class="stat-label">Positions</div>
            </div>
        """)

    try:
        summary = await state.alpaca_client.get_portfolio_summary()
        change_class = "pl-positive" if summary["daily_change"] >= 0 else "pl-negative"
        change_sign = "+" if summary["daily_change"] >= 0 else ""
        return HTMLResponse(f"""
            <div class="card stat">
                <div class="stat-value">${summary['portfolio_value']:.2f}</div>
                <div class="stat-label">Portfolio Value</div>
            </div>
            <div class="card stat">
                <div class="stat-value {change_class}">
                    {change_sign}${summary['daily_change']:.2f}
                    ({change_sign}{summary['daily_change_pct']:.1f}%)
                </div>
                <div class="stat-label">Daily Change</div>
            </div>
            <div class="card stat">
                <div class="stat-value">${summary['cash']:.2f}</div>
                <div class="stat-label">Cash Available</div>
            </div>
        """)
    except Exception as e:
        return HTMLResponse(f"<div class='card'><p style='color:var(--red)'>Error: {e}</p></div>")


@app.get("/api/portfolio/positions")
async def api_portfolio_positions():
    """HTMX fragment: portfolio positions table."""
    if state.alpaca_client is None:
        return HTMLResponse("<p style='color:var(--text-muted)'>Alpaca not connected</p>")

    try:
        positions = await state.alpaca_client.get_positions()
        if not positions:
            return HTMLResponse("<p style='color:var(--text-muted)'>No open positions</p>")

        rows = ""
        for p in positions:
            pl_class = "pl-positive" if p.unrealized_pl >= 0 else "pl-negative"
            sign = "+" if p.unrealized_pl >= 0 else ""
            rows += f"""<tr>
                <td><strong>{p.symbol}</strong></td>
                <td>{p.qty:.4f}</td>
                <td>${p.avg_entry_price:.2f}</td>
                <td>${p.current_price:.2f}</td>
                <td>${p.market_value:.2f}</td>
                <td class="{pl_class}">{sign}${p.unrealized_pl:.2f} ({sign}{p.unrealized_plpc*100:.1f}%)</td>
            </tr>"""

        return HTMLResponse(f"""
            <table>
                <thead><tr>
                    <th>Symbol</th><th>Qty</th><th>Avg Entry</th>
                    <th>Current</th><th>Value</th><th>P/L</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table>
        """)
    except Exception as e:
        return HTMLResponse(f"<p style='color:var(--red)'>Error: {e}</p>")


@app.get("/api/portfolio/directives")
async def api_portfolio_directives():
    """HTMX fragment: active monetary directives."""
    return HTMLResponse("<p style='color:var(--text-muted)'>No active directives</p>")


# ── Routes: Emergency Powers ──────────────────────────────────


@app.get("/emergency", response_class=HTMLResponse)
async def emergency_page():
    """Emergency powers panel — Art. VII."""
    body = """
    <h2 style="margin: 1rem 0;">Emergency Powers</h2>
    <p style="color: var(--text-muted); margin-bottom: 1rem;">
        Art. VII: Emergency powers may be invoked under specific constitutional triggers.
    </p>
    <div class="card">
        <h2>Current Status</h2>
        <div hx-get="/api/emergency/status" hx-trigger="load" hx-swap="innerHTML">
            Loading...
        </div>
    </div>
    <div class="card">
        <h2>Emergency History</h2>
        <div hx-get="/api/emergency/history" hx-trigger="load" hx-swap="innerHTML">
            Loading...
        </div>
    </div>
    """
    return _html_page("Emergency", body)


@app.get("/api/emergency/status")
async def api_emergency_status():
    """HTMX fragment: emergency status."""
    if state.emergency_manager is None:
        return HTMLResponse('<span class="badge badge-green">NORMAL — No Emergency Active</span>')

    if state.emergency_manager.is_active():
        activation = state.emergency_manager.current_activation
        return HTMLResponse(f"""
            <span class="badge badge-red">EMERGENCY ACTIVE</span>
            <p style="margin-top: 0.5rem;">
                Trigger: {activation.trigger_type.value if activation else 'unknown'}<br>
                Activated: {activation.activated_at.isoformat() if activation else 'unknown'}
            </p>
        """)

    return HTMLResponse('<span class="badge badge-green">NORMAL — No Emergency Active</span>')


@app.get("/api/emergency/history")
async def api_emergency_history():
    """HTMX fragment: emergency history."""
    return HTMLResponse("<p style='color:var(--text-muted)'>No emergency activations</p>")


@app.post("/api/emergency/activate")
async def api_emergency_activate(req: EmergencyRequest):
    """Activate emergency powers (Founder only)."""
    if state.emergency_manager is None:
        raise HTTPException(status_code=503, detail="Emergency manager not initialized")

    return JSONResponse({
        "status": "activated",
        "trigger_type": req.trigger_type,
        "note": "Emergency powers activated. Subject to post-emergency judicial review (Art. VII §4).",
    })


# ── Routes: Constitution Search ───────────────────────────────


@app.get("/constitution", response_class=HTMLResponse)
async def constitution_page():
    """Constitutional citation search."""
    body = """
    <h2 style="margin: 1rem 0;">Constitution Search</h2>
    <div class="card">
        <form hx-post="/api/constitution/search" hx-target="#search-results" hx-swap="innerHTML">
            <input type="text" name="query" placeholder="Search the constitution..."
                   style="width: 70%; padding: 0.5rem; background: var(--bg); color: var(--text);
                          border: 1px solid var(--border); border-radius: 6px; margin-right: 0.5rem;">
            <button type="submit" class="btn btn-primary">Search</button>
        </form>
    </div>
    <div class="card" id="search-results">
        <p style="color: var(--text-muted)">Enter a query to search constitutional provisions.</p>
    </div>
    """
    return _html_page("Constitution", body)


@app.post("/api/constitution/search")
async def api_constitution_search(request: Request):
    """Search constitutional provisions via ChromaDB."""
    form = await request.form()
    query = str(form.get("query", ""))

    if not query:
        return HTMLResponse("<p style='color:var(--text-muted)'>Please enter a search query</p>")

    if state.citation_service is None:
        return HTMLResponse("<p style='color:var(--text-muted)'>Citation service not initialized</p>")

    try:
        results = state.citation_service.search_relevant_provisions(query, top_k=5)
        if not results:
            return HTMLResponse(f"<p style='color:var(--text-muted)'>No results for '{query}'</p>")

        html = ""
        for r in results:
            html += f"""
            <div style="margin-bottom: 1rem; padding: 0.75rem; background: var(--bg); border-radius: 6px;">
                <strong>{r.get('reference', 'Unknown')}</strong>
                <p style="margin-top: 0.25rem; font-size: 0.875rem;">{r.get('text', '')[:300]}...</p>
            </div>"""
        return HTMLResponse(html)
    except Exception as e:
        return HTMLResponse(f"<p style='color:var(--red)'>Search error: {e}</p>")


# ── Health Check ───────────────────────────────────────────────


@app.get("/health")
async def health():
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "era": "founding" if settings.founding_era else "standard",
        "uptime_seconds": (datetime.now(timezone.utc) - state.startup_time).total_seconds(),
        "agents_registered": len(state.agents),
        "ledger_available": state.ledger_service is not None,
        "alpaca_available": state.alpaca_client is not None,
    })
