"""
Nova Syntheia — LangGraph Orchestrator.

Central coordination entrypoint that:
1. Initializes all constitutional services (ledger, citations, governance)
2. Instantiates all constitutional agents
3. Runs the LangGraph deliberative cycle state machine
4. Connects the dashboard to live services

This is the entrypoint for the orchestrator container.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from uuid import uuid4

import structlog

from nova_syntheia.config import settings

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """Configure structured logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            (
                structlog.dev.ConsoleRenderer()
                if settings.log_format != "json"
                else structlog.processors.JSONRenderer()
            ),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


async def main() -> None:
    """Main orchestrator loop."""
    configure_logging()
    log = structlog.get_logger()

    log.info(
        "nova_syntheia.orchestrator.starting",
        founding_era=settings.founding_era,
        judicial_model=settings.judicial_model,
        executive_model=settings.executive_model,
    )

    # Phase 1: Initialize infrastructure
    log.info("nova_syntheia.orchestrator.init_ledger")
    from nova_syntheia.ledger.service import LedgerService

    ledger = LedgerService(settings.database_url_sync)
    ledger.initialize()
    log.info("nova_syntheia.orchestrator.ledger_ready")

    # Phase 2: Parse & index constitution
    log.info("nova_syntheia.orchestrator.init_constitution")
    from nova_syntheia.constitution.parser import index_provisions_to_chromadb, parse_constitution

    provisions = parse_constitution("README.md")
    index_provisions_to_chromadb(
        provisions, chroma_host=settings.chroma_host, chroma_port=settings.chroma_port
    )
    log.info(
        "nova_syntheia.orchestrator.constitution_indexed",
        provisions_count=len(provisions),
    )

    # Phase 3: Initialize governance services
    log.info("nova_syntheia.orchestrator.init_governance")
    from nova_syntheia.governance.citations import CitationService
    from nova_syntheia.governance.deliberative_cycle import DeliberativeCycleManager
    from nova_syntheia.governance.emergency import EmergencyPowersManager

    citation_service = CitationService(
        chroma_host=settings.chroma_host,
        chroma_port=settings.chroma_port,
    )
    deliberative_manager = DeliberativeCycleManager()
    emergency_manager = EmergencyPowersManager()

    log.info("nova_syntheia.orchestrator.governance_ready")

    # Phase 4: Instantiate agents
    log.info("nova_syntheia.orchestrator.init_agents")
    from nova_syntheia.agents.custodian.ledger_custodian import LedgerCustodianAgent
    from nova_syntheia.agents.executive.operations import OperationsExecutiveAgent
    from nova_syntheia.agents.executive.portfolio import PortfolioExecutiveAgent
    from nova_syntheia.agents.federal_reserve.monetary_policy import MonetaryPolicyAgent
    from nova_syntheia.agents.judicial.policy_evaluation import PolicyEvaluationAgent

    agents = {
        "operations_executive": OperationsExecutiveAgent(
            member_id=uuid4(), model=settings.executive_model
        ),
        "portfolio_executive": PortfolioExecutiveAgent(
            member_id=uuid4(), model=settings.executive_model
        ),
        "policy_evaluation": PolicyEvaluationAgent(
            member_id=uuid4(), model=settings.judicial_model
        ),
        "ledger_custodian": LedgerCustodianAgent(
            member_id=uuid4(), model=settings.custodian_model
        ),
        "monetary_policy": MonetaryPolicyAgent(
            member_id=uuid4(), model=settings.federal_reserve_model
        ),
    }

    # Inject shared services into agents
    for agent in agents.values():
        agent.ledger_service = ledger
        agent.citation_service = citation_service

    log.info(
        "nova_syntheia.orchestrator.agents_ready",
        agent_count=len(agents),
        agent_names=list(agents.keys()),
    )

    # Phase 5: Wire up dashboard state
    from nova_syntheia.dashboard.app import state as dashboard_state

    dashboard_state.ledger_service = ledger
    dashboard_state.citation_service = citation_service
    dashboard_state.deliberative_manager = deliberative_manager
    dashboard_state.emergency_manager = emergency_manager
    dashboard_state.agents = agents

    # Initialize Alpaca if configured
    if settings.alpaca_api_key:
        from nova_syntheia.integrations.alpaca_client import AlpacaClient

        alpaca = AlpacaClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            base_url=settings.alpaca_base_url,
        )
        dashboard_state.alpaca_client = alpaca
        log.info("nova_syntheia.orchestrator.alpaca_connected")

    log.info("nova_syntheia.orchestrator.running", message="All systems operational")

    # Main loop — keep orchestrator alive, run periodic tasks
    try:
        while True:
            # Periodic health check
            is_valid, entries, msg = ledger.verify_chain()
            if not is_valid:
                log.critical(
                    "nova_syntheia.orchestrator.integrity_failure",
                    message=msg,
                    entries=entries,
                )
                # Trigger emergency
                emergency_manager.check_integrity_threat(
                    chain_valid=False, details=msg
                )

            log.debug(
                "nova_syntheia.orchestrator.heartbeat",
                ledger_entries=entries,
                chain_valid=is_valid,
            )

            await asyncio.sleep(60)  # Heartbeat every 60 seconds

    except KeyboardInterrupt:
        log.info("nova_syntheia.orchestrator.shutdown")
    except Exception as e:
        log.exception("nova_syntheia.orchestrator.fatal_error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
