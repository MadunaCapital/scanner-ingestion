from ingestion.cloudflare_session import extract_cf_clearance


def test_extract_cf_clearance_finds_the_cookie():
    cookies = [
        {"name": "session_id", "value": "abc123"},
        {"name": "cf_clearance", "value": "xyz789"},
        {"name": "other", "value": "ignored"},
    ]

    result = extract_cf_clearance(cookies)

    assert result == {"name": "cf_clearance", "value": "xyz789"}


def test_extract_cf_clearance_returns_none_when_absent():
    cookies = [{"name": "session_id", "value": "abc123"}]

    assert extract_cf_clearance(cookies) is None


def test_extract_cf_clearance_handles_empty_list():
    assert extract_cf_clearance([]) is None
