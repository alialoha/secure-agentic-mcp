from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, url_for

from agent.llm_client import (
    format_llm_error_hint,
    live_llm_configured,
    llm_provider,
    resolved_llm_model,
)
from agent.mcp_llm_host import MCPLLMHost
from web.branding import get_branding
from web.demo import demo_reply
from web.error_status import ErrorStatus, classify_live_failure

_ROOT = Path(__file__).resolve().parent
_REPO = _ROOT.parents[2]
load_dotenv(_REPO / ".env")

# One-line hint so Live mode shows which provider and model are configured.
def _log_llm_backend() -> None:
    p = llm_provider()
    m = resolved_llm_model()
    labels = {
        "openai": "OpenAI API",
        "groq": "Groq",
        "cerebras": "Cerebras",
        "custom": "Custom OPENAI_BASE_URL",
    }
    label = labels.get(p, p)
    extra = ""
    if p == "github":
        extra = "  (unsupported — set LLM_PROVIDER to openai, groq, cerebras, or custom)"
    elif not live_llm_configured():
        extra = "  credentials=MISSING"
    print(
        f"[secure-agentic-mcp] LLM: {label}  model={m}{extra}",
        flush=True,
    )


_log_llm_backend()

app = Flask(
    __name__,
    template_folder=str(_ROOT / "templates"),
    static_folder=str(_ROOT / "static"),
)


def _live_allowed() -> bool:
    return live_llm_configured()


def _run_chat(message: str, prior_messages: list | None = None) -> str:
    """Each HTTP request uses a new host; prior_messages restores in-tab chat memory."""
    host = MCPLLMHost()
    if prior_messages:
        host.conversation_history = MCPLLMHost.sanitize_external_history(prior_messages)
    return asyncio.run(host.chat(message))


@app.route("/")
def index():
    b = get_branding()
    og_description = (
        "Governed Model Context Protocol over streamable HTTP: permissions, audit trail, "
        "then the LLM — a reference UI for permissioned agentic tools."
    )
    return render_template(
        "index.html",
        live_available=_live_allowed(),
        author_name=b["author_name"],
        repo_url=b["repo_url"],
        og_title="Secure MCP — Permissioned tools, then the model",
        og_description=og_description,
        og_url=url_for("index", _external=True),
        og_image=url_for("static", filename="architecture.svg", _external=True),
    )


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}
    user_message = data.get("message")
    mode = data.get("model", "demo")

    if not user_message:
        return jsonify({"error": "Missing message"}), 400

    start = time.time()

    if mode == "demo":
        return jsonify(
            {
                "response": demo_reply(user_message),
                "duration": time.time() - start,
                "mode": "demo",
            }
        )

    if mode == "live":
        if not _live_allowed():
            status = ErrorStatus(
                mode="demo",
                llm_connection="disconnected",
                data_access="unavailable",
                failure_point="llm_gateway",
                error_code="LIVE_DISABLED_OR_UNCONFIGURED",
                detail="No LLM credentials for selected provider, or WEB_ENABLE_LIVE=0",
                retryable=False,
            )
            return jsonify(
                {
                    "response": demo_reply(
                        user_message,
                        error_hint="No LLM credentials for the selected LLM_PROVIDER (see .env.example) or WEB_ENABLE_LIVE=0",
                        status=status,
                    ),
                    "duration": time.time() - start,
                    "mode": "demo",
                    "status": status.__dict__,
                }
            )
        try:
            prior = data.get("history")
            if not isinstance(prior, list):
                prior = None
            text = _run_chat(user_message, prior_messages=prior)
            return jsonify(
                {
                    "response": text,
                    "duration": time.time() - start,
                    "mode": "live",
                }
            )
        except Exception as e:
            hint = format_llm_error_hint(e)
            status = classify_live_failure(hint)
            return jsonify(
                {
                    "response": demo_reply(user_message, error_hint=hint, status=status),
                    "duration": time.time() - start,
                    "mode": status.mode,
                    "error": hint,
                    "status": status.__dict__,
                }
            )

    return jsonify({"error": "Invalid mode; use demo or live"}), 400


if __name__ == "__main__":
    mcp_url = os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8000")
    print("=" * 64)
    print("secure-agentic-mcp | User UI (Flask)")
    print(f"  MCP_SERVER_URL (for Live mode): {mcp_url}")
    print(f"  LLM_PROVIDER: {llm_provider()}  model: {resolved_llm_model()}")
    print("=" * 64)
    app.run(
        host=os.environ.get("FLASK_HOST", "0.0.0.0"),
        port=int(os.environ.get("FLASK_PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )
