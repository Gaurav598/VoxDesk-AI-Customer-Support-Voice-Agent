import re
from dataclasses import dataclass

from voice_agent.domain import KnowledgeHit


TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def normalize_token(token: str) -> str:
    lowered = token.lower()
    if len(lowered) > 3 and lowered.endswith("s"):
        return lowered[:-1]
    return lowered


def tokenize(text: str) -> set[str]:
    return {normalize_token(token) for token in TOKEN_RE.findall(text)}


@dataclass(frozen=True)
class KnowledgeDocument:
    id: str
    organization_id: str
    text: str


class InMemoryKnowledgeBase:
    def __init__(self) -> None:
        self._documents: list[KnowledgeDocument] = []

    def add_document(self, document: KnowledgeDocument) -> None:
        self._documents.append(document)

    def search(self, organization_id: str, query: str, limit: int = 3) -> list[KnowledgeHit]:
        query_tokens = tokenize(query)
        hits: list[KnowledgeHit] = []

        for document in self._documents:
            if document.organization_id != organization_id:
                continue
            doc_tokens = tokenize(document.text)
            if not query_tokens or not doc_tokens:
                continue
            overlap = query_tokens.intersection(doc_tokens)
            if not overlap:
                continue
            score = len(overlap) / len(query_tokens)
            hits.append(KnowledgeHit(document_id=document.id, text=document.text, score=score))

        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]
