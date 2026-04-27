#!/usr/bin/env python3
"""Standalone runner for Eli Lilly India Job Scraper.
ATS: Workday (lilly.wd5.myworkdayjobs.com/LLY)
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from scraper_utils import *

COMPANY    = "Eli Lilly"
OUTPUT_DIR = get_output_dir(COMPANY)

print("=" * 60)
print("ELI LILLY INDIA JOB SCRAPER")
print("ATS: Workday (lilly.wd5.myworkdayjobs.com/LLY)")
print("=" * 60)
print(f"Output directory: {OUTPUT_DIR}")

eli_lilly_jobs = scrape_workday(
    tenant="lilly",
    instance="wd5",
    career_site="LLY",
    company_name="Eli Lilly",
    industry="Pharmaceutical / Life Sciences",
    location_filter="India",
    max_jobs=500,
)

print(f"\nTotal Eli Lilly India jobs: {len(eli_lilly_jobs)}")
df = save_results(eli_lilly_jobs, COMPANY, OUTPUT_DIR)
if df is not None:
    cols = ["title", "location_city", "seniority_level", "business_unit", "job_url"]
    cols = [c for c in df.columns if c in cols]
    print(df[cols].head(10).to_string())
