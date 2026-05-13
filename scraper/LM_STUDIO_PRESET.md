# LM Studio Enrichment Preset

Use the existing LM Studio preset if it follows this contract. The scraper sends
the extraction prompt, system message, `temperature=0.0`, and `max_tokens`
through the OpenAI-compatible API, so the GUI preset does not need to carry the
full job-enrichment instructions.

## Recommended preset: `mirror-cv-fast`

Model:

- `google/gemma-3-4b` for normal enrichment (`MODEL_SPEED=fast`)
- `deepseek-r1-0528-qwen3-8b-mlx` only when quality is more important than speed (`MODEL_SPEED=quality`)

System prompt:

```text
You are a precise job data extractor. Return one valid JSON object only. No explanation, no markdown, no extra text.
```

Runtime settings:

| Setting | Value |
|---|---|
| Temperature | `0.0` |
| Response length | Short; API currently sets `512` tokens for fast mode |
| Context length | At least `2048` tokens |
| Structured output | Optional; if enabled, allow exactly `role_domain` and `skills` |

## Expected API behavior

`scraper/enricher.py` sends:

- `role_domain`: one controlled functional area
- `skills`: up to 13 Lightcast skills from the supplied candidate list, each with `name`, `is_primary`, and `required_level`

The model must return JSON shaped like:

```json
{"role_domain": "Software Engineering", "skills": [{"name": "Python (Programming Language)", "is_primary": true, "required_level": 3}]}
```

The code validates everything after the model responds:

- Unknown `role_domain` values are dropped.
- Skill strings not matching the Lightcast L3 taxonomy are dropped.
- `required_level` is constrained to `1` through `4`.
- Backward-compatible `main_skills` and `side_skills` arrays are derived from `skills`.
- Extra fields are ignored by the pipeline but should not be emitted.

## Quick readiness check

From the repo root:

```bash
curl -s http://localhost:1234/v1/models
```

Confirm the loaded model ID matches `scraper/.env`:

```bash
MODEL_SPEED=fast
LM_STUDIO_MODEL_FAST=google/gemma-3-4b
```

If those match, keep using the existing preset.
