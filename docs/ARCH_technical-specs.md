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
3. **Data & Storage**: File I/O, cache storage, output serialization.

### State & Storage Registry

| Key / Resource | Type | Scope | Notes |
|----------------|------|-------|-------|
| `CONTENT_CACHE_DIR` | Directory Path | Local state | Cache directory for intermediate artifacts |
| `APP_CONFIG_PATH` | File Path | Global config | Path to configuration file |

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
