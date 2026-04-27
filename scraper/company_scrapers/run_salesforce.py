#!/usr/bin/env python3
"""Standalone runner for Salesforce India Job Scraper.
ATS: Workday (salesforce.wd12.myworkdayjobs.com/External_Career_Site)
~160 India jobs.
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from scraper_utils import *

COMPANY    = "Salesforce"
OUTPUT_DIR = get_output_dir(COMPANY)

print("=" * 60)
print("SALESFORCE INDIA JOB SCRAPER")
print("ATS: Workday (salesforce.wd12.myworkdayjobs.com/External_Career_Site)")
print("=" * 60)
print(f"Output directory: {OUTPUT_DIR}")

salesforce_jobs = scrape_workday(
    tenant="salesforce",
    instance="wd12",
    career_site="External_Career_Site",
    company_name="Salesforce",
    industry="Technology / CRM / SaaS",
    location_filter="India",
    max_jobs=500,
)

print(f"\nTotal Salesforce India jobs: {len(salesforce_jobs)}")
df = save_results(salesforce_jobs, COMPANY, OUTPUT_DIR)
if df is not None:
    cols = ["title", "location_city", "seniority_level", "business_unit", "job_url"]
    cols = [c for c in df.columns if c in cols]
    print(df[cols].head(10).to_string())
