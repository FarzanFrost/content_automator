# ARCH_technical-specs — Core architecture, data models, and system boundaries for Content Automator

---

## Rules

> Hard constraints. AI must follow these unconditionally.

| Rule | Detail |
|------|--------|
| Pure domain logic | Domain models must remain decoupled from specific external delivery mechanisms |
| Explicit schemas | All data exchange models must declare explicit schemas using dataclasses or Pydantic |
| Adapter isolation | External third-party APIs and file sinks must be accessed via adapter interfaces |

---

## Architecture & Data Flow

### 3-Layer System Boundaries
1. **Entrypoint / Orchestration**: CLI or batch entry point. Orchestrators dispatch jobs without embedding business rules.
2. **Processor / Domain Logic**: Content transformations, template rendering, and business calculations.
3. **Data & Storage**: File I/O, cache storage, output serialization, and external repository adapters (`FileRepo`, `GoogleDriveRepo`, `NotebookLMRepo`, `GeminiRepo`).

### State & Storage Registry

| Key / Resource | Type | Scope | Notes |
|----------------|------|-------|-------|
| `CONTENT_CACHE_DIR` | Directory Path | Local state | Cache directory for intermediate artifacts |
| `APP_CONFIG_PATH` | File Path | Global config | Path to configuration file |
| `GEMINI_API_KEY` | Environment Variable | Global config | Secret API authentication key for Gemini API |
| `DEFAULT_N_INFOGRAPHICS` | Environment Variable | Global config | Default count for infographic generation (default: 3) |
| `SHORTS_BGM_PATH` | Environment Variable | Global config | Path to background music track for shorts |
| `BASE_OUTPUT_DIR` | Environment Variable | Global config | Root output directory path for project assets |
| `ProjectState` | Dataclass Object | Session state | Active Gradio session state across lifecycle |
| `SHORT_CANVAS_W` | Constant | Video output | Short-form canvas width: 1080 px |
| `SHORT_CANVAS_H` | Constant | Video output | Short-form canvas height: 1920 px (9:16) |
| `SHORT_MAX_DURATION` | Constant | Video output | Maximum short-form video duration: 60 s |

### Data Models & Schemas

| Model | Type | Module | Purpose |
|-------|------|--------|---------|
| `ThumbnailConcept` | Pydantic BaseModel | `app.backend.entities.ai_models` | Structured thumbnail generation directives from Gemini API |
| `ConceptList` | Pydantic BaseModel | `app.backend.entities.ai_models` | Collection container for multiple `ThumbnailConcept` items |
| `ProjectState` | Dataclass | `app.backend.entities.project` | Mutable session state container for Gradio UI lifecycle |
| `AppSettings` | Pydantic BaseSettings | `app.backend.config.settings` | Configuration manager reading `.env` and environment variables |

### Repositories & Adapters

| Repository | Module | Purpose |
|------------|--------|---------|
| `FileRepo` | `app.backend.repositories.file_repo` | Local filesystem project directory structure and versioned markdown storage |
| `GoogleDriveRepo` | `app.backend.repositories.gdrive_repo` | Audio asset download and Drive metadata resolution |
| `NotebookLMRepo` | `app.backend.repositories.notebooklm_repo` | NotebookLM audio source ingestion, summaries, and hashtag generation |
| `GeminiRepo` | `app.backend.repositories.gemini_repo` | Multimodal Imagen 3 image generation and Gemini 1.5 Pro structured concept parsing |

### Utilities

| Utility | Module | Purpose |
|---------|--------|---------|
| `PromptManager` | `app.backend.utils.prompt_manager` | Factory class producing formatted prompt strings for Gemini image and concept generation |
| `FFmpegWrapper` | `app.backend.utils.ffmpeg_wrapper` | Async wrapper around ffmpeg CLI for final video, 9:16 short video, and short thumbnail rendering |

---

## Reference

| Item | Value | Notes |
|------|-------|-------|
| Intermediate Data Format | JSON | Validated structured exchange |
| Output Format | Markdown / Text / Media | Generated deliverables |

---

## Edge Cases

- **Interrupted File Writes**: Write new artifacts to temporary files before atomic rename to avoid corrupted partial outputs.
- **9:16 Short-Form Scaling**: `FFmpegWrapper` short methods use a two-layer `filter_complex` — blur-fill background scaled to 1080×1920, foreground scaled to 1080 px wide and centered — to avoid black bars on 9:16 canvases sourced from 16:9 thumbnails.
- **Islamic Compliance in Prompts**: `PromptManager.get_thumbnail_prompt` always appends the directive `avoid generating eyes` regardless of concept content. Do not remove or make this conditional.

---

*v0.1.0 — 2026-10-10*
