from web.demo import demo_reply
from web.error_status import ErrorStatus


def test_demo_reply_basic():
    out = demo_reply("Hello world")
    assert "[Demo mode" in out
    assert "Hello world" in out


def test_demo_reply_with_error_hint():
    out = demo_reply("x", error_hint="connection refused")
    assert "connection refused" in out
    assert "live request failed" in out.lower()


def test_demo_reply_live_fallback_status():
    out = demo_reply(
        "rates",
        error_hint="Unknown prompt: penske_latest_rates",
        status=ErrorStatus(
            mode="live",
            llm_connection="connected",
            data_access="unavailable",
            failure_point="prompt_router",
            error_code="UNKNOWN_PROMPT",
            detail="Unknown prompt: penske_latest_rates",
            retryable=True,
        ),
    )
    assert "[Live fallback response]" in out
    assert "still connected to Live mode" in out
    assert "Error: UNKNOWN_PROMPT" in out
