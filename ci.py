# -*- coding:utf-8 -*-

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import requests


REQUEST_TIMEOUT_SECONDS = 20
URL_RETRIES = 4
RETRYABLE_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class PackageRecord:
    path: Path
    metadata: Optional[Dict[str, object]]
    error: Optional[str] = None

    @property
    def name(self):
        if self.metadata:
            name = self.metadata.get("name")
            if isinstance(name, str) and name:
                return name
        return self.path.parent.name

    @property
    def weight(self):
        if not self.metadata:
            return 1
        site = self.metadata.get("site", [])
        if not isinstance(site, list):
            return 1
        return 1 + sum(
            1
            for entry in site
            if isinstance(entry, dict)
            and isinstance(entry.get("URL"), str)
            and entry.get("URL")
        )


def _close_response(response):
    close = getattr(response, "close", None)
    if callable(close):
        close()


@lru_cache(maxsize=None)
def determine_url_valid(url_from_srv):
    """Check whether a supported package URL is reachable."""

    parsed_url = urlparse(url_from_srv) if isinstance(url_from_srv, str) else None
    if (
        parsed_url is None
        or parsed_url.scheme.lower() != "https"
        or parsed_url.netloc.lower() != "github.com"
    ):
        print("not support url: {}".format(url_from_srv))
        return False

    headers = {
        "Connection": "keep-alive",
        "Accept-Encoding": "gzip, deflate",
        "Accept": "*/*",
        "User-Agent": "RT-Thread-packages-ci",
    }
    last_error = None

    for attempt in range(URL_RETRIES):
        response = None
        try:
            response = requests.get(
                url_from_srv,
                stream=True,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
                allow_redirects=True,
            )
            if 200 <= response.status_code < 400:
                return True
            last_error = "HTTP {}".format(response.status_code)
            if response.status_code == 404:
                break
            if response.status_code not in RETRYABLE_HTTP_STATUS_CODES:
                break
        except requests.RequestException as exc:
            last_error = str(exc)
        finally:
            if response is not None:
                _close_response(response)

        if attempt + 1 < URL_RETRIES:
            time.sleep(2**attempt)

    print("Warning : {} is invalid ({}).".format(url_from_srv, last_error))
    return False


def get_json_info(json_pathname):
    try:
        with open(json_pathname, "r", encoding="utf-8-sig") as stream:
            return json.load(stream)
    except (OSError, UnicodeError, ValueError) as exc:
        print("The JSON config file syntax checking failed: {} ({})".format(
            json_pathname, exc
        ))
        return None


def file_path_check(package_info, pathname):
    info_dir = os.path.dirname(str(pathname))
    package_name = package_info.get("name")

    if package_name == os.path.basename(info_dir):
        return True

    print("===========================================>")
    print("Error: package name is different with package folder name.")
    print(pathname)
    print("package name:%s" % package_name)
    print("package folder name: %s" % os.path.basename(info_dir))
    return False


def _github_command_escape(value):
    """Escape values used in GitHub Actions workflow commands."""

    return (
        str(value)
        .replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
    )


def _package_relative_path(pathname):
    path = Path(pathname)
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


def _write_failure_summary(failures):
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path or not failures:
        return

    lines = [
        "## Failed packages",
        "",
        "| Package | Path | Reason |",
        "| --- | --- | --- |",
    ]
    for record, reason in failures:
        package = str(record.name).replace("|", "\\|")
        package_path = _package_relative_path(record.path).replace("|", "\\|")
        failure_reason = str(reason).replace("|", "\\|")
        lines.append("| `{}` | `{}` | {} |".format(package, package_path, failure_reason))
    lines.append("")

    try:
        with open(summary_path, "a", encoding="utf-8") as stream:
            stream.write("\n".join(lines))
    except OSError as exc:
        print("Warning: unable to write GitHub step summary: {}".format(exc))


def _report_failed_packages(failures):
    if not failures:
        return

    print("\nFAILED PACKAGES ({}):".format(len(failures)))
    for record, reason in failures:
        package_path = _package_relative_path(record.path)
        annotation = "{}: {}".format(record.name, reason)
        print(
            "::error file={},title={}::{}".format(
                _github_command_escape(package_path),
                _github_command_escape("Package validation failed"),
                _github_command_escape(annotation),
            )
        )
        print("- {} ({})".format(record.name, reason))
    _write_failure_summary(failures)


@lru_cache(maxsize=None)
def check_branch_exists(git_url, branch_name):
    """Check whether branch_name exists in git_url."""

    command = ["git", "ls-remote", "--exit-code", "--heads", git_url, branch_name]
    try:
        subprocess.check_output(
            command,
            stderr=subprocess.STDOUT,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        return True
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


@lru_cache(maxsize=None)
def check_commit_sha_exists(repo_url, commit_sha):
    """Check whether commit_sha exists in a GitHub repository."""

    if repo_url.endswith(".git"):
        repo_url = repo_url[:-4]
    parsed_repo = urlparse(repo_url)
    parts = [part for part in parsed_repo.path.split("/") if part]
    if (
        parsed_repo.scheme.lower() != "https"
        or parsed_repo.netloc.lower() != "github.com"
        or len(parts) != 2
    ):
        return False

    url = "https://api.github.com/repos/{}/{}/git/commits/{}".format(
        parts[0], parts[1], commit_sha
    )
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer {}".format(token)

    for attempt in range(URL_RETRIES):
        response = None
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code == 200:
                return True
            if response.status_code == 404:
                return False
            if response.status_code not in RETRYABLE_HTTP_STATUS_CODES:
                return False
        except requests.RequestException:
            pass
        finally:
            if response is not None:
                _close_response(response)
        if attempt + 1 < URL_RETRIES:
            time.sleep(2**attempt)
    return False


def is_file_link_with_extension(url):
    """Check whether the URL path ends with a filename extension."""

    return re.search(r"\.\w+$", urlparse(url).path) is not None


def _required_string(package_info, key, label):
    value = package_info.get(key)
    if isinstance(value, str) and value:
        return True
    print("The {} of {} package is lost.".format(label, package_info.get("name", "")))
    return False


def json_file_content_check(package_info):
    """Check package metadata and every repository/version URL."""

    if not isinstance(package_info, dict):
        print("Package metadata must be a JSON object.")
        return False

    valid = True
    valid = _required_string(package_info, "category", "category") and valid
    valid = _required_string(package_info, "enable", "enable") and valid
    valid = _required_string(package_info, "license", "license") and valid

    author = package_info.get("author")
    if not isinstance(author, dict):
        print("The author of {} package is lost.".format(package_info.get("name", "")))
        valid = False
    else:
        if not isinstance(author.get("name"), str) or not author.get("name"):
            print("The author name of {} package is lost.".format(package_info.get("name", "")))
            valid = False
        if not isinstance(author.get("email"), str) or not author.get("email"):
            print("The author email of {} package is lost.".format(package_info.get("name", "")))
            valid = False

    repository = package_info.get("repository")
    if not isinstance(repository, str) or not repository:
        print("The repository of {} package is lost.".format(package_info.get("name", "")))
        valid = False
    elif not determine_url_valid(repository):
        valid = False

    sites = package_info.get("site")
    if not isinstance(sites, list):
        print("The site of {} package must be a list.".format(package_info.get("name", "")))
        return False

    for site in sites:
        if not isinstance(site, dict):
            print("Package site entry must be a JSON object.")
            valid = False
            continue

        package_version = site.get("version")
        package_url = site.get("URL")
        print("{} : {}".format(package_version, package_url))
        if not isinstance(package_url, str) or not package_url:
            print("Package URL is lost.")
            valid = False
            continue

        package_url_valid = determine_url_valid(package_url)
        if not package_url_valid:
            valid = False

        if package_url.endswith(".git"):
            ver_sha = site.get("VER_SHA")
            print("VER_SHA: {}".format(ver_sha))
            if not isinstance(ver_sha, str) or not ver_sha:
                print("VER_SHA is lost.")
                valid = False
            elif package_url_valid and not check_branch_exists(package_url, ver_sha):
                if not check_commit_sha_exists(package_url, ver_sha):
                    print("SHA or branch '{}' is not valid.".format(ver_sha))
                    valid = False
        else:
            filename = site.get("filename")
            print("Filename: {}".format(filename))
            if not isinstance(filename, str) or not filename:
                print("Filename is lost.")
                valid = False
            if not is_file_link_with_extension(package_url):
                print("Url is not a file link.")
                valid = False

    return valid


def discover_packages(work_root):
    """Read package metadata in a stable order and flag duplicate names."""

    root = Path(work_root).resolve()
    records = []
    name_paths = {}

    for package_json in sorted(root.rglob("package.json")):
        metadata = get_json_info(str(package_json))
        error = None
        if not isinstance(metadata, dict):
            error = "Unable to read package metadata."
        else:
            name = metadata.get("name")
            if not isinstance(name, str) or not name:
                error = "Package name is missing."
            else:
                name_paths.setdefault(name, []).append(package_json)
        records.append(PackageRecord(package_json, metadata, error))

    duplicate_names = {
        name: paths for name, paths in name_paths.items() if len(paths) > 1
    }
    if duplicate_names:
        print("===========================================>")
        print("Error: duplicated package name found.")
        for name in sorted(duplicate_names):
            print("package name: {}".format(name))
            for pathname in duplicate_names[name]:
                print("  {}".format(pathname))
        duplicate_set = set(duplicate_names)
        records = [
            PackageRecord(
                record.path,
                record.metadata,
                "Duplicated package name." if record.name in duplicate_set else record.error,
            )
            for record in records
        ]

    return records


def _build_shards(records, shard_count):
    shards = [[] for _ in range(shard_count)]
    loads = [0 for _ in range(shard_count)]
    ordered = sorted(
        records,
        key=lambda record: (-record.weight, record.name, record.path.as_posix()),
    )

    for record in ordered:
        shard_index = min(range(shard_count), key=lambda index: (loads[index], index))
        shards[shard_index].append(record)
        loads[shard_index] += record.weight

    for shard in shards:
        shard.sort(key=lambda record: (record.name, record.path.as_posix()))
    return shards, loads


def select_packages(records, package_names=None, shard_count=None, shard_index=None):
    """Select explicitly named packages or one deterministic weighted shard."""

    if package_names is not None:
        requested = set(package_names)
        available_names = {record.name for record in records}
        missing = sorted(requested - available_names)
        if missing:
            raise ValueError("Unknown package names: {}".format(" ".join(missing)))
        return sorted(
            (record for record in records if record.name in requested),
            key=lambda record: (record.name, record.path.as_posix()),
        )

    if shard_count is not None:
        shards, loads = _build_shards(records, shard_count)
        print(
            "Selected URL shard {}/{} with weight {}.".format(
                shard_index + 1, shard_count, loads[shard_index]
            )
        )
        return shards[shard_index]

    return sorted(records, key=lambda record: (record.name, record.path.as_posix()))


def check_package_records(records):
    """Validate all selected package records and aggregate failures."""

    valid = True
    failures = []
    for index, record in enumerate(records, 1):
        print("\nNo.{} {}".format(index, record.name))
        if record.error or not record.metadata:
            print("Error: {} ({})".format(record.error, record.path))
            valid = False
            failures.append((record, record.error or "Unable to read package metadata."))
            continue

        try:
            content_valid = json_file_content_check(record.metadata)
            path_valid = file_path_check(record.metadata, record.path)
        except Exception as exc:
            print("Error checking {}: {}".format(record.path, exc))
            valid = False
            failures.append((record, str(exc)))
            continue

        if not content_valid or not path_valid:
            valid = False
            failures.append((record, "URL or metadata validation failed"))

    _report_failed_packages(failures)
    print("\nChecked {} package(s).".format(len(records)))
    return valid


def check_duplicate_package_names(work_root):
    """Compatibility wrapper used by existing callers."""

    return not any(record.error == "Duplicated package name." for record in discover_packages(work_root))


def check_json_file(work_root, package_names=None, shard_count=None, shard_index=None):
    records = discover_packages(work_root)
    try:
        selected = select_packages(records, package_names, shard_count, shard_index)
    except ValueError as exc:
        print(str(exc))
        return False
    return check_package_records(selected)


def positive_integer(value):
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def build_parser():
    parser = argparse.ArgumentParser(
        description="Validate RT-Thread package metadata and GitHub URLs."
    )
    parser.add_argument(
        "--packages",
        nargs="+",
        help="validate only these package names",
    )
    parser.add_argument(
        "--shard-count",
        type=positive_integer,
        help="split all packages into this many weighted shards",
    )
    parser.add_argument(
        "--shard-index",
        type=int,
        help="zero-based shard to validate",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if (args.shard_count is None) != (args.shard_index is None):
        parser.error("--shard-count and --shard-index must be used together")
    if args.packages and args.shard_count is not None:
        parser.error("--packages cannot be combined with sharding")
    if args.shard_count is not None and not 0 <= args.shard_index < args.shard_count:
        parser.error("--shard-index must be between 0 and shard-count - 1")

    determine_url_valid.cache_clear()
    check_branch_exists.cache_clear()
    check_commit_sha_exists.cache_clear()

    work_root = os.getcwd()
    print(work_root)
    if check_json_file(
        work_root,
        package_names=args.packages,
        shard_count=args.shard_count,
        shard_index=args.shard_index,
    ):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
