import os
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    payment_mode: str = Field("sandbox", validation_alias="PAYMENT_MODE")
    region: str = Field("us-east-1", validation_alias="REGION")


def charge_mode() -> str:
    mode = os.getenv("PAYMENT_MODE", "sandbox")
    if mode == "live":
        return "real"
    return "simulated"


def checkout_enabled(flags) -> bool:
    return flags.is_enabled("checkout-v2")
