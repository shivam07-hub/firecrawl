from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_PACK_FIELDS = {
    "skill_id",
    "skill_name",
    "status",
    "source_status",
    "generation_attribution",
    "source_ids",
    "reference_ids",
    "target_users",
    "core_topics",
    "exam_levels",
}

REQUIRED_ATTRIBUTION_FIELDS = {
    "generated_by",
    "generated_at",
    "review_status",
}

REQUIRED_LEVEL_FIELDS = {
    "level",
    "name",
    "description",
    "outcomes",
    "question_mix",
    "questions",
}

REQUIRED_QUESTION_FIELDS = {
    "id",
    "type",
    "prompt",
    "answer",
    "explanation",
    "source_refs",
}

VALID_SOURCE_STATUSES = {
    "approved_private_sources",
    "public_references_curated",
    "mixed_sources",
    "source_intake_required",
}


def _load_json(path: Path, errors: list[str]) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
    except json.JSONDecodeError as exc:
        errors.append(f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")
    return None


def _load_source_ids(root: Path) -> set[str]:
    path = root / "manifests" / "sources.jsonl"
    if not path.exists():
        return set()
    ids: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and isinstance(record.get("source_id"), str):
            ids.add(record["source_id"])
    return ids


def _load_reference_ids(root: Path) -> set[str]:
    path = root / "manifests" / "reference-links.jsonl"
    if not path.exists():
        return set()
    ids: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and isinstance(record.get("ref_id"), str):
            ids.add(record["ref_id"])
    return ids


def _validate_string_list(value: object, label: str, errors: list[str], allow_empty: bool = False) -> None:
    if not isinstance(value, list):
        errors.append(f"{label}: must be a list")
        return
    if not value and not allow_empty:
        errors.append(f"{label}: must not be empty")
        return
    for index, item in enumerate(value, 1):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{label}[{index}]: must be a non-empty string")


def _validate_question(
    question: object,
    pack_id: str,
    level: int,
    index: int,
    seen_question_ids: set[str],
    allowed_refs: set[str],
    errors: list[str],
) -> None:
    label = f"{pack_id}: level {level}: question {index}"
    if not isinstance(question, dict):
        errors.append(f"{label}: must be an object")
        return

    missing = sorted(REQUIRED_QUESTION_FIELDS - question.keys())
    if missing:
        errors.append(f"{label}: missing fields: {', '.join(missing)}")
        return

    question_id = question["id"]
    if not isinstance(question_id, str) or not question_id.strip():
        errors.append(f"{label}: id must be a non-empty string")
    elif question_id in seen_question_ids:
        errors.append(f"{label}: duplicate question id: {question_id}")
    else:
        seen_question_ids.add(question_id)

    for field in ["type", "prompt", "explanation"]:
        if not isinstance(question[field], str) or not question[field].strip():
            errors.append(f"{label}: {field} must be a non-empty string")

    _validate_string_list(question["source_refs"], f"{label}: source_refs", errors, allow_empty=True)
    for ref in question.get("source_refs", []):
        if isinstance(ref, str) and ref not in allowed_refs:
            errors.append(f"{label}: unknown source ref: {ref}")

    if question["type"] == "mcq":
        choices = question.get("choices")
        if not isinstance(choices, list) or len(choices) < 3:
            errors.append(f"{label}: mcq choices must include at least three options")
        else:
            for choice_index, choice in enumerate(choices, 1):
                if not isinstance(choice, str) or not choice.strip():
                    errors.append(f"{label}: choices[{choice_index}] must be a non-empty string")
            if question["answer"] not in choices:
                errors.append(f"{label}: answer must match one of choices")
    elif not isinstance(question["answer"], str) or not question["answer"].strip():
        errors.append(f"{label}: answer must be a non-empty string")


def _validate_pack(path: Path, root: Path, source_ids: set[str], reference_ids: set[str], errors: list[str]) -> None:
    pack = _load_json(path, errors)
    if not isinstance(pack, dict):
        errors.append(f"{path}: pack must be a JSON object")
        return

    missing = sorted(REQUIRED_PACK_FIELDS - pack.keys())
    if missing:
        errors.append(f"{path.name}: missing fields: {', '.join(missing)}")
        return

    pack_id = pack["skill_id"]
    if not isinstance(pack_id, str) or not pack_id.strip():
        errors.append(f"{path.name}: skill_id must be a non-empty string")
        pack_id = path.stem
    elif path.stem != pack_id:
        errors.append(f"{path.name}: filename must match skill_id {pack_id!r}")

    for field in ["skill_name", "status"]:
        if not isinstance(pack[field], str) or not pack[field].strip():
            errors.append(f"{pack_id}: {field} must be a non-empty string")

    if pack["source_status"] not in VALID_SOURCE_STATUSES:
        errors.append(f"{pack_id}: source_status must be one of {sorted(VALID_SOURCE_STATUSES)}")

    attribution = pack["generation_attribution"]
    if not isinstance(attribution, dict):
        errors.append(f"{pack_id}: generation_attribution must be an object")
    else:
        missing_attribution = sorted(REQUIRED_ATTRIBUTION_FIELDS - attribution.keys())
        if missing_attribution:
            errors.append(f"{pack_id}: generation_attribution missing fields: {', '.join(missing_attribution)}")
        for field in REQUIRED_ATTRIBUTION_FIELDS:
            value = attribution.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{pack_id}: generation_attribution.{field} must be a non-empty string")

    _validate_string_list(pack["source_ids"], f"{pack_id}: source_ids", errors, allow_empty=True)
    _validate_string_list(pack["reference_ids"], f"{pack_id}: reference_ids", errors, allow_empty=True)
    _validate_string_list(pack["target_users"], f"{pack_id}: target_users", errors)
    _validate_string_list(pack["core_topics"], f"{pack_id}: core_topics", errors)

    for source_id in pack["source_ids"]:
        if isinstance(source_id, str) and source_id not in source_ids:
            errors.append(f"{pack_id}: unknown source_id: {source_id}")
    for ref_id in pack["reference_ids"]:
        if isinstance(ref_id, str) and ref_id not in reference_ids:
            errors.append(f"{pack_id}: unknown reference_id: {ref_id}")

    allowed_refs = set(pack["source_ids"]) | set(pack["reference_ids"])
    levels = pack["exam_levels"]
    if not isinstance(levels, list):
        errors.append(f"{pack_id}: exam_levels must be a list")
        return

    level_numbers = [level.get("level") for level in levels if isinstance(level, dict)]
    if level_numbers != [1, 2, 3, 4]:
        errors.append(f"{pack_id}: exam_levels must define levels 1, 2, 3, and 4 in order")

    seen_question_ids: set[str] = set()
    for index, level in enumerate(levels, 1):
        if not isinstance(level, dict):
            errors.append(f"{pack_id}: exam_levels[{index}] must be an object")
            continue

        missing_level = sorted(REQUIRED_LEVEL_FIELDS - level.keys())
        if missing_level:
            errors.append(f"{pack_id}: level {index}: missing fields: {', '.join(missing_level)}")
            continue

        level_number = level["level"]
        if not isinstance(level_number, int) or isinstance(level_number, bool):
            errors.append(f"{pack_id}: level {index}: level must be an integer")
            level_number = index

        for field in ["name", "description"]:
            if not isinstance(level[field], str) or not level[field].strip():
                errors.append(f"{pack_id}: level {level_number}: {field} must be a non-empty string")
        _validate_string_list(level["outcomes"], f"{pack_id}: level {level_number}: outcomes", errors)

        if not isinstance(level["question_mix"], dict) or not level["question_mix"]:
            errors.append(f"{pack_id}: level {level_number}: question_mix must be a non-empty object")
        elif not all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in level["question_mix"].values()):
            errors.append(f"{pack_id}: level {level_number}: question_mix values must be non-negative integers")

        questions = level["questions"]
        if not isinstance(questions, list) or len(questions) < 2:
            errors.append(f"{pack_id}: level {level_number}: questions must include at least two items")
            continue

        for question_index, question in enumerate(questions, 1):
            _validate_question(
                question,
                pack_id,
                level_number,
                question_index,
                seen_question_ids,
                allowed_refs,
                errors,
            )


def _validate_catalog(root: Path, pack_ids: set[str], errors: list[str]) -> None:
    path = root / "skill-exams" / "skills.json"
    if not path.exists():
        return

    catalog = _load_json(path, errors)
    if not isinstance(catalog, dict):
        errors.append(f"{path}: catalog must be a JSON object")
        return

    skills = catalog.get("skills")
    if not isinstance(skills, list) or not skills:
        errors.append("skills.json: skills must be a non-empty list")
        return

    catalog_ids: set[str] = set()
    for index, skill in enumerate(skills, 1):
        label = f"skills.json: skills[{index}]"
        if not isinstance(skill, dict):
            errors.append(f"{label}: must be an object")
            continue

        for field in ["skill_id", "skill_name", "pack_path"]:
            if not isinstance(skill.get(field), str) or not skill[field].strip():
                errors.append(f"{label}: {field} must be a non-empty string")
                continue

        skill_id = skill.get("skill_id")
        if not isinstance(skill_id, str) or not skill_id.strip():
            continue
        if skill_id in catalog_ids:
            errors.append(f"{label}: duplicate skill_id: {skill_id}")
        catalog_ids.add(skill_id)

        pack_path = skill.get("pack_path")
        if not isinstance(pack_path, str) or not pack_path.strip():
            continue
        resolved_pack_path = (root / pack_path).resolve()
        try:
            resolved_pack_path.relative_to(root)
        except ValueError:
            errors.append(f"{label}: catalog pack_path escapes repository: {pack_path}")
            continue
        if not resolved_pack_path.is_file():
            errors.append(f"{label}: catalog pack_path does not exist: {pack_path}")
        elif resolved_pack_path.stem != skill_id:
            errors.append(f"{label}: catalog pack_path must match skill_id: {pack_path}")

    missing_from_catalog = sorted(pack_ids - catalog_ids)
    if missing_from_catalog:
        errors.append(f"skills.json: missing pack ids: {', '.join(missing_from_catalog)}")

    missing_from_packs = sorted(catalog_ids - pack_ids)
    if missing_from_packs:
        errors.append(f"skills.json: unknown pack ids: {', '.join(missing_from_packs)}")

    build_order = catalog.get("build_order")
    if build_order is not None:
        if not isinstance(build_order, list) or not build_order:
            errors.append("skills.json: build_order must be a non-empty list")
        elif any(not isinstance(item, str) or not item.strip() for item in build_order):
            errors.append("skills.json: build_order must contain only non-empty strings")
        elif set(build_order) != catalog_ids:
            errors.append("skills.json: build_order must contain exactly the catalog skill_ids")


def validate_skill_exam_packs(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    pack_dir = root / "skill-exams" / "packs"
    if not pack_dir.exists():
        return [f"missing skill exam pack directory: {pack_dir}"]

    packs = sorted(pack_dir.glob("*.json"))
    if not packs:
        return [f"no skill exam packs found in {pack_dir}"]

    source_ids = _load_source_ids(root)
    reference_ids = _load_reference_ids(root)
    for path in packs:
        _validate_pack(path, root, source_ids, reference_ids, errors)
    _validate_catalog(root, {path.stem for path in packs}, errors)
    return errors


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    errors = validate_skill_exam_packs(root)
    if errors:
        print("Skill exam validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Skill exam validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
