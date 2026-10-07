# Shared personal Codex settings

Canonical live Windows source: `C:\Users\marian\.codex`. Git tracks exactly 17 allowlisted policy, role, profile, preference and verification files. The deny-all `.gitignore` excludes complete native configuration, credentials, keys, sessions, logs, caches, plugins and skills. Never use `git add -f`, `git add .`, or disable the allowlist.

WSL `/home/marian/.codex/AGENTS.md`, six role files and six profile layers use filesystem links to the Windows source. Changes to these source files appear in both systems without a reset script. Native Windows/WSL `config.toml` remain separate to preserve platform-specific settings; each now sets ten child threads and Sol 6.1 High as the delegated default. Native roots remain Windows XHigh and WSL High.

Use a fresh native root/session after changing discovered roles or capacity. Filesystem sharing does not hot-reload an existing thread. Standard/default tier is a configured preference; actually returned inference tier requires separate evidence. Luna Fast remains preserved but deferred. Every Astra use needs a task-specific direct human approval before selection.

Check loading without model turns with `scripts-shared/verify_shared_settings.py --config-home <native-home> --codex <binary> --cwd <native-cwd>`. It parses all six definitions, invokes neither Fast nor Astra profiles, and reads effective configuration from its own temporary strict app-server.

Git is initialized locally only. No GitHub remote or private repository was connected during the setup. Review explicit tracked paths before connecting a PRIVATE remote. Native global AGENTS contains personal paths and project context, so do not publish it publicly. Git does not automatically commit or push later edits.

ChatGPT Work Cloud does not automatically mount these PC files or necessarily consume native config. Its current session provides six workers, regardless of the native ten-worker configuration. Account-level policy readback, private GitHub publication, published Codex Cloud environment and a fresh cloud restore test remain pending.

For Codex Cloud, prepare the environment once, install the portable policy/profiles with native path adaptations, verify effective settings in that supported surface, then Publish. New tasks inherit the published starting setup; task VM state has a separate documented recovery window. Edit + Republish changes future starting setup. This is a supported environment workflow, not a claim that ordinary Work scratch survives deletion.

One-time setup records, backup location and final report are in `C:\dev\projects\codex-environment`. WSL backup: `/home/marian/.local/share/codex-settings-sync/20261007T071436Z`. No scheduled tasks, startup hooks or recurring reset scripts were installed.
