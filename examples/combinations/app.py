import os

def checkout_variant():
    feature = os.getenv("FEATURE_A", "false")
    mode = os.getenv("MODE", "sandbox")
    if feature == "true":
        pass
    if feature == "false":
        pass
    if mode == "sandbox":
        pass
    if mode == "live":
        pass
    return feature, mode
