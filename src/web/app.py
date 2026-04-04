from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from agent.mcp_llm_host import MCPLLMHost
from web.demo import demo_reply

_ROOT = Path(__file__).resolve().parent
_REPO = _ROOT.parents[2]
load_dotenv(_REPO / ".env")

app = Flask(
    __name__,
    template_folder=str(_ROOT / "templates"),
    static_folder=str(_ROOT / "static"),
)


def _live_allowed() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY")) and os.environ.get(
        "WEB_ENABLE_LIVE", "1"
    ) not in ("0", "false", "False")


def _run_chat(message: str) -> str:
    host = MCPLLMHost()
    return asyncio.run(host.chat(message))


@app.route("/")
def index():
    return render_template(
        "index.html",
        live_available=_live_allowed(),
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
            return jsonify(
                {
                    "response": demo_reply(
                        user_message,
                        error_hint="OPENAI_API_KEY not set or WEB_ENABLE_LIVE=0",
                    ),
                    "duration": time.time() - start,
                    "mode": "demo",
                }
            )
        try:
            text = _run_chat(user_message)
            return jsonify(
                {
                    "response": text,
                    "duration": time.time() - start,
                    "mode": "live",
                }
            )
        except Exception as e:
            return jsonify(
                {
                    "response": demo_reply(user_message, error_hint=str(e)),
                    "duration": time.time() - start,
                    "mode": "demo",
                    "error": str(e),
                }
            )

    return jsonify({"error": "Invalid mode; use demo or live"}), 400


if __name__ == "__main__":
    mcp_url = os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8000")
    print("=" * 64)
    print("secure-agentic-mcp | User UI (Flask)")
    print(f"  MCP_SERVER_URL (for Live mode): {mcp_url}")
    print("=" * 64)
    app.run(
        host=os.environ.get("FLASK_HOST", "0.0.0.0"),
        port=int(os.environ.get("FLASK_PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )
