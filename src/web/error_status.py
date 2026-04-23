from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ErrorStatus:
    mode: str
    llm_connection: str
    data_access: str
    failure_point: str
    error_code: str
    detail: str
    retryable: bool = True


def classify_live_failure(error_hint: str) -> ErrorStatus:
    text = (error_hint or "").strip()
    low = text.lower()

    if "unknown prompt" in low:
        return ErrorStatus(
            mode="live",
            llm_connection="connected",
            data_access="unavailable",
            failure_point="prompt_router",
            error_code="UNKNOWN_PROMPT",
            detail=text,
            retryable=True,
        )

    if "401" in low or "unauthorized" in low:
        return ErrorStatus(
            mode="live",
            llm_connection="connected",
            data_access="unavailable",
            failure_point="tool_executor",
            error_code="AUTH_FAILED",
            detail=text,
            retryable=False,
        )

    if (
        "connection" in low
        or "timeout" in low
        or "timed out" in low
        or "refused" in low
        or "unreachable" in low
    ):
        return ErrorStatus(
            mode="demo",
            llm_connection="disconnected",
            data_access="unknown",
            failure_point="llm_gateway",
            error_code="LLM_UNREACHABLE",
            detail=text,
            retryable=True,
        )

    return ErrorStatus(
        mode="live",
        llm_connection="connected",
        data_access="unknown",
        failure_point="unknown",
        error_code="REQUEST_FAILED",
        detail=text or "No additional details",
        retryable=True,
    )

