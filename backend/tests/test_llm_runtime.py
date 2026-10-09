import unittest

from voice_agent.domain import ActionType, AgentDecision, CallMode, CallSession
from voice_agent.llm import OllamaLLMClient, RuleBasedFallbackLLM, create_llm_client, sanitize_decision


class LLMRuntimeTests(unittest.TestCase):
    def test_create_llm_client_uses_fallback_by_default(self):
        client = create_llm_client("fallback")

        self.assertIsInstance(client, RuleBasedFallbackLLM)

    def test_create_llm_client_can_select_ollama(self):
        client = create_llm_client("ollama")

        self.assertIsInstance(client, OllamaLLMClient)

    def test_fallback_handles_greeting_like_a_support_agent(self):
        client = RuleBasedFallbackLLM()
        session = CallSession(
            id="call-1",
            organization_id="demo-org",
            caller_phone="browser-user",
            mode=CallMode.SUPPORT,
        )

        decision = client.decide(session, "hello", [])

        self.assertEqual(decision.intent, "greeting")
        self.assertEqual(decision.status, "discovering_issue")
        self.assertIn("help", decision.reply.lower())
        self.assertNotIn("one more detail", decision.reply.lower())

    def test_fallback_answers_identity_question_naturally(self):
        client = RuleBasedFallbackLLM()
        session = CallSession(
            id="call-1",
            organization_id="demo-org",
            caller_phone="browser-user",
            mode=CallMode.SUPPORT,
        )

        decision = client.decide(session, "who are you", [])

        self.assertEqual(decision.intent, "identity_question")
        self.assertIn("ai", decision.reply.lower())
        self.assertIn("support", decision.reply.lower())

    def test_fallback_identifies_hindi_script(self):
        client = RuleBasedFallbackLLM()
        session = CallSession(
            id="call-1",
            organization_id="demo-org",
            caller_phone="browser-user",
            mode=CallMode.SUPPORT,
        )

        decision = client.decide(session, "मेरा payment fail हो गया", [])

        self.assertEqual(decision.language, "hi")
        self.assertEqual(decision.intent, "support_issue")

    def test_fallback_identifies_telugu_script(self):
        client = RuleBasedFallbackLLM()
        session = CallSession(
            id="call-1",
            organization_id="demo-org",
            caller_phone="browser-user",
            mode=CallMode.SUPPORT,
        )

        decision = client.decide(session, "నా order కనిపించడం లేదు", [])

        self.assertEqual(decision.language, "te")
        self.assertEqual(decision.intent, "support_issue")

    def test_sanitize_decision_removes_ticket_for_greeting(self):
        decision = AgentDecision(
            reply="Hello, I am support.",
            language="en",
            intent="greeting",
            status="initial_greeting",
            actions=[ActionType.REPLY, ActionType.CREATE_TICKET],
            ticket_title="Greeting",
            ticket_description="hello",
        )

        sanitized = sanitize_decision("hello who are you", decision)

        self.assertEqual(sanitized.intent, "identity_question")
        self.assertEqual(sanitized.actions, [ActionType.REPLY])
        self.assertIsNone(sanitized.ticket_title)
        self.assertIsNone(sanitized.ticket_description)


if __name__ == "__main__":
    unittest.main()
