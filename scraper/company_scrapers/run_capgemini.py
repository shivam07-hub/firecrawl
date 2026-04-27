#!/usr/bin/env python3
"""Standalone runner for Capgemini India Job Scraper.
ATS: Workday (capgemini.wd3.myworkdayjobs.com/Global)
Tenant verified from notebook — was listed as 'unconfirmed' in KNOWN_PORTALS.md.
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from scraper_utils import *

COMPANY    = "Capgemini"
OUTPUT_DIR = get_output_dir(COMPANY)

print("=" * 60)
print("CAPGEMINI INDIA JOB SCRAPER")
print("ATS: Workday (capgemini.wd3.myworkdayjobs.com/Global)")
print("=" * 60)
print(f"Output directory: {OUTPUT_DIR}")

capgemini_jobs = scrape_workday(
    tenant="capgemini",
    instance="wd3",
    career_site="Global",
    company_name="Capgemini",
    industry="IT Services & Consulting",
    location_filter="India",
    max_jobs=500,
)

print(f"\nTotal Capgemini India jobs: {len(capgemini_jobs)}")
df = save_results(capgemini_jobs, COMPANY, OUTPUT_DIR)
if df is not None:
    cols = ["title", "location_city", "seniority_level", "business_unit", "job_url"]
    cols = [c for c in df.columns if c in cols]
    print(df[cols].head(10).to_string())
