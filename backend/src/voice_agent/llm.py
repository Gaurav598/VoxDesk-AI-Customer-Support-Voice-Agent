import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from voice_agent.domain import ActionType, AgentDecision, CallSession, KnowledgeHit


class LLMClient(Protocol):
    def decide(self, session: CallSession, user_text: str, knowledge: list[KnowledgeHit]) -> AgentDecision:
        ...


@dataclass(frozen=True)
class OllamaConfig:
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


class OllamaLLMClient:
    def __init__(self, config: OllamaConfig | None = None) -> None:
        self.config = config or OllamaConfig()

    def build_payload(self, session: CallSession, user_text: str, knowledge: list[KnowledgeHit]) -> dict:
        knowledge_text = "\n\n".join(hit.text for hit in knowledge) or "No matching company knowledge found."
        prompt = (
            "You are an AI phone support agent for an Indian organization.\n"
            "Sound like a calm human support agent, not a menu or form.\n"
            "Keep replies short enough for a live phone call: one or two sentences.\n"
            "You MUST reply in the Required reply language. "
            "If Required reply language is hi-IN, reply in Hindi/Hinglish. "
            "If Required reply language is te-IN, reply in Telugu or Telugu-English. "
            "If Required reply language is en-IN, reply in Indian English.\n"
            "Return only valid JSON with keys: reply, language, intent, status, actions, "
            "ticket_title, ticket_description, whatsapp_summary.\n"
            "Allowed actions: reply, create_ticket, send_whatsapp, schedule_callback, human_handoff.\n"
            "If the issue cannot be solved confidently, create a ticket and send WhatsApp.\n\n"
            f"Call mode: {session.mode.value}\n"
            f"Caller phone: {session.caller_phone}\n"
            f"Required reply language: {session.language}\n"
            f"Known transcript: {' | '.join(session.transcript)}\n"
            f"Company knowledge:\n{knowledge_text}\n\n"
            f"Customer said: {user_text}\n"
        )
        return {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

    def decide(self, session: CallSession, user_text: str, knowledge: list[KnowledgeHit]) -> AgentDecision:
        payload = self.build_payload(session, user_text, knowledge)
        request = urllib.request.Request(
            f"{self.config.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
        raw_decision = json.loads(body["response"])
        return sanitize_decision(user_text, decision_from_json(raw_decision), language_hint=session.language)


def decision_from_json(raw: dict) -> AgentDecision:
    actions = [ActionType(action) for action in raw.get("actions", ["reply"])]
    return AgentDecision(
        reply=str(raw["reply"]),
        language=str(raw.get("language", "unknown")),
        intent=str(raw.get("intent", "support_issue")),
        status=str(raw.get("status", "clarifying")),
        actions=actions,
        ticket_title=raw.get("ticket_title"),
        ticket_description=raw.get("ticket_description"),
        whatsapp_summary=raw.get("whatsapp_summary"),
    )


def sanitize_decision(
    user_text: str,
    decision: AgentDecision,
    language_hint: str = "unknown",
) -> AgentDecision:
    cleaned = _clean(user_text)
    language = _preferred_language(language_hint, user_text)
    intent = decision.intent
    status = decision.status
    actions = list(decision.actions)
    ticket_title = decision.ticket_title
    ticket_description = decision.ticket_description
    whatsapp_summary = decision.whatsapp_summary

    if _is_identity_question(cleaned):
        intent = "identity_question"
        status = "explaining_agent"
        actions = [ActionType.REPLY]
        ticket_title = None
        ticket_description = None
        whatsapp_summary = None
    elif _is_greeting(cleaned):
        intent = "greeting"
        status = "discovering_issue"
        actions = [ActionType.REPLY]
        ticket_title = None
        ticket_description = None
        whatsapp_summary = None
    elif not _mentions_payment_or_order(cleaned) and ActionType.CREATE_TICKET in actions:
        actions = [action for action in actions if action != ActionType.CREATE_TICKET]
        ticket_title = None
        ticket_description = None

    if ActionType.REPLY not in actions:
        actions.insert(0, ActionType.REPLY)

    return AgentDecision(
        reply=decision.reply,
        language=language if language != "en" or decision.language in {"unknown", "en"} else decision.language,
        intent=intent,
        status=status,
        actions=actions,
        ticket_title=ticket_title,
        ticket_description=ticket_description,
        whatsapp_summary=whatsapp_summary,
    )


def _clean(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _detect_language(text: str) -> str:
    if any("\u0c00" <= char <= "\u0c7f" for char in text):
        return "te"
    if any("\u0900" <= char <= "\u097f" for char in text):
        return "hi"
    lowered = text.lower()
    hindi_words = ("namaste", "mera", "meri", "mujhe", "paise", "bhai", "order nahi")
    telugu_words = ("namaskaram", "naaku", "naku", "naa", "ledu", "order kanipinchadam")
    if any(word in lowered for word in telugu_words):
        return "te"
    if any(word in lowered for word in hindi_words):
        return "hi"
    return "en"


def _preferred_language(language_hint: str, text: str) -> str:
    if language_hint and language_hint != "unknown":
        return language_hint
    return _detect_language(text)


def _is_greeting(cleaned: str) -> bool:
    return cleaned in {"hi", "hello", "hey", "hello there", "hi there", "good morning", "good afternoon", "good evening"}


def _is_identity_question(cleaned: str) -> bool:
    identity_phrases = (
        "who are you",
        "what are you",
        "are you a bot",
        "are you ai",
        "is this ai",
        "who is speaking",
    )
    return any(phrase in cleaned for phrase in identity_phrases)


def _mentions_payment_or_order(cleaned: str) -> bool:
    payment_terms = ("payment", "deduct", "failed", "refund", "upi", "paid", "paise")
    order_terms = ("order", "delivery", "missing", "not showing", "not visible")
    return any(term in cleaned for term in payment_terms) or any(term in cleaned for term in order_terms)


class RuleBasedFallbackLLM:
    def decide(self, session: CallSession, user_text: str, knowledge: list[KnowledgeHit]) -> AgentDecision:
        cleaned = _clean(user_text)
        language = _preferred_language(session.language, user_text)
        if _is_greeting(cleaned):
            return AgentDecision(
                reply=(
                    "Hi, I am your AI support assistant. "
                    "Tell me what happened, and I will help resolve it or create a ticket for you."
                ),
                language=language,
                intent="greeting",
                status="discovering_issue",
                actions=[ActionType.REPLY],
            )
        if _is_identity_question(cleaned):
            return AgentDecision(
                reply=(
                    "I am the AI support agent for this demo organization. "
                    "I can understand your issue, ask the right follow-up questions, and create a support ticket when needed."
                ),
                language=language,
                intent="identity_question",
                status="explaining_agent",
                actions=[ActionType.REPLY],
            )
        if _mentions_payment_or_order(cleaned):
            return AgentDecision(
                reply=(
                    "Got it. It sounds like a payment or order issue. "
                    "I am creating a support ticket now. If you have the order ID or payment reference, please share it."
                ),
                language=language,
                intent="support_issue",
                status="create_ticket",
                actions=[ActionType.REPLY, ActionType.CREATE_TICKET, ActionType.SEND_WHATSAPP],
                ticket_title="Payment deducted but order not visible",
                ticket_description=user_text,
                whatsapp_summary="We created a ticket for your payment/order visibility issue.",
            )
        return AgentDecision(
            reply=(
                "I am listening. Tell me the issue in one sentence, like payment failed, order missing, "
                "delivery delayed, login problem, or refund needed."
            ),
            language=language,
            intent="support_issue",
            status="clarifying",
            actions=[ActionType.REPLY],
        )


def create_llm_client(runtime: str | None = None) -> LLMClient:
    selected_runtime = (runtime or os.getenv("VOICE_AGENT_LLM", "fallback")).lower()
    if selected_runtime == "ollama":
        return OllamaLLMClient()
    if selected_runtime == "fallback":
        return RuleBasedFallbackLLM()
    raise ValueError(f"Unsupported LLM runtime: {selected_runtime}")
