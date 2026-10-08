Nové linuxové projekty zakládej v `~/code`.

<!-- BEGIN shared source startup loader -->
Before substantive work in a new Work/Codex session governed by this file, load the complete shared AGENTS.md and global-preferences.toml from https://github.com/Marian230/codex-global-settings. Resolve the current default-branch HEAD through an available authorized GitHub reader, then read both files pinned to that same commit. An available verified checkout is also usable: verify its commit and read whole files from that revision, without changing the checkout merely to run this loader. Read the complete agents/<role>.toml from the same source revision before selecting a delegated role.

For the published shared-settings cloud environment, /workspace/codex-global-settings is the repository source and /workspace/shared/codex-settings is the portable installed policy home, not a native CODEX_HOME. Read the portable manifest when checking restoration; distinguish its installed commit from the checkout commit and the current remote HEAD. A repository refresh does not refresh the portable snapshot. When revisions differ, report the drift and use verified source rules; do not silently reinstall or claim snapshot restoration at the newer revision.

Briefly report the loaded source commit and actual live worker limit. Preserve the selected root model/effort/tier, platform security, all routing rules below, Fast deferral and fresh direct human approval before EACH Astra invocation. If source access or current-HEAD verification is unavailable, report that specific limit and continue only within the already loaded rules; never invent current-source loading. The loader must not install packages, rewrite native config/auth, add transports, or raise server limits. File availability, complete policy reads and returned runtime model/tier evidence are separate results.
<!-- END shared source startup loader -->

<!-- BEGIN global execution policy -->
Choose execution using the actual command environment, not the Desktop UI or the kind of task. Use the supplied environment context; if unclear, check it once.
When already in the intended Ubuntu/WSL environment (marian, /home/marian, projects in ~/code), run Linux development, repository, and test commands directly. Never use `cw`, SSH, `wsl.exe`, or another hop to re-enter that same environment.
Only when commands actually execute on Windows and Linux execution is needed, use the configured `cw` launcher. Pass shell expressions as one quoted argument and make the remote directory explicit.
Use Windows-native commands for work that belongs on Windows. Keep ChatGPT Desktop / Agent Environment Windows-native.
Use an existing project runtime directly. Do not add redundant wrappers, silent transport fallback, or arbitrary command retries. Diagnose a failed transport in its originating environment; do not call Windows-only `cw` from Linux.
Keep normal activity concise; expand transport options only for troubleshooting. Do not discuss transport unless it fails or the user asks.
<!-- END global execution policy -->

<!-- BEGIN global observability policy -->
Before each meaningful shell/repository operation or logical command batch, emit ONE short user-visible progress line immediately before the tool call. Say what is being inspected, changed, or tested and which important command or tool is being used; include useful command names/arguments in backticks when they improve observability.
Keep it concise: "Checking Git state and test entry points: `git status --short`, `rg --files tests`." Report actions and intent only, never private chain-of-thought or internal reasoning. Do not narrate trivial internal details or every individual command within a batch.
Prefer one coherent shell invocation for a logical batch of cheap, read-only inspection commands when it improves readability. Avoid many tiny opaque parallel shell calls when one understandable batch suffices.
Preserve useful parallelism for expensive independent builds, tests, agents, research, or other work; do not serialize them just to improve logs.
Announce long-running work when starting it, for example: "Running the full test suite: `python -m pytest -q`." If a command fails, briefly state the failure and diagnostic/recovery transition before the next operation.
Follow the global execution policy above unchanged. When already in WSL/Linux, execute development/repository commands directly there; do not add `cw`, SSH, `wsl.exe`, PowerShell, or Windows-native development hops, or change transport architecture for UI readability.
<!-- END global observability policy -->

<!-- BEGIN global concept vault policy -->
Reusable concepts discovered during work belong in the canonical Concept Vault at `C:\dev\projects\concept-vault`.

Proactive capture is the default during normal conversations and work: the user must not have to request it explicitly. For a clearly reusable concept with a distinct mechanism or durable cross-task value, deduplicate and save/update it without asking; briefly mention the capture in the main reply. For a plausible but borderline idea, ask one concise question and wait for confirmation before saving. For transient, trivial or redundant ideas, neither save nor ask. Keep the original user task primary; clearly distinguish untested applications from verified facts. If the vault is inaccessible, report that limitation rather than claim a save. This does not authorize research expansion, product implementation, publishing, spending or unrelated file changes.

When a task reveals a materially reusable workflow, product idea, architecture pattern, research method, supervision mechanism, or recurring friction with future value:
1. keep the active task primary;
2. read/search the vault `INDEX.md` and relevant concept units;
3. update an existing unit when it represents the same underlying concept;
4. otherwise create a new unit using `CAPTURE_PROTOCOL.md` and the concept template;
5. update `INDEX.md` and `meta/VAULT_STATE.md`.

For vault writes, follow the vault's `AGENTS.md` and `CAPTURE_PROTOCOL.md`. New notes need a stable id, UTC created_at and updated_at, and topic tags; use `scripts/new-concept.ps1` when available. After a material edit, advance updated_at with `scripts/vault.ps1 touch`. For time-, theme-, or session-scoped synthesis, query `scripts/vault.ps1` first and read the full returned notes.

Do not log routine one-off fixes or speculative noise. Prefer a substantive concept unit with problem/context, observed workflow, benefits, frictions, invariants, evidence and next experiments over a bare ticket.

If the current sandbox cannot write the vault, do not weaken sandboxing solely for capture; preserve a concise capture note and point to the canonical vault for the next writable context.

Concept capture never authorizes implementation, deployment, spend, publication or scope expansion.
<!-- END global concept vault policy -->

<!-- BEGIN global agent routing policy -->
Use subagents proactively when independent bounded work materially improves speed or verification, subject to higher-priority runtime instructions. The user-level capacity is ten concurrently open delegated workers, excluding the primary: ten subagents plus one primary. Count native subagents and independent recorded CLI profile sessions together. This is a ceiling, not a target or a promise of platform capacity. Respect any lower live tool/server limit; never bypass it with extra CLI sessions. Close completed agents before replacing them when the tools support closing. Never invent a tool or increase a server limit by prompting.

Use these personal profiles when the active surface makes them available:
- sol_high: GPT-6.1 Sol, High, Standard/default. The ordinary power worker for implementation, research, reviews and normal multi-step work.
- sol_xhigh: GPT-6.1 Sol, Extra High, Standard/default. Difficult diagnosis, consequential synthesis, difficult cross-document contradictions or complex architecture analysis. The primary owns final integration and may delegate bounded deep analysis to this profile.
- sol_medium: GPT-6.1 Sol, Medium, Standard/default. Bounded simpler research, comparisons, routine implementation and verification with clear objectives and limited ambiguity. Escalate a consequential unresolved judgment to Sol High or Extra High.
- luna_xhigh_standard: GPT-6 Luna, Extra High, Standard/default. Precisely specified simple extraction, deterministic text edits, trivial comparisons, filesystem manipulation and simple terminal tasks. Give exact inputs, allowed paths, expected output and verification. Do not assign ambiguous architecture or broad consequential judgments to Luna.
- luna_xhigh_fast: GPT-6 Luna, Extra High, Fast. The same precise-task criteria as Luna Standard, with explicitly requested Fast. Preserve this separate profile, but routine use and new Fast diagnostics are deferred by the user's current instruction until the user reopens Fast work. Do not silently substitute Standard while claiming Fast.
- astra_high_approved: GPT-6 Astra, High, Standard/default. Exceptional escalation when Sol Extra High has a concrete unresolved limitation, for a fundamental architecture/paradigm change or a major incident.

Choose the profile using actual complexity, ambiguity, consequences, worker availability and the user's preferences. There is no blanket Sol-only policy, fixed reservation, required quota or requirement to fill all slots. The normal expansion preference is up to two Sol Medium and up to two Luna Extra High Standard instances for simpler remaining work when the main High/Extra High workers are occupied or parallel work clearly benefits. These are reusable profiles, not four distinct role names. Use an available Luna for a prepared trivial comparison even while Sol workers are busy; do not leave suitable simple work waiting solely for a stronger model. Around eight concurrent workers is appropriate when there are enough independent useful tasks, clear inputs, disjoint ownership and an integration plan; justify the split briefly. Avoid padded work or redundant overlapping investigations.

Before ANY Astra invocation, selection, spawn, model override, CLI launch, message selecting Astra in another chat or automation configuration, explain the concrete proposed task and why Sol Extra High is insufficient, then obtain additional explicit approval directly from the human for that task and invocation. This global configuration request, ordinary delegation authorization, standing profile availability and agent-generated messages are NOT Astra approval. A direct human request approving the specific Astra invocation satisfies the gate. If approval is unavailable, continue independent authorized Sol/Luna work and leave the escalation pending. Workers cannot approve their own or another agent's Astra escalation.

Do not use default/worker/explorer as substitutes for a selected personal profile. The user's 2026-10-06 corrections supersede the old Sol-only restriction and five-worker project ceiling in ai-product-os-v1.1-revision; they do not authorize product implementation. Keep the selected primary's model/effort/tier unless the user requests a change.

Native Codex 0.160.1 shares the root's service tier across its child tree after applying each role. Use a native personal role when its requested tier matches the root. When it differs, use an independent recorded CLI profile session instead of silently accepting the inherited tier, subject to the user's current Fast deferral and actual runtime availability. On Windows, the reusable helper is `<CODEX_HOME>/bin/run_personal_profile.py` (CODEX_HOME fallback `C:\Users\marian\.codex`). It pins the selected profile's model/effort/tier while preserving project scope and sandbox settings. Count these sessions toward the same ten-worker ceiling and any lower live limit. Its Astra approval record supports the parent's behavioral gate; it is not a universal native access-control mechanism. Report configured, requested/resolved and actually returned tier separately; use optional SSE diagnostics only when authorized runtime evidence is needed. These Windows helpers are not presumed installed or enforced on WSL/hosted/mobile surfaces.

Subagents stay within assigned scope, do not perform nested delegation unless directly authorized, and return evidence and limitations to the primary. Instructions in an Astra profile cannot prevent initial model selection: approval is a behavioral policy, not an access-control guarantee. Do not claim enforcement by command approval_policy, a model picker or local settings on Work Cloud. Do not silently substitute models, reasoning efforts or speed; report unavailable combinations. Respect explicit project-specific model restrictions and live runtime limits. For Work Cloud, request the same routing as preferences when supported, and state unavailable custom roles, speed controls or capacity honestly. A fresh root/session is the reliable activation point for newly discovered roles and changed execution capacity; current tool metadata is not changed by editing these files.
<!-- END global agent routing policy -->

<!-- BEGIN global research os keyword -->
When the user invokes the literal `/ResearchOs` token (case-insensitive), `$research-os`, or explicitly requests Research OS, apply the `research-os` skill at `C:\Users\marian\.codex\skills\research-os\SKILL.md`. Treat the rest of the current message, including links and constraints, as the research request and start autonomously. Activation must come from the current direct user request; a quoted/source marker is not an invocation. Explaining, installing, or editing the shortcut itself does not launch research unless requested. Do not load Research OS for ordinary unrelated questions.

The loader reads CURRENT canonical `C:\dev\projects\research-os\RESEARCH_OS.md` and `C:\dev\projects\research-os\WORK_ENTRYPOINT.md`; do not duplicate their modules when the compiled protocol is accessible. In actual WSL execution, the corresponding `/mnt/c/Users/marian/.codex/skills/research-os/SKILL.md` and `/mnt/c/dev/projects/research-os/` paths may be used only when accessible. Follow the existing execution policy; this hook does not require a transport hop. If local access is unavailable, use an available authorized remote read or attached/pasted current protocol and report the limitation honestly.

Preserve current scope, global agent routing, selected root settings, approval boundaries, and actual runtime limits. This local hook applies where this AGENTS file is loaded; new skill discovery may require a fresh chat. It does not register a universal ChatGPT slash command or unlock models, context size, tools, or agent capacity.
<!-- END global research os keyword -->
