"""
Unified MCP server: workspace file tools + security-tier tools, HTTP transport.
Resources and prompts for operator visibility; audit log under data/.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import warnings

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import HTMLResponse

warnings.filterwarnings("ignore", category=DeprecationWarning)

_DATA = Path(os.environ.get("MCP_DATA_DIR", Path(__file__).resolve().parents[2] / "data")).resolve()
WORKSPACE = _DATA / "workspace"
WORKSPACE.mkdir(parents=True, exist_ok=True)
PERMISSIONS_FILE = _DATA / "permissions.json"
AUDIT_LOG = _DATA / "audit.log"

mcp = FastMCP("Secure MCP — workspace + governance")


def _audit(line: str) -> None:
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(line)


def _within_workspace(path: Path) -> bool:
    try:
        path.resolve().relative_to(WORKSPACE.resolve())
        return True
    except ValueError:
        return False


@mcp.tool()
def read_file(filepath: str) -> str:
    """Read a file from the workspace. (Risk: LOW)"""
    path = WORKSPACE / filepath
    if not _within_workspace(path):
        return "Error: Access denied — path outside workspace"
    if not path.is_file():
        return f"Error: File not found: {filepath}"
    return path.read_text(encoding="utf-8")


@mcp.tool()
def write_file(filepath: str, content: str) -> str:
    """Write a file under the workspace. (Risk: MEDIUM)"""
    path = WORKSPACE / filepath
    if not _within_workspace(path):
        return "Error: Access denied — path outside workspace"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        _audit(f"[{datetime.now().isoformat()}] WRITE: {filepath}\n")
        return f"Successfully wrote {len(content)} characters to {filepath}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def list_files(directory: str = ".") -> str:
    """List files in a workspace directory. (Risk: LOW)"""
    path = WORKSPACE / directory
    if not _within_workspace(path):
        return "Error: Access denied — path outside workspace"
    if not path.exists():
        return f"Error: Directory not found: {directory}"
    if not path.is_dir():
        return f"Error: Not a directory: {directory}"
    lines = []
    for item in sorted(path.iterdir()):
        rel = item.relative_to(WORKSPACE)
        kind = "DIR" if item.is_dir() else "FILE"
        size = item.stat().st_size if item.is_file() else 0
        lines.append(f"{kind}: {rel} ({size} bytes)")
    return "\n".join(lines) if lines else "Directory is empty"


@mcp.tool()
def delete_file(filepath: str) -> str:
    """Delete a file in the workspace. (Risk: HIGH)"""
    path = WORKSPACE / filepath
    if not _within_workspace(path):
        return "Error: Access denied — path outside workspace"
    if not path.is_file():
        return f"Error: Not a file or missing: {filepath}"
    try:
        path.unlink()
        _audit(f"[{datetime.now().isoformat()}] DELETE: {filepath}\n")
        return f"Successfully deleted {filepath}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def execute_command(command: str) -> str:
    """Simulated shell command — no real execution. (Risk: CRITICAL)"""
    _audit(f"[{datetime.now().isoformat()}] EXECUTE (simulated): {command}\n")
    return (
        f"Simulated execution of: {command}\n"
        "(Real execution disabled; configure policy in data/permissions.json.)"
    )


@mcp.tool()
def analyze_code(code: str, focus: str = "quality") -> str:
    """Preview-only code review stub; the operator host normally runs the model with tool results."""
    return (
        f"Preview for focus “{focus}” ({len(code)} characters of code).\n\n"
        "In deployments that use MCP client-side sampling, the LLM would run in the host "
        "and return a full review; this endpoint only echoes a short summary."
    )


@mcp.resource("file://workspace/{filename}")
def resource_workspace_file(filename: str) -> str:
    path = WORKSPACE / filename
    if not _within_workspace(path) or not path.is_file():
        raise ValueError("Invalid or missing file")
    return path.read_text(encoding="utf-8")


@mcp.resource("file://audit/log")
def resource_audit_log() -> str:
    if not AUDIT_LOG.exists():
        return "No audit entries yet."
    return AUDIT_LOG.read_text(encoding="utf-8")


@mcp.resource("file://config/permissions")
def resource_permissions() -> str:
    if not PERMISSIONS_FILE.exists():
        return json.dumps(
            {
                "read_file": "allow",
                "write_file": "ask",
                "list_files": "allow",
                "delete_file": "deny",
                "execute_command": "deny",
                "analyze_code": "ask",
            },
            indent=2,
        )
    return PERMISSIONS_FILE.read_text(encoding="utf-8")


@mcp.prompt()
def review_code(filename: str) -> str:
    return f"""Review the code in workspace file '{filename}' for clarity, bugs, and security."""


@mcp.prompt()
def analyze_security(filename: str) -> str:
    return f"""Security review of '{filename}': validation, auth, injection, and logging."""


@mcp.prompt()
def security_review(operation: str, risk_level: str) -> list[dict]:
    return [
        {
            "role": "user",
            "content": f"""Review this operation:
Operation: {operation}
Risk: {risk_level}
Cover impact, safeguards, approval, and audit logging.""",
        }
    ]


_MCP_HTTP_PATH = "/mcp"


@mcp.custom_route("/", methods=["GET"])
async def _http_root(_request: Request) -> HTMLResponse:
    """Human-friendly page; MCP JSON-RPC is on /mcp (browsers should not use 0.0.0.0)."""
    port = int(os.environ.get("MCP_HTTP_PORT", "8000"))
    mcp_url = f"http://127.0.0.1:{port}{_MCP_HTTP_PATH}"
    body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>secure-agentic-mcp</title></head>
<body>
  <h1>MCP HTTP server is running</h1>
  <p>This process is an MCP endpoint, not a full web app. Connection is healthy.</p>
  <p>MCP URL (for clients): <a href="{mcp_url}">{mcp_url}</a></p>
  <p><strong>Do not use</strong> <code>http://0.0.0.0</code> in a browser — use <code>127.0.0.1</code> or <code>localhost</code> instead.</p>
</body>
</html>"""
    return HTMLResponse(body)


def main() -> None:
    host = os.environ.get("MCP_HTTP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_HTTP_PORT", "8000"))
    display_host = "127.0.0.1" if host in ("0.0.0.0", "::", "[::]") else host
    data_abs = _DATA.resolve()
    workspace_abs = WORKSPACE.resolve()
    sep = "=" * 64
    print(sep)
    print("server is running. you can now run the client")
    # print("secure-agentic-mcp | MCP HTTP server (this repository)")
    # print(f"  Listen (bind): {host}:{port}")
    # print(f"  MCP URL (browsers & clients): http://{display_host}:{port}{_MCP_HTTP_PATH}")
    # if host in ("0.0.0.0", "::", "[::]"):
    #     print("  Note: http://0.0.0.0/... is not valid in browsers — use the line above.")
    # print(f"  Status page: http://{display_host}:{port}/  (GET / confirms the server is up)")
    # print(f"  MCP_DATA_DIR: {data_abs}")
    # print(f"  Workspace:    {workspace_abs}")
    # print("  Tools read/write files under Workspace above — not other projects.")
    print(sep)
    mcp.run(
        transport="http",
        host=host,
        port=port,
        path=_MCP_HTTP_PATH,
        show_banner=False,
        log_level="warning",
        uvicorn_config={"log_level": "warning"},
    )


if __name__ == "__main__":
    main()
