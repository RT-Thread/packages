#!/usr/bin/env python3
"""Print package names affected by a Git diff.

Each changed path is associated with the nearest package.json in the
currently checked-out tree. The package's name field is emitted once,
sorted lexicographically, and separated by spaces.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterator, Sequence


class PackageMetadataError(ValueError):
    """Raised when a current package.json cannot be used safely."""


def _run_git(repo_root: Path, args: Sequence[str]) -> str:
    """Run Git in repo_root and return decoded stdout."""

    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
    )
    return result.stdout


def find_repo_root(start: Path | None = None) -> Path:
    """Resolve the Git repository root from start (or the current cwd)."""

    start = (start or Path.cwd()).resolve()
    output = _run_git(start, ["rev-parse", "--show-toplevel"]).strip()
    return Path(output).resolve()


def changed_paths(repo_root: Path, base: str, head: str) -> Iterator[str]:
    """Yield every old and new path changed between base and head.

    NUL-delimited output keeps paths with whitespace (and other unusual
    characters) intact. Rename/copy records contain both paths.
    """

    output = _run_git(
        repo_root,
        [
            "diff",
            "--name-status",
            "--find-renames",
            "--find-copies",
            "--diff-filter=ACDMRTUXB",
            "-z",
            base,
            head,
            "--",
        ],
    )
    fields = output.split("\0")
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index]
        index += 1
        if status[:1] in {"R", "C"}:
            if index + 1 >= len(fields):
                break
            yield fields[index]
            yield fields[index + 1]
            index += 2
        else:
            if index >= len(fields):
                break
            yield fields[index]
            index += 1


def _package_name(package_json: Path) -> str:
    """Read and validate a current package.json name."""

    try:
        with package_json.open("r", encoding="utf-8-sig") as stream:
            metadata = json.load(stream)
    except (OSError, UnicodeError) as exc:
        raise PackageMetadataError(
            f"Unable to read {package_json}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise PackageMetadataError(
            f"Invalid JSON in {package_json}: {exc}"
        ) from exc

    if not isinstance(metadata, dict):
        raise PackageMetadataError(f"Expected an object in {package_json}")
    name = metadata.get("name")
    if not isinstance(name, str) or not name:
        raise PackageMetadataError(f"Missing package name in {package_json}")
    if re.fullmatch(r"[A-Za-z0-9_.+-]+", name) is None:
        raise PackageMetadataError(
            f"Invalid package name {name!r} in {package_json}"
        )
    return name


def package_for_path(repo_root: Path, changed_path: str) -> str | None:
    """Find the nearest current ancestor package for a changed path."""

    # Git emits POSIX separators even on Windows; Path accepts them on both
    # supported platforms. Resolve before checking containment to reject '..'.
    relative_path = Path(changed_path)
    if relative_path.is_absolute():
        relative_path = Path(*relative_path.parts[1:])
    repo_root = repo_root.resolve()
    candidate = (repo_root / relative_path).resolve()

    # A changed path normally names a file. If it currently exists as a
    # directory, include that directory itself in the ancestor search.
    current = candidate if candidate.is_dir() else candidate.parent
    try:
        current.relative_to(repo_root)
    except ValueError:
        return None

    while True:
        package_json = current / "package.json"
        try:
            package_json.stat()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise PackageMetadataError(
                f"Unable to inspect {package_json}: {exc}"
            ) from exc
        else:
            return _package_name(package_json)
        if current == repo_root:
            return None
        current = current.parent


def detect_changed_packages(repo_root: Path, base: str, head: str) -> list[str]:
    """Return sorted unique package names affected by a Git diff."""

    names = {
        name
        for path in changed_paths(repo_root, base, head)
        if (name := package_for_path(repo_root, path)) is not None
    }
    return sorted(names)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", help="base Git revision")
    parser.add_argument("head", help="head Git revision")
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="repository root (defaults to the current Git repository)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        repo_root = find_repo_root(args.repo_root) if args.repo_root else find_repo_root()
        names = detect_changed_packages(repo_root, args.base, args.head)
    except (OSError, PackageMetadataError, subprocess.CalledProcessError) as exc:
        print(f"detect_changed_packages.py: {exc}", file=sys.stderr)
        return 1
    print(" ".join(names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
