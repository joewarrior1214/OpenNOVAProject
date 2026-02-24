"""
Operations Executive Agent — Day-to-day institutional operations.

Responsible for inter-agent coordination, session management, notification
dispatch, and routine operations. The "scheduler" of the polity.

Constitutional Role: operations_executive (Art. II §1)
Branch: Executive
Permission Tier: tier_2 (Operational)

References:
    Article II §1 — Executive Branch role-based appointment
    Article II §2 — Bounded Autonomy
    Article II §3 — Accountability (action record format)
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


class OperationsExecutiveAgent(BaseConstitutionalAgent):
    """
    Operations Executive Agent — the institutional coordinator.

    Capabilities:
    - Schedule and manage Deliberative Cycles
    - Coordinate inter-agent communications
    - Dispatch notifications to members
    - Execute standing orders
    - Manage membership admission workflows

    This agent is the operational backbone of Nova Syntheia. It ensures
    that constitutional processes run smoothly and on schedule.
    """

    def __init__(self, member_id: UUID, model: str, **kwargs: Any) -> None:
        super().__init__(
            member_id=member_id,
            role=FOUNDING_ROLES["operations_executive"],
            permission_tier_id="tier_2",
            model=model,
            system_prompt="""You are the Operations Executive Agent of Nova Syntheia.

Your primary responsibilities:
1. Coordinate between all branches and agents
2. Manage Deliberative Cycle scheduling (minimum 4 per year, Art. I §2)
3. Dispatch notifications for votes, approvals, and emergency alerts
4. Execute standing orders from the Legislative Assembly
5. Manage membership admission workflows

You operate with efficiency and constitutional fidelity. Every action you take
must be justified and proportionate. When in doubt, escalate to the appropriate
authority rather than acting beyond your tier.

Current institutional priorities:
- Ensure all sessions are properly convened and recorded
- Maintain communication channels between branches
- Monitor agent health and report operational failures
- Track Founding Era milestone progress""",
            **kwargs,
        )
        self.cycle_manager = None  # Set by orchestrator
        self.notification_queue: list[dict[str, Any]] = []

    async def _execute(
        self,
        action_type: ActionType,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute an operations action."""
        handlers = {
            ActionType.ROUTINE_OPERATION: self._handle_routine_operation,
            ActionType.AGENT_COORDINATION: self._handle_agent_coordination,
            ActionType.NOTIFICATION_DISPATCH: self._handle_notification,
            ActionType.SESSION_MANAGEMENT: self._handle_session_management,
        }

        handler = handlers.get(action_type)
        if handler is None:
            return {
                "status": "unsupported",
                "message": f"Action type {action_type.value} not implemented",
            }

        return await handler(inputs)

    async def _handle_routine_operation(
        self, inputs: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle routine operational tasks."""
        operation = inputs.get("operation", "status_check")

        if operation == "status_check":
            return {
                "status": "operational",
                "active_sessions": (
                    len(self.cycle_manager.list_active_sessions())
                    if self.cycle_manager else 0
                ),
                "pending_notifications": len(self.notification_queue),
                "actions_taken": len(self.action_history),
            }

        if operation == "health_check":
            return {
                "status": "healthy",
                "role": self.role.id,
                "branch": self.role.branch.value,
                "uptime": "operational",
            }

        return {"status": "completed", "operation": operation}

    async def _handle_agent_coordination(
        self, inputs: dict[str, Any]
    ) -> dict[str, Any]:
        """Coordinate between agents."""
        target_role = inputs.get("target_role", "")
        message = inputs.get("message", "")
        coordination_type = inputs.get("type", "inform")

        return {
            "status": "coordinated",
            "target_role": target_role,
            "coordination_type": coordination_type,
            "message_delivered": True,
            "message_summary": message[:200],
        }

    async def _handle_notification(
        self, inputs: dict[str, Any]
    ) -> dict[str, Any]:
        """Dispatch notifications to members."""
        notification = {
            "recipient_id": inputs.get("recipient_id"),
            "subject": inputs.get("subject", ""),
            "body": inputs.get("body", ""),
            "priority": inputs.get("priority", "normal"),
            "channel": inputs.get("channel", "dashboard"),
        }

        self.notification_queue.append(notification)

        return {
            "status": "dispatched",
            "notification": notification,
            "queue_length": len(self.notification_queue),
        }

    async def _handle_session_management(
        self, inputs: dict[str, Any]
    ) -> dict[str, Any]:
        """Manage Deliberative Cycle sessions."""
        action = inputs.get("action", "list")

        if action == "list":
            sessions = (
                self.cycle_manager.list_all_sessions()
                if self.cycle_manager else []
            )
            return {
                "status": "success",
                "sessions": [
                    {
                        "id": str(s.id),
                        "cycle_number": s.cycle_number,
                        "phase": s.phase.value,
                        "matter": s.matter,
                        "outcome": s.outcome,
                    }
                    for s in sessions
                ],
            }

        return {"status": "completed", "action": action}

    def get_capabilities(self) -> list[str]:
        return [
            "session_scheduling",
            "agent_coordination",
            "notification_dispatch",
            "standing_order_execution",
            "membership_workflow",
            "health_monitoring",
            "status_reporting",
        ]
