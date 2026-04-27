#!/usr/bin/env python3
"""Standalone runner for Chanel India Job Scraper.
ATS: Workday (cc.wd3.myworkdayjobs.com/ChanelCareers)
Low volume (~5 India jobs) — luxury brand, selective hiring.
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from scraper_utils import *

COMPANY    = "Chanel"
OUTPUT_DIR = get_output_dir(COMPANY)

print("=" * 60)
print("CHANEL INDIA JOB SCRAPER")
print("ATS: Workday (cc.wd3.myworkdayjobs.com/ChanelCareers)")
print("=" * 60)
print(f"Output directory: {OUTPUT_DIR}")

chanel_jobs = scrape_workday(
    tenant="cc",
    instance="wd3",
    career_site="ChanelCareers",
    company_name="Chanel",
    industry="Luxury / Fashion & Beauty",
    location_filter="India",
    max_jobs=500,
)

print(f"\nTotal Chanel India jobs: {len(chanel_jobs)}")
df = save_results(chanel_jobs, COMPANY, OUTPUT_DIR)
if df is not None:
    cols = ["title", "location_city", "seniority_level", "business_unit", "job_url"]
    cols = [c for c in df.columns if c in cols]
    print(df[cols].head(10).to_string())
