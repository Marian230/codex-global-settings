import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import shutil
import subprocess
import sys
from unittest import mock

import bootstrap_shared_settings as bootstrap

COMMIT = "1" * 40

class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.target = self.root / "home"
        self.source.mkdir()
        for name in bootstrap.FILES:
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("source " + name + "\n").encode())
        self.attestation = self.root / "export.json"
        self.attest()

    def attest(self, commit=COMMIT):
        self.attestation.write_text(json.dumps({"commit": commit, "files": {
            name: bootstrap.digest((self.source / name).read_bytes())
            for name in bootstrap.FILES}}), encoding="utf-8")

    def install(self, commit=COMMIT, update=False):
        return bootstrap.install(self.source, self.target, commit,
                                 self.attestation, update)

    def test_new_home_and_idempotence(self):
        first = self.install()
        self.assertEqual(first["status"], "FILES_AVAILABLE")
        self.assertFalse(first["policy_load_proven"])
        before = {str(p.relative_to(self.target)): (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.target.rglob("*") if p.is_file()}
        second = self.install()
        after = {str(p.relative_to(self.target)): (p.read_bytes(), p.stat().st_mtime_ns)
                 for p in self.target.rglob("*") if p.is_file()}
        self.assertEqual(second["changed_files"], [])
        self.assertEqual(before, after)
        self.assertEqual(set(before), set(bootstrap.FILES) | {bootstrap.MANIFEST})

    def test_no_machine_config_or_credentials_changes(self):
        self.target.mkdir()
        sentinel = {"config.toml": b"model = 'platform-model'\n", "auth.json": b"sentinel"}
        for name, data in sentinel.items():
            (self.target / name).write_bytes(data)
        self.install()
        self.assertEqual(sentinel, {name: (self.target / name).read_bytes() for name in sentinel})
        self.assertNotIn("global-preferences.toml", bootstrap.FILES)

    def test_optional_startup_probe_only_changes_target_policy(self):
        source_policy = (self.source / "AGENTS.md").read_bytes()
        bootstrap.install(self.source, self.target, COMMIT, self.attestation,
                          instruction_probe=True)
        manifest = json.loads((self.target / bootstrap.MANIFEST).read_text())
        receipt = ("SHARED_SETTINGS_RECEIPT:" + manifest["startup_probe"]).encode()
        self.assertIn(receipt, (self.target / "AGENTS.md").read_bytes())
        self.assertEqual((self.source / "AGENTS.md").read_bytes(), source_policy)
        self.assertEqual(manifest["source_files"]["AGENTS.md"], bootstrap.digest(source_policy))
        self.assertNotEqual(manifest["files"]["AGENTS.md"], manifest["source_files"]["AGENTS.md"])
        self.assertEqual(self.install()["changed_files"], [])

    def test_unmanaged_conflict_refuses_before_any_write(self):
        self.target.mkdir()
        (self.target / "sol_high.config.toml").write_bytes(b"existing")
        with self.assertRaisesRegex(ValueError, "unmanaged destination conflict"):
            self.install()
        self.assertEqual(list(self.target.iterdir()), [self.target / "sol_high.config.toml"])

    def test_managed_update_requires_flag_and_old_hashes(self):
        self.install()
        original = (self.target / "AGENTS.md").read_bytes()
        (self.source / "AGENTS.md").write_bytes(b"new policy\n")
        next_commit = "2" * 40
        self.attest(next_commit)
        with self.assertRaisesRegex(ValueError, "requires --update-managed"):
            self.install(next_commit)
        self.assertEqual((self.target / "AGENTS.md").read_bytes(), original)
        result = self.install(next_commit, True)
        self.assertEqual(result["changed_files"], ["AGENTS.md"])
        (self.target / "agents/sol_high.toml").write_bytes(b"local edit")
        with self.assertRaisesRegex(ValueError, "locally modified"):
            self.install(next_commit, True)

    def test_attestation_hash_or_commit_mismatch_refuses(self):
        (self.source / "AGENTS.md").write_bytes(b"unexpected")
        with self.assertRaisesRegex(ValueError, "attestation mismatch"):
            self.install()
        self.assertFalse(self.target.exists())
        self.attest("3" * 40)
        with self.assertRaisesRegex(ValueError, "attestation mismatch"):
            self.install()

    def test_missing_managed_file_fails_closed(self):
        self.install()
        (self.target / "AGENTS.md").unlink()
        with self.assertRaisesRegex(ValueError, "managed file missing"):
            self.install(update=True)

    def test_symlink_directory_cannot_redirect_install(self):
        self.target.mkdir()
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        try:
            (self.target / "agents").symlink_to(elsewhere, target_is_directory=True)
        except OSError:
            self.skipTest("symlink privilege unavailable")
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.install()
        self.assertEqual(list(elsewhere.iterdir()), [])
        self.assertFalse((self.target / "AGENTS.md").exists())

    def test_symlink_ancestor_above_target_root_is_rejected_before_mkdir(self):
        outside = self.root / "outside"
        outside.mkdir()
        alias = self.root / "alias"
        try:
            alias.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("symlink privilege unavailable")
        with self.assertRaisesRegex(ValueError, "symlink"):
            bootstrap.install(self.source, alias / "home", COMMIT, self.attestation)
        self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_ancestor_above_source_root_is_rejected_before_read(self):
        alias = self.root / "alias"
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except OSError:
            self.skipTest("symlink privilege unavailable")
        with self.assertRaisesRegex(ValueError, "symlink"):
            bootstrap.install(alias / "source", self.target, COMMIT, self.attestation)
        self.assertFalse(self.target.exists())

    def test_lock_prevents_concurrent_installer(self):
        self.target.mkdir()
        (self.target / bootstrap.LOCK).write_bytes(b"active")
        with self.assertRaises(FileExistsError):
            self.install()
        self.assertEqual((self.target / bootstrap.LOCK).read_bytes(), b"active")

    def test_git_source_checks_head_and_blob_bytes(self):
        def git_output(args):
            if args[-2:] == ["rev-parse", "HEAD"]:
                return (COMMIT + "\n").encode()
            name = args[-1].split(":", 1)[1]
            return (self.source / name).read_bytes()
        with mock.patch.object(bootstrap.subprocess, "check_output", side_effect=git_output):
            result = bootstrap.read_source(self.source, COMMIT)
            self.assertEqual(set(result), set(bootstrap.FILES))
        with mock.patch.object(bootstrap.subprocess, "check_output", return_value=b"0" * 40 + b"\n"):
            with self.assertRaisesRegex(ValueError, "checkout commit mismatch"):
                bootstrap.read_source(self.source, COMMIT)

class VerifierTests(unittest.TestCase):
    def optimized_verifier(self, mutation=None, effective_capacity=10):
        base = Path(__file__).parents[1]
        script = base / "scripts-shared/verify_shared_settings.py"
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            home.mkdir()
            for name in bootstrap.FILES:
                destination = home / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(base / name, destination)
            (home / "config.toml").write_text('[agents]\nmax_concurrent_threads_per_session = 10\ndefault_subagent_model = "gpt-6.1-sol"\ndefault_subagent_reasoning_effort = "high"\n')
            if mutation == "wrong_profile":
                (home / "agents/sol_high.toml").write_text('model = "wrong-model"\nmodel_reasoning_effort = "high"\nservice_tier = "default"\n')
            elif mutation == "empty_agents":
                (home / "AGENTS.md").write_text("")
            # Stub the config transport only. Real main() parses the fixture and
            # runs every validation under an actually optimized Python process.
            runner = ('import importlib.util,sys\n'
                      'script,home,capacity=sys.argv[1:]\n'
                      'spec=importlib.util.spec_from_file_location("verifier",script)\n'
                      'mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)\n'
                      'mod.effective_config=lambda *args: {"agents": {"max_concurrent_threads_per_session": int(capacity), "default_subagent_model": "gpt-6.1-sol", "default_subagent_reasoning_effort": "high"}}\n'
                      'sys.argv=[script,"--config-home",home,"--codex","unused","--cwd",home]\n'
                      'mod.main()\n')
            results = []
            for interpreter_args, additions in ((["-O"], {}), ([], {"PYTHONOPTIMIZE": "1"})):
                env = os.environ.copy()
                env.update(additions)
                results.append(subprocess.run([sys.executable, *interpreter_args, "-c", runner,
                                               str(script), str(home), str(effective_capacity)],
                                              capture_output=True, text=True, env=env, timeout=10))
            return results

    def test_optimized_verifier_valid_fixture_passes(self):
        for result in self.optimized_verifier():
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "PASS")

    def test_optimized_verifier_rejects_wrong_profile(self):
        for result in self.optimized_verifier(mutation="wrong_profile"):
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("profile differs", result.stderr)
            self.assertNotIn('"PASS"', result.stdout)

    def test_optimized_verifier_rejects_empty_agents(self):
        for result in self.optimized_verifier(mutation="empty_agents"):
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("AGENTS.md empty", result.stderr)
            self.assertNotIn('"PASS"', result.stdout)

    def test_optimized_verifier_rejects_effective_zero_capacity(self):
        for result in self.optimized_verifier(effective_capacity=0):
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("effective server: worker capacity differs", result.stderr)
            self.assertNotIn('"PASS"', result.stdout)

    def verifier(self):
        script = Path(__file__).parents[1] / "scripts-shared/verify_shared_settings.py"
        spec = importlib.util.spec_from_file_location("shared_verifier", script)
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        return verifier

    def test_windows_interop_requires_native_path_and_deduplicates_wslenv(self):
        verifier = self.verifier()
        with mock.patch.object(verifier.os, "name", "posix"):
            with self.assertRaisesRegex(ValueError, "requires explicit"):
                verifier.server_environment("/mnt/c/bin/codex.exe", "/mnt/c/Users/marian/.codex")
            with mock.patch.dict(os.environ, {"WSLENV": "OTHER/p:CODEX_HOME/p:CODEX_HOME/w"}):
                env = verifier.server_environment("/mnt/c/bin/codex.exe", "/mnt/c/Users/marian/.codex", "C:\\Users\\marian\\.codex")
            self.assertEqual(env["CODEX_HOME"], "C:\\Users\\marian\\.codex")
            self.assertEqual(env["WSLENV"], "OTHER/p:CODEX_HOME/w")

    def test_explicit_config_home_passed_to_app_server(self):
        verifier = self.verifier()
        process = mock.Mock()
        process.stdout = io.StringIO(json.dumps({"id": 1, "result": {}}) + "\n" +
                                      json.dumps({"id": 2, "result": {"config": {
                                          "model": "home-bound-model", "agents": {}}}}) + "\n")
        process.stdin = io.StringIO()
        with tempfile.TemporaryDirectory() as temp:
            selected = Path(temp) / "selected-home"
            with mock.patch.dict(os.environ, {"CODEX_HOME": "wrong-home", "TEST_KEEP": "preserved"}):
                with mock.patch.object(verifier.subprocess, "Popen", return_value=process) as popen:
                    result = verifier.effective_config("codex", temp, selected)
                child = popen.call_args.kwargs["env"]
                self.assertEqual(child["CODEX_HOME"], str(selected.resolve()))
                self.assertEqual(child["TEST_KEEP"], "preserved")
                self.assertEqual(os.environ["CODEX_HOME"], "wrong-home")
            self.assertEqual(result["model"], "home-bound-model")
            self.assertEqual(popen.call_args.args[0], ["codex", "app-server", "--strict-config"])

if __name__ == "__main__":
    unittest.main()
