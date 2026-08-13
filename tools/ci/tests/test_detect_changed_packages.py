from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "detect_changed_packages.py"


class DetectChangedPackagesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp_dir.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Test User")
        self.git("config", "user.email", "test@example.invalid")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )
        return result.stdout.strip()

    def write(self, relative_path: str, content: str) -> None:
        path = self.repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def package(self, relative_path: str, name: str) -> None:
        self.write(relative_path + "/package.json", json.dumps({"name": name}))

    def commit(self, message: str) -> str:
        self.git("add", "--all")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def detect(self, base: str, head: str) -> str:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), base, head, "--repo-root", str(self.repo)],
            cwd=self.repo,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )
        return result.stdout

    def test_nested_packages_use_nearest_name_and_dedupe(self) -> None:
        self.package("outer", "outer")
        self.package("outer/inner", "inner")
        self.write("outer/inner/first.c", "old")
        self.write("outer/second.c", "old")
        self.write("README.md", "old")
        base = self.commit("base")

        self.write("outer/inner/first.c", "new")
        self.write("outer/inner/second.c", "new")
        self.write("outer/second.c", "new")
        self.write("README.md", "new")
        head = self.commit("head")

        self.assertEqual(self.detect(base, head), "inner outer\n")

    def test_renamed_and_deleted_paths_are_mapped(self) -> None:
        self.package("alpha", "alpha")
        self.package("beta", "beta")
        self.write("alpha/src/moved.c", "same content")
        self.write("beta/src/removed.c", "to remove")
        base = self.commit("base")

        self.git("mv", "alpha/src/moved.c", "beta/src/moved.c")
        self.git("rm", "beta/src/removed.c")
        head = self.commit("head")

        self.assertEqual(self.detect(base, head), "alpha beta\n")

    def test_deleted_package_metadata_produces_empty_value(self) -> None:
        self.package("gone", "gone")
        self.write("gone/file.c", "old")
        base = self.commit("base")

        self.git("rm", "gone/package.json")
        head = self.commit("head")

        self.assertEqual(self.detect(base, head), "\n")

    def run_detector(self, base: str, head: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), base, head, "--repo-root", str(self.repo)],
            cwd=self.repo,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )

    def test_malformed_current_package_metadata_fails(self) -> None:
        self.package("broken", "broken")
        self.write("broken/file.c", "old")
        base = self.commit("base")

        self.write("broken/package.json", "{")
        head = self.commit("head")

        result = self.run_detector(base, head)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid JSON", result.stderr)

    def test_invalid_package_name_fails(self) -> None:
        self.package("unsafe", "unsafe")
        self.write("unsafe/file.c", "old")
        base = self.commit("base")

        self.write("unsafe/package.json", json.dumps({"name": "unsafe name"}))
        head = self.commit("head")

        result = self.run_detector(base, head)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid package name", result.stderr)



if __name__ == "__main__":
    unittest.main()
