import unittest

from voice_agent.knowledge import InMemoryKnowledgeBase, KnowledgeDocument


class KnowledgeTests(unittest.TestCase):
    def test_search_returns_matching_organization_documents_only(self):
        knowledge = InMemoryKnowledgeBase()
        knowledge.add_document(
            KnowledgeDocument(
                id="doc-1",
                organization_id="org-1",
                text="If payment is deducted and order is missing, create a ticket.",
            )
        )
        knowledge.add_document(
            KnowledgeDocument(
                id="doc-2",
                organization_id="org-2",
                text="Refund policy for another organization.",
            )
        )

        hits = knowledge.search("org-1", "payment deducted order missing")

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].document_id, "doc-1")


if __name__ == "__main__":
    unittest.main()
