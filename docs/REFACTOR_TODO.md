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
  - [ ] Implement `scripts/bump_version.py`

---

## 🧊 On Hold / Backlog
- [ ] Implementation of content pipeline components (Awaiting domain design)

---

## Safety & Verification
1. Zero-Loss Refactor Protocol: No behavioral changes allowed.
2. Test before and after every major edit.
3. Build must pass before commit.
