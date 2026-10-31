"""Streamlit chat UI for DrugGPT.

Run from the project root:

    streamlit run frontend/streamlit_app.py

The backend owns conversation history in SQLite. This UI only keeps the
active thread id and the messages currently on screen.

The chat response is a stream of NDJSON events, which lets this UI show
Claude-style tool cards (tool name, input, result) while the answer is
being generated.
"""

import html
import json
import os

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
REQUEST_TIMEOUT = 120

st.set_page_config(page_title="DrugGPT", page_icon="💊", layout="wide")

st.markdown(
    """
    <style>
    .dg-tool-card {
        border: 1px solid rgba(99, 102, 241, 0.28);
        border-left: 3px solid #6366f1;
        background: rgba(99, 102, 241, 0.06);
        border-radius: 8px;
        padding: 0.6rem 0.8rem;
        margin: 0.3rem 0 0.65rem 0;
        font-size: 0.88rem;
        line-height: 1.45;
    }
    .dg-tool-head {
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 0.35rem;
    }
    .dg-tool-input {
        margin-top: 0.3rem;
        color: rgba(120, 120, 120, 0.95);
    }
    .dg-tool-input code {
        background: rgba(120, 120, 120, 0.14);
        padding: 1px 5px;
        border-radius: 4px;
        font-size: 0.82rem;
    }
    .dg-tool-status {
        margin-top: 0.35rem;
        font-weight: 500;
        color: #16a34a;
    }
    .dg-tool-status.running {
        color: #d97706;
    }
    .dg-thinking {
        color: rgba(120, 120, 120, 0.95);
        font-style: italic;
        padding: 0.35rem 0 0.1rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("💊 DrugGPT")


def _request(method: str, path: str, **kwargs) -> requests.Response:
    """Send a request to the backend and raise on HTTP errors."""
    response = requests.request(
        method,
        f"{API_BASE_URL}{path}",
        timeout=REQUEST_TIMEOUT,
        **kwargs,
    )
    response.raise_for_status()
    return response


def fetch_threads() -> list[dict]:
    """Load the conversation list."""
    return _request("GET", "/threads").json()


def create_thread() -> dict:
    """Create a new empty conversation."""
    return _request("POST", "/threads").json()


def fetch_thread(thread_id: str) -> dict:
    """Load one conversation with its persisted messages."""
    return _request("GET", f"/threads/{thread_id}").json()


def rename_thread(thread_id: str, title: str) -> None:
    """Rename a conversation."""
    _request("PATCH", f"/threads/{thread_id}", json={"title": title})


def delete_thread(thread_id: str) -> None:
    """Delete a conversation and its graph state."""
    _request("DELETE", f"/threads/{thread_id}")


def stream_chat(
    question: str,
    thread_id: str,
    on_event,
) -> dict:
    """Stream the assistant response and collect the final message.

    ``on_event`` is called for every NDJSON event so the UI can update as
    thinking, tool, source, and answer events arrive.
    """
    answer = ""
    sources: list[dict] = []
    tools: dict[str, dict] = {}

    with requests.post(
        f"{API_BASE_URL}/chat",
        json={"message": question, "thread_id": thread_id},
        stream=True,
        timeout=(10, REQUEST_TIMEOUT),
    ) as response:
        response.raise_for_status()

        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line:
                continue

            line = raw_line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                # Backwards compatibility: the backend sent plain text.
                answer += line
                on_event({"type": "answer", "content": answer})
                continue

            event_type = event.get("type")

            if event_type == "tool_call":
                tool = event.get("tool", {})
                tools[tool.get("name", "tool")] = tool
            elif event_type == "tool_result":
                tool = event.get("tool", {})
                name = tool.get("name", "tool")
                tools[name] = {**tools.get(name, {}), **tool}
                sources = event.get("sources", []) or []
            elif event_type == "answer":
                answer = event.get("content", "")
            elif event_type == "error":
                answer = event.get("message", "")

            on_event(event)

    # A stream that ended before tool_result (or an older backend) should not
    # leave a tool card stuck on "running".
    final_tools: list[dict] = []
    for tool in tools.values():
        if tool.get("status") == "running":
            tool = {
                **tool,
                "status": "completed",
                "summary": tool.get("summary") or "Done",
            }
        final_tools.append(tool)

    return {
        "answer": answer,
        "sources": sources,
        "tool_calls": final_tools,
    }


def _tool_icon(name: str) -> str:
    """Pick an icon for a tool card."""
    lowered = (name or "").lower()
    if any(word in lowered for word in ("rag", "retriev", "search")):
        return "📚"
    return "🔧"


def tool_card_html(tool: dict) -> str:
    """Render a Claude-style tool call card as HTML."""
    name = str(tool.get("name") or "tool")
    title = html.escape(str(tool.get("title") or name))
    question = str((tool.get("input") or {}).get("question", "")).strip()
    status = tool.get("status", "completed")

    if status == "running":
        status_html = '<div class="dg-tool-status running">⏳ Running…</div>'
    else:
        summary = html.escape(str(tool.get("summary") or "Done"))
        status_html = f'<div class="dg-tool-status">✅ {summary}</div>'

    parts = [
        '<div class="dg-tool-card">',
        f'<div class="dg-tool-head">{_tool_icon(name)} {title}</div>',
    ]
    if question:
        parts.append(
            '<div class="dg-tool-input">Input: '
            f"<code>{html.escape(question)}</code></div>"
        )
    parts.append(status_html)
    parts.append("</div>")
    return "".join(parts)


def render_sources(sources: list[dict]) -> None:
    """Render retrieved references under an answer."""
    if not sources:
        return

    with st.expander(f"📖 Sources ({len(sources)})", expanded=False):
        for source in sources:
            title = source.get("title") or source.get("source") or "Medical reference"
            page = source.get("page")
            suffix = f" — page {page}" if page else ""
            st.markdown(f"- **{title}**{suffix}")


def init_session() -> None:
    """Create the session values we need on the first page load."""
    st.session_state.setdefault("thread_id", None)
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("threads", [])


def start_new_chat() -> None:
    """Create a thread and make it the active conversation."""
    thread = create_thread()
    st.session_state.thread_id = thread["thread_id"]
    st.session_state.messages = []


def open_thread(thread_id: str) -> None:
    """Load a conversation's messages into the current session."""
    detail = fetch_thread(thread_id)
    st.session_state.thread_id = thread_id
    st.session_state.messages = detail["messages"]


def show_history() -> None:
    """Render all messages in the active conversation."""
    if not st.session_state.messages:
        st.caption("Start a new chat or pick one from the sidebar.")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            for tool in message.get("tool_calls") or []:
                st.markdown(tool_card_html(tool), unsafe_allow_html=True)
            st.markdown(message["content"])
            render_sources(message.get("sources") or [])


def render_sidebar() -> None:
    """Render the chat list and its controls."""
    with st.sidebar:
        st.subheader("Chats")

        if st.button("➕ New chat", use_container_width=True):
            try:
                start_new_chat()
            except requests.RequestException as exc:
                st.error(f"Could not create a chat: {exc}")
            else:
                st.rerun()

        try:
            threads = fetch_threads()
        except requests.RequestException as exc:
            st.error(f"Could not load chats: {exc}")
            return

        st.session_state.threads = threads

        if not threads:
            st.caption("No chats yet.")
            return

        for thread in threads:
            thread_id = thread["thread_id"]
            active = thread_id == st.session_state.thread_id

            open_col, rename_col, delete_col = st.columns([0.72, 0.14, 0.14])

            if open_col.button(
                thread["title"],
                key=f"open-{thread_id}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                try:
                    open_thread(thread_id)
                except requests.RequestException as exc:
                    st.error(f"Could not open chat: {exc}")
                else:
                    st.rerun()

            with rename_col.popover("✏️"):
                new_title = st.text_input(
                    "Title",
                    value=thread["title"],
                    key=f"title-{thread_id}",
                    label_visibility="collapsed",
                )
                if st.button("Save", key=f"save-{thread_id}"):
                    if not new_title.strip():
                        st.warning("Title cannot be empty.")
                    else:
                        try:
                            rename_thread(thread_id, new_title.strip())
                        except requests.RequestException as exc:
                            st.error(f"Could not rename chat: {exc}")
                        else:
                            st.rerun()

            if delete_col.button("🗑", key=f"delete-{thread_id}", help="Delete chat"):
                try:
                    delete_thread(thread_id)
                except requests.RequestException as exc:
                    st.error(f"Could not delete chat: {exc}")
                else:
                    if active:
                        st.session_state.thread_id = None
                        st.session_state.messages = []
                    st.rerun()


def render_live_response(
    question: str,
    thread_id: str,
) -> dict | None:
    """Stream one answer into the chat and return the persisted message."""
    with st.chat_message("assistant"):
        thinking_ph = st.empty()
        tool_ph = st.empty()
        answer_ph = st.empty()
        sources_ph = st.empty()

        live = {
            "answer": "",
            "sources": [],
            "tools": {},
        }

        def on_event(event: dict) -> None:
            event_type = event.get("type")

            if event_type == "thinking":
                label = event.get("label", "Thinking…")
                thinking_ph.markdown(
                    f'<div class="dg-thinking">💭 {html.escape(label)}</div>',
                    unsafe_allow_html=True,
                )
            elif event_type == "tool_call":
                thinking_ph.empty()
                tool = event.get("tool", {})
                live["tools"][tool.get("name", "tool")] = tool
                tool_ph.markdown(tool_card_html(tool), unsafe_allow_html=True)
            elif event_type == "tool_result":
                tool = event.get("tool", {})
                name = tool.get("name", "tool")
                live["tools"][name] = {**live["tools"].get(name, {}), **tool}
                live["sources"] = event.get("sources", []) or []
                tool_ph.markdown(
                    tool_card_html(live["tools"][name]),
                    unsafe_allow_html=True,
                )
            elif event_type == "answer":
                live["answer"] = event.get("content", "")
                answer_ph.markdown(live["answer"])
            elif event_type == "error":
                live["answer"] = event.get("message", "")
                answer_ph.error(live["answer"])
            elif event_type == "done":
                thinking_ph.empty()

        try:
            result = stream_chat(question, thread_id, on_event)
        except requests.RequestException as exc:
            thinking_ph.empty()
            answer_ph.error(f"Backend request failed: {exc}")
            return None

        thinking_ph.empty()

        if live["sources"]:
            with sources_ph.container():
                render_sources(live["sources"])

        return {
            "role": "assistant",
            "content": result["answer"] or live["answer"],
            "sources": result["sources"],
            "tool_calls": result["tool_calls"],
        }


def main() -> None:
    init_session()
    render_sidebar()
    show_history()

    question = st.chat_input("Ask a medical question...")
    if not question:
        return

    try:
        if st.session_state.thread_id is None:
            start_new_chat()

        thread_id = st.session_state.thread_id

        st.session_state.messages.append(
            {"role": "user", "content": question}
        )
        with st.chat_message("user"):
            st.markdown(question)

        assistant_message = render_live_response(question, thread_id)
        if assistant_message is not None:
            st.session_state.messages.append(assistant_message)
    except requests.RequestException as exc:
        st.error(f"Backend request failed: {exc}")
        return

    # Refresh the sidebar so a new thread or title appears immediately.
    st.rerun()


main()
