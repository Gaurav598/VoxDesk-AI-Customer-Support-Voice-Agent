import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from voice_agent.domain import CallSession, KnowledgeHit, Ticket
from voice_agent.knowledge import tokenize


class SQLiteStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def migrate(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS knowledge_documents (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    text TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS calls (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    caller_phone TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    language TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS call_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    call_id TEXT NOT NULL,
                    speaker TEXT NOT NULL,
                    text TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    caller_phone TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    call_id TEXT NOT NULL
                );
                """
            )

    def add_knowledge(self, organization_id: str, text: str) -> str:
        document_id = f"DOC-{uuid4().hex[:8].upper()}"
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO knowledge_documents (id, organization_id, text) VALUES (?, ?, ?)",
                (document_id, organization_id, text),
            )
        return document_id

    def list_knowledge(self, organization_id: str | None = None) -> list[dict]:
        with self._connect() as connection:
            if organization_id:
                rows = connection.execute(
                    "SELECT id, organization_id, text FROM knowledge_documents WHERE organization_id = ? ORDER BY rowid DESC",
                    (organization_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT id, organization_id, text FROM knowledge_documents ORDER BY rowid DESC"
                ).fetchall()
        return [{"id": row["id"], "organization_id": row["organization_id"], "text": row["text"]} for row in rows]


    def search_knowledge(self, organization_id: str, query: str, limit: int = 3) -> list[KnowledgeHit]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, text FROM knowledge_documents WHERE organization_id = ?",
                (organization_id,),
            ).fetchall()

        hits: list[KnowledgeHit] = []
        for row in rows:
            doc_tokens = tokenize(row["text"])
            overlap = query_tokens.intersection(doc_tokens)
            if overlap:
                hits.append(
                    KnowledgeHit(
                        document_id=row["id"],
                        text=row["text"],
                        score=len(overlap) / len(query_tokens),
                    )
                )
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]

    def save_call_session(self, session: CallSession) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO calls (id, organization_id, caller_phone, mode, language)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.organization_id,
                    session.caller_phone,
                    session.mode.value,
                    session.language,
                ),
            )

    def append_call_turn(self, call_id: str, speaker: str, text: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO call_turns (call_id, speaker, text) VALUES (?, ?, ?)",
                (call_id, speaker, text),
            )

    def get_call_transcript(self, call_id: str) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT speaker, text FROM call_turns WHERE call_id = ? ORDER BY id",
                (call_id,),
            ).fetchall()
        return [f"{row['speaker']}: {row['text']}" for row in rows]

    def list_calls(self, organization_id: str | None = None) -> list[dict]:
        with self._connect() as connection:
            if organization_id:
                rows = connection.execute(
                    "SELECT id, organization_id, caller_phone, mode, language FROM calls WHERE organization_id = ? ORDER BY rowid DESC",
                    (organization_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT id, organization_id, caller_phone, mode, language FROM calls ORDER BY rowid DESC"
                ).fetchall()
        return [
            {
                "id": row["id"],
                "organization_id": row["organization_id"],
                "caller_phone": row["caller_phone"],
                "mode": row["mode"],
                "language": row["language"],
                "turns": self.get_call_transcript(row["id"]),
            }
            for row in rows
        ]


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
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tickets (id, organization_id, caller_phone, title, description, call_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket.id,
                    ticket.organization_id,
                    ticket.caller_phone,
                    ticket.title,
                    ticket.description,
                    ticket.call_id,
                ),
            )
        return ticket

    def list_tickets(self) -> list[Ticket]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, organization_id, caller_phone, title, description, call_id FROM tickets ORDER BY rowid"
            ).fetchall()
        return [
            Ticket(
                id=row["id"],
                organization_id=row["organization_id"],
                caller_phone=row["caller_phone"],
                title=row["title"],
                description=row["description"],
                call_id=row["call_id"],
            )
            for row in rows
        ]
