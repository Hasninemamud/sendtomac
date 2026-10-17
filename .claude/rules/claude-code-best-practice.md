# Claude Code best practices (from shanraisshan/claude-code-best-practice)

Reference: https://github.com/shanraisshan/claude-code-best-practice

## Primitives

| Primitive | Location | Use |
|-----------|----------|-----|
| **Commands** | `.claude/commands/*.md` | User-invoked `/command` entry points |
| **Subagents** | `.claude/agents/*.md` | Delegated work; use Agent tool, not bash |
| **Skills** | `.claude/skills/<name>/SKILL.md` | Focused instructions; YAML frontmatter |
| **Rules** | `.claude/rules/*.md` | Always-on project memory |
| **Settings** | `.claude/settings.json` | Permissions, hooks, team defaults |

Config precedence: managed → CLI flags → `.claude/settings.local.json` → `.claude/settings.json` → `~/.claude/settings.json`.

## Orchestration pattern

**Command → Agent → Skill**: command gathers input, agent runs with preloaded skills, skills hold reusable steps. Template demo upstream: `/weather-orchestrator`.

## Subagents

- Subagents cannot spawn subagents via shell; use the Agent tool with explicit `subagent_type`.
- Frontmatter: `tools`, `model`, `skills` (preload), `permissionMode`, `maxTurns`.

## Workflow

Research → Plan → Execute → Review → Ship. Prefer existing helpers in this repo before new abstractions.

## Full reference install

Run `./scripts/install-claude-best-practice.sh` to merge upstream `.claude/` (demo commands, agents, skills, hooks). Keeps this repo’s `CLAUDE.md` and SendToMac-specific rules.
