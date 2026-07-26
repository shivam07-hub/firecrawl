# AGENTS.md

## Scope

All work must remain inside this repository.

## Privacy

- Repository visibility must remain private.
- Import only paths listed in `manifests/import-allowlist.txt`.
- Never import CVs, identity records, payroll records, signatures, photographs,
  personal correspondence, credentials, or private company records.
- Third-party originals stay private and are never exported as public assets.

## V1 Authoring

- V1 content is authored and cross-reviewed through Claude and Codex sessions.
- Give agents only the minimum relevant approved source files.
- Record source IDs plus generation and review attribution on derived work.
- Do not add cloud-LLM API keys or unattended LLM API integrations.

## Change Discipline

- Preserve original source files unchanged.
- Update manifests when adding, moving, or replacing a source.
- Run corpus validation and unit tests before every commit.
- Do not commit generated vector indexes, model caches, or extracted text.
