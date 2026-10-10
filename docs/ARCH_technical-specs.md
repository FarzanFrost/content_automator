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

---

## Reference

| Item | Value | Notes |
|------|-------|-------|
| Intermediate Data Format | JSON | Validated structured exchange |
| Output Format | Markdown / Text / Media | Generated deliverables |

---

## Edge Cases

- **Interrupted File Writes**: Write new artifacts to temporary files before atomic rename to avoid corrupted partial outputs.

---

*v0.1.0 — 2026-10-10*
