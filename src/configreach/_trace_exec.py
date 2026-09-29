from __future__ import annotations

import atexit
import hashlib
import json
import os
import runpy
import sys
from pathlib import Path


_OUT = os.environ.get("CONFIGREACH_TRACE_OUT")
_EVENTS: set[tuple[str, str]] = set()
_ORIGINAL_GETITEM = os._Environ.__getitem__
_ORIGINAL_GET = os._Environ.get


def _fingerprint(value: object) -> str:
    if value is None:
        return "<none>"
    return hashlib.sha256(str(value).encode("utf-8", "replace")).hexdigest()[:12]


def _remember(key: object, value: object) -> None:
    if isinstance(key, str) and key not in {"CONFIGREACH_TRACE_OUT", "PYTHONPATH"}:
        _EVENTS.add((key, _fingerprint(value)))


def _getenv(key: str, default=None):
    value = _ORIGINAL_GET(os.environ, key, default)
    _remember(key, value)
    return value


def _getitem(self, key):
    value = _ORIGINAL_GETITEM(self, key)
    _remember(key, value)
    return value


def _get(self, key, default=None):
    value = _ORIGINAL_GET(self, key, default)
    _remember(key, value)
    return value


def _install() -> None:
    os.getenv = _getenv
    os._Environ.__getitem__ = _getitem
    os._Environ.get = _get


@atexit.register
def _flush() -> None:
    if not _OUT:
        return
    path = Path(_OUT)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for key, fingerprint in sorted(_EVENTS):
            handle.write(json.dumps({"key": key, "fingerprint": fingerprint}) + "\n")


def _run(command: list[str]) -> int:
    if not command:
        raise ValueError("missing traced command")
    first = Path(command[0]).name.lower()
    if first.startswith("python"):
        command = command[1:]
        if not command:
            raise ValueError("python command requires a script, -m module, or -c code")
    if command[0] in {"pytest", "py.test"}:
        sys.argv = [command[0], *command[1:]]
        try:
            runpy.run_module("pytest", run_name="__main__")
        except SystemExit as exc:
            return int(exc.code or 0)
        return 0
    if command[0] == "-m" and len(command) >= 2:
        module = command[1]
        sys.argv = [module, *command[2:]]
        try:
            runpy.run_module(module, run_name="__main__", alter_sys=True)
        except SystemExit as exc:
            return int(exc.code or 0)
        return 0
    if command[0] == "-c" and len(command) >= 2:
        sys.argv = ["-c", *command[2:]]
        namespace = {"__name__": "__main__", "__file__": "<string>"}
        exec(compile(command[1], "<string>", "exec"), namespace, namespace)
        return 0
    script = Path(command[0])
    if script.suffix == ".py" and script.exists():
        sys.argv = [str(script), *command[1:]]
        try:
            runpy.run_path(str(script), run_name="__main__")
        except SystemExit as exc:
            return int(exc.code or 0)
        return 0
    raise ValueError(
        "v0.1 trace supports Python scripts, python -m, python -c, and pytest; "
        f"unsupported command: {command[0]}"
    )


def main() -> int:
    _install()
    try:
        return _run(sys.argv[1:])
    except ValueError as exc:
        sys.stderr.write(f"ConfigReach trace: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
