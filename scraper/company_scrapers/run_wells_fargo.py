#!/usr/bin/env python3
"""Standalone runner for Wells Fargo India Job Scraper.
ATS: Workday (wf.wd1.myworkdayjobs.com/WellsFargoJobs)
~235 India jobs; scrape_workday() fetches JD from CXS detail endpoint.
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from scraper_utils import *

COMPANY    = "Wells Fargo"
OUTPUT_DIR = get_output_dir(COMPANY)

print("=" * 60)
print("WELLS FARGO INDIA JOB SCRAPER")
print("ATS: Workday (wf.wd1.myworkdayjobs.com/WellsFargoJobs)")
print("=" * 60)
print(f"Output directory: {OUTPUT_DIR}")

wells_fargo_jobs = scrape_workday(
    tenant="wf",
    instance="wd1",
    career_site="WellsFargoJobs",
    company_name="Wells Fargo",
    industry="Banking / Financial Services",
    location_filter="India",
    max_jobs=500,
)

print(f"\nTotal Wells Fargo India jobs: {len(wells_fargo_jobs)}")
df = save_results(wells_fargo_jobs, COMPANY, OUTPUT_DIR)
if df is not None:
    cols = ["title", "location_city", "seniority_level", "business_unit", "job_url"]
    cols = [c for c in df.columns if c in cols]
    print(df[cols].head(10).to_string())
