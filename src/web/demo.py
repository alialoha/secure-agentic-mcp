"""Deterministic replies when live LLM is unavailable or user selects Demo."""

from __future__ import annotations

from web.error_status import ErrorStatus


def _status_line(status: ErrorStatus) -> str:
    return (
        f"Mode: {status.mode.capitalize()} · "
        f"LLM: {status.llm_connection.capitalize()} · "
        f"Data Tool: {status.data_access.capitalize()} · "
        f"Error: {status.error_code}"
    )


def demo_reply(
    user_message: str,
    error_hint: str | None = None,
    status: ErrorStatus | None = None,
) -> str:
    text = (user_message or "").strip()[:400]
    extra = ""
    banner = "[Demo mode — no live LLM]"
    lead = "This is a canned response so the UI stays usable without API keys or when the model is unreachable."
    if error_hint:
        if status is None:
            extra = (
                f"\n\nLive request failed: {error_hint}\n"
                "Status: mode unknown; this may be a request-specific failure."
            )
        elif status.llm_connection == "disconnected":
            extra = (
                "\n\nLive LLM/API is currently unreachable, so this response uses offline demo behavior.\n"
                f"{_status_line(status)}\n"
                f"Failure point: {status.failure_point}\n"
                f"Detail: {status.detail}"
            )
        else:
            banner = "[Live fallback response]"
            lead = "Live mode is connected; this is a request-specific fallback message."
            extra = (
                "\n\nYou are still connected to Live mode. "
                "This fallback is for this request path only.\n"
                f"{_status_line(status)}\n"
                f"Failure point: {status.failure_point}\n"
                f"Detail: {status.detail}"
            )
    return (
        f"{banner} {lead}\n\n"
        f"You said: «{text}»\n\n"
        "The full experience uses tool-calling (OpenAI-compatible API) against the MCP HTTP server "
        "(same stack as the Operator console). Set LLM credentials per .env.example (OpenAI, Groq, Cerebras, custom URL, etc.) and choose **Live**."
        f"{extra}"
    )
