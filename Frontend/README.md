# DrugGPT Frontend

A Vercel-ready Next.js UI for the DrugGPT medical/drug education assistant.
This is the **only UI** for the project — the old Streamlit app under `../src/ui`
has been removed.

## Features

- **Role gate** on entry: *Normal user (Patient)* or *Drug Professional (Doctor / Paramedic)*.
  Roles are a local toggle (no login) and can be switched from the header at any time.
- **Patient mode** — normal chatbot: conversation sidebar, new chats, streaming answers,
  markdown, expandable source citations, and dedicated states for emergency guidance,
  clarification, out-of-scope notices, and clinician-review pending.
- **Professional mode** — two tabs:
  - **Pro Chat** — the same chat UX framed for drug/pharmacology questions.
  - **Requests** — queue of user requests with status filters and search, full context,
    internal draft, approve/reject with guidance and note, full conversation transcript,
    free-text clinician reply, and a "New request" form.
- Light/dark theme, responsive layout, keyboard-accessible controls.
- **Mock-first API layer**: the UI runs standalone with seeded demo data, so it can be
  deployed to Vercel without a backend.

## Run locally

```bash
npm install
npm run dev
```

Open <http://localhost:3000>. With no environment variable set, the app uses seeded
mock data (a badge in the disclaimer confirms this).

Typecheck / production build:

```bash
npm run typecheck
npm run build
```

## Connect the real backend

Copy `.env.example` to `.env.local` and set the FastAPI URL:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Then start the backend from the repo root:

```bash
uvicorn src.main:app --reload
```

All backend calls go through `src/lib/api/`:

| File | Purpose |
|------|---------|
| `types.ts` | TypeScript mirror of the Pydantic models (`ChatResponse`, `MedicationReview`, …) |
| `client.ts` | `HttpApiClient` — the only code that knows backend URL shapes, including SSE streaming |
| `mock.ts` | `MockApiClient` — seeded in-memory demo data |
| `index.ts` | Picks the implementation from `NEXT_PUBLIC_API_BASE_URL` |

To change the backend later, edit only these files. No component imports a URL directly.

### Endpoints used

- `GET/POST /patients`, `GET/POST /patients/{id}/conversations`
- `GET /conversations/{id}/messages`, `POST /conversations/{id}/messages`
- `POST /conversations/{id}/messages/stream` (SSE: `token`, `response`, `error`)
- `GET /reviews?status=…`, `GET /reviews/{id}`, `POST /reviews/{id}/decision`
- `GET /conversations/{id}/transcript`, `POST /conversations/{id}/clinician-reply`

> Note: new professional requests are raised by posting a structured question through chat,
> because the backend creates medication reviews with a LangGraph interrupt. If the question
> isn't a personal medication decision, the backend answers normally and no review is queued.

## Deploy to Vercel

Import this repository in Vercel and set the **Root Directory** to `DrugGPT/Frontend`.
Framework preset: Next.js; build command `npm run build`; output `.next`.

Deploy with no `NEXT_PUBLIC_API_BASE_URL` for a standalone demo, or set it to your
publicly reachable FastAPI URL to use the real backend.

## Safety

Educational use only. Not medical advice. Do not enter real patient data.
