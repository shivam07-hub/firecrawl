from csv_importer import _job_skill_entries, _parse_batch_date


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"PASS  {label}")
        return
    raise AssertionError(f"FAIL  {label} {detail}")


def test_structured_entries() -> None:
    entries = _job_skill_entries({
        "skills": [
            {"name": "Python (Programming Language)", "is_primary": True, "required_level": 4},
            {"name": "Communication", "is_primary": False, "required_level": 99},
            {"name": "", "is_primary": True, "required_level": 3},
            "bad",
        ],
    })

    check("keeps valid structured entries only", len(entries) == 2, str(entries))
    check("keeps explicit level", entries[0]["required_level"] == 4)
    check("defaults invalid side level", entries[1]["required_level"] == 1)


def test_legacy_entries() -> None:
    entries = _job_skill_entries({
        "main_skills": ["SQL (Programming Language)"],
        "side_skills": ["Leadership"],
    })

    check("legacy count", len(entries) == 2, str(entries))
    check("legacy primary default", entries[0] == {
        "name": "SQL (Programming Language)",
        "is_primary": True,
        "required_level": 2,
    })
    check("legacy side default", entries[1] == {
        "name": "Leadership",
        "is_primary": False,
        "required_level": 1,
    })


def test_batch_date_parser() -> None:
    check("compact date", _parse_batch_date("20260510") == 20260510)
    check("hyphen date", _parse_batch_date("2026-05-10") == 20260510)
    check("underscore date", _parse_batch_date("2026_05_10") == 20260510)
    check("invalid date", _parse_batch_date("latest") is None)


if __name__ == "__main__":
    test_structured_entries()
    test_legacy_entries()
    test_batch_date_parser()
