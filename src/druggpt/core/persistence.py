"""Local SQLite persistence for development-only patient and chat workflows."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from druggpt.core.models import (
    Conversation,
    ConversationMessage,
    MedicationReview,
    Patient,
    PatientFact,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class LocalStore:
    """A small repository; do not use this unauthenticated store for real patient data."""

    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.database_path = database_path
        self._setup()

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _setup(self) -> None:
        with self._connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS patients (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, date_of_birth TEXT, sex TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS patient_facts (
                    id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, category TEXT NOT NULL,
                    value TEXT NOT NULL, approved INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS clinical_summaries (
                    id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, summary TEXT NOT NULL,
                    approved INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, title TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, role TEXT NOT NULL,
                    content TEXT NOT NULL, status TEXT, metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS medication_reviews (
                    id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, conversation_id TEXT NOT NULL,
                    message_id TEXT NOT NULL, graph_thread_id TEXT NOT NULL, status TEXT NOT NULL,
                    draft_guidance TEXT NOT NULL, context_json TEXT NOT NULL, reviewer_name TEXT,
                    reviewer_note TEXT, approved_guidance TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_conversation_patient ON conversations(patient_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_message_conversation ON messages(conversation_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_review_status ON medication_reviews(status, updated_at DESC);
                """
            )

    @staticmethod
    def _patient(row: sqlite3.Row) -> Patient:
        return Patient(**dict(row))

    @staticmethod
    def _conversation(row: sqlite3.Row) -> Conversation:
        return Conversation(**dict(row))

    @staticmethod
    def _fact(row: sqlite3.Row) -> PatientFact:
        values = dict(row)
        values["approved"] = bool(values["approved"])
        return PatientFact(**values)

    @staticmethod
    def _message(row: sqlite3.Row) -> ConversationMessage:
        values = dict(row)
        values["metadata"] = json.loads(values.pop("metadata_json"))
        return ConversationMessage(**values)

    @staticmethod
    def _review(row: sqlite3.Row) -> MedicationReview:
        values = dict(row)
        values.pop("graph_thread_id", None)
        values.pop("context_json", None)
        return MedicationReview(**values)

    def create_patient(self, name: str, date_of_birth: str | None, sex: str | None) -> Patient:
        patient_id, now = str(uuid4()), _now()
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO patients VALUES (?, ?, ?, ?, ?, ?)",
                (patient_id, name, date_of_birth, sex, now, now),
            )
        return self.get_patient(patient_id)

    def ensure_demo_patient(self) -> Patient:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM patients ORDER BY created_at LIMIT 1").fetchone()
        return self._patient(row) if row else self.create_patient("Guest patient", None, None)

    def list_patients(self) -> list[Patient]:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM patients ORDER BY updated_at DESC").fetchall()
        return [self._patient(row) for row in rows]

    def get_patient(self, patient_id: str) -> Patient:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
        if not row:
            raise KeyError("Patient not found")
        return self._patient(row)

    def update_patient(self, patient_id: str, **changes: str | None) -> Patient:
        patient = self.get_patient(patient_id)
        name = changes.get("name") or patient.name
        dob = changes["date_of_birth"] if "date_of_birth" in changes else patient.date_of_birth
        sex = changes["sex"] if "sex" in changes else patient.sex
        with self._connection() as conn:
            conn.execute(
                "UPDATE patients SET name=?, date_of_birth=?, sex=?, updated_at=? WHERE id=?",
                (name, dob, sex, _now(), patient_id),
            )
        return self.get_patient(patient_id)

    def add_fact(self, patient_id: str, category: str, value: str, approved: bool) -> PatientFact:
        self.get_patient(patient_id)
        fact_id, now = str(uuid4()), _now()
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO patient_facts VALUES (?, ?, ?, ?, ?, ?)",
                (fact_id, patient_id, category, value, int(approved), now),
            )
        return PatientFact(id=fact_id, category=category, value=value, approved=approved, created_at=now)

    def list_facts(self, patient_id: str, approved_only: bool = False) -> list[PatientFact]:
        query = "SELECT id, category, value, approved, created_at FROM patient_facts WHERE patient_id = ?"
        if approved_only:
            query += " AND approved = 1"
        with self._connection() as conn:
            rows = conn.execute(query + " ORDER BY created_at", (patient_id,)).fetchall()
        return [self._fact(row) for row in rows]

    def latest_summary(self, patient_id: str) -> str | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT summary FROM clinical_summaries WHERE patient_id=? AND approved=1 ORDER BY created_at DESC LIMIT 1",
                (patient_id,),
            ).fetchone()
        return row["summary"] if row else None

    def save_summary(self, patient_id: str, summary: str, approved: bool = True) -> None:
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO clinical_summaries VALUES (?, ?, ?, ?, ?)",
                (str(uuid4()), patient_id, summary, int(approved), _now()),
            )

    def create_conversation(self, patient_id: str, title: str) -> Conversation:
        self.get_patient(patient_id)
        conversation_id, now = str(uuid4()), _now()
        with self._connection() as conn:
            conn.execute("INSERT INTO conversations VALUES (?, ?, ?, ?, ?)", (conversation_id, patient_id, title, now, now))
        return self.get_conversation(conversation_id)

    def get_conversation(self, conversation_id: str) -> Conversation:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone()
        if not row:
            raise KeyError("Conversation not found")
        return self._conversation(row)

    def list_conversations(self, patient_id: str) -> list[Conversation]:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM conversations WHERE patient_id=? ORDER BY updated_at DESC", (patient_id,)).fetchall()
        return [self._conversation(row) for row in rows]

    def ensure_demo_conversation(self, patient_id: str) -> Conversation:
        conversations = self.list_conversations(patient_id)
        return conversations[0] if conversations else self.create_conversation(patient_id, "General medical chat")

    def add_message(self, conversation_id: str, role: str, content: str, status: str | None = None, metadata: dict | None = None) -> ConversationMessage:
        self.get_conversation(conversation_id)
        message_id, now = str(uuid4()), _now()
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?)",
                (message_id, conversation_id, role, content, status, json.dumps(metadata or {}), now),
            )
            conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conversation_id))
        return ConversationMessage(id=message_id, conversation_id=conversation_id, role=role, content=content, status=status, created_at=now, metadata=metadata or {})

    def list_messages(self, conversation_id: str, limit: int | None = None) -> list[ConversationMessage]:
        query = "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at"
        params: list[object] = [conversation_id]
        if limit:
            query = "SELECT * FROM (" + query + " DESC LIMIT ?) ORDER BY created_at"
            params.append(limit)
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._message(row) for row in rows]

    def create_or_get_review(self, patient_id: str, conversation_id: str, message_id: str, graph_thread_id: str, draft: str, context: dict) -> MedicationReview:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM medication_reviews WHERE graph_thread_id=? ORDER BY created_at DESC LIMIT 1",
                (graph_thread_id,),
            ).fetchone()
            if row:
                return self._review(row)
            review_id, now = str(uuid4()), _now()
            conn.execute(
                "INSERT INTO medication_reviews VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?)",
                (review_id, patient_id, conversation_id, message_id, graph_thread_id, "pending", draft, json.dumps(context), now, now),
            )
        return self.get_review(review_id)

    def get_review(self, review_id: str) -> MedicationReview:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM medication_reviews WHERE id=?", (review_id,)).fetchone()
        if not row:
            raise KeyError("Review not found")
        return self._review(row)

    def get_review_internal(self, review_id: str) -> sqlite3.Row:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM medication_reviews WHERE id=?", (review_id,)).fetchone()
        if not row:
            raise KeyError("Review not found")
        return row

    def list_reviews(self, status: str = "pending") -> list[MedicationReview]:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM medication_reviews WHERE status=? ORDER BY updated_at DESC", (status,)).fetchall()
        return [self._review(row) for row in rows]

    def find_pending_review(self, graph_thread_id: str) -> MedicationReview | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM medication_reviews WHERE graph_thread_id=? AND status='pending' ORDER BY created_at DESC LIMIT 1",
                (graph_thread_id,),
            ).fetchone()
        return self._review(row) if row else None

    def review_context(self, review_id: str) -> dict:
        row = self.get_review_internal(review_id)
        return json.loads(row["context_json"])

    def review_graph_thread_id(self, review_id: str) -> str:
        return str(self.get_review_internal(review_id)["graph_thread_id"])

    def decide_review(self, review_id: str, decision: str, reviewer_name: str, note: str | None, guidance: str | None) -> MedicationReview:
        review = self.get_review(review_id)
        if review.status != "pending":
            raise ValueError("This review has already been decided.")
        if decision == "approved" and not guidance:
            guidance = review.draft_guidance
        with self._connection() as conn:
            conn.execute(
                "UPDATE medication_reviews SET status=?, reviewer_name=?, reviewer_note=?, approved_guidance=?, updated_at=? WHERE id=?",
                (decision, reviewer_name, note, guidance, _now(), review_id),
            )
        return self.get_review(review_id)
