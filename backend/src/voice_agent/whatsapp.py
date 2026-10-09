from dataclasses import dataclass


@dataclass(frozen=True)
class WhatsAppMessage:
    to_phone: str
    body: str
    dry_run: bool


class DryRunWhatsAppClient:
    def __init__(self) -> None:
        self.sent: list[WhatsAppMessage] = []

    def send(self, to_phone: str, body: str) -> WhatsAppMessage:
        message = WhatsAppMessage(to_phone=to_phone, body=body, dry_run=True)
        self.sent.append(message)
        return message
