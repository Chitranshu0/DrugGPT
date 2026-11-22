"""OpenAPI metadata for the DrugGPT API."""

API_VERSION = "3.0.0"

TAGS_METADATA = [
    {
        "name": "Meta",
        "description": "Liveness and discovery endpoints. Start here when wiring up a client.",
    },
    {
        "name": "Index",
        "description": "Inspect or rebuild the local vector index built from PDFs in `data/raw`.",
    },
    {
        "name": "Patients",
        "description": "Create and manage the local patient records that conversations attach to.",
    },
    {
        "name": "Chat",
        "description": (
            "Send messages and read conversation history. LangGraph routes each message to an "
            "educational answer, a clarification question, emergency/scope guidance, or a "
            "`review_pending` status when a clinician must review a personal health decision."
        ),
    },
    {
        "name": "Reviews",
        "description": (
            "List pending clinician reviews (medicines, tests, treatments, report interpretation) "
            "and record a decision to resume a chat."
        ),
    },
    {
        "name": "Clinician",
        "description": "Read a full conversation transcript and record a clinician's free-text reply.",
    },
]

DESCRIPTION = (
    "Local, development-only medical education and clinician-review API.\n\n"
    "**Typical flow**\n"
    "1. `POST /patients` to create a patient.\n"
    "2. `POST /conversations` with that patient id.\n"
    "3. `POST /conversations/{conversation_id}/messages` to chat. LangGraph routes the message "
    "to RAG-backed education, a clarification question, emergency/scope guidance, or clinician review.\n"
    "4. If the response status is `review_pending`, decide it with "
    "`POST /reviews/{review_id}/decision` or reply with "
    "`POST /conversations/{conversation_id}/clinician-reply`.\n\n"
    "This service is **not** a medical device and must not be used for real clinical decisions."
)
