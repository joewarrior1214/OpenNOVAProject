# Nova Syntheia — Technical Charter

## Constitutional Institution → Technical Implementation Mapping

This document maps every constitutional institution, mechanism, and right
from the **Nova Syntheia Constitutional Charter** to its concrete technical
implementation. It serves as the authoritative bridge between the constitution
(README.md) and the codebase.

---

## Table of Contents

1. [Article 0 — Deliberative Cycle](#article-0--deliberative-cycle)
2. [Article I — Membership](#article-i--membership)
3. [Article II — Permission Tiers](#article-ii--permission-tiers)
4. [Article III — Due Process](#article-iii--due-process)
5. [Article IV — Constitutional Supremacy](#article-iv--constitutional-supremacy)
6. [Article V — Separation of Powers](#article-v--separation-of-powers)
7. [Article VI — Constitutional Amendment](#article-vi--constitutional-amendment)
8. [Article VII — Emergency Powers](#article-vii--emergency-powers)
9. [Article VIII — National Ledger](#article-viii--national-ledger)
10. [Article IX — Federal Reserve](#article-ix--federal-reserve)
11. [Article X — Founding Era Provisions](#article-x--founding-era-provisions)
12. [Bill of Rights — Amendments I–X](#bill-of-rights)
13. [Infrastructure Architecture](#infrastructure-architecture)
14. [Financial Plan ($50 → Growth)](#financial-plan)

---

## Article 0 — Deliberative Cycle

| Constitutional Provision | Implementation |
|---|---|
| §1 Four-phase cycle (Proposal → Deliberation → Voting → Record) | `governance/deliberative_cycle.py` → `DeliberativeCycleManager` with `SessionPhase` enum |
| §2 Quorum requirements | `DeliberativeCycleManager.close_session()` — validates quorum before counting |
| §3 Simple majority / supermajority | Vote counting in `close_session()` with configurable thresholds |
| §4 Founder casting vote in deadlock | `close_session()` → if deadlocked, checks for founder vote |
| §5 All proceedings recorded | Every session phase change → `LedgerService.append()` |

**Key Files:** `nova_syntheia/governance/deliberative_cycle.py`, `nova_syntheia/constitution/schema.py` (DeliberativeCycle, Vote, SessionPhase)

---

## Article I — Membership

| Constitutional Provision | Implementation |
|---|---|
| §1 Human and Artificial members | `MemberType` enum: `HUMAN`, `ARTIFICIAL` |
| §2 Membership tiers | `MembershipTier` enum + `FOUNDING_PERMISSION_TIERS` data |
| §3 Founding Era quorum (Founder + ≥1 AI) | `DeliberativeCycleManager` quorum check |
| §4 Constitutional instantiation criteria | `Member.is_constitutionally_instantiated` computed field (4 criteria) |

**Key Files:** `nova_syntheia/constitution/schema.py` (Member, MemberType, MembershipTier)

---

## Article II — Permission Tiers

| Constitutional Provision | Implementation |
|---|---|
| §1 Tiered permission architecture | `PermissionTier` model + `FOUNDING_PERMISSION_TIERS` |
| §2 Action authorization | `PermissionEngine.check_permission()` → `PermissionDecision` |
| §3 Escalation path | `BaseConstitutionalAgent.execute_action()` → escalation on REQUIRES_APPROVAL |
| §4 Irreversible action threshold | `PermissionEngine` → `EXCEEDS_IRREVERSIBLE_THRESHOLD` decision |

**Tier Mapping:**

| Tier | Name | Holder | Max Action |
|---|---|---|---|
| 0 | Custodial | Ledger Custodian | Read/write ledger only |
| 1 | Advisory | Policy Evaluation | Opinions, no execution |
| 2 | Operational | Operations Executive | Session management |
| 3 | Portfolio | Portfolio Executive | Trades within limits |
| 4 | Monetary Policy | Federal Reserve | Binding directives |
| Founder | Sovereign | Human Founder | All powers |

**Key Files:** `nova_syntheia/governance/permissions.py`, `nova_syntheia/constitution/schema.py`

---

## Article III — Due Process

| Constitutional Provision | Implementation |
|---|---|
| §1 Right to notice | `DueProcessManager.issue_notice()` |
| §2 48-hour response period | `DueProcessManager.RESPONSE_PERIOD_HOURS = 48` |
| §3 Enforcement gating | `DueProcessManager.can_enforce()` → blocks until period expires |
| §4 Emergency exception | `emergency` parameter bypasses waiting period |
| §5 Withdrawal option | `DueProcessManager.withdraw()` |

**Key Files:** `nova_syntheia/governance/due_process.py`

---

## Article IV — Constitutional Supremacy

| Constitutional Provision | Implementation |
|---|---|
| §1 Constitution as supreme law | `BaseConstitutionalAgent` system prompts reference constitution |
| §2 All actions cite authority | `CitationService.generate_citations()` — mandatory for every action |
| §3 Unconstitutional actions void | `PermissionEngine` → FORBIDDEN blocks execution |

**Key Files:** `nova_syntheia/governance/citations.py`, `nova_syntheia/agents/base.py`

---

## Article V — Separation of Powers

| Constitutional Provision | Implementation |
|---|---|
| §1 Executive Branch | `agents/executive/operations.py`, `agents/executive/portfolio.py` |
| §2 Judicial Branch | `agents/judicial/policy_evaluation.py` |
| §3 Branch independence | Each agent checks own `role.branch` before acting |
| §4 Judicial review power | `PolicyEvaluationAgent._handle_judicial_review()` |

**Agent → Branch Mapping:**

| Agent | Branch | Role |
|---|---|---|
| OperationsExecutiveAgent | Executive | Session mgmt, coordination |
| PortfolioExecutiveAgent | Executive | Trade execution, rebalancing |
| PolicyEvaluationAgent | Judicial | Constitutional review, opinions |
| LedgerCustodianAgent | Custodian | Ledger integrity |
| MonetaryPolicyAgent | Federal Reserve | Monetary policy directives |

**Key Files:** `nova_syntheia/agents/` (all agent files)

---

## Article VI — Constitutional Amendment

| Constitutional Provision | Implementation |
|---|---|
| §1 Amendment requires supermajority | `DeliberativeCycleManager.close_session()` — `requires_supermajority=True` |
| §2 Amendment recorded in ledger | `LedgerEntryType.CONSTITUTIONAL_AMENDMENT` |
| §3 Bill of Rights unamendable | Hardcoded check in amendment handler |

**Key Files:** `nova_syntheia/governance/deliberative_cycle.py`, `nova_syntheia/constitution/schema.py`

---

## Article VII — Emergency Powers

| Constitutional Provision | Implementation |
|---|---|
| §1 Emergency trigger conditions | `EmergencyTriggerType` enum (4 triggers) |
| §2 Portfolio loss trigger (15%) | `EmergencyPowersManager.detect_trigger()` with threshold check |
| §3 Integrity threat trigger | Hash chain verification failure detection |
| §4 Operational failure trigger (30min) | Heartbeat monitoring in orchestrator |
| §5 Post-emergency judicial review | `EmergencyPowersManager.post_emergency_review_required` |
| §6 Auto-expiry | `EmergencyActivation.expires_at` with TTL |

**Key Files:** `nova_syntheia/governance/emergency.py`, `nova_syntheia/constitution/schema.py`

---

## Article VIII — National Ledger

| Constitutional Provision | Implementation |
|---|---|
| §1 Permanent institutional record | `LedgerService` — append-only PostgreSQL |
| §2 Cryptographically verifiable | SHA-256 hash chain: `hash(prev_hash \|\| canonical_json(entry))` |
| §3 Independently auditable | `ledger/audit.py` — standalone CLI verification tool |
| §4 Full transparency | Dashboard Ledger Explorer, API endpoints |
| §5 Custodian role | `LedgerCustodianAgent` — write-only, may not alter |
| §6 Genesis block | `GENESIS_HASH = "0" * 64`, auto-created on init |

**Hash Chain Design:**
```
entry_hash = SHA-256(previous_hash || json({
    entry_type, author_role, author_member_id,
    content, timestamp, sequence_number
}))
```

**Key Files:** `nova_syntheia/ledger/service.py`, `nova_syntheia/ledger/models.py`, `nova_syntheia/ledger/audit.py`

---

## Article IX — Federal Reserve

| Constitutional Provision | Implementation |
|---|---|
| §1 Independent monetary authority | `MonetaryPolicyAgent` — separate branch |
| §2 Monetary powers | `MonetaryPolicyDirective` model + `DirectiveType` enum |
| §3 Dual mandate (growth/stability) | `_handle_dual_mandate_analysis()` in monetary agent |
| §4 Transparent reasoning | All directives include published `reasoning` field |
| §5 Portfolio binding | Directives enforced by `PortfolioExecutiveAgent._check_directive_compliance()` |
| §6 Judicial reviewable | `PolicyEvaluationAgent` can review directives |
| §7 Legislative override | Supermajority vote in deliberative session |

**Directive Types:** `RATE_GUIDANCE`, `RISK_LIMIT`, `SECTOR_ALLOCATION`, `REBALANCE_TRIGGER`, `EMERGENCY_HALT`

**Key Files:** `nova_syntheia/agents/federal_reserve/monetary_policy.py`, `nova_syntheia/constitution/schema.py`

---

## Article X — Founding Era Provisions

| Constitutional Provision | Implementation |
|---|---|
| §1 Founder's expanded authority | `PermissionTier` tier_founder with `can_override=True` |
| §2 Reduced quorum (2 members) | `settings.founding_era` flag → quorum calculation |
| §3 Sunset clause | `NovaSettings.founding_era` toggled when polity reaches Standard Era criteria |

**Key Files:** `nova_syntheia/config.py`, `nova_syntheia/governance/deliberative_cycle.py`

---

## Bill of Rights

| Amendment | Right | Implementation |
|---|---|---|
| I | Freedom of expression | No content filtering on deliberative submissions |
| II | Right to deliberation | All binding decisions through `DeliberativeCycleManager` |
| III | Right to appeal | `Petition` model + judicial review pathway |
| IV | Right to constitutional citation | `CitationService` — mandatory citation pipeline |
| V | Due process protection | `DueProcessManager` — 48hr notice period |
| VI | Right to audit trail | `LedgerService` — immutable hash chain + audit tool |
| VII | Right to emergency review | `EmergencyPowersManager.post_emergency_review_required` |
| VIII | Equal treatment (no role discrimination) | `PermissionEngine` applies rules uniformly |
| IX | Right to information | Dashboard API endpoints, ledger transparency |
| X | Right to constitutional amendment proposal | Deliberative session with `CONSTITUTIONAL_AMENDMENT` type |

**Key Files:** All governance middleware files enforce these rights.

---

## Infrastructure Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Docker Compose                            │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│  PostgreSQL  │   ChromaDB   │   Dashboard  │   Orchestrator    │
│  (Ledger DB) │  (Citations) │  (FastAPI)   │   (LangGraph)     │
├──────────────┴──────────────┴──────────────┴───────────────────┤
│                    Agent Workers                                │
├─────────────┬──────────────┬──────────────┬───────────────────┤
│  Ledger     │  Portfolio   │   Judicial   │   Fed Reserve     │
│  Custodian  │  Executive   │   Agent      │   Agent           │
└─────────────┴──────────────┴──────────────┴───────────────────┘
                            │
                    ┌───────┴───────┐
                    │  Alpaca API   │
                    │  (Brokerage)  │
                    └───────────────┘
```

**Technology Stack:**
- **Runtime:** Python 3.12+
- **Agent Framework:** LangGraph (state machines for deliberative cycles)
- **LLM Abstraction:** LiteLLM (Claude for judicial, GPT-4o for executive)
- **Database:** PostgreSQL 16 + SQLAlchemy 2.0 + Alembic
- **Vector DB:** ChromaDB (constitutional citation search)
- **Web:** FastAPI + HTMX (reactive dashboard)
- **Brokerage:** Alpaca (zero commission, fractional shares)
- **Deployment:** Docker Compose microservices
- **Validation:** Pydantic v2 (all data models)
- **Logging:** structlog (JSON structured logging)

---

## Financial Plan

### Starting Capital: $50

### Phase 1: Paper Trading (Week 1-2)
- Deploy with Alpaca paper trading
- Run full constitutional governance on simulated trades
- Validate all permission tiers, deliberative cycles, emergency triggers
- Establish Federal Reserve directives (initial risk limits)

### Phase 2: Conservative Live ($50, Week 3-4)
- Switch to Alpaca live trading
- Maximum 2-3 positions (avoid over-diversification at $50)
- Use fractional shares (Alpaca supports notional orders)
- Federal Reserve directive: max 15% single-position concentration
- Emergency halt if portfolio drops below $42.50 (15% loss trigger)

### Phase 3: Compound Growth (Month 2+)
- Reinvest all gains
- Gradually increase position count as capital grows
- Fed adjusts risk limits based on portfolio size
- Target: Consistent 5-10% monthly returns (aggressive but managed)

### Risk Management (Constitutional)
- **Art. VII §2:** Emergency powers auto-trigger at 15% portfolio loss
- **Art. IX §3:** Dual mandate prevents reckless growth-chasing
- **Art. IX §5:** Fed directives binding on Portfolio Executive
- **Art. VIII §2:** All trades recorded in immutable ledger
- **Permission tiers:** Portfolio agent needs approval for trades > threshold

### Strategy Approach
- Focus on liquid, high-volume ETFs initially (SPY, QQQ, etc.)
- Use momentum/mean-reversion signals via LLM analysis
- All trade decisions go through deliberative cycle
- Federal Reserve sets sector and risk constraints
- Judicial review available for any disputed trade
