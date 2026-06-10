# Figma → Flutter Pipeline

A 4-step automated pipeline that converts a Figma screen node into production-ready Flutter code, running entirely inside **Claude Code** with isolated subagents.

```
Figma URL
  → Step 1: normalize  (figma-extract-agent + Figma MCP)  → JSON + PNG per widget
  → Step 2: analyze    (analyze-design-agent)              → pre_plan.md + preview.html
  → Step 3: plan       (ui-plan-architect)                 → plan.md (detailed)
  → Step 4: code       (ui-code-agent)                     → Dart files + flutter analyze clean
```

Each step runs in an **isolated subagent context** so the main conversation stays light — no manual `/compact` needed.

---

## Requirements

- Flutter project with `pubspec.yaml`
- [Claude Code](https://claude.ai/code)
- [Figma Desktop](https://www.figma.com/downloads/) + [figma-mcp-go](https://github.com/hapins/figma-mcp-go) plugin
- `jq` (for settings merge — `brew install jq` on macOS)

---

## Installation

### One-liner (run inside your Flutter project root)

```bash
curl -sSL https://raw.githubusercontent.com/chientran28/figma-claude-workflow/main/install.sh | bash
```

### Or clone and run locally

```bash
git clone https://github.com/chientran28/figma-claude-workflow.git
./figma-claude-workflow/install.sh /path/to/your/flutter-project
```

### Upgrade (re-run install — kit/ is always overwritten, your config is preserved)

```bash
./install.sh /path/to/your/flutter-project
```

---

## Post-install setup (required)

These steps require AI — `install.sh` cannot do them automatically:

**1. Start Figma MCP server**
Open Figma Desktop → Plugins → figma-mcp-go → Start Server

**2. Configure the pipeline for your project**
Open Claude Code in your project root, then run:
```
/init-ui-workspace
```
This scans your project's color/font/asset Dart files, sets `figma_file_id`, and builds `token_map.json` (Figma variables → Dart constants).

**3. Convert your first screen**
```
/organize-figma https://www.figma.com/design/YOUR_FILE/...?node-id=123-456
```

---

## Commands

| Command | Description |
|---|---|
| `/init-ui-workspace` | One-time setup: scan project sources, set Figma file ID, build token map |
| `/organize-figma <url>` | Run the full 4-step pipeline on a Figma node |
| `/get-exist-design` | Scan existing widgets/assets into `.ui-workspace/exist_design/` for reuse |
| `/get-asset-figma` | Extract icons/images from Figma into the project |
| `/learn-from-failed` | Record a UI bug and its fix as a reusable pattern |
| `/skeleton` | Add skeleton loading state to a screen |

---

## What gets installed

```
.claude/
├── skills/
│   ├── organize-figma/        # Master coordinator
│   ├── analyze-design/        # Widget classification + visual analysis
│   ├── make-ui-plan/          # Detailed Flutter code plan
│   ├── coding-ui/             # Dart code generator
│   └── learn-from-failed/     # Bug → pattern learner
├── agents/
│   ├── figma-extract-agent.md # Figma MCP access + normalize (Step 1)
│   ├── analyze-design-agent.md# Visual analysis (Step 2)
│   ├── ui-plan-architect.md   # Plan generation (Step 3)
│   └── ui-code-agent.md       # Code generation (Step 4)
├── commands/
│   ├── normalize-figma-file.md
│   ├── init-ui-workspace.md
│   ├── get-asset-figma.md
│   ├── get-exist-design.md
│   ├── skeleton.md
│   └── scripts/figma_preprocessor.py  # Core Python normalizer
├── hooks/
│   ├── dart-analyze-feedback.sh   # Auto dart analyze on file edit
│   ├── knowledge-eval.sh          # Validate knowledge file health
│   ├── known-patterns-inject.sh   # Inject learned patterns into context
│   ├── learnings-reinjection.sh   # Reinject after context compact
│   └── pipeline-gate.sh           # Pipeline readiness check on stop
└── rules/
    ├── token-naming-rules.md
    ├── coding-standards.md
    ├── clean-code-scalability.md
    └── l10n-reuse.md

.ui-workspace/
├── figma_config.json          # Figma file ID + project_sources paths
├── token_map.json             # Figma token name → Dart constant
├── exist_design/              # Registry of reusable widgets + assets
├── flutter_helper_design.md   # Accumulated rendering patterns
├── ui_failed.md               # UI bug history + fixes
└── learnings.md               # Meta-learnings from past screens
```

---

## Configuration files

### `.ui-workspace/figma_config.json`
Filled by `/init-ui-workspace`. Key fields:
- `figma_file_id` — from your Figma URL: `/design/<FILE_ID>/`
- `project_sources` — paths to your color/font/asset Dart files
- `enable_html_visualization` — `true` for iPhone mockup preview before coding

### `.ui-workspace/token_map.json`
Maps Figma variable names to Dart constants. Built by `/init-ui-workspace` via `get_variable_defs` MCP call + project scan. Format:
```json
{
  "color.brand.primary": "AppColors.brandPrimary",
  "color.surface.white": "AppColors.white"
}
```

---

## What the pipeline does NOT do automatically

| Item | Why | How to handle |
|---|---|---|
| `token_map.json` content | Each project has different Figma tokens + Dart class names | `/init-ui-workspace` generates a proposal; you confirm |
| `figma_file_id` | Specific to your team's Figma file | Set during `/init-ui-workspace` |
| `project_sources` paths | Different projects use different file structures | Auto-scanned by `/init-ui-workspace` |
| Knowledge files content | Patterns are project-specific; seeding cross-project causes wrong outputs | Pipeline learns via `/learn-from-failed` |
| `CLAUDE.md` project rules | Stack conventions (Riverpod/BLoC, GoRouter/AutoRoute) vary | Write your own `CLAUDE.md` |

---

## Uninstall

```bash
# Keep .ui-workspace/ (recommended — preserves accumulated knowledge)
./uninstall.sh /path/to/flutter-project

# Remove everything including knowledge
./uninstall.sh /path/to/flutter-project --purge
```

---

## How it works (pipeline internals)

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the detailed 4-step breakdown including why each step runs in an isolated subagent.

---

## License

MIT
