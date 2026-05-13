from enricher import _validate_enrichment


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"PASS  {label}")
        return
    raise AssertionError(f"FAIL  {label} {detail}")


def test_structured_skills() -> None:
    data = _validate_enrichment({
        "role_domain": "Software Engineering",
        "skills": [
            {"name": "Python", "is_primary": True, "required_level": 3},
            {"name": "SQL", "is_primary": True, "required_level": 9},
            {"name": "Communication", "is_primary": False},
            {"name": "Not A Real Skill", "is_primary": True, "required_level": 4},
            {"name": "Python", "is_primary": False, "required_level": 1},
        ],
    })

    check("role_domain kept", data["role_domain"] == "Software Engineering")
    check("invalid + duplicate dropped", len(data["skills"]) == 3, str(data["skills"]))
    check("canonical Python", data["skills"][0]["name"] == "Python (Programming Language)")
    check("primary level kept", data["skills"][0]["required_level"] == 3)
    check("invalid primary level defaults to 2", data["skills"][1]["required_level"] == 2)
    check("missing side level defaults to 1", data["skills"][2]["required_level"] == 1)
    check("main_skills derived", data["main_skills"] == ["Python (Programming Language)", "SQL (Programming Language)"])
    check("side_skills derived", data["side_skills"] == ["Communication"])


def test_legacy_arrays() -> None:
    data = _validate_enrichment({
        "role_domain": "Invented Domain",
        "main_skills": ["Machine Learning"],
        "side_skills": ["Leadership"],
    })

    check("invalid role_domain dropped", data["role_domain"] is None)
    check("legacy arrays become structured", len(data["skills"]) == 2)
    check("legacy primary level", data["skills"][0]["required_level"] == 2)
    check("legacy side level", data["skills"][1]["required_level"] == 1)


if __name__ == "__main__":
    test_structured_skills()
    test_legacy_arrays()
