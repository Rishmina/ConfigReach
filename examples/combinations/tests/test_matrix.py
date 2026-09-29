def test_enabled_sandbox(monkeypatch):
    monkeypatch.setenv("FEATURE_A", "true")
    monkeypatch.setenv("MODE", "sandbox")

def test_disabled_live(monkeypatch):
    monkeypatch.setenv("FEATURE_A", "false")
    monkeypatch.setenv("MODE", "live")
