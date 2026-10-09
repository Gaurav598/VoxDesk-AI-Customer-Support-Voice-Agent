from uuid import uuid4

from voice_agent.domain import Ticket


class InMemoryTicketStore:
    def __init__(self) -> None:
        self._tickets: list[Ticket] = []

    def create_ticket(
        self,
        organization_id: str,
        caller_phone: str,
        call_id: str,
        title: str,
        description: str,
    ) -> Ticket:
        ticket = Ticket(
            id=f"TCK-{uuid4().hex[:8].upper()}",
            organization_id=organization_id,
            caller_phone=caller_phone,
            call_id=call_id,
            title=title,
            description=description,
        )
        self._tickets.append(ticket)
        return ticket

    def list_tickets(self) -> list[Ticket]:
        return list(self._tickets)
