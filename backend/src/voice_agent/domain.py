from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CallMode(str, Enum):
    SUPPORT = "support"
    SALES = "sales"


class ActionType(str, Enum):
    REPLY = "reply"
    CREATE_TICKET = "create_ticket"
    SEND_WHATSAPP = "send_whatsapp"
    SCHEDULE_CALLBACK = "schedule_callback"
    HUMAN_HANDOFF = "human_handoff"


@dataclass(frozen=True)
class Organization:
    id: str
    name: str
    support_phone: str | None = None
    escalation_phone: str | None = None


@dataclass
class CallSession:
    id: str
    organization_id: str
    caller_phone: str
    mode: CallMode
    language: str = "unknown"
    transcript: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeHit:
    document_id: str
    text: str
    score: float


@dataclass(frozen=True)
class AgentDecision:
    reply: str
    language: str
    intent: str
    status: str
    actions: list[ActionType]
    ticket_title: str | None = None
    ticket_description: str | None = None
    whatsapp_summary: str | None = None


@dataclass(frozen=True)
class Ticket:
    id: str
    organization_id: str
    caller_phone: str
    title: str
    description: str
    call_id: str
