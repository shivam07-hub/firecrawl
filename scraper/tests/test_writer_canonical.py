from __future__ import annotations

from schema import CANONICAL_FIELDS
from writer import to_canonical


def check(label: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"PASS {label}")


def test_to_canonical_matches_jobs_table_fields() -> None:
    raw = {
        "job_id": "req-1",
        "title": "Senior Engineer",
        "raw_jd_text": "Build reliable data systems.",
        "industry": "Technology",
        "job_url": "https://example.com/jobs/req-1",
        "location_city": "Bengaluru, India",
    }
    row = to_canonical(raw, "Example Co")

    check("canonical key order", list(row.keys()) == CANONICAL_FIELDS)
    check("title mapped", row["job_title"] == "Senior Engineer")
    check("description mapped", row["job_description"] == "Build reliable data systems.")
    check("company mapped", row["company_name"] == "Example Co")
    check("location mapped", row["location"] == "Bengaluru, India")
    check("location raw defaults", row["location_raw"] == "Bengaluru, India")
    check("country defaults to India", row["location_country"] == "India")
    check("skill fields default empty", row["skills"] == [] and row["main_skills"] == [] and row["side_skills"] == [])


def main() -> None:
    test_to_canonical_matches_jobs_table_fields()
    print("All writer canonical tests passed.")


if __name__ == "__main__":
    main()
