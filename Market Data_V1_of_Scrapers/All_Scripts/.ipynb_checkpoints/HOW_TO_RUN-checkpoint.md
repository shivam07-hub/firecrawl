# Job Scraper Suite v2.0 - Quick Start Guide

## What Changed (v2 vs v1)
- **Correct career portal URLs** for all 18 companies (v1 used fake/guessed API endpoints)
- **Workday API scraper** for Novartis, Sanofi, Fidelity, Capgemini, HCL (JSON API, no browser needed)
- **SmartRecruiters API** for Syngenta (direct JSON API)
- **Eightfold API** for Morgan Stanley
- **Selenium with correct selectors** for Apple, Microsoft, Google, TCS, Infosys, Wipro, Cognizant, Goldman Sachs, Accenture, IBM, L'Oreal
- **Fixed consolidation** - picks up ALL output CSVs, not just current month
- **Shared utilities** (`scraper_utils.py`) - no more duplicated code across 18 notebooks

## File Structure
```
All_Scripts/
├── scraper_utils.py                      # Shared utilities (normalize, save, Workday/SmartRecruiters scrapers)
├── create_all_scrapers_v2.py             # Generates all 18 notebooks
├── MASTER_Job_Scraper_Orchestrator_v2.py # Full pipeline: generate → scrape → consolidate
├── RUN_ALL_AND_CONSOLIDATE.py            # Just consolidation (after you've run scrapers)
├── [18 scraper notebooks]                # Individual company scrapers
└── HOW_TO_RUN.md                         # This file
```

## How to Run

### Option A: Run everything automatically
```bash
cd ~/Job_Scrapers/All_Scripts
python MASTER_Job_Scraper_Orchestrator_v2.py
```
This will: regenerate notebooks → run all 18 scrapers → consolidate into master Excel.

### Option B: Run individual scrapers in Jupyter
1. Open Jupyter: `jupyter notebook`
2. Navigate to `All_Scripts/`
3. Open any scraper notebook (e.g., `Microsoft India Job Scrapper.ipynb`)
4. Run All Cells
5. Check output in `~/Job_Scrapers/{Company}/Outputs/{YYYY_MM}/`

### Option C: Just consolidate existing data
```bash
python MASTER_Job_Scraper_Orchestrator_v2.py --skip-scrape --skip-generate
```

## Dependencies
```bash
pip install selenium webdriver-manager pandas openpyxl requests beautifulsoup4 lxml playwright
playwright install chromium
```

## Troubleshooting

**Scraper returns 0 jobs:**
- The career portal may have changed its HTML structure. Open the URL in Chrome, inspect the page, and update the CSS selectors in the notebook.
- For Workday companies: check the tenant/instance/career_site values haven't changed.

**Selenium timeout:**
- Increase `time.sleep()` values - some sites load slowly.
- Try running without `--headless` to debug visually.

**Consolidation missing a company:**
- Check that the scraper output is a `.csv` file in `~/Job_Scrapers/{Company}/Outputs/` or `~/Job_Scrapers/{Company}/Output/`.

## Companies by ATS Platform

| Platform | Companies | Scraping Method |
|----------|-----------|----------------|
| Workday JSON API | Novartis, Sanofi, Fidelity, Capgemini*, HCL* | `scrape_workday()` - no browser needed |
| SmartRecruiters API | Syngenta | `scrape_smartrecruiters()` - no browser needed |
| Eightfold API | Morgan Stanley | `scrape_eightfold()` - no browser needed |
| Custom + Selenium | Apple, Microsoft, Google, TCS, Infosys, Wipro, Cognizant, Goldman Sachs, Accenture, IBM, L'Oreal | Selenium headless Chrome |

*Capgemini and HCL try Workday first, fall back to Selenium if Workday endpoint doesn't match.
