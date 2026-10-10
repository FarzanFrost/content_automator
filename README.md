# Content Automator

Automated content generation pipeline for Islamic educational content. Takes a Friday sermon audio file and produces: infographic images, YouTube thumbnails (16:9), short-form thumbnails (9:16), long-form video, and short-form video — driven by Gemini AI and ffmpeg.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| AI / Image Generation | Google Gemini 1.5 Pro, Imagen 3 (`google-genai`) |
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
│   └── backend/
│       ├── config/
│       │   └── settings.py          # AppSettings — env/config via pydantic-settings
│       ├── entities/
│       │   ├── ai_models.py         # ThumbnailConcept, ConceptList (Pydantic)
│       │   └── project.py           # ProjectState (dataclass, session state)
│       ├── repositories/
│       │   ├── file_repo.py         # FileRepo — local filesystem & markdown storage
│       │   ├── gdrive_repo.py       # GoogleDriveRepo — audio download from Drive
│       │   ├── gemini_repo.py       # GeminiRepo — Imagen 3 + Gemini 1.5 Pro
│       │   └── notebooklm_repo.py   # NotebookLMRepo — summary & hashtag generation
│       └── utils/
│           ├── prompt_manager.py    # PromptManager — AI prompt factory
│           └── ffmpeg_wrapper.py    # FFmpegWrapper — async video/image rendering
├── tests/
│   ├── test_foundations.py          # Entities and settings tests
│   ├── test_file_repo.py
│   ├── test_gdrive_repo.py
│   ├── test_gemini_repo.py
│   ├── test_notebooklm_repo.py
│   ├── test_prompt_manager.py
│   └── test_ffmpeg_wrapper.py
├── docs/                            # Living Docs (source of truth)
├── AGENTS.md                        # Session-critical rules & project metadata
├── requirements.txt
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
GEMINI_API_KEY=your_gemini_api_key
DEFAULT_N_INFOGRAPHICS=3
SHORTS_BGM_PATH=/path/to/bgm.mp3
BASE_OUTPUT_DIR=/path/to/output
```

### 3. Run

```bash
python -m src.main
```

### 4. Tests

```bash
.venv\Scripts\python.exe -m pytest          # all 47 tests
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
| `GeminiRepo` | `repositories.gemini_repo` | Generate images via Imagen 3; parse structured concepts via Gemini 1.5 Pro |

### Utilities

| Class | Module | Responsibility |
|-------|--------|---------------|
| `PromptManager` | `utils.prompt_manager` | Factory methods returning formatted prompt strings for Gemini |
| `FFmpegWrapper` | `utils.ffmpeg_wrapper` | Async wrapper producing final video, 9:16 short video, and 9:16 short thumbnail |

#### `PromptManager` methods

| Method | Output |
|--------|--------|
| `get_infographic_prompt(summary)` | 16:9 infographic prompt — title forced to `A FRIDAY SERMON SUMMARY` |
| `get_concept_prompt(summary, theme?)` | Requests 3 thumbnail concepts with Visual Hook, Design Directive, Text Hook, Color Theory |
| `get_thumbnail_prompt(concept, reference_image)` | 16:9 YouTube thumbnail prompt — always enforces `avoid generating eyes` for Islamic compliance |

#### `FFmpegWrapper` methods

| Method | Output |
|--------|--------|
| `create_final_video(img, audio, out)` | 16:9 MP4 — static image looped over full audio duration |
| `create_short_video(img, bgm, out)` | 9:16 MP4 — blur-fill background + centered foreground, BGM, max 60 s |
| `create_short_thumbnail(img, out)` | 9:16 JPEG/PNG — blur-fill background + centered foreground, single frame |

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

