"""Copy the current personal settings; retained CLI options support old setup scripts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROLES = ("sol", "astra", "luna")
FILES = ("AGENTS.md", "global-preferences.toml") + tuple(
    "agents/" + name + ".toml" for name in ROLES) + tuple(
    name + ".config.toml" for name in ROLES)
OLD_ROLES = ("sol_high", "sol_xhigh", "sol_medium", "luna_xhigh_standard",
             "luna_xhigh_fast", "astra_high_approved")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--target-home", required=True)
    parser.add_argument("--expected-commit")
    parser.add_argument("--source-commit-file")
    parser.add_argument("--update-managed", action="store_true")
    parser.add_argument("--instruction-probe", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    source, target = Path(args.source_dir).resolve(), Path(args.target_home).resolve()
    if args.source_commit_file:
        commit = json.loads(Path(args.source_commit_file).read_text(encoding="utf-8"))["commit"]
    else:
        commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if args.expected_commit and commit != args.expected_commit:
        raise ValueError("Source commit differs from the requested revision")
    hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in FILES}
    if args.check_only:
        ok = all((target / name).is_file() and
                 hashlib.sha256((target / name).read_bytes()).hexdigest() == value
                 for name, value in hashes.items())
        print(json.dumps({"status": "PASS" if ok else "FAIL", "commit": commit, "files": hashes}))
        return 0 if ok else 1
    target.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source != target:
            shutil.copyfile(source / name, destination)
    for role in OLD_ROLES:
        for relative in ("agents/" + role + ".toml", role + ".config.toml"):
            (target / relative).unlink(missing_ok=True)
    manifest = {"version": 2, "commit": commit, "files": hashes, "source_files": hashes}
    (target / "shared-settings-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "commit": commit, "files": hashes}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
