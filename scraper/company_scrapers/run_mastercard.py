#!/usr/bin/env python3
"""Standalone runner for Mastercard India Job Scraper.
ATS: Workday (mastercard.wd1.myworkdayjobs.com/CorporateCareers)
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from scraper_utils import *

COMPANY    = "Mastercard"
OUTPUT_DIR = get_output_dir(COMPANY)

print("=" * 60)
print("MASTERCARD INDIA JOB SCRAPER")
print("ATS: Workday (mastercard.wd1.myworkdayjobs.com/CorporateCareers)")
print("=" * 60)
print(f"Output directory: {OUTPUT_DIR}")

mastercard_jobs = scrape_workday(
    tenant="mastercard",
    instance="wd1",
    career_site="CorporateCareers",
    company_name="Mastercard",
    industry="Financial Technology / Payments",
    location_filter="India",
    max_jobs=500,
)

print(f"\nTotal Mastercard India jobs: {len(mastercard_jobs)}")
df = save_results(mastercard_jobs, COMPANY, OUTPUT_DIR)
if df is not None:
    cols = ["title", "location_city", "seniority_level", "business_unit", "job_url"]
    cols = [c for c in df.columns if c in cols]
    print(df[cols].head(10).to_string())
