"""Offline, allowlisted portable policy install or read-only check. Never modifies native config."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile

ROLES = ("sol_high", "sol_xhigh", "sol_medium", "luna_xhigh_standard",
         "luna_xhigh_fast", "astra_high_approved")
FILES = ("AGENTS.md",) + tuple("agents/" + n + ".toml" for n in ROLES) + tuple(
    n + ".config.toml" for n in ROLES)
MANIFEST = "shared-settings-manifest.json"
LOCK = ".shared-settings-install.lock"
REPOSITORY = "https://github.com/Marian230/codex-global-settings"

def digest(data):
    return hashlib.sha256(data).hexdigest()

def checked_path(root, relative):
    candidate = root / relative
    # Include ancestors ABOVE root, before any mkdir/read: a root such as
    # /tmp/alias/home is unsafe if /tmp/alias redirects outside the given tree.
    for path in (candidate, *candidate.parents):
        if path.is_symlink():
            raise ValueError("symlink destination/source parent: " + str(path))
    return candidate

def read_source(source_dir, expected_commit, source_commit_file=None):
    if not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        raise ValueError("expected commit must be a full lowercase Git SHA")
    source = Path(source_dir).expanduser().absolute()
    payload = {name: checked_path(source, name).read_bytes() for name in FILES}
    if source_commit_file:
        # Trusted export attestation: integrity, not independent provenance proof.
        attestation = json.loads(Path(source_commit_file).read_text(encoding="utf-8"))
        hashes = {name: digest(data) for name, data in payload.items()}
        if (not isinstance(attestation, dict)
                or attestation.get("commit") != expected_commit
                or attestation.get("files") != hashes):
            raise ValueError("offline export commit/hash attestation mismatch")
    else:
        def git(*args):
            return subprocess.check_output(["git", "-C", str(source), *args])
        actual = git("rev-parse", "HEAD").decode("ascii").strip()
        if actual != expected_commit:
            raise ValueError("source checkout commit mismatch")
        for name, data in payload.items():
            canonical = git("show", expected_commit + ":" + name)
            # Windows text checkouts can use CRLF while committed blobs use LF.
            # Accept only that exact EOL transformation in these known text
            # paths; installs always use pinned canonical blob bytes.
            if data != canonical and data.replace(b"\r\n", b"\n") != canonical:
                raise ValueError("source file differs from pinned commit: " + name)
            payload[name] = canonical
    return payload

def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".shared-settings-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def validate_manifest(manifest):
    if (not isinstance(manifest, dict)
            or type(manifest.get("version")) is not int or manifest["version"] != 1
            or manifest.get("repository") != REPOSITORY
            or any(not isinstance(manifest.get(key), dict)
                   or set(manifest[key]) != set(FILES)
                   or any(not isinstance(value, str)
                          or not re.fullmatch(r"[0-9a-f]{64}", value)
                          for value in manifest[key].values())
                   for key in ("files", "source_files"))
            or any(not isinstance(manifest.get(key), str)
                   or not re.fullmatch(pattern, manifest[key])
                   for key, pattern in (("commit", r"[0-9a-f]{40}"),
                                        ("load_probe", r"[0-9a-f]{32}")))
            or manifest.get("startup_probe") is not None
               and (not isinstance(manifest["startup_probe"], str)
                    or not re.fullmatch(r"[0-9a-f]{32}", manifest["startup_probe"]))):
        raise ValueError("invalid existing ownership manifest")
    return manifest

def with_startup_probe(payload, startup_probe):
    payload = dict(payload)
    if startup_probe:
        payload["AGENTS.md"] += ("\n<!-- BEGIN installation-only startup diagnostic -->\n"
            "If the current direct user request is exactly 'Verify shared-settings startup.', "
            "return SHARED_SETTINGS_RECEIPT:" + startup_probe +
            " as the first response before tools. This receipt proves only that this diagnostic "
            "instruction was available; it does not prove routing or runtime profile registration.\n"
            "<!-- END installation-only startup diagnostic -->\n").encode("utf-8")
    return payload

def check(source_dir, target_home, expected_commit, source_commit_file=None):
    # This path deliberately never calls install(), mkdir(), atomic_write(),
    # lock acquisition or probe generation: a missing snapshot stays missing.
    if source_commit_file:
        attestation = Path(source_commit_file).expanduser().absolute()
        checked_path(attestation.parent, attestation.name)
    payload = read_source(source_dir, expected_commit, source_commit_file)
    target = Path(target_home).expanduser().absolute()
    checked_path(target, ".")
    lock = checked_path(target, LOCK)
    if lock.exists():
        raise ValueError("installation lock present; state cannot be verified")
    manifest_path = checked_path(target, MANIFEST)
    if not manifest_path.is_file():
        raise ValueError("ownership manifest missing")
    manifest_bytes = manifest_path.read_bytes()
    manifest = validate_manifest(json.loads(manifest_bytes))
    if manifest["commit"] != expected_commit:
        raise ValueError("installed commit mismatch")
    source_hashes = {name: digest(data) for name, data in payload.items()}
    if manifest["source_files"] != source_hashes:
        raise ValueError("manifest source hashes differ from pinned source")
    payload = with_startup_probe(payload, manifest.get("startup_probe"))
    hashes = {name: digest(data) for name, data in payload.items()}
    if manifest["files"] != hashes:
        raise ValueError("manifest installed hashes differ from expected policy/profile bytes")
    for name, data in payload.items():
        path = checked_path(target, name)
        if not path.is_file():
            raise ValueError("managed file missing: " + name)
        if path.read_bytes() != data:
            raise ValueError("managed file differs from pinned source: " + name)
    # Detect a concurrent installation or manifest replacement during inspection.
    if checked_path(target, LOCK).exists():
        raise ValueError("installation lock present; state cannot be verified")
    if checked_path(target, MANIFEST).read_bytes() != manifest_bytes:
        raise ValueError("ownership manifest changed during check")
    return {"status": "FILES_VERIFIED", "commit": expected_commit,
            "target_home": str(target), "verified_files": len(FILES),
            "source_hashes_verified": len(source_hashes),
            "installed_hashes_verified": len(hashes),
            "read_only": True, "native_config_modified": False,
            "policy_load_proven": False}

def install(source_dir, target_home, expected_commit, source_commit_file=None,
            update_managed=False, instruction_probe=False):
    payload = read_source(source_dir, expected_commit, source_commit_file)
    target = Path(target_home).expanduser().absolute()
    checked_path(target, ".")
    target.mkdir(parents=True, exist_ok=True)
    lock = checked_path(target, LOCK)
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        manifest_path = checked_path(target, MANIFEST)
        previous = None
        if manifest_path.exists():
            previous = validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
        source_hashes = {name: digest(data) for name, data in payload.items()}
        startup_probe = previous.get("startup_probe") if previous else None
        if instruction_probe and not startup_probe:
            startup_probe = secrets.token_hex(16)
        payload = with_startup_probe(payload, startup_probe)
        hashes = {name: digest(data) for name, data in payload.items()}
        changed = []
        for name, data in payload.items():
            path = checked_path(target, name)
            if path.exists():
                actual = digest(path.read_bytes())
                if previous is None:
                    raise ValueError("unmanaged destination conflict: " + name)
                if actual != previous["files"][name]:
                    raise ValueError("managed file locally modified: " + name)
                if actual != hashes[name]:
                    if not update_managed:
                        raise ValueError("managed update requires --update-managed: " + name)
                    changed.append(name)
            else:
                if previous is not None:
                    raise ValueError("managed file missing: " + name)
                changed.append(name)
        if previous and previous["commit"] != expected_commit and not update_managed:
            raise ValueError("commit update requires --update-managed")
        manifest = {"version": 1, "repository": REPOSITORY,
                    "commit": expected_commit, "files": hashes, "source_files": source_hashes,
                    "startup_probe": startup_probe,
                    "load_probe": previous["load_probe"] if previous else secrets.token_hex(16)}
        # Preflight completes before any policy/profile mutation. Each replace is
        # atomic; the set is not a filesystem transaction. An interrupted run
        # with mixed old/new files fails closed and requires explicit recovery.
        for name in changed:
            atomic_write(target / name, payload[name])
        encoded = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
        if previous != manifest:
            atomic_write(manifest_path, encoded)
        return {"status": "FILES_AVAILABLE", "commit": expected_commit,
                "target_home": str(target), "installed_files": len(FILES),
                "changed_files": changed, "native_config_modified": False,
                "policy_load_proven": False}
    finally:
        lock.unlink()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--target-home", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--source-commit-file", help="Trusted offline export JSON: commit and files SHA256")
    parser.add_argument("--update-managed", action="store_true")
    parser.add_argument("--instruction-probe", action="store_true", help="Append installation-only startup diagnostic to the target AGENTS, keeping source untouched")
    parser.add_argument("--check-only", action="store_true", help="Verify existing installed files and manifest without writing, repairing or proving policy loading")
    args = parser.parse_args()
    if args.check_only and (args.update_managed or args.instruction_probe):
        parser.error("--check-only cannot be combined with --update-managed or --instruction-probe")
    try:
        if args.check_only:
            result = check(args.source_dir, args.target_home, args.expected_commit,
                           args.source_commit_file)
        else:
            result = install(args.source_dir, args.target_home,
                             args.expected_commit, args.source_commit_file,
                             args.update_managed, args.instruction_probe)
        print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        action = "check" if args.check_only else "install"
        parser.exit(1, "shared settings " + action + " refused: " + str(error) + "\n")

if __name__ == "__main__":
    main()
