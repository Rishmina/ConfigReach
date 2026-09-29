def test_configuration(monkeypatch):
    monkeypatch.setenv("PAYMENT_MODE", "sandbox")
    monkeypatch.setenv("ENABLE_IDEMPOTENCY", "true")
