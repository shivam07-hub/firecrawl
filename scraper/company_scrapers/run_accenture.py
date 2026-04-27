#!/usr/bin/env python3
"""Standalone runner for Accenture India Job Scraper.
ATS: Workday (accenture.wd103.myworkdayjobs.com/AccentureCareers)
~1800 unique India jobs. scrape_workday() deduplicates by jobReqId during pagination.
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from scraper_utils import *

COMPANY    = "Accenture"
OUTPUT_DIR = get_output_dir(COMPANY)

print("=" * 60)
print("ACCENTURE INDIA JOB SCRAPER")
print("ATS: Workday (accenture.wd103.myworkdayjobs.com/AccentureCareers)")
print("NOTE: broad India fetch — dedup applied during pagination")
print("=" * 60)
print(f"Output directory: {OUTPUT_DIR}")

accenture_jobs = scrape_workday(
    tenant="accenture",
    instance="wd103",
    career_site="AccentureCareers",
    company_name="Accenture",
    industry="Consulting & IT Services",
    location_filter="India",
    max_jobs=500,
)

print(f"\nTotal Accenture India jobs: {len(accenture_jobs)}")
df = save_results(accenture_jobs, COMPANY, OUTPUT_DIR)
if df is not None:
    cols = ["title", "location_city", "seniority_level", "business_unit", "job_url"]
    cols = [c for c in df.columns if c in cols]
    print(df[cols].head(10).to_string())
