from dataclasses import dataclass


@dataclass(frozen=True)
class InboundCallEvent:
    provider: str
    call_id: str
    organization_phone: str
    caller_phone: str


class ExotelAdapter:
    def parse_inbound_call(self, payload: dict) -> InboundCallEvent:
        return InboundCallEvent(
            provider="exotel",
            call_id=str(payload.get("CallSid") or payload.get("call_sid") or payload["call_id"]),
            organization_phone=str(payload.get("To") or payload.get("to")),
            caller_phone=str(payload.get("From") or payload.get("from")),
        )
