from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from . import __version__

RELEASE_MANIFEST_SCHEMA_VERSION = 1


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_member_name(name: str) -> str:
    parts = PurePosixPath(name).parts
    if len(parts) > 1 and parts[0].startswith("configreach-"):
        parts = parts[1:]
    return PurePosixPath(*parts).as_posix()


def canonical_archive_digest(path: str | Path) -> str:
    """Hash archive contents while ignoring container timestamp/order metadata."""
    artifact = Path(path)
    digest = hashlib.sha256()

    if artifact.suffix == ".whl":
        with zipfile.ZipFile(artifact) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            for item in sorted(members, key=lambda value: value.filename):
                name = _normalized_member_name(item.filename)
                digest.update(name.encode("utf-8"))
                digest.update(b"\0")
                digest.update(archive.read(item.filename))
                digest.update(b"\0")
        return digest.hexdigest()

    if artifact.name.endswith(".tar.gz"):
        with tarfile.open(artifact, "r:gz") as archive:
            members = [item for item in archive.getmembers() if item.isfile()]
            for item in sorted(members, key=lambda value: value.name):
                name = _normalized_member_name(item.name)
                handle = archive.extractfile(item)
                if handle is None:
                    continue
                digest.update(name.encode("utf-8"))
                digest.update(b"\0")
                digest.update(handle.read())
                digest.update(b"\0")
        return digest.hexdigest()

    raise ValueError(f"unsupported release artifact: {artifact.name}")


def normalize_sdist(path: str | Path, epoch: int) -> None:
    """Rewrite an sdist using deterministic tar/gzip container metadata.

    The source distribution payload is preserved, but archive-only metadata is rebuilt
    from scratch: sorted member order, fixed timestamps, normalized ownership and stable
    modes. This avoids inheriting host/wall-clock metadata from setuptools TarInfo objects.
    """
    artifact = Path(path)
    if not artifact.name.endswith(".tar.gz"):
        raise ValueError(f"not an sdist: {artifact.name}")
    if epoch < 0:
        raise ValueError("epoch must be non-negative")

    entries: list[tuple[tarfile.TarInfo, bytes | None]] = []
    with tarfile.open(artifact, "r:gz") as source:
        for member in sorted(source.getmembers(), key=lambda item: item.name):
            data: bytes | None = None
            if member.isfile():
                handle = source.extractfile(member)
                if handle is None:
                    raise ValueError(f"could not read sdist member: {member.name}")
                data = handle.read()

            info = tarfile.TarInfo(member.name)
            info.type = member.type
            info.linkname = member.linkname
            info.mtime = epoch
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.devmajor = 0
            info.devminor = 0
            info.pax_headers = {}
            if member.isdir():
                info.mode = 0o755
                info.size = 0
            elif member.isfile():
                info.mode = 0o755 if member.mode & 0o111 else 0o644
                info.size = len(data or b"")
            elif member.issym() or member.islnk():
                info.mode = 0o777
                info.size = 0
            else:
                info.mode = 0o644
                info.size = 0
            entries.append((info, data))

    temporary = artifact.with_name(artifact.name + ".normalized")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=raw,
            compresslevel=9,
            mtime=epoch,
        ) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as target:
                for info, data in entries:
                    target.addfile(info, io.BytesIO(data) if data is not None else None)
    temporary.replace(artifact)


@dataclass(frozen=True)
class ReleaseArtifact:
    filename: str
    kind: str
    size: int
    sha256: str
    canonical_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReleaseManifest:
    project: str
    version: str
    artifacts: tuple[ReleaseArtifact, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RELEASE_MANIFEST_SCHEMA_VERSION,
            "project": self.project,
            "version": self.version,
            "artifacts": [item.to_dict() for item in self.artifacts],
        }


@dataclass(frozen=True)
class ReleaseComparison:
    left: ReleaseManifest
    right: ReleaseManifest
    exact_reproducible: bool
    content_reproducible: bool
    differences: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RELEASE_MANIFEST_SCHEMA_VERSION,
            "project": self.left.project,
            "version": self.left.version,
            "exact_reproducible": self.exact_reproducible,
            "content_reproducible": self.content_reproducible,
            "differences": list(self.differences),
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }


def build_release_manifest(directory: str | Path) -> ReleaseManifest:
    root = Path(directory)
    if not root.is_dir():
        raise ValueError(f"release directory does not exist: {root}")

    paths = sorted(
        [*root.glob("*.whl"), *root.glob("*.tar.gz")],
        key=lambda item: item.name,
    )
    if not paths:
        raise ValueError(f"no wheel or sdist artifacts found in {root}")

    artifacts: list[ReleaseArtifact] = []
    for path in paths:
        kind = "wheel" if path.suffix == ".whl" else "sdist"
        artifacts.append(
            ReleaseArtifact(
                filename=path.name,
                kind=kind,
                size=path.stat().st_size,
                sha256=_sha256_file(path),
                canonical_sha256=canonical_archive_digest(path),
            )
        )
    return ReleaseManifest("configreach", __version__, tuple(artifacts))


def compare_release_manifests(
    left: ReleaseManifest,
    right: ReleaseManifest,
) -> ReleaseComparison:
    differences: list[str] = []
    exact = True
    content = True

    if left.project != right.project:
        differences.append(f"project differs: {left.project!r} != {right.project!r}")
        exact = False
        content = False
    if left.version != right.version:
        differences.append(f"version differs: {left.version!r} != {right.version!r}")
        exact = False
        content = False

    left_by_name = {item.filename: item for item in left.artifacts}
    right_by_name = {item.filename: item for item in right.artifacts}
    if set(left_by_name) != set(right_by_name):
        missing_left = sorted(set(right_by_name) - set(left_by_name))
        missing_right = sorted(set(left_by_name) - set(right_by_name))
        if missing_left:
            differences.append(f"missing from left: {', '.join(missing_left)}")
        if missing_right:
            differences.append(f"missing from right: {', '.join(missing_right)}")
        exact = False
        content = False

    for name in sorted(set(left_by_name) & set(right_by_name)):
        first = left_by_name[name]
        second = right_by_name[name]
        if first.sha256 != second.sha256:
            exact = False
            differences.append(f"byte digest differs: {name}")
        if first.canonical_sha256 != second.canonical_sha256:
            content = False
            differences.append(f"archive content differs: {name}")

    return ReleaseComparison(left, right, exact, content, tuple(differences))


def render_release_manifest(manifest: ReleaseManifest, format_name: str = "text") -> str:
    if format_name == "json":
        return json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n"
    if format_name != "text":
        raise ValueError(f"unsupported release format: {format_name}")
    lines = [f"ConfigReach release manifest {manifest.version}"]
    for item in manifest.artifacts:
        lines.append(
            f"- {item.filename}: {item.kind} bytes={item.size} sha256={item.sha256} canonical={item.canonical_sha256}"
        )
    return "\n".join(lines) + "\n"


def render_release_comparison(comparison: ReleaseComparison, format_name: str = "text") -> str:
    if format_name == "json":
        return json.dumps(comparison.to_dict(), indent=2, sort_keys=True) + "\n"
    if format_name != "text":
        raise ValueError(f"unsupported release format: {format_name}")
    lines = [
        f"ConfigReach release reproducibility: {'PASS' if comparison.exact_reproducible else 'FAIL'}",
        f"exact byte reproducibility: {'yes' if comparison.exact_reproducible else 'no'}",
        f"canonical content reproducibility: {'yes' if comparison.content_reproducible else 'no'}",
    ]
    lines.extend(f"- {item}" for item in comparison.differences)
    return "\n".join(lines) + "\n"
