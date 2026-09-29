import os

PAYMENT_MODE = os.getenv("PAYMENT_MODE", "sandbox")
ENABLE_IDEMPOTENCY = os.getenv("ENABLE_IDEMPOTENCY", "true")
REGION = os.environ.get("REGION", "local")


def process_payment(amount: int) -> str:
    if PAYMENT_MODE == "live":
        return f"live:{amount}"
    return f"sandbox:{amount}"
