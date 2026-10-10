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
| Phase 1 Execution | Chained Event | `phase1_btn.click(...).then(...)` | `on_start_notebooklm` runs first and renders summary + hashtags; `.then()` auto-triggers `on_generate_infographics` displaying loading state on gallery without human intervention |
| NotebookLM Auth | `gr.Markdown` & `gr.Button` | "Login to NotebookLM" | Displays live auth status via `on_check_auth_status`; button triggers `on_notebooklm_login` (browser Playwright flow) and updates status |
| Wizard Step 2 | `gr.Accordion` | "Step 2: Text Review" (open) | Interactive summary textbox, max-2 hashtag checkbox group, "Save Edited Summary" button |
| Hashtag Limiting | `gr.CheckboxGroup` | Max 2 items | Selection change handler clamps selected list to length 2 |
| Edited Text Output | Markdown file | Name: `v2_edited.md` in `project_dir` | Atomic file write dispatched via `FileRepo.save_text_version` |
| Wizard Step 3 | `gr.Accordion` | "Step 3: Infographic Selection" (open) | `gr.Gallery` for Phase 1 infographics (select 1), "Confirm Infographic" primary button |
| Infographic Confirmation | Decoupled Listeners | `confirm_infographic_btn.click(...)` | Button disables upon valid click; triggers 3 independent listeners (`on_create_final_video`, `on_create_short_video`, `on_generate_thumbnails`) showing isolated loading spinners on each component |
| Wizard Step 4 | `gr.Accordion` | "Step 4: Thumbnail Selection" (open) | `gr.Gallery` for $3 \times (k+1)$ thumbnails (select 1), "Confirm Thumbnail & Create Shorts Thumbnail" primary button |
| Thumbnail Confirmation | `confirm_thumbnail_btn` | Button click | Runs `on_confirm_thumbnail` producing 9:16 shorts thumbnail from user's selected 16:9 thumbnail; disables button after execution |
| Wizard Step 5 | `gr.Accordion` | "Step 5: Final Outputs" (open) | Multi-column layout with individual status markdown for `final_video_player` (`final_video.mp4`), `shorts_video_player` (`shorts_video_fancy.mp4` / `shorts_video.mp4`), and `shorts_thumb_display` (`shorts_thumbnail.png`) |
| Settings Inspector | `gr.Tab` | "Settings" | Read-only inspector displaying `BASE_OUTPUT_DIR`, `DEFAULT_N_INFOGRAPHICS`, `SHORTS_BGM_PATH`, `RESOURCES_DIR` |

---

## Edge Cases

> Only document cases that are non-obvious or have caused regressions.

- **Non-TTY Environments**: When stdout is redirected to a pipe or file, strip ANSI color codes.

---

*v0.1.0 — 2026-10-10*
