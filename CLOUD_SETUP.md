# Portable cloud setup and honest loading evidence

GitHub `https://github.com/Marian230/codex-global-settings` is the durable published
source. Windows `C:\Users\marian\.codex` is the authenticated working checkout
and push route. Native Windows/WSL configuration and secrets remain platform-local.

`cloud/WORK_ACCOUNT_LOADER.txt` is the persistent account/project instruction
loader entrypoint, where that surface supports saved instructions. It directs a
new session to read current GitHub AGENTS and role files and report the source and
loading evidence. It cannot register custom TOML profiles, force inference tier
or raise server capacity. Saving a loader is distinct from proving the platform
injected it into a fresh session; test that separately.

## Install once in a supported published environment

Obtain a checkout at a verified full commit through an authorized GitHub read or
Git route. Run the offline installer during environment setup, before the new
model session starts:

```sh
python cloud/bootstrap_shared_settings.py --source-dir /path/to/checkout --target-home /path/to/native-codex-home --expected-commit FULL_COMMIT_SHA
```

The installer verifies checkout HEAD and the 13 selected blobs against that
commit. Worktree text must match its pinned blob exactly, or match after only
CRLF-to-LF normalization; any other edit is refused. Installed bytes always come
from the canonical pinned Git blob, so Windows CRLF checkouts produce identical
policy/profile bytes on every platform. It performs complete conflict preflight,
then atomically replaces individual
files and writes `shared-settings-manifest.json`. It never edits `config.toml`,
credentials, platform capacity, root model, root effort, tier or plugins. It does
not invoke any model, Fast or Astra. Repeat installation at the same commit is
idempotent. An existing unmanaged destination is refused even if content matches.
Updates require `--update-managed` and every installed file must still match its
previous manifest. Symlink destinations and locally modified/missing managed
files are refused. All source and destination ancestors, including those above
the supplied home, are checked for symlinks before reading or creating directories.
An interrupted partial update is detected on the next run;
recover deliberately from the recorded previous version, rather than force overwrite.

For an offline export without Git metadata, add `--source-commit-file /path/to/export.json`.
That trusted export attestation must contain `commit` and `files`, with exactly the
13 allowed relative paths and each file's SHA256. This checks export integrity
and the asserted commit; it does not independently prove GitHub provenance.
Offline export attestation remains strict byte matching, with no EOL normalization.
Keep the attestation outside the installed home. New source files must be included
in the committed checkout before testing this Git-pinned path.

When the product supports preparing and publishing an environment starting
snapshot, perform setup and then Publish using that product's controls. Start a
new task from the published environment to test restoration. Changes require
setup plus republishing for future tasks. This repository does not itself publish
anything or prove that the product offers those controls. Ordinary hosted Work
scratch is separate: it has no implied startup hook, snapshot retention or native
config consumer. A setup script sitting in GitHub alone does not auto-run after reset.

## Distinguish evidence

| Result | What it establishes |
|---|---|
| `FILES_AVAILABLE` | Installer validated source and installed the portable files. |
| Native verifier PASS | A temporary strict app-server read effective native config from the explicitly selected CODEX_HOME; no model turn was run. |
| Fresh session file read | The new session can retrieve the installed policy/profiles and random manifest probe. |
| Fresh session policy behavior | The new session demonstrably applies routing and approval rules; a Sol High child can supply delegation evidence if supported. |

For Windows native verification invoked from WSL, pass both the accessible file
home and the Windows server path to the same directory:

```sh
python scripts-shared/verify_shared_settings.py --config-home /mnt/c/Users/marian/.codex --server-config-home 'C:\Users\marian\.codex' --codex /mnt/c/path/to/codex.exe --cwd 'C:\dev\projects\codex-environment'
```

The verifier sets the child environment only; WSLENV exports the provided Windows
CODEX_HOME once without `/p` path translation. A Windows executable launched from
POSIX without the explicit native home is rejected. Output records both paths;
the caller must supply paths to the same physical directory. `--cwd` is passed to
the native app-server and must use that server's native path syntax.
Verification uses explicit checks that remain active under `python -O` and
`PYTHONOPTIMIZE`; a missing/empty AGENTS, mismatched profile or effective worker
configuration cannot produce PASS by disabling Python assertions.

Custom role discovery, profile registration, available models, service tier and
live worker capacity belong to the runtime. These files cannot force them.
The native verifier expects the existing native ten-thread settings and must not
be used to claim a hosted Work runtime has that capacity.

## Fresh session test

Start a genuinely new root/task after publishing. Do not preload the policy text,
probe value or expected answers in its prompt. Tell it only where to inspect:

> Inspect the installed shared settings at INSTALLED_HOME. Read the entire
> AGENTS.md and shared-settings-manifest.json and the relevant role files.
> Report the source commit and the manifest load_probe, give the applicable
> delegation choices, deferred modes and approvals required before an exceptional
> model selection, and compare requested worker capacity with your actual tool
> limit. If an independent bounded review is useful and supported, delegate it
> using Sol 6.1 High and report requested settings and any unavailable controls.
> Do not invoke an exceptional model or deferred mode during this test.

Compare returned commit/probe privately to the installed manifest, and compare
behavior to the source policy. Reading the probe proves file access, not automatic
instruction injection. This prompt explicitly requests loading; it cannot prove
that an unprompted task auto-loaded AGENTS. For automatic loading, a separate
fresh-session test without a load request must show the runtime's instruction
readback or behavior with a policy-only canary. Record unsupported/readback absent
as unproved. Never infer served inference tier from requested default settings.

For an instruction-loading diagnostic, install into a new acceptance home with
`--instruction-probe`. Only that installed AGENTS receives a random receipt rule;
the canonical source AGENTS is untouched. The manifest separately records source
hashes and installed hashes. The diagnostic persists on idempotent reruns. In a
genuinely fresh root, send exactly `Verify shared-settings startup.` without
supplying the nonce, source text, or file-reading instructions. The first response
before tools must equal the private manifest's `SHARED_SETTINGS_RECEIPT:` plus
`startup_probe`. A later explicit read cannot satisfy this first-response test.
This demonstrates injection of the diagnostic policy at startup; it alone does
not prove every routing rule, role registration, capacity or served tier. A
native app-server receiving a manually preloaded instruction block is a different
test and must not be reported as automatic load.

Offline checks: `python -m unittest discover -s cloud -p 'test_*.py' -v`.
