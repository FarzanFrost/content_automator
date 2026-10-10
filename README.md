# Content Automator

Automated content generation pipeline for Islamic educational content. Takes a Friday sermon audio file and produces: infographic images, YouTube thumbnails (16:9), short-form thumbnails (9:16), long-form video, and short-form video — driven by Gemini AI and ffmpeg.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| AI / Image Generation | Google Gemini (`google-genai`) — image generation and structured concept extraction |
| Audio Ingestion | NotebookLM (`notebooklm-py`) |
| Cloud Storage | Google Drive (`google-api-python-client`) |
| Video Processing | ffmpeg CLI (`ffmpeg-python`) |
| UI | Gradio |
| Config | pydantic-settings, python-dotenv |
| Testing | pytest, `IsolatedAsyncioTestCase` |
| Formatting | black, isort |

---

## Project Structure

```
content_automator/
├── app/
│   ├── backend/
│   │   ├── config/
│   │   │   └── settings.py          # AppSettings — env/config via pydantic-settings
│   │   ├── entities/
│   │   │   ├── ai_models.py         # ThumbnailConcept, ConceptList (Pydantic)
│   │   │   └── project.py           # ProjectState (dataclass, session state)
│   │   ├── repositories/
│   │   │   ├── file_repo.py         # FileRepo — local filesystem & markdown storage
│   │   │   ├── gdrive_repo.py       # GoogleDriveRepo — audio download from Drive
│   │   │   ├── gemini_repo.py       # GeminiRepo — Gemini image generation + structured concept extraction
│   │   │   └── notebooklm_repo.py   # NotebookLMRepo — summary & hashtag generation
│   │   ├── services/
│   │   │   ├── automation_service.py # AutomationService — Phase 1 & 2 orchestrator
│   │   │   └── notebooklm_auth_service.py # NotebookLMAuthService — browser login & session management
│   │   └── utils/
│   │       ├── prompt_manager.py    # PromptManager — AI prompt factory
│   │       └── ffmpeg_wrapper.py    # FFmpegWrapper — async video/image rendering
│   └── ui/
│       └── app.py                   # ContentAutomatorUI — 5-step class-based Gradio UI
├── resources/                       # Static project assets & templates (e.g., shorts_video_fancy.mp4)
├── tests/
│   ├── test_foundations.py          # Entities and settings tests
│   ├── test_file_repo.py
│   ├── test_gdrive_repo.py
│   ├── test_gemini_repo.py
│   ├── test_notebooklm_auth_service.py
│   ├── test_notebooklm_repo.py
│   ├── test_prompt_manager.py
│   ├── test_ffmpeg_wrapper.py
│   ├── test_automation_service.py
│   └── test_ui_app.py
├── docs/                            # Living Docs (source of truth)
├── AGENTS.md                        # Session-critical rules & project metadata
├── requirements.txt
├── run.py                           # Gradio application launch entry point
└── .env                             # Environment variables (not committed)
```

---

## Quickstart

### 1. Environment Setup

```powershell
# Windows (PowerShell)
.venv\Scripts\activate
```
```bash
# Bash / Git Bash
source .venv/Scripts/activate
```

### 2. Configuration

Copy `.env.example` to `.env` and populate:

```env
GEMINI_IMAGE_API_KEY=your_gemini_image_api_key
GEMINI_CONCEPTS_API_KEY=your_gemini_concepts_api_key
GEMINI_IMAGE_MODEL=gemini-2.5-flash-image
GEMINI_CONCEPTS_MODEL=gemini-2.5-flash
DEFAULT_N_INFOGRAPHICS=1
SHORTS_BGM_PATH=/path/to/bgm.mp3
BASE_OUTPUT_DIR=/path/to/output
RESOURCES_DIR=resources
```

### 3. Run

```bash
python run.py
```

### 4. Tests

```bash
.venv\Scripts\python.exe -m pytest          # all tests
.venv\Scripts\python.exe -m pytest -v       # verbose
```

---

## Backend Architecture

### 3-Layer System

```
Entrypoint / Orchestration  →  Processor / Domain Logic  →  Data & Storage
```

Orchestrators dispatch jobs. Domain logic handles transformations. Repositories and utilities handle all external I/O.

### Entities

| Class | Module | Type | Purpose |
|-------|--------|------|---------|
| `ThumbnailConcept` | `entities.ai_models` | Pydantic BaseModel | Structured thumbnail generation directives from Gemini |
| `ConceptList` | `entities.ai_models` | Pydantic BaseModel | Container for multiple `ThumbnailConcept` items |
| `ProjectState` | `entities.project` | Dataclass | Mutable session state across the Gradio UI lifecycle |
| `AppSettings` | `config.settings` | Pydantic BaseSettings | Reads `.env` and environment variables at startup |

### Repositories

| Class | Module | Responsibility |
|-------|--------|---------------|
| `FileRepo` | `repositories.file_repo` | Create project directory structure; save versioned markdown files |
| `GoogleDriveRepo` | `repositories.gdrive_repo` | Download sermon audio from Google Drive; resolve filenames from headers |
| `NotebookLMRepo` | `repositories.notebooklm_repo` | Submit audio to NotebookLM; generate summaries and hashtags |
| `GeminiRepo` | `repositories.gemini_repo` | Generate images via Gemini (`_image_client`); parse structured concepts via Gemini (`_concepts_client`) — each with its own API key and model |

### Services

| Class | Module | Responsibility |
|---|---|---|
| `AutomationService` | `services.automation_service` | Orchestrate Phase 1 (ingestion, summary, early infographics) and Phase 2 (concepts, thumbnails, videos) |
| `NotebookLMAuthService` | `services.notebooklm_auth_service` | Verify Google session cookies, maintain persistent Chrome profile (`fresh=False`), and run Playwright browser login with headless auto-renewal |

### Utilities

| Class | Module | Responsibility |
|-------|--------|---------------|
| `PromptManager` | `utils.prompt_manager` | Factory methods returning formatted prompt strings for NotebookLM, Imagen 3, and Gemini |
| `FFmpegWrapper` | `utils.ffmpeg_wrapper` | Async wrapper producing final video, 9:16 short video, and 9:16 short thumbnail |

#### `PromptManager` methods

| Method | Output |
|--------|--------|
| `get_summary_prompt()` | Prompt asking NotebookLM to translate into English and structure content into topics |
| `get_hashtags_prompt()` | Prompt asking NotebookLM for 5 to 10 topic-specific YouTube hashtags prefixed with `#` |
| `get_infographic_prompt(summary)` | 16:9 infographic image prompt — title forced to `A FRIDAY SERMON SUMMARY` |
| `get_concept_prompt(summary, theme?)` | Master Digital Content Strategist prompt for 3 thumbnail concepts across psychological triggers |
| `get_thumbnail_prompt(concept, reference_image)` | 16:9 YouTube thumbnail prompt — matches reference image and enforces `avoid generating eyes` |


#### `FFmpegWrapper` methods

| Method | Output |
|--------|--------|
| `create_final_video(img, audio, out)` | 16:9 MP4 — static image looped over full audio duration (`-c:a copy`, `yuv420p`) |
| `create_short_video(img, bgm, out)` | 9:16 MP4 — blur-fill background (`boxblur=20:10`) + centered foreground, BGM stream copy (`-c:a copy`, `-shortest`) |
| `create_short_thumbnail(img, out)` | 9:16 JPEG/PNG — blur-fill background (`boxblur=20:10`) + centered foreground, single frame |

---

## Documentation

Living Docs — source of truth for all behavior, architecture, and standards:

| File | Purpose |
|------|---------|
| [AGENTS.md](AGENTS.md) | Session-critical rules, quick-reference, project metadata |
| [docs/ARCH_technical-specs.md](docs/ARCH_technical-specs.md) | Architecture, data models, state registry, system boundaries |
| [docs/ARCH_documentation-governance.md](docs/ARCH_documentation-governance.md) | Doc registry and task → load mapping |
| [docs/GUIDE_developer.md](docs/GUIDE_developer.md) | Implementation standards, refactoring rules, anti-patterns |
| [docs/STANDARDS_interface.md](docs/STANDARDS_interface.md) | CLI output, exit codes, IO formats |
| [docs/REF_developer-reference.md](docs/REF_developer-reference.md) | Naming conventions, command reference |
| [docs/REFACTOR_TODO.md](docs/REFACTOR_TODO.md) | Current implementation progress and backlog |

