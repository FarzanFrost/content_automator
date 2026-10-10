# Agent — Content Automator (v0.1.0) — 2026-10-10

> **Strict Rule**: Read this file at every session start.

## Project Setup
- **Project Name**: Content Automator
- **Version**: 0.1.0 — use bump script only, never manually edit
- **Status**: Active
- **Tech Stack**: Python 3.11+, pytest, virtualenv (.venv)
- **Context Anchors**: None

## Documentation Priority
- `docs/` is the source of truth for behavior, architecture, and implementation rules.
- `AGENTS.md` holds only: session-critical rules, quick-reference checklists, metadata.
- Do not duplicate detailed explanations here — link to `docs/` instead.
- **Scope unclear?** Open `docs/ARCH_documentation-governance.md` first — task→load mapping is there.

## Documentation Governance
- **Implementation Standards**: `docs/GUIDE_developer.md` — how we write code, refactor, and test.
- **Architecture & Data**: `docs/ARCH_technical-specs.md` — data models, routing, system boundaries.
- **Visual & IO Standards**: `docs/STANDARDS_*.md` — design tokens, output formats, interface specs.
- **Rule**: Never consolidate these files without explicit intent. Keep concerns isolated to prevent accidental regressions.

## AI Technical Governance (CRITICAL)
- **Discussion Precedence (CRITICAL)**: **Strictly forbidden to create, modify, or delete any code/files until the plan is fully discussed and finalized with the user.**

## TDD Decision Rule
- **Use TDD** for: logic, data processing, routing, rendering output, business rules.
- **Skip TDD** for: docs, copy, rename, formatting, cosmetic edits.

## Goal-Driven Execution
Verify → trace → build → confirm. Never guess → build → fix → repeat.
Before multi-step tasks, state a brief plan: `[Step] → verify: [check]`.

## Response Style (CRITICAL)
- Answer only what's asked. No intro, recap, outro, filler, or padding.
- Markdown only when it helps (tables, code blocks).
- Unsure → ask **one** question. No assumptions.

### Writing Rules
Drop: articles (a/an/the), filler (just/really/basically/actually/simply), pleasantries (sure/certainly/of course/happy to), hedging. Fragments OK. Short synonyms (big not extensive, fix not "implement a solution for"). Technical terms exact. Code blocks unchanged. Errors quoted exact.

Pattern: `[thing] [action] [reason]. [next step].`

- ❌ "Sure! I'd be happy to help you with that. The issue you're experiencing is likely caused by..."
- ✅ "Bug in auth middleware. Token expiry check use `<` not `<=`. Fix:"
- "Why React component re-render?" → "New object ref each render. Inline object prop = new ref = re-render. Wrap in `useMemo`."
- "Explain database connection pooling." → "Pool reuse open DB connections. No new connection per request. Skip handshake overhead."

### Auto-Clarity
Revert to full sentences for: security warnings, irreversible action confirmations, multi-step sequences where fragment order risks misread. Resume terse after.

### Boundaries
Code blocks, commit messages, PR descriptions: write normal always.

## Common Mistakes
| Mistake | Prevention |
|---------|------------|
| Refactoring working code without being asked | Only refactor on explicit request |
| Adding work to an existing changelog entry | New task = new version header always |
| Duplicating a rule across multiple files | One file owns each rule — link, don't copy |
| Manual version bumps | Always use the bump script |
| Assuming without confirming | If unsure, ask one question |
| Changing unrelated files in the same edit | One edit = one concern |
| Skipping the registry when adding a doc | Register before use, always |

## Pre-Commit Protocol
1. **Test**: Run full test suite. All tests must pass.
2. **Bump**: Use bump script — never manually edit version numbers.
3. **Docs**: Add notes to new version header only. Never insert into old entries.
4. **Build**: Confirm production build passes.
5. **Clean**: Remove debug statements, fix TODOs, delete scratch files.
6. **Git**: No `push` or `commit` without explicit user approval per action.

## Milestones
- [x] v0.1.0: Project bootstrapping and Living Docs architecture initialized
- [ ] v0.2.0: Core content automation pipeline and models
  - [x] Repository layer adapters implemented and tested (23 tests passing)
  - [x] Automation service orchestration implemented and tested (50 tests passing)
  - [x] Class-based Gradio UI and launch entrypoint implemented and tested (64 tests passing)

## Commands
- `python -m src.main`: local development.
- `.venv\Scripts\python.exe -m pytest`: run tests.
- `python -m build`: production build.
- `python scripts/bump_version.py`: sync version across all files. Never manually edit version numbers.

## Project Notes
> Python environment active (.venv). Living Docs initialized.

---

*v0.1.0 — 2026-10-10*
