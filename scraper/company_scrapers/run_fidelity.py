#!/usr/bin/env python3
"""Standalone runner for Fidelity Investments India Job Scraper.
ATS: Workday — tries FMR (Fidelity Management & Research) first, then FIL (Fidelity International).
~30 India jobs combined.
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from scraper_utils import *

COMPANY    = "Fidelity Investments"
OUTPUT_DIR = get_output_dir(COMPANY)

print("=" * 60)
print("FIDELITY INVESTMENTS INDIA JOB SCRAPER")
print("ATS: Workday — FMR (wd1) + FIL (wd3) tenants")
print("=" * 60)
print(f"Output directory: {OUTPUT_DIR}")

fidelity_jobs = scrape_workday(
    tenant="fmr",
    instance="wd1",
    career_site="FidelityCareers",
    company_name="Fidelity Investments",
    industry="Financial Services",
    location_filter="India",
    max_jobs=500,
)
print(f"  FMR tenant: {len(fidelity_jobs)} jobs")

# Fidelity International (separate Workday tenant)
fil_jobs = scrape_workday(
    tenant="fil",
    instance="wd3",
    career_site="001",
    company_name="Fidelity Investments",
    industry="Financial Services",
    location_filter="India",
    max_jobs=200,
)
print(f"  FIL tenant: {len(fil_jobs)} jobs")

# Merge, dedup by job_id
seen = {j.get("job_id") for j in fidelity_jobs}
for j in fil_jobs:
    if j.get("job_id") not in seen:
        fidelity_jobs.append(j)
        seen.add(j.get("job_id"))

print(f"\nTotal Fidelity India jobs: {len(fidelity_jobs)}")
df = save_results(fidelity_jobs, COMPANY, OUTPUT_DIR)
if df is not None:
    cols = ["title", "location_city", "seniority_level", "business_unit", "job_url"]
    cols = [c for c in df.columns if c in cols]
    print(df[cols].head(10).to_string())
