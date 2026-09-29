def test_payment_modes(monkeypatch):
    monkeypatch.setenv("PAYMENT_MODE", "sandbox")
    monkeypatch.setenv("PAYMENT_MODE", "live")


def test_region(monkeypatch):
    monkeypatch.setenv("REGION", "us-east-1")
