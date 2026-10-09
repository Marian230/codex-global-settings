# Personal model preferences

AGENTS.md contains three short preferences about delegation and model selection.

- agents/sol.toml: GPT-6.1 Sol.
- agents/astra.toml: GPT-6 Astra.
- agents/luna.toml: GPT-6 Luna for basic terminal/filesystem work.

Role files leave reasoning effort selectable per task. The corresponding *.config.toml files are CLI model presets with a context window of 872,000 tokens, the maximum reported by the current native catalog for these models. Automatic compaction uses native model defaults. Recheck the supported maximum when changing models. global-preferences.toml contains the native worker defaults and limit of ten workers beside the primary.

The optional cloud copier copies these files and records their source revision. Account instructions use the same short text as AGENTS.md. Historical workflows remain in Git history. Native roles are discovered in a new Codex session.
