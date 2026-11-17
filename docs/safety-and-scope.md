# Safety and scope

DrugGPT is a **medical education assistant** for students and the general public. It explains health topics in plain language, but it is not a clinician and must not be used for real clinical decisions.

## What DrugGPT does

- Holds a conversation: when a message is too vague, it returns one fixed, reviewed clarifying question instead of guessing (no LLM call by default).
- Searches local, licensed medical PDFs and prefers source-grounded answers with page citations.
- Falls back to clearly labeled general educational information when no source is relevant enough.
- Declines unrelated questions and applies deterministic guardrails (`triage_query`) to every message.
- Pauses personal clinical decisions for a human clinician (see below).

## What DrugGPT does NOT do

- It is **not** a diagnostic, prescribing, testing, or emergency-care service.
- It does not give individual doses or personal medical advice.
- It does not replace qualified healthcare professionals.
- It does not interpret a personal test report or decide what test or treatment someone should get.

## Human-in-the-loop triggers

A request is held for clinician review when it asks for a **personal clinical decision**, including:

- **Medicine** — which drug or dose a person should take, or whether to start/stop/change one.
- **Testing** — which test or scan a person should get.
- **Treatment** — which treatment or therapy a person should start.
- **Test report** — what a personal lab result, scan, or report means.

The assistant drafts internal guidance, saves it as a review, and pauses with a LangGraph `interrupt`. Nothing is shown to the user until a clinician approves it via `POST /reviews/{review_id}/decision` or writes a free-text reply via `POST /conversations/{id}/clinician-reply`. Rejected reviews become a safety refusal. A conversation can also be switched to human mode so all further messages wait for the clinician directly.

## Emergency handling

Emergency signals (for example chest pain, difficulty breathing, overdose, or self-harm) are classified first and always win over other rules. DrugGPT returns immediate emergency guidance and directs the user to contact local emergency services or the nearest emergency department. Emergency messages are **never** placed in a review queue.

## Local-only guarantee

`LocalStore` has **no authentication** and is for local demos only. `Settings.validate()` refuses to bind the API to a non-loopback host unless `DRUGGPT_ALLOW_REMOTE=1`, which is itself only for trusted local-network demos. Never enter real patient data, and never expose this service to the public internet.

## Verification

Verify research conclusions against the original PDFs and qualified professionals. If no indexed source sufficiently supports a question, DrugGPT provides general educational information rather than inventing an answer. Citations use repo-relative paths and one-based page numbers; confirm them against the original PDF.
