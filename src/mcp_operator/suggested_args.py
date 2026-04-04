"""Default JSON examples for Tools / Prompts tabs (no Gradio import — safe for unit tests)."""
from __future__ import annotations

import json
from typing import Any


def tool_name_from_dropdown(selection: str) -> str:
    """Strip ` (allow)`-style suffix from the Tools dropdown value."""
    if not selection:
        return ""
    return selection.split(" (", 1)[0].strip()

# When prompts/list has not been run yet, or the server omits `required` flags.
REQUIRED_PROMPT_ARG_KEYS: dict[str, list[str]] = {
    "review_code": ["filename"],
    "analyze_security": ["filename"],
    "security_review": ["operation", "risk_level"],
}


def sample_json_for_tool(tool_name: str) -> str:
    """Editable example arguments for the Tools tab (paths are under the server workspace)."""
    samples: dict[str, dict] = {
        "read_file": {"filepath": "README.md"},
        "write_file": {"filepath": "notes.txt", "content": "Hello"},
        "list_files": {"directory": "."},
        "delete_file": {"filepath": "old.txt"},
        "execute_command": {"command": "echo ok"},
        "analyze_code": {
            "code": "def add(a, b):\n    return a + b",
            "focus": "readability",
        },
    }
    if tool_name not in samples:
        return "{}"
    return json.dumps(samples[tool_name], indent=2)


def sample_json_for_prompt(prompt_name: str) -> str:
    """Editable example arguments for the Prompts tab (matches server prompt parameters)."""
    samples: dict[str, dict] = {
        "review_code": {"filename": "README.md"},
        "analyze_security": {"filename": "README.md"},
        "security_review": {
            "operation": "deploy to production",
            "risk_level": "high",
        },
    }
    if prompt_name not in samples:
        return "{}"
    return json.dumps(samples[prompt_name], indent=2)


def format_prompt_list_line(p: Any) -> str:
    """One prompt as a bullet; no trailing ': ' when the server sends an empty description."""
    name = getattr(p, "name", "?")
    desc = (getattr(p, "description", None) or "").strip()
    if desc:
        return f"- {name}\n  {desc}"
    return f"- {name}"
