#!/usr/bin/env python3
"""
Career Ops Agent — rank the firecrawl_Supabase job set against a candidate's CV.

Flow (mirrors the firecrawl_Supabase journey end-to-end):
  scraper -> Supabase jobs  ──►  prefilter (free heuristic)  ──►  OpenRouter deep eval  ──►  ranked report

Usage:
  python agent.py --dry-run                 # free: fetch + heuristic shortlist, no LLM
  python agent.py --rank --top 20           # deep-eval top 20 via OpenRouter (needs key)
  python agent.py --rank --api-key sk-or-... --model anthropic/claude-sonnet-4
  python agent.py --tailor <job_id>         # tailor the CV for one job (needs key)
  python agent.py --batch-date 20260527     # restrict to one scrape batch

The OpenRouter key is supplied by the user at run time (--api-key / env / .env);
nothing is committed.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import config
import openrouter_client as orc
import prefilter
import prompts
import referrals as ref
import render
import supabase_client as sb


# ── tiny flat-YAML reader (no PyYAML dep) ────────────────────────────────────
def load_profile(path: Path) -> dict[str, Any]:
    """Minimal YAML: scalars, `- ` lists, and `>`/`|` block scalars."""
    if not path.exists():
        sys.exit(f"Profile not found: {path}")
    prof: dict[str, Any] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    cur_list_key: str | None = None
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        if raw.lstrip().startswith("- "):
            if cur_list_key:
                prof.setdefault(cur_list_key, []).append(raw.split("- ", 1)[1].strip())
            i += 1
            continue
        if ":" in raw:
            key, _, val = raw.partition(":")
            key, val = key.strip(), val.strip()
            if val in (">", "|", ">-", "|-"):  # block scalar — gather indented lines
                block, i = [], i + 1
                while i < len(lines) and (not lines[i].strip() or lines[i].startswith((" ", "\t"))):
                    if lines[i].strip():
                        block.append(lines[i].strip())
                    i += 1
                prof[key] = " ".join(block)
                cur_list_key = None
                continue
            val = val.strip('"').strip("'")
            if val == "":
                cur_list_key = key
                prof.setdefault(key, [])
            else:
                cur_list_key = None
                prof[key] = val
        i += 1
    return prof


def load_cv(path: Path) -> str:
    if not path.exists():
        sys.exit(f"CV not found: {path}. Put your CV markdown there or set CV_PATH.")
    return path.read_text(encoding="utf-8")


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ── output writers ───────────────────────────────────────────────────────────
def write_shortlist_csv(rows: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "prefilter_score", "company", "title", "role_domain",
                    "location", "fit_cues", "apply_url"])
        for i, j in enumerate(rows, 1):
            w.writerow([i, j["_prefilter_score"], j.get("company_name"),
                        j.get("job_title"), j.get("role_domain"), j.get("location"),
                        ", ".join(j.get("_fit_cues", [])), j.get("apply_url")])


def write_ranked_csv(rows: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "overall_score", "grade", "recommendation", "company",
                    "title", "role_domain", "location", "role_fit", "comp_fit",
                    "growth_fit", "culture_fit", "risk_score", "summary",
                    "application_angle", "apply_url"])
        for i, j in enumerate(rows, 1):
            e = j["_eval"]
            w.writerow([i, e.get("overall_score"), e.get("grade"),
                        e.get("recommendation"), j.get("company_name"),
                        j.get("job_title"), j.get("role_domain"), j.get("location"),
                        e.get("role_fit"), e.get("comp_fit"), e.get("growth_fit"),
                        e.get("culture_fit"), e.get("risk_score"),
                        e.get("summary"), e.get("application_angle"),
                        j.get("apply_url")])


def write_ranked_md(rows: list[dict[str, Any]], path: Path, model: str) -> None:
    lines = [f"# Career Ops — Ranked Job Leads ({datetime.now():%Y-%m-%d %H:%M})",
             f"\nModel: `{model}` · {len(rows)} jobs deep-evaluated\n",
             "| # | Score | Grade | Rec | Company | Title | Location | Angle |",
             "|--:|--:|:--|:--|---|---|---|---|"]
    for i, j in enumerate(rows, 1):
        e = j["_eval"]
        lines.append(
            f"| {i} | {e.get('overall_score')} | {e.get('grade')} | "
            f"{e.get('recommendation')} | {j.get('company_name')} | "
            f"{j.get('job_title')} | {j.get('location')} | "
            f"{e.get('application_angle','')} |"
        )
    lines.append("\n---\n## Detail\n")
    for i, j in enumerate(rows, 1):
        e = j["_eval"]
        lines += [
            f"### {i}. {j.get('job_title')} — {j.get('company_name')}  ({e.get('grade')} / {e.get('overall_score')})",
            f"- **Recommendation:** {e.get('recommendation')}",
            f"- **Location:** {j.get('location')} · **Domain:** {j.get('role_domain')}",
            f"- **Fit:** role {e.get('role_fit')} · comp {e.get('comp_fit')} · growth {e.get('growth_fit')} · culture {e.get('culture_fit')} · risk {e.get('risk_score')}",
            f"- **Summary:** {e.get('summary')}",
            f"- **Strengths:** {'; '.join(e.get('strengths', []))}",
            f"- **Concerns:** {'; '.join(e.get('concerns', []))}",
            f"- **Angle:** {e.get('application_angle','')}",
            f"- **Apply:** {j.get('apply_url')}\n",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")


# ── commands ─────────────────────────────────────────────────────────────────
def cmd_dry_run(args, profile, cv) -> None:
    jobs = sb.fetch_jobs(batch_date=args.batch_date, limit=args.limit)
    print(f"Fetched {len(jobs)} active jobs from Supabase.")
    counts = sb.fetch_companies(jobs)
    print("Top companies:", ", ".join(f"{c}({n})" for c, n in list(counts.items())[:10]))
    ranked = prefilter.rank(jobs)
    top = ranked[: args.top]
    csv_path = config.OUT_DIR / f"shortlist_{_ts()}.csv"
    write_shortlist_csv(top, csv_path)
    print(f"\nTop {len(top)} heuristic matches (no LLM):")
    for i, j in enumerate(top[:25], 1):
        print(f"{i:2}. [{j['_prefilter_score']:5}] {j.get('company_name'):22.22} | "
              f"{(j.get('job_title') or '')[:48]:48} | {(j.get('location') or '')[:24]}")
    print(f"\nShortlist CSV → {csv_path}")
    print("Run with --rank to deep-evaluate these via OpenRouter.")


def cmd_rank(args, profile, cv) -> None:
    if not config.openrouter_ready():
        sys.exit("OPENROUTER_API_KEY missing. Pass --api-key sk-or-... or set it in .env / env.")
    jobs = sb.fetch_jobs(batch_date=args.batch_date, limit=args.limit)
    print(f"Fetched {len(jobs)} jobs. Prefiltering to top {args.top}...")
    shortlist = prefilter.rank(jobs)[: args.top]
    system = prompts.build_system_prompt(profile, cv)
    evaluated: list[dict[str, Any]] = []
    for i, job in enumerate(shortlist, 1):
        ctx = prompts.build_job_context(job)
        try:
            text, usage = orc.chat(system, f"Evaluate this job:\n\n{ctx}",
                                   model=args.model, max_tokens=1400)
            e = orc.extract_json(text)
        except Exception as ex:  # noqa: BLE001
            print(f"  [{i}/{len(shortlist)}] {job.get('company_name')} — FAILED: {ex}")
            continue
        job["_eval"] = e
        evaluated.append(job)
        print(f"  [{i}/{len(shortlist)}] {job.get('company_name'):20.20} {job.get('job_title','')[:36]:36} "
              f"→ {e.get('grade')} {e.get('overall_score')} ({e.get('recommendation')})")
    evaluated.sort(key=lambda j: -(j["_eval"].get("overall_score") or 0))
    ts = _ts()
    write_ranked_csv(evaluated, config.OUT_DIR / f"ranked_{ts}.csv")
    write_ranked_md(evaluated, config.OUT_DIR / f"ranked_{ts}.md", args.model or config.OPENROUTER_MODEL)
    (config.OUT_DIR / f"ranked_{ts}.json").write_text(
        json.dumps([{**{k: j[k] for k in ("job_id", "job_title", "company_name",
                    "location", "role_domain", "apply_url")}, "eval": j["_eval"]}
                    for j in evaluated], indent=2), encoding="utf-8")
    apply = [j for j in evaluated if j["_eval"].get("recommendation") == "Apply"]
    print(f"\nDone. {len(evaluated)} evaluated, {len(apply)} marked APPLY.")
    print(f"Reports → {config.OUT_DIR}/ranked_{ts}.(md|csv|json)")


def cmd_tailor(args, profile, cv) -> None:
    if not config.openrouter_ready():
        sys.exit("OPENROUTER_API_KEY missing. Pass --api-key sk-or-...")
    jobs = sb.fetch_jobs(limit=args.limit)
    match = next((j for j in jobs if str(j.get("job_id")) == str(args.tailor)), None)
    if not match:
        sys.exit(f"job_id {args.tailor} not found in active jobs.")
    system = prompts.build_system_prompt(profile, cv)
    ctx = prompts.build_job_context(match)
    text, _ = orc.chat(system, f"Evaluate this job:\n\n{ctx}", model=args.model, max_tokens=1400)
    try:
        ev = orc.extract_json(text)
    except Exception:  # noqa: BLE001
        ev = None
    tailored, _ = orc.chat(
        "You are an expert CV writer. Output only markdown.",
        prompts.build_tailor_prompt(cv, match, ev),
        model=args.model, max_tokens=4096,
    )
    ts = _ts()
    slug = (match.get("company_name") or "job").lower().replace(" ", "-")
    out = config.OUT_DIR / f"cv_{slug}_{ts}.md"
    out.write_text(tailored, encoding="utf-8")
    print(f"Tailored CV → {out}")
    if ev:
        print(f"Eval: {ev.get('grade')} {ev.get('overall_score')} — {ev.get('recommendation')}")


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in (s or "job").lower()).strip("-")[:40]


def _write_brief(job, ev, packet_dir: Path) -> None:
    main_sk = ", ".join(job.get("main_skills") or []) or "n/a"
    lines = [
        f"# {job.get('job_title')} — {job.get('company_name')}",
        "",
        f"- **Apply:** {job.get('apply_url')}",
        f"- **Location:** {job.get('location')}  ·  **Domain:** {job.get('role_domain')}",
        f"- **job_id:** `{job.get('job_id')}`",
    ]
    if ev:
        lines += [
            f"- **Verdict:** {ev.get('recommendation')}  ·  **Grade:** {ev.get('grade')}  ·  **Score:** {ev.get('overall_score')}",
            f"- **Fit:** role {ev.get('role_fit')} · comp {ev.get('comp_fit')} · growth {ev.get('growth_fit')} · culture {ev.get('culture_fit')} · risk {ev.get('risk_score')}",
            "",
            f"**Summary:** {ev.get('summary')}",
            "",
            f"**Application angle:** {ev.get('application_angle','')}",
            "",
            f"**Strengths to lead with:** {'; '.join(ev.get('strengths', []))}",
            f"**Gaps to address:** {'; '.join(ev.get('concerns', []))}",
        ]
    lines += ["", f"**Job's required skills:** {main_sk}"]
    (packet_dir / "brief.md").write_text("\n".join(lines), encoding="utf-8")


def cmd_tailor_top(args, profile, cv) -> None:
    if not config.openrouter_ready():
        sys.exit("OPENROUTER_API_KEY missing. Pass --api-key sk-or-...")
    ok, msg = render.have_renderer()
    print(f"PDF renderer: {msg}")
    jobs = sb.fetch_jobs(batch_date=args.batch_date, limit=args.limit)
    shortlist = prefilter.rank(jobs)[: args.top]
    print(f"Building {len(shortlist)} application packets (eval + tailor + PDF)...")
    system = prompts.build_system_prompt(profile, cv)
    root = config.OUT_DIR / f"applications_{_ts()}"
    root.mkdir(parents=True, exist_ok=True)
    index = ["# Application Packets", ""]
    for i, job in enumerate(shortlist, 1):
        ctx = prompts.build_job_context(job)
        ev = None
        try:
            text, _ = orc.chat(system, f"Evaluate this job:\n\n{ctx}", model=args.model, max_tokens=1400)
            ev = orc.extract_json(text)
        except Exception as ex:  # noqa: BLE001
            print(f"  [{i}] eval failed for {job.get('company_name')}: {ex}")
        try:
            tailored, _ = orc.chat(
                "You are an expert CV writer. Output only clean markdown.",
                prompts.build_tailor_prompt(cv, job, ev),
                model=args.model, max_tokens=4096,
            )
        except Exception as ex:  # noqa: BLE001
            print(f"  [{i}] tailor failed for {job.get('company_name')}: {ex}")
            continue
        pdir = root / f"{i:02d}_{_slug(job.get('company_name'))}_{_slug(job.get('job_title'))}"
        pdir.mkdir(parents=True, exist_ok=True)
        cv_md = pdir / "cv.md"
        cv_md.write_text(tailored, encoding="utf-8")
        _write_brief(job, ev, pdir)
        pdf_note = ""
        if ok:
            try:
                render.md_to_pdf(cv_md, pdir / "cv.pdf")
                pdf_note = " + PDF"
            except Exception as ex:  # noqa: BLE001
                pdf_note = f" (PDF failed: {ex})"
        grade = ev.get("grade") if ev else "?"
        rec = ev.get("recommendation") if ev else "?"
        print(f"  [{i:02d}] {job.get('company_name'):20.20} {grade:3} {rec:9} → {pdir.name}{pdf_note}")
        index.append(f"{i}. **{job.get('company_name')}** — {job.get('job_title')} "
                     f"({grade}/{rec}) → `{pdir.name}/` · [apply]({job.get('apply_url')})")
    (root / "INDEX.md").write_text("\n".join(index), encoding="utf-8")
    print(f"\nPackets → {root}")
    print("Each folder: cv.md, cv.pdf, brief.md. See INDEX.md.")


def cmd_referrals(args, profile, cv) -> None:
    conn_path = Path(args.connections) if args.connections else (config.HERE / "Connections.csv")
    if not conn_path.exists():
        sys.exit(
            f"Connections file not found: {conn_path}\n"
            "Export it from LinkedIn → Settings → Data Privacy → Get a copy of your data "
            "→ Connections → download Connections.csv, then pass --connections <path>."
        )
    connections = ref.load_connections(conn_path)
    jobs = sb.fetch_jobs(batch_date=args.batch_date, limit=args.limit)
    print(f"Loaded {len(connections)} connections; matching against "
          f"{len({j.get('company_name') for j in jobs})} companies with open roles...")
    ranked = ref.rank_referrers(connections, jobs)
    if not ranked:
        print("No connections matched a target company. Widen the job set or check the CSV.")
        return

    use_llm = config.openrouter_ready()
    ts = _ts()
    md = [f"# Referral Targets — {datetime.now():%Y-%m-%d %H:%M}",
          f"\nFrom your {len(connections)} connections · {len(ranked)} target companies have a warm contact.\n"]
    rows_csv: list[list[Any]] = []
    for company, conns in ranked.items():
        md.append(f"\n## {company}  ({len(conns)} contact{'s' if len(conns) != 1 else ''})")
        for c in conns[: args.per_company]:
            if use_llm:
                try:
                    draft, _ = orc.chat(
                        "You write short, warm, specific LinkedIn referral messages. 3-4 sentences, no fluff, one ask.",
                        f"Candidate: {profile.get('full_name')} — {profile.get('superpower','')}\n"
                        f"Contact: {c['name']}, {c['position']} at {company}\n"
                        f"Open role: {c['sample_job']} ({c['sample_apply_url']})\n"
                        f"Write the referral ask message.",
                        model=args.model, max_tokens=300)
                except Exception:  # noqa: BLE001
                    draft = ref.template_ask(c, company, profile)
            else:
                draft = ref.template_ask(c, company, profile)
            md += [
                f"\n### {c['name']} — {c['position']}  (score {c['score']})",
                f"- {', '.join(c['why'])}" + (f" · ✉ {c['email']}" if c['email'] else ""),
                f"- {c['url']}",
                f"- **Ask draft:** {draft}",
            ]
            rows_csv.append([company, c['name'], c['position'], c['score'],
                             ", ".join(c['why']), c['email'], c['url'],
                             c['sample_job'], c['sample_apply_url'], draft])

    out_md = config.OUT_DIR / f"referrals_{ts}.md"
    out_md.write_text("\n".join(md), encoding="utf-8")
    with (config.OUT_DIR / f"referrals_{ts}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["company", "name", "position", "score", "why", "email", "url",
                    "sample_job", "apply_url", "ask_draft"])
        w.writerows(rows_csv)
    total = sum(len(c) for c in ranked.values())
    print(f"Matched {total} warm contacts across {len(ranked)} companies "
          f"({'LLM-drafted asks' if use_llm else 'template asks — add --api-key for tailored drafts'}).")
    print(f"Report → {out_md}")


def main() -> None:
    p = argparse.ArgumentParser(description="Career Ops Agent")
    p.add_argument("--dry-run", action="store_true", help="heuristic shortlist only, no LLM")
    p.add_argument("--rank", action="store_true", help="deep-evaluate shortlist via OpenRouter")
    p.add_argument("--tailor", metavar="JOB_ID", help="tailor CV for a specific job_id")
    p.add_argument("--tailor-top", action="store_true",
                   help="batch: eval + tailor + PDF the top --top jobs into application packets")
    p.add_argument("--referrals", action="store_true",
                   help="rank your LinkedIn connections as referral targets for the job set")
    p.add_argument("--connections", default=None, help="path to LinkedIn Connections.csv")
    p.add_argument("--per-company", type=int, default=3, help="max referrers listed per company")
    p.add_argument("--top", type=int, default=20, help="how many jobs to deep-evaluate (default 20)")
    p.add_argument("--limit", type=int, default=5000, help="max jobs to fetch from Supabase")
    p.add_argument("--batch-date", type=int, default=None, help="restrict to a scrape batch, e.g. 20260527")
    p.add_argument("--model", default=None, help="OpenRouter model slug (default from env)")
    p.add_argument("--api-key", default=None, help="OpenRouter API key (overrides env)")
    args = p.parse_args()

    if args.api_key:
        config.OPENROUTER_API_KEY = args.api_key
    if not config.supabase_ready():
        sys.exit("SUPABASE_URL / SUPABASE_SERVICE_KEY missing (expected in ../scraper/.env).")
    config.OUT_DIR.mkdir(exist_ok=True)

    profile = load_profile(config.PROFILE_PATH)
    cv = load_cv(config.CV_PATH)

    if args.referrals:
        cmd_referrals(args, profile, cv)
    elif args.tailor_top:
        cmd_tailor_top(args, profile, cv)
    elif args.tailor:
        cmd_tailor(args, profile, cv)
    elif args.rank:
        cmd_rank(args, profile, cv)
    else:
        cmd_dry_run(args, profile, cv)


if __name__ == "__main__":
    main()
