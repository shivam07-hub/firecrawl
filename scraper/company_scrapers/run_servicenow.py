#!/usr/bin/env python3
"""Standalone runner for ServiceNow India Job Scraper.
ATS: SmartRecruiters (careers.smartrecruiters.com/ServiceNow)
Direct API — full JD + business unit in every response. ~450 India jobs.
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from scraper_utils import *

COMPANY    = "ServiceNow"
OUTPUT_DIR = get_output_dir(COMPANY)

print("=" * 60)
print("SERVICENOW INDIA JOB SCRAPER")
print("ATS: SmartRecruiters (careers.smartrecruiters.com/ServiceNow)")
print("=" * 60)
print(f"Output directory: {OUTPUT_DIR}")

servicenow_jobs = scrape_smartrecruiters(
    company_id="ServiceNow",
    company_name="ServiceNow",
    industry="Technology / IT Service Management / SaaS",
    country="",          # fetch global, India filtered in scrape_smartrecruiters via is_india()
    max_jobs=500,
)

print(f"\nTotal ServiceNow India jobs: {len(servicenow_jobs)}")
df = save_results(servicenow_jobs, COMPANY, OUTPUT_DIR)
if df is not None:
    cols = ["title", "location_city", "seniority_level", "business_unit", "job_url"]
    cols = [c for c in df.columns if c in cols]
    print(df[cols].head(10).to_string())
