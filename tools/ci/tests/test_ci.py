import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("packages_ci", REPO_ROOT / "ci.py")
CI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CI)


def package_record(root, name, site_count=1):
    path = root / name / "package.json"
    metadata = {
        "name": name,
        "site": [{} for _ in range(site_count)],
    }
    return CI.PackageRecord(path, metadata)


class UrlValidationTests(unittest.TestCase):
    def setUp(self):
        CI.determine_url_valid.cache_clear()

    def test_reachable_url_is_valid(self):
        response = mock.Mock(status_code=200)
        with mock.patch.object(CI.requests, "get", return_value=response) as get:
            self.assertTrue(CI.determine_url_valid("https://github.com/RT-Thread/packages"))

        get.assert_called_once()
        self.assertEqual(get.call_args.kwargs["timeout"], CI.REQUEST_TIMEOUT_SECONDS)
        response.close.assert_called_once()

    def test_reachable_gitee_url_is_valid(self):
        response = mock.Mock(status_code=200)
        with mock.patch.object(CI.requests, "get", return_value=response) as get:
            self.assertTrue(CI.determine_url_valid("https://gitee.com/Gemsea/lite-type"))

        get.assert_called_once()
        response.close.assert_called_once()

    def test_http_error_is_retried_and_rejected(self):
        response = mock.Mock(status_code=500)
        with mock.patch.object(CI.requests, "get", return_value=response) as get:
            with mock.patch.object(CI.time, "sleep"):
                self.assertFalse(
                    CI.determine_url_valid("https://github.com/RT-Thread/missing")
                )

        self.assertEqual(get.call_count, CI.URL_RETRIES)

    def test_transient_502_can_recover(self):
        responses = [mock.Mock(status_code=502), mock.Mock(status_code=502), mock.Mock(status_code=200)]
        with mock.patch.object(CI.requests, "get", side_effect=responses) as get:
            with mock.patch.object(CI.time, "sleep") as sleep:
                self.assertTrue(CI.determine_url_valid("https://github.com/RT-Thread/recover"))

        self.assertEqual(get.call_count, 3)
        self.assertEqual(sleep.call_args_list, [mock.call(1), mock.call(2)])

    def test_not_found_is_not_retried(self):
        response = mock.Mock(status_code=404)
        with mock.patch.object(CI.requests, "get", return_value=response) as get:
            with mock.patch.object(CI.time, "sleep") as sleep:
                self.assertFalse(CI.determine_url_valid("https://github.com/RT-Thread/missing"))

        get.assert_called_once()
        sleep.assert_not_called()

    def test_unsupported_host_is_rejected_without_request(self):
        with mock.patch.object(CI.requests, "get") as get:
            self.assertFalse(CI.determine_url_valid("https://example.com/pkg.zip"))
        get.assert_not_called()

    def test_lookalike_github_host_is_rejected(self):
        with mock.patch.object(CI.requests, "get") as get:
            self.assertFalse(
                CI.determine_url_valid("https://github.com.evil.invalid/pkg.zip")
            )
        get.assert_not_called()

    def test_lookalike_gitee_host_is_rejected(self):
        with mock.patch.object(CI.requests, "get") as get:
            self.assertFalse(
                CI.determine_url_valid("https://gitee.com.evil.invalid/pkg.zip")
            )
        get.assert_not_called()

    def test_gitee_commit_sha_is_checked_with_gitee_api(self):
        response = mock.Mock(status_code=200)
        with mock.patch.object(CI.requests, "get", return_value=response) as get:
            self.assertTrue(
                CI.check_commit_sha_exists(
                    "https://gitee.com/Gemsea/lite-type.git",
                    "0d4c69927328a936fd316a73e3abee36d499c63f",
                )
            )

        self.assertEqual(
            get.call_args.args[0],
            "https://gitee.com/api/v5/repos/Gemsea/lite-type/commits/"
            "0d4c69927328a936fd316a73e3abee36d499c63f",
        )
        self.assertNotIn("Authorization", get.call_args.kwargs["headers"])

    def test_unsupported_git_url_is_not_passed_to_git(self):
        metadata = {
            "name": "alpha",
            "category": "misc",
            "enable": "PKG_USING_ALPHA",
            "author": {"name": "A", "email": "a@example.com"},
            "license": "MIT",
            "repository": "https://github.com/a/alpha",
            "site": [
                {
                    "version": "latest",
                    "URL": "https://example.com/a/alpha.git",
                    "VER_SHA": "main",
                }
            ],
        }
        with mock.patch.object(
            CI,
            "determine_url_valid",
            side_effect=lambda url: url.startswith("https://github.com/"),
        ):
            with mock.patch.object(CI, "check_branch_exists") as branch_check:
                self.assertFalse(CI.json_file_content_check(metadata))

        branch_check.assert_not_called()


class PackageSelectionTests(unittest.TestCase):
    def test_explicit_package_selection_is_sorted(self):
        root = Path("repo")
        records = [
            package_record(root, "gamma"),
            package_record(root, "alpha"),
            package_record(root, "beta"),
        ]

        selected = CI.select_packages(records, package_names=["gamma", "alpha"])

        self.assertEqual([record.name for record in selected], ["alpha", "gamma"])

    def test_unknown_package_is_rejected(self):
        records = [package_record(Path("repo"), "alpha")]
        with self.assertRaisesRegex(ValueError, "missing"):
            CI.select_packages(records, package_names=["missing"])

    def test_explicit_selection_preserves_duplicate_name_errors(self):
        records = [
            CI.PackageRecord(
                Path("repo/one/package.json"),
                {"name": "duplicate", "site": []},
                "Duplicated package name.",
            ),
            CI.PackageRecord(
                Path("repo/two/package.json"),
                {"name": "duplicate", "site": []},
                "Duplicated package name.",
            ),
        ]

        selected = CI.select_packages(records, package_names=["duplicate"])

        self.assertEqual(len(selected), 2)
        self.assertTrue(all(record.error for record in selected))

    def test_weighted_shards_are_deterministic_and_complete(self):
        root = Path("repo")
        records = [
            package_record(root, "alpha", 8),
            package_record(root, "beta", 5),
            package_record(root, "gamma", 3),
            package_record(root, "delta", 2),
            package_record(root, "epsilon", 1),
            package_record(root, "zeta", 1),
        ]

        shards, loads = CI._build_shards(records, 3)
        repeated, repeated_loads = CI._build_shards(list(reversed(records)), 3)

        self.assertEqual(
            [[record.name for record in shard] for shard in shards],
            [[record.name for record in shard] for shard in repeated],
        )
        self.assertEqual(loads, repeated_loads)
        self.assertEqual(
            sorted(record.name for shard in shards for record in shard),
            sorted(record.name for record in records),
        )
        self.assertLessEqual(max(loads) - min(loads), max(record.weight for record in records))

    def test_weight_ignores_site_entries_without_urls(self):
        record = CI.PackageRecord(
            Path("repo/alpha/package.json"),
            {"name": "alpha", "site": [{"URL": ""}, {}, {"URL": "https://github.com/a/b.git"}]},
        )
        self.assertEqual(record.weight, 2)


class AggregateValidationTests(unittest.TestCase):
    def test_all_selected_packages_are_checked_after_failure(self):
        records = [
            package_record(Path("repo"), "alpha"),
            package_record(Path("repo"), "beta"),
        ]
        with mock.patch.object(
            CI, "json_file_content_check", side_effect=[False, True]
        ) as content_check:
            with mock.patch.object(CI, "file_path_check", return_value=True):
                self.assertFalse(CI.check_package_records(records))

        self.assertEqual(content_check.call_count, 2)

    def test_failed_packages_are_reported_as_annotations_and_summary(self):
        records = [
            package_record(Path("repo"), "broken"),
            package_record(Path("repo"), "healthy"),
        ]
        with mock.patch.object(
            CI, "json_file_content_check", side_effect=[False, True]
        ):
            with mock.patch.object(CI, "file_path_check", return_value=True):
                with mock.patch("builtins.print") as printer:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        summary_path = Path(temp_dir) / "summary.md"
                        with mock.patch.dict(
                            CI.os.environ,
                            {"GITHUB_STEP_SUMMARY": str(summary_path)},
                            clear=False,
                        ):
                            self.assertFalse(CI.check_package_records(records))

                        output = "\n".join(
                            str(call.args[0])
                            for call in printer.call_args_list
                            if call.args
                        )
                        self.assertIn("::error", output)
                        self.assertIn("broken", output)
                        self.assertNotIn("healthy: URL or metadata validation failed", output)
                        self.assertIn("## Failed packages", summary_path.read_text(encoding="utf-8"))

    def test_valid_commit_sha_does_not_print_branch_warning(self):
        metadata = {
            "name": "alpha",
            "category": "misc",
            "enable": "PKG_USING_ALPHA",
            "author": {"name": "A", "email": "a@example.com"},
            "license": "MIT",
            "repository": "https://github.com/a/alpha",
            "site": [
                {
                    "version": "v1",
                    "URL": "https://github.com/a/alpha.git",
                    "VER_SHA": "deadbeef",
                }
            ],
        }
        with mock.patch.object(CI, "determine_url_valid", return_value=True):
            with mock.patch.object(CI, "check_branch_exists", return_value=False):
                with mock.patch.object(CI, "check_commit_sha_exists", return_value=True):
                    with mock.patch("builtins.print") as printer:
                        self.assertTrue(CI.json_file_content_check(metadata))

        output = " ".join(str(call) for call in printer.call_args_list)
        self.assertNotIn("branch 'deadbeef'", output)


class KconfigValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "packages"
        self.package_dir = self.root / "misc" / "sample"
        self.package_dir.mkdir(parents=True)
        (self.root / "misc" / "Kconfig").write_text(
            'menu "misc packages"\n'
            'source "$PKGS_DIR/packages/misc/sample/Kconfig"\n'
            "endmenu\n",
            encoding="utf-8",
        )
        self.metadata = {
            "name": "sample",
            "category": "misc",
            "enable": "PKG_USING_SAMPLE",
        }
        self.package_path = self.package_dir / "package.json"
        self.package_path.write_text(json.dumps(self.metadata), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def record(self) -> object:
        return CI.PackageRecord(self.package_path, self.metadata)

    def write_kconfig(self, content: str) -> None:
        (self.package_dir / "Kconfig").write_text(content, encoding="utf-8")

    def test_valid_kconfig_is_accepted(self) -> None:
        self.write_kconfig(
            'menuconfig PKG_USING_SAMPLE\n'
            '    bool "Sample"\n'
            "    default n\n"
        )

        self.assertEqual(CI.check_package_kconfig(self.record(), self.root), (True, ""))

    def test_missing_kconfig_is_rejected(self) -> None:
        valid, reason = CI.check_package_kconfig(self.record(), self.root)

        self.assertFalse(valid)
        self.assertIn("Kconfig file is missing", reason)

    def test_invalid_kconfig_is_rejected(self) -> None:
        self.write_kconfig('menuconfig PKG_USING_SAMPLE\n    bool "unterminated\n')

        valid, reason = CI.check_package_kconfig(self.record(), self.root)

        self.assertFalse(valid)
        self.assertIn("Kconfig parse failed", reason)

    def test_enable_symbol_must_be_defined(self) -> None:
        self.write_kconfig('menuconfig PKG_USING_OTHER\n    bool "Other"\n')

        valid, reason = CI.check_package_kconfig(self.record(), self.root)

        self.assertFalse(valid)
        self.assertIn("PKG_USING_SAMPLE", reason)

    def test_category_kconfig_must_source_package(self) -> None:
        (self.root / "misc" / "Kconfig").write_text(
            'menu "misc packages"\nendmenu\n', encoding="utf-8"
        )
        self.write_kconfig('menuconfig PKG_USING_SAMPLE\n    bool "Sample"\n')

        valid, reason = CI.check_package_kconfig(self.record(), self.root)

        self.assertFalse(valid)
        self.assertIn("category Kconfig does not source", reason)

    def test_discovery_keeps_invalid_json_for_its_shard(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            valid_dir = root / "alpha"
            invalid_dir = root / "broken"
            valid_dir.mkdir()
            invalid_dir.mkdir()
            (valid_dir / "package.json").write_text(
                '{"name":"alpha","site":[]}', encoding="utf-8"
            )
            (invalid_dir / "package.json").write_text("{", encoding="utf-8")

            records = CI.discover_packages(root)

        self.assertEqual(len(records), 2)
        self.assertEqual(sum(record.error is not None for record in records), 1)


class ArgumentValidationTests(unittest.TestCase):
    def test_shard_arguments_must_be_paired(self):
        with self.assertRaises(SystemExit):
            CI.main(["--shard-count", "8"])

    def test_package_and_shard_modes_are_mutually_exclusive(self):
        with self.assertRaises(SystemExit):
            CI.main(
                [
                    "--packages",
                    "alpha",
                    "--shard-count",
                    "8",
                    "--shard-index",
                    "0",
                ]
            )


if __name__ == "__main__":
    unittest.main()
