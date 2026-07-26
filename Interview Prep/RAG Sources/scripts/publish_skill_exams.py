#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class RuntimeQuestion:
    prompt: str
    options: tuple[str, str, str, str]
    correct_index: int
    answer: str
    explanation: str
    source_url: str | None


@dataclass(frozen=True)
class RuntimeSkill:
    taxonomy_key: str
    display_name: str
    l1_domain: str
    l2_cluster: str
    description: str
    description_source: str
    source_url: str | None
    questions_by_level: dict[int, list[RuntimeQuestion]]


@dataclass(frozen=True)
class RuntimeSeed:
    skills: tuple[RuntimeSkill, ...]


LEVEL_NAMES = {
    1: "Scout",
    2: "Trailblazer",
    3: "Excavator",
    4: "Cartographer",
    5: "Legend",
}


SKILL_CONFIGS = [
    {
        "taxonomy_key": "Frontend Engineering",
        "display_name": "Frontend Engineering",
        "l1_domain": "Information Technology",
        "l2_cluster": "Frontend Engineering",
        "description": "Builds reliable, accessible, and performant user interfaces using JavaScript, component frameworks, browser APIs, and frontend architecture patterns.",
        "description_source": "skill-exams:v1:frontend-engineering",
        "source_url": "https://github.com/greatfrontend/awesome-front-end-system-design",
        "level_focus": {
            1: ["semantic HTML", "CSS layout", "JavaScript events", "DOM updates", "form validation", "React props", "React state", "TypeScript props", "browser storage", "accessibility labels"],
            2: ["component decomposition", "state lifting", "controlled forms", "API loading states", "client-side errors", "render performance", "responsive layout", "reusable hooks", "type-safe events", "testable UI behavior"],
            3: ["notification center design", "checkout flow design", "search and filter experience", "dashboard data refresh", "optimistic updates", "pagination design", "error recovery UX", "frontend observability", "design-system adoption", "microfrontend boundaries"],
            4: ["SSR tradeoffs", "bundle splitting", "large-list rendering", "migration planning", "accessibility audits", "analytics contracts", "cache invalidation", "cross-team UI ownership", "visual regression testing", "performance budgets"],
            5: ["multi-app frontend platform", "global design system governance", "critical revenue-flow resilience", "organization-wide migration strategy", "frontend incident response", "privacy-aware telemetry", "edge rendering strategy", "internationalization architecture", "microfrontend governance", "long-term maintainability"],
        },
    },
    {
        "taxonomy_key": "Data Analytics and SQL",
        "display_name": "Data Analytics and SQL",
        "l1_domain": "Data",
        "l2_cluster": "Analytics",
        "description": "Uses SQL, metric definitions, dashboards, and experiment interpretation to answer business questions from structured data.",
        "description_source": "skill-exams:v1:data-analytics-sql",
        "source_url": None,
        "level_focus": {
            1: ["SELECT queries", "WHERE filters", "GROUP BY", "COUNT", "SUM", "conversion rate", "average order value", "date filters", "NULL handling", "ORDER BY"],
            2: ["LEFT JOIN", "INNER JOIN", "metric denominators", "duplicate rows", "cohort grouping", "funnel drop-off", "dashboard filters", "data quality checks", "time zones", "basic segmentation"],
            3: ["checkout conversion analysis", "retention cohort analysis", "promotion impact analysis", "customer segmentation", "funnel diagnosis", "weekly business review", "product metric selection", "instrumentation validation", "sales pipeline analysis", "support ticket trend analysis"],
            4: ["A/B test design", "guardrail metrics", "sample-size reasoning", "metric governance", "causal caveats", "dashboard prioritization", "executive narrative", "data model tradeoffs", "experiment readout", "decision thresholds"],
            5: ["analytics operating model", "north-star metric design", "cross-functional metric disputes", "longitudinal experiment strategy", "data quality incident response", "semantic layer governance", "privacy-aware analytics", "multi-source reconciliation", "portfolio-level dashboarding", "analytics roadmap prioritization"],
        },
    },
    {
        "taxonomy_key": "Python Programming",
        "display_name": "Python Programming",
        "l1_domain": "Information Technology",
        "l2_cluster": "Software Development",
        "description": "Solves practical programming problems with Python syntax, data structures, functions, files, debugging, and maintainable scripts.",
        "description_source": "skill-exams:v1:python-programming",
        "source_url": None,
        "level_focus": {
            1: ["lists", "dictionaries", "tuples", "loops", "conditionals", "functions", "return values", "string methods", "basic exceptions", "imports"],
            2: ["deduplicating records", "parsing CSV rows", "validating inputs", "file reading", "JSON handling", "dictionary counting", "list comprehensions", "small algorithm design", "unit-testable functions", "clear error messages"],
            3: ["debugging KeyError", "debugging off-by-one loops", "refactoring long functions", "separating I/O from logic", "API response handling", "retryable failures", "configuration loading", "logging useful context", "test fixture design", "performance hotspots"],
            4: ["streaming large files", "command-line interface design", "module boundaries", "type hints", "dependency isolation", "atomic output writes", "memory-efficient aggregation", "exception taxonomy", "package structure", "maintainable automation"],
            5: ["Python service architecture", "data pipeline reliability", "plugin-style extensibility", "concurrency tradeoffs", "observability design", "backward-compatible APIs", "security-conscious input handling", "large-scale refactoring", "library design", "production incident debugging"],
        },
    },
    {
        "taxonomy_key": "Business Analytics and Statistics",
        "display_name": "Business Analytics and Statistics",
        "l1_domain": "Business",
        "l2_cluster": "Business Analytics",
        "description": "Applies statistics, regression interpretation, forecasting, and analytical judgment to business decisions.",
        "description_source": "skill-exams:v1:business-analytics-statistics",
        "source_url": "https://www.iiml.ac.in/master-business-administration",
        "level_focus": {
            1: ["mean", "median", "variance", "correlation", "regression coefficient", "dependent variable", "independent variable", "outliers", "sample size", "descriptive statistics"],
            2: ["interpreting R-squared", "confounding variables", "forecast errors", "trend analysis", "seasonality", "hypothesis framing", "business controls", "confidence intervals", "model assumptions", "baseline comparison"],
            3: ["discount impact analysis", "churn forecasting", "demand forecasting", "pricing analysis", "customer lifetime value", "sales driver analysis", "campaign measurement", "operations bottleneck analysis", "market sizing with data", "risk segmentation"],
            4: ["model explainability", "overfitting risk", "feature selection", "scenario analysis", "decision thresholds", "uncertainty communication", "forecast governance", "experiment interpretation", "bias in business data", "tradeoff between rigor and speed"],
            5: ["analytics strategy", "model-risk governance", "executive decision framing", "multi-market forecasting", "portfolio analytics", "causal-inference roadmap", "analytical operating cadence", "high-stakes model review", "measurement-system design", "statistical storytelling"],
        },
    },
    {
        "taxonomy_key": "Backend and API System Design",
        "display_name": "Backend and API System Design",
        "l1_domain": "Information Technology",
        "l2_cluster": "Backend Engineering",
        "description": "Designs APIs, data models, authentication, caching, async work, and reliability patterns for backend systems.",
        "description_source": "skill-exams:v1:backend-api-system-design",
        "source_url": None,
        "level_focus": {
            1: ["HTTP status codes", "REST resources", "request validation", "authentication", "authorization", "database tables", "primary keys", "API errors", "pagination", "environment configuration"],
            2: ["idempotency keys", "partial updates", "ownership checks", "database indexes", "rate limiting", "input schemas", "transaction boundaries", "API versioning", "structured logging", "basic caching"],
            3: ["notification service design", "checkout API design", "search API design", "file upload workflow", "background jobs", "retry strategy", "webhook handling", "multi-tenant data access", "audit logging", "service decomposition"],
            4: ["read-heavy catalog scaling", "cache invalidation", "queue backpressure", "consistency tradeoffs", "database migration safety", "incident observability", "zero-downtime deploys", "API contract testing", "authorization design", "dependency timeouts"],
            5: ["platform API governance", "regional resilience", "multi-service reliability", "distributed tracing strategy", "data partitioning", "event-driven architecture", "security review process", "cost-aware scaling", "backward compatibility strategy", "failure-mode analysis"],
        },
    },
]


def _question_for(skill: dict, level: int, topic: str, index: int) -> RuntimeQuestion:
    level_name = LEVEL_NAMES[level]
    prompt = (
        f"In {skill['display_name']} at L{level} ({level_name}), which option best demonstrates sound judgment for {topic}?"
    )
    correct = f"Define the goal for {topic}, apply the appropriate technique, and verify the result with evidence."
    options = [
        correct,
        f"Skip validation for {topic} if the first attempt appears to work.",
        f"Treat {topic} as a one-time task that does not need review or testing.",
        f"Optimize {topic} before understanding the user, data, or system constraint.",
    ]
    rotation = (level + index) % 4
    rotated = options[rotation:] + options[:rotation]
    correct_index = rotated.index(correct)
    explanation = (
        f"At L{level}, {topic} should be handled with explicit goals, fit-for-purpose technique, and verification rather than guesswork."
    )
    return RuntimeQuestion(
        prompt=prompt,
        options=tuple(rotated),
        correct_index=correct_index,
        answer=correct,
        explanation=explanation,
        source_url=skill["source_url"],
    )


def build_runtime_seed() -> RuntimeSeed:
    skills: list[RuntimeSkill] = []
    for skill_config in SKILL_CONFIGS:
        questions_by_level: dict[int, list[RuntimeQuestion]] = {}
        for level in range(1, 6):
            topics = skill_config["level_focus"][level]
            if len(topics) != 10:
                raise ValueError(f"{skill_config['display_name']} level {level} must define 10 topics")
            questions_by_level[level] = [
                _question_for(skill_config, level, topic, index)
                for index, topic in enumerate(topics, 1)
            ]
        skills.append(
            RuntimeSkill(
                taxonomy_key=skill_config["taxonomy_key"],
                display_name=skill_config["display_name"],
                l1_domain=skill_config["l1_domain"],
                l2_cluster=skill_config["l2_cluster"],
                description=skill_config["description"],
                description_source=skill_config["description_source"],
                source_url=skill_config["source_url"],
                questions_by_level=questions_by_level,
            )
        )
    return RuntimeSeed(skills=tuple(skills))


def _sql_literal(value: str | None) -> str:
    if value is None:
        return "null"
    return "'" + value.replace("'", "''") + "'"


def _jsonb_literal(value: object) -> str:
    return _sql_literal(json.dumps(value, ensure_ascii=False)) + "::jsonb"


def _dedupe_hash(skill_key: str, level: int, prompt: str) -> str:
    payload = f"{skill_key}|{level}|{prompt}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def render_seed_sql(seed: RuntimeSeed) -> str:
    skill_rows = []
    question_rows = []
    for skill in seed.skills:
        skill_rows.append(
            "("
            + ", ".join(
                [
                    _sql_literal(skill.taxonomy_key),
                    _sql_literal(skill.display_name),
                    _sql_literal(skill.l1_domain),
                    _sql_literal(skill.l2_cluster),
                    _sql_literal(skill.description),
                    _sql_literal(skill.description_source),
                ]
            )
            + ")"
        )
        for level, questions in skill.questions_by_level.items():
            for question in questions:
                question_rows.append(
                    "("
                    + ", ".join(
                        [
                            _sql_literal(skill.taxonomy_key),
                            str(level),
                            _sql_literal(question.prompt),
                            _jsonb_literal(list(question.options)),
                            str(question.correct_index),
                            _sql_literal(question.explanation),
                            _sql_literal(question.source_url),
                            _sql_literal(_dedupe_hash(skill.taxonomy_key, level, question.prompt)),
                        ]
                    )
                    + ")"
                )

    return "\n".join(
        [
            "-- Generated by scripts/publish_skill_exams.py. Review before applying.",
            "begin;",
            "",
            "with seed_skills(taxonomy_key, display_name, l1_domain, l2_cluster, description, description_source) as (",
            "  values",
            "  " + ",\n  ".join(skill_rows),
            ")",
            "insert into public.skills (taxonomy_key, display_name, is_active, l1_domain, l2_cluster, description, description_source, description_fetched_at)",
            "select taxonomy_key, display_name, true, l1_domain, l2_cluster, description, description_source, now()",
            "from seed_skills",
            "on conflict (taxonomy_key) do update set",
            "  display_name = excluded.display_name,",
            "  is_active = true,",
            "  l1_domain = excluded.l1_domain,",
            "  l2_cluster = excluded.l2_cluster,",
            "  description = excluded.description,",
            "  description_source = excluded.description_source,",
            "  description_fetched_at = excluded.description_fetched_at;",
            "",
            "with seed_questions(skill_key, level, question_text, options, correct_index, explanation, source_url, dedupe_hash) as (",
            "  values",
            "  " + ",\n  ".join(question_rows),
            ")",
            "insert into public.skill_questions (skill_id, skill_key, level, question_text, options, correct_index, explanation, source_url, dedupe_hash, status)",
            "select s.id, q.skill_key, q.level::smallint, q.question_text, q.options, q.correct_index::smallint, q.explanation, q.source_url, q.dedupe_hash, 'active'",
            "from seed_questions q",
            "join public.skills s on s.taxonomy_key = q.skill_key",
            "on conflict (skill_id, level, dedupe_hash) do update set",
            "  skill_key = excluded.skill_key,",
            "  question_text = excluded.question_text,",
            "  options = excluded.options,",
            "  correct_index = excluded.correct_index,",
            "  explanation = excluded.explanation,",
            "  source_url = excluded.source_url,",
            "  status = 'active';",
            "",
            "commit;",
            "",
        ]
    )


def _validate_seed(seed: RuntimeSeed) -> list[str]:
    errors: list[str] = []
    if len(seed.skills) != 5:
        errors.append(f"expected 5 runtime skills, got {len(seed.skills)}")
    for skill in seed.skills:
        levels = sorted(skill.questions_by_level)
        if levels != [1, 2, 3, 4, 5]:
            errors.append(f"{skill.display_name}: expected levels 1-5, got {levels}")
            continue
        for level, questions in skill.questions_by_level.items():
            if len(questions) != 10:
                errors.append(f"{skill.display_name}: level {level} expected 10 questions, got {len(questions)}")
            for index, question in enumerate(questions, 1):
                if len(question.options) != 4:
                    errors.append(f"{skill.display_name}: level {level} question {index} must have 4 options")
                if question.correct_index < 0 or question.correct_index >= len(question.options):
                    errors.append(f"{skill.display_name}: level {level} question {index} has invalid correct_index")
                elif question.options[question.correct_index] != question.answer:
                    errors.append(f"{skill.display_name}: level {level} question {index} answer mismatch")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render runtime SQL for skill exam seeds.")
    parser.add_argument("--check", action="store_true", help="validate the generated seed and exit")
    parser.add_argument("--sql", action="store_true", help="print SQL to stdout")
    parser.add_argument("--out", type=Path, help="write SQL to a file")
    args = parser.parse_args(argv)

    seed = build_runtime_seed()
    errors = _validate_seed(seed)
    if errors:
        print("Skill exam runtime seed validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    if args.check:
        question_count = sum(len(questions) for skill in seed.skills for questions in skill.questions_by_level.values())
        print(f"OK (check): {len(seed.skills)} skills, {question_count} runtime MCQs")
        return 0

    sql = render_seed_sql(seed)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(sql, encoding="utf-8")
    if args.sql or not args.out:
        print(sql)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
