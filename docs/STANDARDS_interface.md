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

---

## Edge Cases

> Only document cases that are non-obvious or have caused regressions.

- **Non-TTY Environments**: When stdout is redirected to a pipe or file, strip ANSI color codes.

---

*v0.1.0 — 2026-10-10*
