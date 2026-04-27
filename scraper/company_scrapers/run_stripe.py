#!/usr/bin/env python3
"""Standalone runner for Stripe India Job Scraper.
ATS: Greenhouse (boards-api.greenhouse.io/v1/boards/stripe)
Direct API — full JD in every response. ~60 India jobs across offices.
"""
import sys
from pathlib import Path
from datetime import datetime

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from scraper_utils import *
import requests

COMPANY    = "Stripe"
OUTPUT_DIR = get_output_dir(COMPANY)

print("=" * 60)
print("STRIPE INDIA JOB SCRAPER")
print("ATS: Greenhouse (boards-api.greenhouse.io/v1/boards/stripe)")
print("=" * 60)
print(f"Output directory: {OUTPUT_DIR}")

# Use scraper_utils Greenhouse helper first
stripe_jobs = scrape_greenhouse(
    board_token="stripe",
    company_name="Stripe",
    industry="Financial Technology / Payments",
    location_filter="",   # global fetch; India filter applied inside helper
    max_jobs=500,
)

# Greenhouse sometimes lists APAC / city-level offices — catch any missed
if len(stripe_jobs) < 5:
    print("\n  Falling back to full Greenhouse listing + manual India filter...")
    session = get_session()
    resp = session.get(
        "https://boards-api.greenhouse.io/v1/boards/stripe/jobs",
        params={"content": "true"},
        timeout=30,
    )
    if resp.status_code == 200:
        india_kw = {"india", "bengaluru", "bangalore", "mumbai", "pune",
                    "chennai", "hyderabad", "delhi", "gurugram", "noida", "apac"}
        seen_ids = {j["job_id"] for j in stripe_jobs}
        for p in resp.json().get("jobs", []):
            loc = p.get("location", {}).get("name", "").lower()
            offices = " ".join(
                o.get("location", "") + " " + o.get("name", "")
                for o in p.get("offices", [])
            ).lower()
            if not any(k in loc or k in offices for k in india_kw):
                continue
            jid = str(p.get("id", ""))
            if jid in seen_ids:
                continue
            dept = (p.get("departments", [{}])[0].get("name", "")
                    if p.get("departments") else "")
            stripe_jobs.append({
                "job_id":           jid,
                "title":            p.get("title", ""),
                "company_name":     "Stripe",
                "job_url":          p.get("absolute_url", ""),
                "source_api_url":   "https://boards-api.greenhouse.io/v1/boards/stripe/jobs",
                "business_unit":    dept,
                "raw_jd_text":      html_to_text(p.get("content", "")),
                "location_city":    p.get("location", {}).get("name", "India").split(",")[0].strip(),
                "location_country": "India",
                "industry":         "Financial Technology / Payments",
                "date_posted":      (p.get("updated_at", "")[:10]
                                     or datetime.now().strftime("%Y-%m-%d")),
                "is_active":        True,
                "salary_currency":  "INR",
                "source_platform":  "Greenhouse",
            })

print(f"\nTotal Stripe India jobs: {len(stripe_jobs)}")
df = save_results(stripe_jobs, COMPANY, OUTPUT_DIR)
if df is not None:
    cols = ["title", "location_city", "seniority_level", "business_unit", "job_url"]
    cols = [c for c in df.columns if c in cols]
    print(df[cols].head(10).to_string())
