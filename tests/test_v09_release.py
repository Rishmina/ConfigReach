from __future__ import annotations

import gzip
import io
import tarfile
import zipfile
from pathlib import Path

from configreach import __version__
from configreach.release import (
    RELEASE_MANIFEST_SCHEMA_VERSION,
    build_release_manifest,
    canonical_archive_digest,
    compare_release_manifests,
    normalize_sdist,
)


def _write_wheel(path: Path, *, year: int) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        info = zipfile.ZipInfo("configreach/module.py", date_time=(year, 1, 1, 0, 0, 0))
        archive.writestr(info, b"VALUE = 1\n")
        metadata = zipfile.ZipInfo(
            "configreach-0.9.0.dist-info/METADATA", date_time=(year, 1, 1, 0, 0, 0)
        )
        archive.writestr(metadata, b"Name: configreach\nVersion: 0.9.0\n")


def _write_sdist(path: Path, *, gzip_mtime: int, member_mtime: int = 123) -> None:
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode="w") as archive:
        data = b"VALUE = 1\n"
        info = tarfile.TarInfo("configreach-0.9.0/src/configreach/module.py")
        info.size = len(data)
        info.mtime = member_mtime
        info.uid = member_mtime % 100
        info.gid = member_mtime % 50
        info.uname = "builder"
        info.gname = "builder"
        archive.addfile(info, io.BytesIO(data))
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=gzip_mtime, filename="") as compressed:
            compressed.write(payload.getvalue())


def test_canonical_wheel_digest_ignores_zip_timestamps(tmp_path: Path) -> None:
    left = tmp_path / "left.whl"
    right = tmp_path / "right.whl"
    _write_wheel(left, year=2024)
    _write_wheel(right, year=2026)
    assert left.read_bytes() != right.read_bytes()
    assert canonical_archive_digest(left) == canonical_archive_digest(right)


def test_canonical_sdist_digest_ignores_gzip_timestamp(tmp_path: Path) -> None:
    left = tmp_path / "left.tar.gz"
    right = tmp_path / "right.tar.gz"
    _write_sdist(left, gzip_mtime=100)
    _write_sdist(right, gzip_mtime=200)
    assert left.read_bytes() != right.read_bytes()
    assert canonical_archive_digest(left) == canonical_archive_digest(right)


def test_normalize_sdist_produces_exact_bytes(tmp_path: Path) -> None:
    left = tmp_path / "left.tar.gz"
    right = tmp_path / "right.tar.gz"
    _write_sdist(left, gzip_mtime=100, member_mtime=123)
    _write_sdist(right, gzip_mtime=200, member_mtime=999)
    assert left.read_bytes() != right.read_bytes()
    normalize_sdist(left, 1700000000)
    normalize_sdist(right, 1700000000)
    assert left.read_bytes() == right.read_bytes()
    assert canonical_archive_digest(left) == canonical_archive_digest(right)


def test_release_manifest_and_comparison(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    wheel_name = "configreach-0.9.0-py3-none-any.whl"
    sdist_name = "configreach-0.9.0.tar.gz"
    _write_wheel(first / wheel_name, year=2024)
    _write_wheel(second / wheel_name, year=2026)
    _write_sdist(first / sdist_name, gzip_mtime=100)
    _write_sdist(second / sdist_name, gzip_mtime=200)

    left = build_release_manifest(first)
    right = build_release_manifest(second)
    result = compare_release_manifests(left, right)

    assert RELEASE_MANIFEST_SCHEMA_VERSION == 1
    assert left.version == __version__ == "0.9.0"
    assert {item.kind for item in left.artifacts} == {"wheel", "sdist"}
    assert result.exact_reproducible is False
    assert result.content_reproducible is True
    assert any("byte digest differs" in item for item in result.differences)
    assert not any("archive content differs" in item for item in result.differences)


def test_release_manifest_rejects_empty_directory(tmp_path: Path) -> None:
    try:
        build_release_manifest(tmp_path)
    except ValueError as exc:
        assert "no wheel or sdist artifacts" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")
