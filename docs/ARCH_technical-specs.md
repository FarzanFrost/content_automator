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
| `GEMINI_IMAGE_API_KEY` | Environment Variable | Global config | API key for Gemini image generation calls |
| `GEMINI_CONCEPTS_API_KEY` | Environment Variable | Global config | API key for Gemini structured concept generation calls |
| `GEMINI_IMAGE_MODEL` | Environment Variable | Global config | Model used for Gemini image generation (e.g. `gemini-2.5-flash-image`) |
| `GEMINI_CONCEPTS_MODEL` | Environment Variable | Global config | Model used for structured concept generation (e.g. `gemini-2.5-flash`) |
| `DEFAULT_N_INFOGRAPHICS` | Environment Variable | Global config | Default count for infographic generation (default: 1) |
| `SHORTS_BGM_PATH` | Environment Variable | Global config | Path to background music track for shorts |
| `BASE_OUTPUT_DIR` | Environment Variable | Global config | Root output directory path for project assets |
| `RESOURCES_DIR` | Environment Variable | Global config | Directory path for static external project assets (default: `resources`) |
| `SERVER_NAME` | Environment Variable | Launch config | Gradio host binding address (default: `127.0.0.1`) |
| `SERVER_PORT` | Environment Variable | Launch config | Gradio host port number (default: `7860`) |
| `ProjectState` | Dataclass Object | Session state | Active Gradio session state across lifecycle |
| `SHORT_CANVAS_W` | Constant | Video output | Short-form canvas width: 1080 px |
| `SHORT_CANVAS_H` | Constant | Video output | Short-form canvas height: 1920 px (9:16) |
| `SHORT_MAX_DURATION` | Constant | Video output | Maximum short-form video duration: 60 s |
| `NOTEBOOKLM_STORAGE_PATH` | File Path (`~/.notebooklm/profiles/default/storage_state.json`) | Local auth state | Preserved Google session cookies for `NotebookLMClient` |

### Data Models & Schemas

| Model | Type | Module | Purpose |
|-------|------|--------|---------|
| `ThumbnailConcept` | Pydantic BaseModel | `app.backend.entities.ai_models` | Structured thumbnail generation directives from Gemini API |
| `ConceptList` | Pydantic BaseModel | `app.backend.entities.ai_models` | Collection container for multiple `ThumbnailConcept` items |
| `ProjectState` | Dataclass | `app.backend.entities.project` | Mutable session state container for Gradio UI lifecycle |
| `AppSettings` | Pydantic BaseSettings | `app.backend.config.settings` | Configuration manager reading `.env` and environment variables |

### Presentation & UI

| Component | Module | Purpose |
|-----------|--------|---------|
| `ContentAutomatorUI` | `app.ui.app` | Class-based Gradio user interface encapsulating reactive layout, event listeners, and session state |
| `main` / `run.py` | `run` | Application launch entry point configuring host/port bindings and initializing UI service |

### Repositories & Adapters

| Repository | Module | Purpose |
|------------|--------|---------|
| `FileRepo` | `app.backend.repositories.file_repo` | Local filesystem project directory structure and versioned markdown storage |
| `GoogleDriveRepo` | `app.backend.repositories.gdrive_repo` | Audio asset download and Drive metadata resolution |
| `NotebookLMRepo` | `app.backend.repositories.notebooklm_repo` | NotebookLM audio source ingestion, summaries, and hashtag generation |
| `GeminiRepo` | `app.backend.repositories.gemini_repo` | Gemini image generation (`_image_client`) and structured concept parsing (`_concepts_client`), each using a dedicated API key and model |

### Services

| Service | Module | Purpose |
|---------|--------|---------|
| `AutomationService` | `app.backend.services.automation_service` | Orchestrator for Phase 1 (ingestion, summary, early infographics) and Phase 2 (concepts, thumbnails, videos) |
| `NotebookLMAuthService` | `app.backend.services.notebooklm_auth_service` | Session verification, cache invalidation, and Playwright-driven Google login for NotebookLM |

### Utilities

| Utility | Module | Purpose |
|---------|--------|---------|
| `PromptManager` | `app.backend.utils.prompt_manager` | Factory class producing formatted prompt strings for NotebookLM (summaries, hashtags) and Gemini/Imagen (infographics, concepts, thumbnails) |
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
- **9:16 Short-Form Scaling**: `FFmpegWrapper` short methods use a `-vf` split filtergraph (`split[v1][v2]`) — blur-fill background scaled to 1080×1920 with `boxblur=20:10`, foreground scaled to fit inside 1080×1920 (`force_original_aspect_ratio=decrease`) and centered (`(main_w-overlay_w)/2:(main_h-overlay_h)/2`) — to avoid black bars and distortion on 9:16 canvases sourced from 16:9 thumbnails.
- **Audio Stream Copy & Pixel Format Compatibility**: `FFmpegWrapper.create_final_video` and `create_short_video` use stream copy (`-c:a copy`) for instant lossless audio integration without re-encoding, paired with `-shortest` and `-pix_fmt yuv420p` to guarantee video playback compatibility across web browsers, mobile players, and QuickTime.
- **Islamic Compliance in Prompts**: `PromptManager.get_thumbnail_prompt` enforces `Also to make the resulting thumbnail islamic, avoid generating eyes` and styling similarity to reference image. Do not remove or make this conditional.
- **NotebookLM Prompt Delegation**: `NotebookLMRepo` delegates all audio question synthesis (`get_summary_prompt`, `get_hashtags_prompt`) to `PromptManager`, supporting dependency injection and centralizing prompt mutations.
- **Non-blocking Background Task GC Prevention**: In `AutomationService.phase_1_process`, spawned background `asyncio` tasks for infographic generation must be retained in an in-memory set (`_background_tasks`) until completion to prevent garbage collection before execution finishes.

- **Phase 2 Prerequisite Validation**: `AutomationService.phase_2_process` requires `ProjectState.selected_infographic_path` to be non-empty before initiating downstream concept, thumbnail, or video rendering. Raises `ValueError` if missing.
- **Concept & Thumbnail Concurrency**: `AutomationService.phase_2_process` dispatches $k+1$ concept generation prompts concurrently ($1$ base + $k$ themes) and flattens outputs to $3 \times (k+1)$ concepts, generating all thumbnails in parallel before video composition.
- **Gradio State Dataclass Serialization**: In `ContentAutomatorUI.build_ui`, `gr.State` must be initialized with an instantiated dataclass (`gr.State(value=ProjectState())`) rather than the dataclass class type to satisfy Gradio's internal `dataclasses.asdict` conversion.
- **Lazy UI Dependency Resolution**: `ContentAutomatorUI` resolves `AutomationService` and `FileRepo` via lazy property getters rather than direct instantiation in `__init__`, allowing UI construction and inspection without triggering external client authentication during testing or offline environments.
- **Hashtag Selection Clamping**: `ContentAutomatorUI.on_hashtag_change` clamps user hashtag selections to a strict maximum of 2, updating session state and restoring UI selections immediately upon change.
- **Static Resource Resolution & Fallback**: In `AutomationService.phase_2_process`, when static asset `shorts_video_fancy.mp4` exists in `RESOURCES_DIR`, it is copied into `project_dir` and returned in the deliverables list; otherwise, the pipeline falls back seamlessly to the generated `shorts_video.mp4`.
- **Gradio Gallery Event Value Extraction**: In `ContentAutomatorUI._extract_path_from_event`, gallery `.select()` events extract file paths across varying Gradio versions and payload formats (dict with image object, dict with caption, raw string, or tuple list) to ensure robust state synchronization.
- **NotebookLM Client Async Context Lifecycle**: In `NotebookLMRepo`, `_get_client` is decorated with `@asynccontextmanager` ensuring `NotebookLMClient` is entered and exited via `async with` blocks during `generate_summary` and `generate_hashtags`, preventing unhandled session disconnects or hanging connections.
- **NotebookLM Session Cookie Verification**: `NotebookLMAuthService.is_authenticated` asserts that `storage_state.json` contains both `SID` and `__Secure-1PSIDTS` cookies required by Google services; missing tokens indicate expired or partial sessions.
- **Phase 1 NotebookLM Authentication Gate**: `ContentAutomatorUI.on_start_phase_1` validates `auth_service.is_authenticated()` prior to dispatching processing, returning a direct user prompt to login if unauthenticated and preventing downstream ingestion failures.
- **Gemini Developer API Image Modality**: `GeminiRepo.generate_image` uses `generate_content` with `types.GenerateContentConfig(response_modalities=['IMAGE'])` to support Gemini Developer API mode without requiring Vertex AI enterprise endpoints.
- **Gemini Split Client Architecture**: `GeminiRepo` maintains two separate `genai.Client` instances — `_image_client` (keyed by `GEMINI_IMAGE_API_KEY`, model `GEMINI_IMAGE_MODEL`) and `_concepts_client` (keyed by `GEMINI_CONCEPTS_API_KEY`, model `GEMINI_CONCEPTS_MODEL`) — allowing independent quota, project, and model configuration per operation type. Both clients are injectable for testing.
- **Safe Background Image Generation**: `AutomationService._safe_generate_image` wraps `GeminiRepo.generate_image` in a try/except, logging errors without re-raising, so background task failures never surface as unhandled exceptions in the Gradio event loop.
- **Gradio Output Path Whitelisting & Placeholders**: `run.py` whitelists `BASE_OUTPUT_DIR` in `demo.launch(allowed_paths=[...])`, and `AutomationService.phase_1_process` writes immediate placeholder PNG files to disk, ensuring Gradio file cache validation passes before async image generation completes.

---

*v0.1.0 — 2026-10-10*
