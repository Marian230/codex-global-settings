import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import bootstrap_shared_settings as bootstrap

COMMIT = "1" * 40


class CheckSharedSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.target = self.root / "installed"
        self.source.mkdir()
        self.target.mkdir()
        self.payload = {name: ("pinned " + name + "\n").encode()
                        for name in bootstrap.FILES}
        for directory in (self.source, self.target):
            for name, data in self.payload.items():
                path = directory / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        self.hashes = {name: bootstrap.digest(data)
                       for name, data in self.payload.items()}
        self.attestation = self.root / "export.json"
        self.attestation.write_text(json.dumps({"commit": COMMIT, "files": self.hashes}))
        self.manifest = {"version": 1, "repository": bootstrap.REPOSITORY,
                         "commit": COMMIT, "files": dict(self.hashes),
                         "source_files": dict(self.hashes),
                         "load_probe": "a" * 32, "startup_probe": None}
        self.write_manifest()

    def write_manifest(self):
        (self.target / bootstrap.MANIFEST).write_text(json.dumps(self.manifest))

    def check(self):
        return bootstrap.check(self.source, self.target, COMMIT, self.attestation)

    def snapshot(self):
        # File bytes, mtimes and directory listing catch repairs, lock creation,
        # probe changes and missing-home creation; native/auth paths are excluded.
        return {str(path.relative_to(self.root)):
                (path.is_dir(), path.stat().st_mtime_ns,
                 None if path.is_dir() else path.read_bytes())
                for path in self.root.rglob("*")}

    def test_valid_check_is_read_only_and_does_not_disclose_probes(self):
        before = self.snapshot()
        with mock.patch.object(bootstrap, "atomic_write", side_effect=AssertionError("write")), \
             mock.patch.object(bootstrap.os, "open", side_effect=AssertionError("lock")), \
             mock.patch.object(bootstrap.secrets, "token_hex", side_effect=AssertionError("probe")), \
             mock.patch.object(Path, "mkdir", side_effect=AssertionError("mkdir")):
            result = self.check()
        self.assertEqual(before, self.snapshot())
        self.assertEqual(result["status"], "FILES_VERIFIED")
        self.assertEqual(result["verified_files"], 13)
        self.assertEqual(result["source_hashes_verified"], 13)
        self.assertEqual(result["installed_hashes_verified"], 13)
        self.assertTrue(result["read_only"])
        self.assertFalse(result["policy_load_proven"])
        self.assertNotIn(self.manifest["load_probe"], json.dumps(result))

    def test_missing_snapshot_is_not_created(self):
        self.target = self.root / "absent" / "snapshot"
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "manifest missing"):
            self.check()
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.target.parent.exists())

    def test_missing_or_changed_file_is_not_repaired(self):
        for change in ("missing", "changed"):
            with self.subTest(change=change):
                path = self.target / "AGENTS.md"
                path.write_bytes(self.payload["AGENTS.md"])
                if change == "missing":
                    path.unlink()
                else:
                    path.write_bytes(b"locally changed or interrupted update")
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, "managed file"):
                    self.check()
                self.assertEqual(before, self.snapshot())

    def test_manifest_commit_source_and_installed_hashes_are_checked(self):
        original = dict(self.manifest)
        changes = (("commit", "2" * 40),
                   ("source_files", dict(self.hashes, **{"AGENTS.md": "0" * 64})),
                   ("files", dict(self.hashes, **{"AGENTS.md": "0" * 64})))
        for key, value in changes:
            with self.subTest(key=key):
                self.manifest = dict(original, **{key: value})
                self.write_manifest()
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, "mismatch|hashes differ"):
                    self.check()
                self.assertEqual(before, self.snapshot())

    def test_forged_manifest_cannot_authorize_changed_installed_bytes(self):
        changed = b"forged policy"
        (self.target / "AGENTS.md").write_bytes(changed)
        self.manifest["files"]["AGENTS.md"] = bootstrap.digest(changed)
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "installed hashes differ"):
            self.check()

    def test_malformed_or_inexact_manifest_is_refused(self):
        candidates = [[], None, {**self.manifest, "files": []},
                      {**self.manifest, "startup_probe": 123},
                      {**self.manifest, "version": True},
                      {**self.manifest, "source_files": {**self.hashes, "extra": "0" * 64}},
                      {**self.manifest, "files": {k: v for k, v in self.hashes.items()
                                                 if k != "AGENTS.md"}}]
        for value in candidates:
            with self.subTest(value=value):
                (self.target / bootstrap.MANIFEST).write_text(json.dumps(value))
                with self.assertRaisesRegex(ValueError, "invalid existing ownership manifest"):
                    self.check()

    def test_lock_is_preserved_and_refused(self):
        lock = self.target / bootstrap.LOCK
        lock.write_bytes(b"active or stale; checker must not remove")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "lock present"):
            self.check()
        self.assertEqual(before, self.snapshot())

    def test_symlink_target_file_or_ancestor_is_refused(self):
        path = self.target / "AGENTS.md"
        path.unlink()
        try:
            path.symlink_to(self.source / "AGENTS.md")
        except OSError:
            self.skipTest("symlink privilege unavailable")
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.check()
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        self.target = alias / "installed"
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.check()

    def test_source_symlink_is_refused(self):
        alias = self.root / "alias"
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except OSError:
            self.skipTest("symlink privilege unavailable")
        self.source = alias / "source"
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.check()

    def test_manifest_and_attestation_symlinks_are_refused(self):
        manifest_path = self.target / bootstrap.MANIFEST
        original = self.root / "manifest-copy.json"
        original.write_bytes(manifest_path.read_bytes())
        manifest_path.unlink()
        try:
            manifest_path.symlink_to(original)
        except OSError:
            self.skipTest("symlink privilege unavailable")
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.check()
        manifest_path.unlink()
        self.write_manifest()
        alias = self.root / "attestation-link.json"
        alias.symlink_to(self.attestation)
        self.attestation = alias
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.check()

    def test_lock_or_manifest_change_during_inspection_is_refused(self):
        original_read = Path.read_bytes
        last_file = self.target / bootstrap.FILES[-1]
        for change in ("lock", "manifest"):
            with self.subTest(change=change):
                self.write_manifest()
                lock = self.target / bootstrap.LOCK
                if lock.exists():
                    lock.unlink()
                def concurrent_read(path):
                    data = original_read(path)
                    if path == last_file:
                        if change == "lock":
                            lock.write_bytes(b"concurrent installer")
                        else:
                            changed = dict(self.manifest, load_probe="b" * 32)
                            (self.target / bootstrap.MANIFEST).write_text(json.dumps(changed))
                    return data
                with mock.patch.object(Path, "read_bytes", concurrent_read):
                    with self.assertRaisesRegex(ValueError, "lock present|manifest changed"):
                        self.check()
                if change == "lock":
                    self.assertEqual(lock.read_bytes(), b"concurrent installer")

    def test_probe_install_remains_compatible_and_suffix_cannot_be_forged(self):
        # One disposable fixture verifies the shared suffix builder preserves
        # installer/checker compatibility; this is not a native install.
        self.target = self.root / "probe-install"
        bootstrap.install(self.source, self.target, COMMIT, self.attestation,
                          instruction_probe=True)
        before = self.snapshot()
        result = self.check()
        self.assertEqual(before, self.snapshot())
        self.assertFalse(result["policy_load_proven"])
        self.manifest = json.loads((self.target / bootstrap.MANIFEST).read_text())
        self.assertNotIn(self.manifest["startup_probe"], json.dumps(result))
        data = (self.target / "AGENTS.md").read_bytes() + b"extra injected rule"
        (self.target / "AGENTS.md").write_bytes(data)
        self.manifest["files"]["AGENTS.md"] = bootstrap.digest(data)
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "installed hashes differ"):
            self.check()

    def test_git_check_uses_canonical_lf_bytes_for_crlf_worktree(self):
        for name, data in self.payload.items():
            (self.source / name).write_bytes(data.replace(b"\n", b"\r\n"))
        def git(args):
            if args[-2:] == ["rev-parse", "HEAD"]:
                return (COMMIT + "\n").encode()
            return self.payload[args[-1].split(":", 1)[1]]
        with mock.patch.object(bootstrap.subprocess, "check_output", side_effect=git):
            result = bootstrap.check(self.source, self.target, COMMIT)
        self.assertEqual(result["installed_hashes_verified"], 13)

    def test_cli_check_and_incompatible_flags(self):
        command = [sys.executable, str(Path(bootstrap.__file__)),
                   "--source-dir", str(self.source), "--target-home", str(self.target),
                   "--expected-commit", COMMIT, "--source-commit-file", str(self.attestation),
                   "--check-only"]
        before = self.snapshot()
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "FILES_VERIFIED")
        for flag in ("--update-managed", "--instruction-probe"):
            result = subprocess.run(command + [flag], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertIn("cannot be combined", result.stderr)
            self.assertEqual(result.stdout, "")
        self.assertEqual(before, self.snapshot())

    def test_nonobject_export_attestation_is_cleanly_refused_without_writes(self):
        for value in (None, [], "not an object", 123):
            with self.subTest(value=value):
                self.attestation.write_text(json.dumps(value))
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, "offline export commit/hash attestation mismatch"):
                    self.check()
                self.assertEqual(before, self.snapshot())


if __name__ == "__main__":
    unittest.main()
