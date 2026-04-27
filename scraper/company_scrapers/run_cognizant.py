#!/usr/bin/env python3
"""Standalone runner for Cognizant India Job Scraper.
Source: careers.cognizant.com/india-en/jobs (XML feed)
No Selenium needed — direct XML GET, full JD in feed.
~500 India jobs across all functions.
"""
import sys
from pathlib import Path
from datetime import datetime

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from scraper_utils import *
from bs4 import BeautifulSoup

COMPANY    = "Cognizant"
OUTPUT_DIR = get_output_dir(COMPANY)

print("=" * 60)
print("COGNIZANT INDIA JOB SCRAPER")
print("ATS: Cognizant XML feed (careers.cognizant.com/india-en/jobs/xml/)")
print("=" * 60)
print(f"Output directory: {OUTPUT_DIR}")

XML_URL  = "https://careers.cognizant.com/india-en/jobs/xml/?rss=true"
session  = get_session()
cognizant_jobs = []

try:
    resp = session.get(XML_URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "xml")
    jobs_xml = soup.find_all("job") or soup.find_all("item")
    print(f"  XML feed returned {len(jobs_xml)} entries")

    for job_el in jobs_xml:
        def txt(tag):
            el = job_el.find(tag)
            return el.get_text(strip=True) if el else ""

        country = txt("country")
        if country.lower() != "india":
            continue

        title   = txt("title")
        if not title or not is_valid_job_title(title):
            continue

        url_el  = job_el.find("url") or job_el.find("link")
        link    = url_el.get_text(strip=True) if url_el else ""
        req_id  = txt("requisitionid") or (link.split("/")[-1] if link else str(len(cognizant_jobs)))
        desc    = html_to_text(txt("description"))
        city    = txt("city") or "India"
        pub_date = txt("date")
        category = txt("category")
        remote   = txt("remotetype").lower()
        work_mode = ("remote" if "remote" in remote
                     else "hybrid" if "hybrid" in remote
                     else "onsite")

        cognizant_jobs.append({
            "job_id":           req_id,
            "title":            title,
            "company_name":     "Cognizant",
            "job_url":          link,
            "source_api_url":   XML_URL,
            "business_unit":    category,
            "raw_jd_text":      desc,
            "location_city":    city,
            "location_country": "India",
            "industry":         "IT Services & Consulting",
            "work_mode":        work_mode,
            "date_posted":      pub_date[:10] if pub_date else datetime.now().strftime("%Y-%m-%d"),
            "is_active":        True,
            "salary_currency":  "INR",
            "source_platform":  "Cognizant XML Feed",
        })

except Exception as e:
    print(f"  [ERROR] {e}")
    import traceback; traceback.print_exc()

print(f"\nTotal Cognizant India jobs: {len(cognizant_jobs)}")
df = save_results(cognizant_jobs, COMPANY, OUTPUT_DIR)
if df is not None:
    cols = ["title", "location_city", "seniority_level", "business_unit", "job_url"]
    cols = [c for c in df.columns if c in cols]
    print(df[cols].head(10).to_string())
