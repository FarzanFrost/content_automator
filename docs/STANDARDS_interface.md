# STANDARDS_interface — Visual / Interface / IO specifications for Content Automator

---

## Rules

> Hard constraints for this domain. AI must follow unconditionally.

| Rule | Detail |
|------|--------|
| No magic numbers | All values must come from tokens or shared constants |
| Structured Logging | Console / CLI output must adhere to standard log formats or clean CLI output |
| Output formats | JSON outputs must be UTF-8 encoded with strict schema validation |

---

## Interface Reference

### Design Tokens / Output Formatting

| Token | Value | Usage |
|-------|-------|-------|
| `CLI_INDENT` | 2 spaces | Standard CLI hierarchical indentation |
| `TIMESTAMP_FORMAT` | ISO-8601 (`YYYY-MM-DDTHH:MM:SSZ`) | Log and serialized timestamp standard |
| `ENCODING` | UTF-8 | Default file and stream encoding |

### CLI Output Standards

| Component | Format / Pattern | Purpose |
|-----------|-----------------|---------|
| Success message | `[OK] <message>` | Operation succeeded |
| Error message | `[ERROR] <message>` | Operation failed |
| Warning message | `[WARN] <message>` | Non-fatal anomaly |

### Exit Codes

| Code | Value | Meaning |
|------|-------|---------|
| `EXIT_SUCCESS` | 0 | Normal termination |
| `EXIT_USAGE` | 2 | Command line syntax / argument error |
| `EXIT_FAILURE` | 1 | General runtime error |

### Gradio UI Specifications

| View / Container | Component | Spec / Constraints | Behavior / Event |
|---|---|---|---|
| Root Application | `gr.Blocks` | `title="Content Automator"` | Houses session `gr.State(value=ProjectState())` |
| Primary Navigation | `gr.Tabs` | "Jummah Automation", "Settings" | Top-level workflow navigation |
| Wizard Step 1 | `gr.Accordion` | "Step 1: Init" (open) | Drive URL input, Themes input, "Start Phase 1 Processing" primary button |
| Wizard Step 2 | `gr.Accordion` | "Step 2: Text Review" (open) | Interactive summary textbox, max-2 hashtag checkbox group, "Save Edited Summary" button |
| Hashtag Limiting | `gr.CheckboxGroup` | Max 2 items | Selection change handler clamps selected list to length 2 |
| Edited Text Output | Markdown file | Name: `v2_edited.md` in `project_dir` | Atomic file write dispatched via `FileRepo.save_text_version` |
| Settings Inspector | `gr.Tab` | "Settings" | Read-only inspector displaying `BASE_OUTPUT_DIR`, `DEFAULT_N_INFOGRAPHICS`, `SHORTS_BGM_PATH` |

---

## Edge Cases

> Only document cases that are non-obvious or have caused regressions.

- **Non-TTY Environments**: When stdout is redirected to a pipe or file, strip ANSI color codes.

---

*v0.1.0 — 2026-10-10*
