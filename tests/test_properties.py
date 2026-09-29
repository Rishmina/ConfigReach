import json
import random
import string
from pathlib import Path

from configreach.discover import scan
from configreach.reporters import json_report


def _key(rng: random.Random) -> str:
    return "CFG_" + "".join(rng.choice(string.ascii_uppercase) for _ in range(8))


def test_generated_env_inventory_is_complete_and_deterministic(tmp_path: Path):
    rng = random.Random(20260929)
    names = sorted({_key(rng) for _ in range(40)})
    (tmp_path / "app.py").write_text(
        "import os\n" + "\n".join(f'v{i}=os.getenv("{name}")' for i, name in enumerate(names)) + "\n",
        encoding="utf-8",
    )
    first = scan(tmp_path, use_cache=False)
    second = scan(tmp_path, use_cache=False)
    assert set(first.keys) == set(names)
    assert json.loads(json_report(first))["keys"] == json.loads(json_report(second))["keys"]


def test_secret_values_never_appear_in_reports(tmp_path: Path):
    secret = "dont-print-this-value-123"
    (tmp_path / ".env.example").write_text(f"DATABASE_PASSWORD={secret}\n", encoding="utf-8")
    report = scan(tmp_path, use_cache=False)
    rendered = json_report(report)
    assert secret not in rendered
    assert "<redacted>" in rendered
