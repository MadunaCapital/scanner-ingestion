from ingestion.proxy import ProxyConfig


def test_from_env_returns_none_when_unset(monkeypatch):
    monkeypatch.delenv("PROXY_URL", raising=False)
    assert ProxyConfig.from_env() is None


def test_from_env_reads_configured_variable(monkeypatch):
    monkeypatch.setenv("PROXY_URL", "http://user:pass@proxy.example.com:7777")
    config = ProxyConfig.from_env()

    assert config is not None
    assert config.url == "http://user:pass@proxy.example.com:7777"


def test_as_dict_format_for_curl_cffi():
    config = ProxyConfig(url="http://proxy.example.com:7777")
    assert config.as_dict() == {
        "http": "http://proxy.example.com:7777",
        "https": "http://proxy.example.com:7777",
    }


def test_as_playwright_proxy_format():
    config = ProxyConfig(url="http://proxy.example.com:7777")
    assert config.as_playwright_proxy() == {"server": "http://proxy.example.com:7777"}


def test_from_env_respects_custom_variable_name(monkeypatch):
    monkeypatch.setenv("CUSTOM_PROXY", "http://other.example.com:8888")
    monkeypatch.delenv("PROXY_URL", raising=False)

    assert ProxyConfig.from_env("PROXY_URL") is None
    config = ProxyConfig.from_env("CUSTOM_PROXY")
    assert config.url == "http://other.example.com:8888"
