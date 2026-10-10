# Refactor TODO — Content Automator

> Working note for current refactoring tasks. Canonical rules: `GUIDE_developer.md`.

---

## ✅ Phase 0: System Initialization (Done)
- [x] Bootstrapped Living Docs architecture (Done)

---

## 🚀 Phase 1: Core Setup (In Progress)

Objective: Establish baseline project structure, package configuration, and initial test suite.

- [ ] **1. Project Foundation**
  - [ ] Setup `pyproject.toml`
  - [x] Configure `pytest` and linter tooling
  - [x] Implement foundational entities and settings (`ThumbnailConcept`, `ConceptList`, `ProjectState`, `AppSettings`)
  - [x] Implement class-based repository layer (`FileRepo`, `GoogleDriveRepo`, `NotebookLMRepo`, `GeminiRepo`)
  - [x] Implement utility layer (`PromptManager`, `FFmpegWrapper`)
  - [x] Implement service orchestration layer (`AutomationService`)
  - [ ] Implement `scripts/bump_version.py`

---

## 🧊 On Hold / Backlog
- [x] Implementation of core content pipeline orchestration (`AutomationService`)
- [x] UI integration with Gradio lifecycle (`ContentAutomatorUI`, `run.py`)

---

## Safety & Verification
1. Zero-Loss Refactor Protocol: No behavioral changes allowed.
2. Test before and after every major edit.
3. Build must pass before commit.
