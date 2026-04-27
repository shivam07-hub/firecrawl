#!/usr/bin/env python3
"""Standalone runner for HCL Technologies India Job Scraper.
ATS: Workday (hcltech.wd3.myworkdayjobs.com/HCLTech)
Tenant verified from notebook — was listed as 'unconfirmed' in KNOWN_PORTALS.md.
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from scraper_utils import *

COMPANY    = "HCL Technologies"
OUTPUT_DIR = get_output_dir(COMPANY)

print("=" * 60)
print("HCL TECHNOLOGIES INDIA JOB SCRAPER")
print("ATS: Workday (hcltech.wd3.myworkdayjobs.com/HCLTech)")
print("=" * 60)
print(f"Output directory: {OUTPUT_DIR}")

hcl_jobs = scrape_workday(
    tenant="hcltech",
    instance="wd3",
    career_site="HCLTech",
    company_name="HCL Technologies",
    industry="IT Services & Consulting",
    location_filter="India",
    max_jobs=500,
)

print(f"\nTotal HCL Technologies India jobs: {len(hcl_jobs)}")
df = save_results(hcl_jobs, COMPANY, OUTPUT_DIR)
if df is not None:
    cols = ["title", "location_city", "seniority_level", "business_unit", "job_url"]
    cols = [c for c in df.columns if c in cols]
    print(df[cols].head(10).to_string())
