# KNOWN_PORTALS.md — Careers Portal Registry
**Last verified: 2026-04-19 (Part 4) — 1-job investigation: Zomato confirmed 1 real job (⬇️); Wipro corrected ATS → SAP SF hcm55.sapsf.eu (auth-gated 🔴); Infosys confirmed Angular SPA (🔴 no direct API); Swiggy/Walmart confirmed JS-only (no public API). 10 small boutiques marked ⬇️ low-priority. Oracle _oracle() fix: careers_url now read → Firecrawl fallback unblocked for JP Morgan/Honeywell/TI/BNY.**

Each entry: Company | Human Careers URL | ATS Platform | Scraping API / Endpoint | India Filter Param | Status | Notes

---

## HOW TO READ THIS FILE

| Column | Meaning |
|--------|---------|
| **Careers URL** | Human-visible page — what you'd visit in a browser |
| **ATS** | Underlying platform (Workday, Greenhouse, SmartRecruiters, etc.) |
| **Scraping Endpoint** | The actual API/URL to hit programmatically |
| **India Filter** | How to narrow to India jobs in the API |
| **Status** | `✅ working` / `⚠️ broken` / `🔴 no-india-jobs` / `🟡 js-required` / `🔒 login-required` |

---

## WORKDAY COMPANIES
*API pattern: `POST https://{tenant}.{instance}.myworkdayjobs.com/wday/cxs/{tenant}/{career_site}/jobs`*
*Body: `{"appliedFacets": {"<facet_param>": ["<india_uuid>"]}, "limit": 20, "offset": 0, "searchText": ""}`*
*Note: facet_param varies per tenant — scraper auto-discovers it alongside the India UUID.*
*Some tenants return 303 (Cloudflare) — scraper falls back to Firecrawl automatically.*

| Company | Careers URL | Tenant | Instance | Career Site | India Jobs | Status |
|---------|-------------|--------|----------|-------------|-----------|--------|
| Accenture | https://www.accenture.com/us-en/careers | accenture | wd103 | AccentureCareers | ~800+ | ✅ working |
| Airbus | https://www.airbus.com/en/careers | ag | wd3 | Airbus | ~150 | ✅ working |
| Chanel | https://cc.wd3.myworkdayjobs.com/ChanelCareers | cc | wd3 | ChanelCareers | 1 | ✅ working (1 India job only) |
| Eli Lilly | https://careers.lilly.com/us/en/india | lilly | wd5 | LillyCareers | 3 | 🔴 wrong ATS — Lilly migrated to Phenom People (careers.lilly.com); all Workday slugs 404; see OTHER PLATFORMS section |
| Engie | https://jobs.engie.com | engie | wd3 | ENGIE | ? | ✅ working — Firecrawl fallback uses careers_url (fixed 2026-04-11) |
| Fidelity Investments | https://jobs.fidelity.com | fmr | wd1 | FidelityCareers | ~80 | ✅ working |
| Mastercard | https://careers.mastercard.com/us/en/search-results | mastercard | wd1 | CorporateCareers | ? | 🔴 no India UUID — India facet not found in tenant; skip until manual XHR inspection confirms facet UUID |
| Novartis | https://www.novartis.com/careers | novartis | wd3 | Novartis_Careers | ~115 | ✅ working — career_site slug corrected 2026-04-12; broad mode fetches all India jobs |
| Salesforce | https://www.salesforce.com/company/careers/locations/india/ | salesforce | wd12 | External_Career_Site | ~169 | ✅ working — 169 India jobs scraped 2026-04-11 |
| Sanofi | https://www.sanofi.com/en/careers | sanofi | wd3 | SanofiCareers | ~300+ | ✅ working |
| Shell | https://www.shell.com/careers | shell | wd3 | ShellCareers | ~188 | ✅ working |
| Synopsys | https://careers.synopsys.com/ | synopsys | wd1 | SynopsysCareers | ? | ✅ working — Firecrawl fallback uses careers_url (fixed 2026-04-11) |
| Wells Fargo | https://www.wellsfargojobs.com/en/jobs/ | wf | wd1 | WellsFargoJobs | ~300+ | ✅ working |
| Philips | https://www.careers.philips.com/global/en | philips | wd3 | jobs-and-careers | ~48 | ✅ working — uses locationHierarchy1 facet (not locationCountry); hardcoded IDs in company_registry.py 2026-04-12 |
| BrowserStack | https://www.browserstack.com/careers | browserstack | wd3 | External | ? | 🔴 no India UUID — India facet not found in tenant; skip |
| Baker Hughes | https://careers.bakerhughes.com/global/en/search-results?qcountry=India | bakerhughes | wd5 | BakerHughes | ? | 🔴 no India UUID — India facet not found in tenant; skip |
| Dell | https://jobs.dell.com/en-us/search-jobs/India | dell | wd1 | External | ? | ✅ Workday tenant confirmed via XHR inspection 2026-04-16 |
| Haleon | https://www.haleon.com/careers | gsknch | wd3 | GSKCareers | ? | ✅ Workday tenant confirmed from URL gsknch.wd3.myworkdayjobs.com/GSKCareers |
| Capgemini | https://www.capgemini.com/in-en/careers/job-search/ | capgemini | wd3 | ⚠️ career site name unconfirmed | ? | ⚠️ Workday tenant found, correct career_site slug needed — try: Capgemini_Careers, CapgeminiCareers |
| HCL Technologies | https://careers.hcltech.com/go/India/9553955/ | hcltech | wd3 | ⚠️ career site name unconfirmed | ? | ⚠️ Workday tenant found, correct career_site slug needed — try: HCLTech_Careers, HCL_Careers |
| MSCI | https://careers.msci.com/ | msci | wd3 | ⚠️ career site name unconfirmed | ? | ⚠️ Old portal (careers.msci.com) is 404. Moved to Workday (msci.wd3) — career_site slug unknown. Try: MSCI, MSCIExternal, MSCI_External |
| Intel | https://jobs.intel.com/en/search | intel | wd1 | External | ~84 | ✅ working — searchText="india" mode (no India UUID in tenant); company_registry.py hardcoded; is_india() Python filter applied; fixed 2026-04-19 |
| State Street | https://careers.statestreet.com | statestreet | wd1 | Global | 351 | ✅ working — 351 India jobs scraped with full JDs via CXS; probed 2026-04-19 |
| DBS Bank | https://www.dbs.com/dbstechindia/index.html | dbs | wd3 | DBS_Careers | 285 | ✅ working — 285 India jobs scraped with full JDs via CXS; probed 2026-04-19 |
| BlackBerry | https://www.blackberry.com/us/en/company/careers | bb | wd3 | BlackBerry | ~39 total | 🟡 Workday CXS confirmed wd3/BlackBerry — India UUID TBD; probed 2026-04-19 |
| Lloyds Banking Group | https://www.lloydsbankinggroup.com/careers | lbg | wd3 | LBG_Careers | ~128 total | 🟡 Workday CXS confirmed wd3/LBG_Careers — India UUID TBD; probed 2026-04-19 |
| EA (Electronic Arts) | https://www.ea.com/careers | ea | wd5 | EA_Global | ? | 🟡 Workday confirmed via FC scrape — CXS returns 401; Firecrawl fallback via careers_url; probed 2026-04-19 |
| GE Aerospace | https://www.gecareers.com | ge | wd5 | GE_ExternalSite | ? | 🟡 Workday confirmed via FC scrape — CXS returns 422 (Cloudflare); Firecrawl fallback via careers_url; probed 2026-04-19 |
| Medtronic | https://www.medtronic.com/en-us/about/careers.html | medtronic | wd3 | MedtronicCareers | ? | 🟡 Workday confirmed via FC scrape — CXS returns 422 (Cloudflare); Firecrawl fallback via careers_url; probed 2026-04-19 |
| Oracle | https://www.oracle.com/careers | oracle | wd1 | OracleJobs | ? | 🟡 Workday confirmed via FC scrape — CXS returns 422 (Cloudflare); Firecrawl fallback via careers_url; probed 2026-04-19 |
| Bank of America | https://careers.bankofamerica.com | bankofamerica | wd1 | Global | ? | 🟡 Workday confirmed via FC scrape — CXS returns 422 (Cloudflare); Firecrawl fallback via careers_url; probed 2026-04-19 |
| Siemens | https://new.siemens.com/global/en/company/jobs.html | siemens | wd3 | External | ? | 🟡 Workday confirmed via FC scrape on wd3 — CXS returns 401; Firecrawl fallback via careers_url; probed 2026-04-19 |
| Inspire Brands | https://careers.inspirebrands.com | inspirebrands | wd1 | InspireBrandsCareers | ? | 🟡 Workday confirmed via FC scrape — CXS returns 422 (Cloudflare); Firecrawl fallback via careers_url; probed 2026-04-19 |
| Ford | https://www.ford.com/careers/ | fordcareers | wd12 | Ford_Careers | ? | 🟡 Workday confirmed via FC scrape — CXS 422; FC fallback via `https://fordcareers.wd12.myworkdayjobs.com/en-US/Ford_Careers?q=india`; probed 2026-04-19 |
| Unilever | https://careers.unilever.com/job-search?search%5B%5D=IN | unilever | wd3 | ⚠️ career_site unconfirmed | ? | 🟡 Workday confirmed — CXS 403; FC fallback via India-filtered careers.unilever.com URL; probed 2026-04-19 |
| Adobe | https://careers.adobe.com/us/en/india | adobe | wd5 | external_experienced | ? | 🟡 Workday confirmed via page source (`adobe.wd5.myworkdayjobs.com/en-US/external_experienced`) — CXS 422; FC fallback; probed 2026-04-19 |
| Hitachi Vantara | https://hitachivantara.wd3.myworkdayjobs.com/HitachiVantaraCareers | hitachivantara | wd3 | HitachiVantaraCareers | ? | 🟡 Workday confirmed — CXS 422 blocked; FC fallback via en-US URL with India filter; probed 2026-04-19 |
| Thomson Reuters | https://thomsonreuters.com/en/careers.html | thomsonreuters | wd3 | tr_External_Applicant | ? | 🟡 Workday confirmed (`thomsonreuters.wd3/tr_External_Applicant`) — CXS 422; FC fallback; probed 2026-04-19 |
| CGI | https://www.cgi.com/en/careers | cgicareers | wd3 | CGI | ? | 🟡 Workday confirmed (`cgicareers.wd3/CGI`) — CXS 422; FC fallback via careers_url; probed 2026-04-19 |
| ADP | https://jobs.adp.com | adp | wd5 | ADP | ? | 🟡 Workday confirmed (`adp.wd5/ADP`) — CXS 422; FC fallback; probed 2026-04-19 |
| Intuit | https://careers.intuit.com/job-search-results/?location=India | intuit | wd5 | Intuit | ? | 🟡 Workday tenant confirmed — CXS 422 blocked; careers.intuit.com returns only 212 chars (antibot); FC fallback on India-filtered URL; probed 2026-04-19 |
| Samsung | https://job.samsung.com/en/search/?search_keyword=&career_type=1&search_country=IND | samsungelectronics | wd3 | ⚠️ career_site unconfirmed | ? | 🟡 Workday suspected (`samsungelectronics.wd3`) — CXS 422 blocked; job.samsung.com also FC-blocked; FC fallback via careers_url TBD; probed 2026-04-19 |
| Carelon Global Solutions | https://www.carelonglobal.in/careers | elevancehealth | wd1 | carelonglobal_in | ? | 🟡 Workday confirmed (`elevancehealth.wd1/carelonglobal_in`) — only 7 total jobs, no India UUID found; FC fallback via careers_url; probed 2026-04-19 |
| Target | https://careers.target.com/jobs | target | wd5 | TargetCareers | ~265 | ✅ working — searchText="india" mode (no India UUID in tenant); company_registry.py hardcoded; is_india() Python filter applied; fixed 2026-04-19 |
| Broadcom | https://careers.broadcom.com/careers?query=&location=India | broadcom | wd1 | ⚠️ career_site unconfirmed | ? | 🟡 Workday suspected — all career_site slugs 404; broadcom.wd1 tenant confirmed; correct slug TBD (try: External, BroadcomCareers, BCICareers); FC-blocked; probed 2026-04-19 |
| 3M | https://www.3m.com/3M/en_US/careers-us/ | 3m | wd1 | Search | 81 | ✅ working — 81 India jobs, 100% JD; facet=Location_Country; scraped 2026-04-19 |
| NXP Semiconductors | https://careers.nxp.com | nxp | wd3 | careers | 161 | ✅ working — 161 India jobs, 100% JD; facet=Location_Country; scraped 2026-04-19 |
| Autodesk | https://careers.autodesk.com | autodesk | wd1 | Ext | 111 | ✅ working — 111 India jobs, 100% JD; facet=locationCountry; scraped 2026-04-19 |
| Roche | https://careers.roche.com | roche | wd3 | roche-ext | 1 | 🔴 only 1 India job — low volume, skip; locations facet uuid=54c59631...; verified 2026-04-19 |
| ING Bank | https://careers.ing.com | ing | wd3 | ICSGBLCOR | 0 | 🔴 no India locations in ICSGBLCOR portal; skip; verified 2026-04-19 |
| Barclays | https://search.jobs.barclays | barclays | wd3 | External_Career_Site_Barclays | 500+ | ✅ working — 500 India jobs (cap), 100% JD; 12 India office UUIDs via locations facet; scraped 2026-04-19 |
| Maersk | https://www.maersk.com/careers/vacancies | maersk | wd3 | Maersk_Careers | 97 | ✅ working — 97 India jobs, 100% JD; 26 India office UUIDs via locations facet; scraped 2026-04-19 |
| DXC Technology | https://careers.dxc.com | dxctechnology | wd1 | DXCJobs | 211 | ✅ working — 211 India jobs, 100% JD; facet=locationCountry; scraped 2026-04-19 |
| ABB | https://careers.abb/global/en | abb | wd3 (suspected) | ⚠️ career_site unconfirmed | ? | ⚠️ Workday confirmed (official docs confirm Workday ATS) — tenant `abb.wd3` suspected; career_site slug TBD (try: ABBcareers, External, ABB_Careers); probe CXS; probed 2026-04-19 |
| Juniper Networks | https://www.juniper.net/us/en/company/careers.html | ⚠️ HPE merger Jan 2024 | — | — | ? | ⚠️ Acquired by HPE (closed Jan 2024) — careers likely redirect to HPE Workday (`hpe.wd3`); verify if Juniper-branded portal still active or redirect to HPE; probed 2026-04-19 |

---

## SMARTRECRUITERS COMPANIES
*API pattern: `GET https://api.smartrecruiters.com/v1/companies/{company_id}/postings?country=in&limit=100&offset=0`*
*Country param: `in` = India. Also try `?q=&location=India`*

| Company | Careers URL | SmartRecruiters ID | India Jobs | Status |
|---------|-------------|-------------------|-----------|--------|
| Continental | https://www.continental.com/en/career/ | continental | ~400+ | ✅ working |
| LDC (Louis Dreyfus) | https://www.ldc.com/global/en/careers/ | LouisDreyfusCompany | ~100+ | ✅ working |
| ServiceNow | https://careers.servicenow.com/locations/apj/india/ | servicenow | ~200+ | ✅ working |
| Zomato | https://careers.smartrecruiters.com/Zomato1 | Zomato1 | 1 | ⬇️ low-priority — `totalFound: 1` confirmed via API 2026-04-19; genuine single India role, not a scraper failure |
| Bosch | https://jobs.bosch.com/en?pages=1&country=in | BoschGroup | 100 | ✅ working — 100 India jobs, 100% JD; scraped 2026-04-19 |
| Visa | https://corporate.visa.com/en/jobs/?q=&location=India | Visa | 2 | ✅ SmartRecruiters ID `Visa` confirmed — 2 India jobs; probed 2026-04-19 |
| Societe Generale | https://careers.societegenerale.com/en/search | SocieteGenerale4 | ? | ✅ no_country_filter — `country=in` returns 0 for this tenant; portal fetches all postings, is_india() Python filter applied; fixed 2026-04-19 |
| Freshworks | https://careers.smartrecruiters.com/freshworks | freshworks | 4 | ✅ working — 4 India jobs; Chennai/Bengaluru; scraped 2026-04-19 |
| Publicis Sapient | https://careers.publicissapient.com | PublicisSapient | 0 | 🔴 SmartRecruiters returns 0 for all known IDs; careers site is SPA (ATS unidentified); investigate via XHR before re-adding |

---

## GREENHOUSE COMPANIES
*API pattern: `GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`*
*Filter: check `location.name` field for India cities in the response*

| Company | Careers URL | Board Token | India Jobs | Status |
|---------|-------------|-------------|-----------|--------|
| Atlassian | https://www.atlassian.com/company/careers | atlassian | ? | ⚠️ broken — Greenhouse board token "atlassian" returns 404 as of 2026-04-11; token may have changed |
| General Atlantic | https://www.generalatlantic.com/careers/ | generalatlantic | 0 | 🔴 0 India jobs — Greenhouse board confirmed but no India listings found; moved to end of registry |
| Stripe | https://stripe.com/in/jobs | stripe | ~20 | ✅ working |
| Storable | https://www.storable.com/careers | storable | ? | 🟡 Greenhouse board confirmed active (boards.greenhouse.io/storable); India jobs TBD; probed 2026-04-19 |
| CyberArk | https://www.cyberark.com/careers | cyberark | ? | ⚠️ Greenhouse board "cyberark" is no longer active as of 2026-04-19; careers.cyberark.com antibot-blocked — find new ATS or skip |
| Airbnb | https://careers.airbnb.com | airbnb | 15 | ✅ working — 15 India jobs, 100% JD; scraped 2026-04-19 |
| Razorpay | https://razorpay.com/jobs/ | razorpaysoftwareprivatelimited | 46 | ✅ working — 46 India jobs, 100% JD; scraped 2026-04-19 |
| PhonePe | https://www.phonepe.com/careers/ | phonepe | 43 | ✅ working — 43 India jobs, 100% JD; scraped 2026-04-19 |
| Thoughtworks | https://www.thoughtworks.com/careers | thoughtworks | 2 | ✅ working — 2 India jobs, 100% JD; scraped 2026-04-19 |
| Mozilla | https://www.mozilla.org/en-US/careers/listings/ | mozilla | 0 | 🔴 0 India jobs — 47 global Greenhouse jobs confirmed (boards.greenhouse.io/mozilla) but none India-located; probed 2026-04-26 |

---

## LEVER COMPANIES
*API pattern: `GET https://api.lever.co/v0/postings/{company}?mode=json`*
*Returns all active jobs as JSON array. Filter by `location` field for India cities.*
*India-founded companies below: no filter needed — all postings are India.*

| Company | Careers URL | Lever Slug | India Jobs | Status |
|---------|-------------|-----------|-----------|--------|
| Spotify | https://www.lifeatspotify.com/jobs | spotify | 2 | ✅ working — ATS is Lever (jobs.lever.co/spotify); 2 India jobs (Gurgaon + Mumbai); lifeatspotify.com WP front-end confirmed; probed 2026-04-26 |
| Meesho | https://meesho.io/jobs | meesho | 52 | ✅ working — 52 India jobs, 100% JD; scraped 2026-04-19 |
| CRED | https://careers.cred.club/openings | cred | 7 | ✅ working — 7 India jobs, 100% JD; scraped 2026-04-19 |
| Paytm | https://paytm.com/careers | paytm | 203 | ✅ working — 203 India jobs, 96% JD; scraped 2026-04-19 |

---

## EIGHTFOLD AI COMPANIES
*⚠️ API BROKEN as of 2026-04-10: `GET /api/apply/v2/jobs?num=50&start=0` returns 404. New format returns only metadata, not job listings.*
*To fix: inspect XHR calls on the careers page for the actual current endpoint.*

| Company | Careers URL | Eightfold Domain | Status |
|---------|-------------|-----------------|--------|
| American Express | https://aexp.eightfold.ai/careers/?location=India&domain=aexp.com&hl=en | aexp.eightfold.ai | 🟡 updated to direct Eightfold India URL 2026-04-19 |
| Morgan Stanley | https://morganstanley.eightfold.ai/careers?location=INDIA&domain=morganstanley.com | morganstanley.eightfold.ai | 🟡 updated endpoint 2026-04-19 — old URL was article page not job listing; Eightfold India-filtered URL |
| STMicroelectronics | https://stmicroelectronics.eightfold.ai/careers?location=India&hl=en | stmicroelectronics.eightfold.ai | 🟡 updated to direct Eightfold India URL 2026-04-19 |
| Philip Morris International | https://join.pmicareers.com/search-results | join.pmicareers.com (Eightfold hosted) | 🔴 API broken — `/api/apply/v2/jobs` returns "Tenant not identified"; route via Firecrawl scrape on search page |
| Micron Technology | https://micron.eightfold.ai/careers?location=India&hl=en | micron.eightfold.ai | 🟡 updated to direct Eightfold India URL 2026-04-19 |
| Qualcomm | https://careers.qualcomm.com | app.eightfold.ai (Qualcomm tenant) | 🟡 Eightfold confirmed via FC scrape — route via Firecrawl scrape; probed 2026-04-19 |
| Citibank | https://jobs.citi.com/search-jobs/India | citi.eightfold.ai | 🟡 Eightfold confirmed (`citi.eightfold.ai`) via FC scrape of jobs.citi.com — India jobs present; route via Firecrawl scrape; probed 2026-04-19 |

---

## CUSTOM / PROPRIETARY APIs

| Company | Careers URL | ATS / Platform | Scraping Endpoint | India Filter | India Jobs | Status |
|---------|-------------|----------------|------------------|-------------|-----------|--------|
| Amazon | https://www.amazon.jobs | Custom (AWS Jobs) | `GET https://www.amazon.jobs/en/search.json?base_query=&loc_query=India&country=IND&result_limit=100` | `country=IND` param | ~2,963 | ✅ working — clean JSON API |
| Apple | https://jobs.apple.com/en-in/search | Apple Jobs | `GET https://jobs.apple.com/en-in/search?location=india-INDC` | location param | ~100+ | 🟡 js-required — old /api/role/search returns 301→404 as of 2026-04-11; use Firecrawl on careers page |
| Cognizant | https://careers.cognizant.com/india-en/jobs | XML Feed | `GET https://careers.cognizant.com/india-en/jobs/xml/?rss=true` | Already India-only feed | 2 | ✅ working via Firecrawl — 2 India jobs extracted + enriched 2026-04-11 |
| Google | https://careers.google.com | GCS | `GET https://www.google.com/about/careers/applications/jobs/results?location=India` | `location=India` param | 3 | ✅ working via Firecrawl — 3 India jobs extracted + enriched 2026-04-11 |
| Infosys | https://career.infosys.com/joblist | Angular SPA | `GET https://career.infosys.com/api/jobs?...` — inspect XHR | location=India | 3 | 🔴 Angular SPA — all direct API attempts (`/api/jobs`, `/joblist`, `/search`) return full Angular HTML (200 OK, no JSON); FC scrape extracting only 3 jobs; needs XHR inspection via Docker browser to find real XHR endpoint; investigated 2026-04-19 |
| L'Oréal | https://careers.loreal.com | Phenom | `GET https://careers.loreal.com/en_US/jobs/SearchJobs/India` | URL path | 3 | ✅ working via Firecrawl — 3 India jobs extracted + enriched 2026-04-11 |
| Microsoft | https://careers.microsoft.com/professionals/us/en/l-india | GCS (Microsoft) | India-filtered listing page | `l-india` path | ? | 🟡 js-required — updated to India landing page 2026-04-19 |
| Stellantis | https://www.stellantis.com/en/careers | Custom | careers page | JS-rendered | 3 | ✅ working via Firecrawl — 3 India jobs extracted + enriched 2026-04-11 |
| Wipro | https://careers.wipro.com | SAP SuccessFactors (hcm55.sapsf.eu) | `GET https://hcm55.sapsf.eu/careers?company=wipro` — OData API requires OAuth | URL param | 1 | 🔴 auth-gated — CSP header reveals real backend is `hcm55.sapsf.eu` (SAP SF), NOT Radancy; OData `/odata/v2/Posting_Search` returns `[LGN0003] Authentication information is missing`; FC scrape on careers.wipro.com returns only 1 job; needs OAuth flow or Docker browser XHR; investigated 2026-04-19 |
| TCS | https://www.tcs.com/careers | iBegin (custom) | `GET https://ibegin.tcs.com/iBegin/...` — inspect XHR | — | 3 | ⚠️ broken — tcs.com antibot block (document_antibot) as of 2026-04-17; was working 2026-04-11 |

---

## SAP SUCCESSFACTORS / JOBS2WEB COMPANIES
*API pattern varies — most return HTML, route through Firecrawl*

| Company | Careers URL | ATS | Scraping Endpoint | India Jobs | Status |
|---------|-------------|-----|------------------|-----------|--------|
| Alstom | https://jobsearch.alstom.com | SAP SuccessFactors | `GET https://jobsearch.alstom.com/search/jobs?country=India&startrow=0&sortColumn=referencedate&sortDirection=desc` | ~200+ | 🟡 js-required — India-filtered SAP Jobs2Web URL; Firecrawl extract 2026-04-12 |
| Monitor Deloitte | https://southasiacareers.deloitte.com/go/Deloitte-India/718244/ | SAP SuccessFactors | `GET https://southasiacareers.deloitte.com/go/Deloitte-India/718244/` | ? | 🟡 js-required — SAP SuccessFactors confirmed via XHR inspection 2026-04-16 |
| GMR Group | https://careers.gmrgroup.in | SAP SuccessFactors | `GET https://careers.gmrgroup.in` | ? | 🟡 js-required — SAP SuccessFactors confirmed via XHR inspection 2026-04-16; tenant on career2.successfactors.eu |
| CMA CGM | https://jobs.cmacgm-group.com | SAP SuccessFactors / Jobs2Web | `GET https://jobs.cmacgm-group.com/search/jobs?country=India&startrow=0&sortColumn=referencedate&sortDirection=desc` | ~100+ | 🟡 js-required — India-filtered SAP Jobs2Web URL; Firecrawl extract 2026-04-12 |
| CNHI | https://careers.cnh.com | SAP SuccessFactors / JS SPA | `https://careers.cnh.com` | India jobs on homepage featured section | ✅ working via Firecrawl — 5 jobs from homepage featured section (India jobs surface here); actual search at join.cnh.com but India filter is JS-rendered; verified 2026-04-17 |
| Volvo Group | https://www.volvogroup.com/en/careers | SAP SuccessFactors | `GET https://jobs.volvogroup.com/search/?q=&locationsearch=India` | ? | 🟡 js-required — India-filtered URL; Firecrawl extract 2026-04-12 |
| Deloitte India | https://apply.deloitte.com/careers/SearchJobs/?countryCode=IN | SAP SuccessFactors | `GET https://apply.deloitte.com/careers/SearchJobs/?countryCode=IN` | countryCode=IN | 🟡 js-required — separate from Monitor Deloitte; 853 India jobs confirmed on page; probed 2026-04-19 |
| EY India | https://careers.ey.com/ey/search/?q=&countryCode=IN | SAP SuccessFactors | `GET https://careers.ey.com/ey/search/?q=&countryCode=IN` | countryCode=IN | 🟡 js-required — SAP SF confirmed via `rmkcdn.successfactors.com` CDN assets; India-filtered URL confirmed; route via Firecrawl scrape; probed 2026-04-19 |
| PepsiCo | https://www.pepsicojobs.com/main/jobs?location=India | iCIMS | `https://globalcareers-pepsico.icims.com` | location=India | 🟡 iCIMS confirmed (`globalcareers-pepsico.icims.com`) — India jobs confirmed in page; iCIMS returns HTML not JSON; route via Firecrawl scrape on pepsicojobs.com India URL; probed 2026-04-19 |

---

## ORACLE HCM COMPANIES
*API pattern: `GET https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?limit=25&offset=0&onlyData=true`*
*India filter: `q=PrimaryLocation.CountryName="India"` — but may require authentication*

| Company | Careers URL | Oracle Host | India Jobs | Status |
|---------|-------------|------------|-----------|--------|
| Technip Energies | https://www.technipenergies.com/careers/ | hcxg.fa.em2.oraclecloud.com | ? | ⚠️ broken — REST API returns 0 items, may need auth or different endpoint |
| EXL Digital | https://www.exlservice.com/careers | fa-ewjt-saasfaprod1.fa.ocs.oraclecloud.com | ? | 🔴 API auth-gated — base URL returns 200 but count=0 items=0 even without India filter; public API not exposed; route via Firecrawl scrape |
| JP Morgan Chase | https://careers.jpmorgan.com | jpmc.fa.oraclecloud.com | ? | 🟡 Oracle HCM confirmed via FC scrape (oraclecloud.com link) — host=jpmc.fa.oraclecloud.com; India filter TBD; probed 2026-04-19 |
| Honeywell | https://careers.honeywell.com/us/en | ibqbjb.fa.ocs.oraclecloud.com | ? | 🟡 Oracle HCM confirmed via FC scrape redirect — host=ibqbjb.fa.ocs.oraclecloud.com; India filter TBD; probed 2026-04-19 |
| KPMG India | https://home.kpmg/in/en/home/careers.html | ejgk.fa.em2.oraclecloud.com | 0 | 🔴 Oracle HCM confirmed (`ejgk.fa.em2.oraclecloud.com`) — REST API returns count=0 without auth; auth-gated; route via Firecrawl scrape on kpmgcareers.in (FC-blocked as of 2026-04-19); probed 2026-04-19 |
| Texas Instruments | https://careers.ti.com | edbz.fa.us2.oraclecloud.com | ? | 🟡 Oracle HCM CandidateExperience confirmed — `edbz.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/jobs`; India filter: `q=PrimaryLocation.CountryName="India"`; legacy Taleo at `ti.taleo.net` deprecated; probed 2026-04-19 |
| Nokia | https://jobs.nokia.com | jobs.nokia.com | ? | 🟡 Oracle HCM CandidateExperience confirmed — `jobs.nokia.com/en/sites/CX_1/jobs`; REST: `jobs.nokia.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?q=PrimaryLocation.CountryName="India"`; India R&D centers in Chennai/Bengaluru/Hyderabad; probed 2026-04-19 |
| BNY Mellon | https://www.bny.com/corporate/global/en/about-us/careers | eofe.fa.us2.oraclecloud.com | ? | 🟡 Oracle HCM confirmed (NOT Workday) — `eofe.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/BNY-Careers`; India GCC in Chennai/Pune; India filter TBD; probed 2026-04-19 |

---

## iCIMS COMPANIES
*API: iCIMS REST not publicly documented — inspect XHR on careers page for `sc` (site config ID)*
*Typical search URL: `https://{company}.icims.com/jobs/search?ss=1&in_iframe=1&hashed=-1&mobile=false&country=IN&location=india`*

| Company | Careers URL | iCIMS Tenant | India Jobs | Status |
|---------|-------------|-------------|-----------|--------|
| ARM Holdings | https://careers.arm.com | arm | ? | 🟡 iCIMS confirmed — `earlycareers-arm.icims.com` for graduate roles; main full-time roles at `careers.arm.com` (likely `arm.icims.com`); India offices in Bengaluru/Noida; India filter via XHR inspection needed; probed 2026-04-19 |

---

## PHENOM REST API COMPANIES
*Direct paginated JSON API with location + category filters. Full JDs included in response.*
*API pattern: `GET {API Endpoint}&page=N` — paginate until jobs array empty*

| Company | Careers URL | API Endpoint | Status |
|---------|-------------|-------------|--------|
| Schneider Electric | https://www.se.com/en/careers/ | `https://careers.se.com/api/jobs?location=India&categories=Digital+Innovation+%26+Technology&pageSize=10` | ✅ working — Phenom/iCIMS JSON REST API; ~132 India IT jobs; verified 2026-04-02 |
| BCG | https://careers.bcg.com/global/en/locations/india | `https://careers.bcg.com/global/en/search-results?keywords=india` | ⚠️ Phenom API returns empty body (JSON parse error) as of 2026-04-17; use Firecrawl Docker scrape on search-results URL |
| Oliver Wyman | https://www.oliverwyman.com/careers.html | `https://mmc.phenompeople.com/global/en/oliver-wyman-search` | ⚠️ Phenom API returns 404 on careers.marsh.com redirect as of 2026-04-17; route via Firecrawl Docker scrape on mmc.phenompeople.com page |
| HP (HPE) | https://careers.hpe.com/us/en/search-results?qcountry=IN | `https://careers.hpe.com/us/en/search-results?qcountry=IN` | 🟡 Phenom confirmed (`cdn.phenompeople.com/HPE1US`) — India-filtered URL works; route via Firecrawl scrape; probed 2026-04-19 |

---

## AVATURE COMPANIES
*Avature requires JavaScript rendering — no clean JSON API. Use Firecrawl.*

| Company | Careers URL | India Jobs | Status |
|---------|-------------|-----------|--------|
| TotalEnergies | https://jobs.totalenergies.com/en_US/careers/SearchJobs/?location=India | ? | 🟡 js-required — India-filtered URL 2026-04-12 |

---

## OTHER PLATFORMS

| Company | Careers URL | ATS | Notes | Status |
|---------|-------------|-----|-------|--------|
| Air France | https://recrutement.airfrance.com | Custom | French-language portal | ⚠️ broken — Firecrawl crawl timeout (95s) as of 2026-04-11 |
| AstraZeneca | https://careers.astrazeneca.com/search-jobs/India | Phenom / TalentBrew | URL-based India filter | ✅ working via Firecrawl — 3 India jobs extracted + enriched 2026-04-11 |
| Eli Lilly | https://careers.lilly.com/us/en/india | Phenom People | India-filtered URL — 48 India jobs confirmed in page filter; 5 extracted via FC validate 2026-04-17 | ✅ working via Firecrawl — migrated from Workday to Phenom; verified 2026-04-17 |
| Cisco | https://jobs.cisco.com | Phenom (Cisco custom) | HTML portal — inspect XHR for JSON API | 🔍 needs investigation |
| Michelin | https://www.michelin.com/en/careers/find-a-job/ | Phenom / TalentBrew | India filter in URL | ⚠️ broken — 404 as of 2026-04-11; careers URL may have changed |
| Philips | https://www.careers.philips.com/global/en | Phenom / TalentBrew | India filter in URL | ⚠️ broken — Firecrawl crawled generic homepage (no India listing); needs India-filtered URL 2026-04-11 |
| SAP | https://jobs.sap.com | SAP (own platform) | `GET https://jobs.sap.com/search/?q=&locationsearch=India` | 🟡 js-required | ⚠️ broken — Firecrawl crawl timeout (95s) as of 2026-04-11 |
| Tech Mahindra | https://www.techmahindra.com/en-in/careers/ | Custom | URL may have changed from careers.techmahindra.com | ⚠️ broken — verify URL |
| Dr. Reddy's | https://careers.drreddys.com | Custom (SaaS ATS) | careers.drreddys.com — JS-rendered; SmartRecruiters API returns 0; custom ATS | 🟡 js-required — custom ATS confirmed; probed 2026-04-19 |
| Boeing | https://jobs.boeing.com | Custom | `https://jobs.boeing.com/boeing/jobs/India` — custom career portal (TalentNet integration) | 🟡 js-required — custom ATS; probed 2026-04-19 |
| Uber | https://www.uber.com/careers/list/ | Custom | `https://www.uber.com/careers/list/` — custom SPA; no ATS fingerprint detected | 🟡 js-required — custom ATS; probed 2026-04-19 |
| Align Technology | https://www.aligntech.com/careers | Pinpoint | `https://app.pinpointhq.com` — Pinpoint ATS detected in page assets; slug TBD | 🟡 js-required — Pinpoint ATS confirmed; India filter TBD; probed 2026-04-19 |
| Mondee Holdings | https://jobs.ashbyhq.com/mondee | Ashby | `https://jobs.ashbyhq.com/mondee` — Ashby ATS; no active India listings found as of probe | 🟡 js-required — Ashby ATS confirmed; may have 0 India jobs currently; probed 2026-04-19 |
| AMD | https://www.amd.com/en/corporate/careers | iCIMS | `https://amd.icims.com` — iCIMS ATS confirmed; India filter TBD | 🟡 js-required — iCIMS ATS confirmed (amd.icims.com); probed 2026-04-19 |
| Syneriq Global | https://www.syneriqglobal.com | Custom | No dedicated careers page found — small company; check LinkedIn or main site footer | 🟡 js-required — no careers page detected; probed 2026-04-19 |
| ZF Lifetec | https://www.zf.com/global/en/careers | SAP SuccessFactors (suspected) | zf.com antibot-blocked; zf-lifetec.com/career.html is 404 — parent ZF Group uses SAP SF | ⚠️ blocked — antibot on zf.com; zf-lifetec.com has no careers page; re-probe via zf.com direct browser visit |
| HMIE | https://hmie.in | Custom | hmie.in/careers and hmie.in/jobs both 404 — no independent career portal found | 🔴 no career portal — Hyundai Motor India Engineering hires via parent or LinkedIn; skip |
| Netflix | https://jobs.netflix.com/search?location=India | Custom SPA | `https://jobs.netflix.com/search?location=India` — custom Next.js SPA; no Greenhouse board; no JSON API found | 🟡 js-required — FC scrape returns 25K chars but JS-rendered listings; probed 2026-04-19 |
| Meta | https://www.metacareers.com/jobs/?locations[0]=India | Custom (GraphQL) | `https://www.metacareers.com/jobs/?locations[0]=India` — custom React+GraphQL app; GraphQL 400 without session cookies | 🟡 js-required — FC-blocked; try FC scrape with stealth mode; probed 2026-04-19 |
| Walmart | https://careers.walmart.com/results?q=india | Custom SPA | `https://careers.walmart.com/results?q=india` — custom Next.js SPA (Walmart Global Tech India) | 🟡 js-required — FC scrape returns 7K chars (JS shell, no listings); all `/_next/` API attempts redirect to HTML; needs XHR inspection via Docker browser; only 1 job returned currently; investigated 2026-04-19 |
| DE Shaw | https://www.deshawindia.com/careers | Custom | `https://www.deshawindia.com/careers` — D.E. Shaw India custom career portal; no ATS fingerprint detected | 🟡 js-required — FC scrape returns 54K chars (full page loaded); India-specific; probed 2026-04-19 |
| LTIMindtree | https://www.ltimindtree.com/careers/job-openings/ | Custom | `https://www.ltimindtree.com/careers/job-openings/` — custom portal; no ATS fingerprint; SmartRecruiters 0 results | 🟡 js-required — custom ATS; FC scrape returns 16K chars; probed 2026-04-19 |
| Genpact | https://careers.genpact.com | Custom | `https://careers.genpact.com` — Genpact custom career portal; SmartRecruiters 0 results; Workday 422 | 🟡 js-required — custom ATS; FC scrape of open-positions page; probed 2026-04-19 |
| Amdocs | https://www.amdocs.com/about/careers | Workday (suspected) | `https://amdocs.wd3.myworkdayjobs.com` — Workday CXS 422 blocked; SmartRecruiters 0 results | 🟡 Workday tenant `amdocs.wd3` confirmed but CXS blocked and career_site slug TBD; FC fallback; probed 2026-04-19 |
| Rakuten India | https://corp.rakuten.co.in/careers/ | Custom | `https://corp.rakuten.co.in/careers/` — Rakuten's India development centre; custom portal; India-specific; no ATS fingerprint | 🟡 js-required — custom portal; FC scrape on careers page; probed 2026-04-19 |
| ANZ Bank | https://careers.anz.com | Custom | `https://careers.anz.com` — ANZ custom careers portal; ~278 India jobs (LinkedIn); India GCC in Bengaluru | 🟡 js-required — custom ATS; FC scrape with India filter if available; probed 2026-04-19 |
| Swiggy | https://careers.swiggy.com | MyNextHire (custom) | `https://careers.swiggy.com` — confirmed MyNextHire ATS via case study; ~148 Bengaluru jobs; India-founded | 🟡 js-required — MyNextHire custom portal; `mynexthire.com` API returns 404; FC scrape only option but returning 1 job; no public JSON endpoint found; investigated 2026-04-19 |
| Flipkart | https://www.flipkartcareers.com | Custom | `https://www.flipkartcareers.com` — Flipkart custom careers portal; Walmart-owned; India-founded; Bengaluru HQ | 🟡 js-required — custom ATS; FC scrape; probed 2026-04-19 |
| Zoho | https://careers.zohocorp.com/jobs/careers | Zoho Recruit (self-hosted) | `https://careers.zohocorp.com/jobs/careers` — Zoho uses own Zoho Recruit product; 1000+ India jobs; Chennai HQ | 🟡 js-required — Zoho Recruit portal; FC scrape; probed 2026-04-19 |
| Tata Elxsi | https://www.tataelxsi.com/careers/job-openings | Custom | `https://www.tataelxsi.com/careers/job-openings` — Tata Elxsi custom portal; Bengaluru HQ; India-only | 🟡 js-required — custom ATS; FC scrape; probed 2026-04-19 |
| ZS Associates | https://jobs.zs.com/all/jobs | Custom | `https://jobs.zs.com/all/jobs` — ZS custom career portal; consulting firm; India offices in Pune/Bengaluru | 🟡 js-required — custom portal; try `GET jobs.zs.com/all/jobs` (may return JSON); FC scrape fallback; probed 2026-04-19 |
| Virtusa | https://www.virtusa.com/careers | Custom | `https://www.virtusa.com/careers` — custom portal; IT services; India offices in Chennai/Bengaluru/Hyderabad | 🟡 js-required — custom ATS; FC scrape; probed 2026-04-19 |
| Mu Sigma | https://www.mu-sigma.com/careers | Custom | `https://www.mu-sigma.com/careers` — Mu Sigma custom portal; analytics firm; Bengaluru HQ; India-only | 🟡 js-required — custom ATS; FC scrape; probed 2026-04-19 |
| InMobi | https://www.inmobi.com/company/careers/ | Custom/Greenhouse (TBD) | `https://www.inmobi.com/company/careers/` — InMobi custom portal or Greenhouse; Bengaluru HQ; probe XHR | 🟡 js-required — ATS unconfirmed; check `boards.greenhouse.io/inmobi`; FC scrape fallback; probed 2026-04-19 |
| Ola Electric | https://www.olaelectric.com/careers | Custom | `https://www.olaelectric.com/careers` — Ola Electric custom portal; EV company; Bengaluru HQ; India-only | 🟡 js-required — custom ATS; FC scrape; probed 2026-04-19 |
| Keysight Technologies | https://jobs.keysight.com | Custom (SAP SF suspected) | `https://jobs.keysight.com` — custom portal likely SAP SuccessFactors; India R&D in Bengaluru | 🟡 js-required — probe XHR for SF API; FC scrape fallback; probed 2026-04-19 |
| Telefonica | https://www.telefonica.com/en/careers/ | Custom/SAP SF | Europe/LatAm focused — India presence minimal; no confirmed India GCC | ⚠️ India presence unclear — Telefónica Tech has some India ops; verify India jobs before adding; probed 2026-04-19 |
| Credit Suisse | — | MERGED → UBS | Acquired by UBS (March 2023); no standalone portal | 🔴 Merged into UBS — use UBS entry; careers.credit-suisse.com redirects to UBS; skip |

---

## CONSULTING COMPANIES
*ATS varies — most route through Firecrawl extract until direct API is confirmed.*

| Company | Careers URL | ATS | Status |
|---------|-------------|-----|--------|
| Bain & Company | https://www.bain.com/careers/ | Workday (unconfirmed) | 🟡 js-required — add to Workday section once tenant slug confirmed |
| BCG | https://careers.bcg.com/global/en/search-results?keywords=india | Phenom | ✅ working via Firecrawl — 5 jobs via FC scrape on India search URL; verified 2026-04-17 |
| EY Parthenon | https://www.ey.com/en_in/careers/parthenon | SmartRecruiters (unconfirmed) | 🟡 js-required |
| EY India (general) | https://careers.ey.com/ey/search/?q=&countryCode=IN | SAP SuccessFactors | → tracked in SAP SUCCESSFACTORS section; probed 2026-04-19 |
| KPMG India | https://home.kpmg/in/en/home/careers.html | Oracle HCM | → tracked in ORACLE HCM section (🔴 auth-gated); probed 2026-04-19 |
| Kearney | https://www.kearney.com/about/locations/india/careers/india-people-careers | Custom | 🟡 js-required |
| L.E.K. Consulting | https://www.lek.com/careers | Custom | 🟡 js-required |
| McKinsey & Company | https://www.mckinsey.com/careers/search-jobs?countries=India | Custom | 🟡 js-required — India-filtered URL confirmed via Firecrawl discovery 2026-04-16 |
| Monitor Deloitte | https://southasiacareers.deloitte.com/go/Deloitte-India/718244/ | SAP SuccessFactors | ⚠️ moved to SAP section 2026-04-16 |
| Oliver Wyman | https://mmc.phenompeople.com/global/en/oliver-wyman-search | Phenom (mmc.phenompeople.com) | ✅ working via Firecrawl — 5 jobs via FC scrape on mmc.phenompeople.com; verified 2026-04-17 |
| Practus | https://roibypractus.com/people-careers/ | Custom | ⬇️ low-priority — small boutique consulting firm; likely genuine low job count; deprioritised 2026-04-19 |
| Praxis Global Alliance | https://www.praxisga.com/career | Custom | ⬇️ low-priority — small boutique firm; deprioritised 2026-04-19 |
| PwC India | https://www.pwc.in/careers/job-search.html | SmartRecruiters (unconfirmed) | 🟡 js-required |
| Simon-Kucher & Partners | https://www.simon-kucher.com/en/careers | Custom | 🟡 js-required |
| Strategy& (PwC) | https://www.strategyand.pwc.com/gx/en/careers.html | Custom | 🟡 js-required |
| Takshashila Consulting | https://tkc.firm.in/career.html | Custom | 🟡 js-required |
| TransformationX | https://transformationx.com/join-us/ | Custom | ⬇️ low-priority — small boutique firm; deprioritised 2026-04-19 |
| Vector Consulting Group | https://www.vectorconsulting.in/careers/career-listings/ | Custom | 🟡 js-required |
| Black Brix | https://blackbrix.com/job-openings/ | Custom | 🟡 js-required |

---

## BFSI — INVESTMENT BANKING & ASSET MANAGEMENT

| Company | Careers URL | ATS | Notes | Status |
|---------|-------------|-----|-------|--------|
| ARGA Investment Management | https://www.argainvest.com | None (email: resumes@argainvest.com) | No public portal | 🔒 email-only |
| Arpwood Capital | https://www.arpwood.com/careers | Custom | Small boutique IB | ⬇️ low-priority — small firm, genuine low job count; deprioritised 2026-04-19 |
| Avendus Capital | https://www.avendus.com/careers/apply-now | Custom | India-based IB | 🟡 js-required |
| Claypond Capital | — | None (LinkedIn / email) | Manipal Group family office | 🔒 no public portal |
| Deutsche Bank | https://careers.db.com/explore-the-bank/locations/asia-pacific/bangalore | SAP SuccessFactors | India-city landing page (links into job portal filtered to Bangalore) | 🟡 js-required — updated to Bangalore India page 2026-04-19 |
| Elevation Capital | https://apply.workable.com/elevation-capital-3/ | Workable | VC firm | ⚠️ antibot blocked — all FC engines failed 2026-04-17; moved to ANTIBOT section |
| Everstone Capital | — | None (LinkedIn) | PE firm — no dedicated portal | 🔒 no public portal |
| General Atlantic | https://www.generalatlantic.com/careers/ | Greenhouse | Global PE/growth equity | ⚠️ moved to Greenhouse section 2026-04-16 |
| HSBC | https://hsbc.eightfold.ai/careers?location=India&hl=en | Eightfold | SPA returns JSON config only — no job links rendered; mycareer.hsbc.com dead | ⚠️ broken — Eightfold SPA unrenderable 2026-04-19 |
| O3 Capital | http://www.o3capital.com | None (email: careers@o3capital.com) | Boutique IB | 🔒 email-only |
| Premji Invest | https://in.premjiinvest.com | Custom | Family office / PE | 🟡 js-required |
| Standard Chartered Bank | https://www.sc.com/en/global-careers/experienced-hire/spotlight-career-opportunities/careers-in-india/ | Custom | Large global bank | 🟡 js-required |
| UBS | https://www.ubs.com/global/en/careers/about-us/locations/india.html | Custom | Global IB | 🟡 js-required |
| SBI Mutual Fund | https://www.sbimf.com/careers | Custom | India AMC | 🟡 js-required |
| Integrow Asset Management | https://www.integrowamc.com/career/ | Custom | India AMC | 🟡 js-required |

---

## BFSI — BANKING & FINANCE

| Company | Careers URL | ATS | Notes | Status |
|---------|-------------|-----|-------|--------|
| Bank of India | https://bankofindia.bank.in/career | Custom | PSU bank — limited listings | ⬇️ low-priority — PSU bank with infrequent tech openings; deprioritised 2026-04-19 |
| Credila (HDFC Credila) | https://www.credila.com/careers | Custom | Education finance NBFC | 🟡 js-required |
| CRISIL | https://www.crisil.com/en/home/careers.html | SmartRecruiters (LinkedIn redirect) | Ratings & analytics | 🟡 js-required |
| IIFL Finance | https://iifl.darwinbox.in/ms/candidate/careers | Darwinbox | NBFC | 🟡 js-required — Darwinbox ATS URL found in page source via XHR inspection 2026-04-16 |
| IndusInd Bank | https://www.indusind.bank.in | Custom | Private sector bank | 🟡 js-required |
| L&T Finance | https://www.ltfs.com/careers.html | Custom | NBFC | ⬇️ low-priority — small NBFC, limited tech roles; deprioritised 2026-04-19 |
| Navi Technologies | https://navi.com/careers/jobs | Custom | Fintech NBFC | 🟡 js-required — direct jobs page confirmed via Firecrawl discovery 2026-04-16 |
| S&P Global | https://www.spglobal.com/en/explore-s-p-global/careers | SmartRecruiters (unconfirmed) | Ratings & data | ⚠️ antibot blocked — document_antibot 2026-04-17; moved to ANTIBOT section |
| FinIQ | https://www.finiq.com/JobsPage/jobs.html | Custom HTML | Fintech SaaS | ✅ working — direct HTML page |

---

## CONGLOMERATES

| Company | Careers URL | ATS | Notes | Status |
|---------|-------------|-----|-------|--------|
| Adani Group | https://www.adani.com/careers | Custom / SAP | Large Indian conglomerate | 🟡 js-required |
| Aditya Birla Group | https://careers.adityabirla.com/job-search | Custom / SAP | Large Indian conglomerate | 🟡 js-required — job-search page confirmed via Firecrawl discovery 2026-04-16 |
| CK Birla Group | https://www.ckabirlagroup.com/workingwithus | Custom | Mid-size Indian conglomerate | 🟡 js-required |
| GMR Group | https://careers.gmrgroup.in | SAP SuccessFactors | Infrastructure conglomerate | ⚠️ moved to SAP section 2026-04-16 |
| Lodha Ventures | https://www.instahyre.com/jobs-at-lodha-ventures/ | Instahyre | Lodha family ventures arm | 🟡 js-required |
| Tata Administrative Services | https://www.tata.com/careers/programs/tas | Custom | Tata Group management programme | 🟡 js-required |

---

## CONSUMER GOODS (FMCG)

*Note: Haleon is tracked in WORKDAY COMPANIES section (tenant: gsknch).*
*Note: L'Oréal is tracked in CUSTOM / PROPRIETARY APIs section.*

| Company | Careers URL | ATS | Notes | Status |
|---------|-------------|-----|-------|--------|
| Coromandel International | https://www.coromandel.biz/careers/ | Custom | Agri-inputs; part of Murugappa Group | 🟡 js-required |
| Dabur | https://www.dabur.com/join-us/explore-opportunities | Custom / SAP | Large FMCG India | ⚠️ antibot blocked — all FC engines failed 2026-04-17; moved to ANTIBOT section |
| Philip Morris International | https://join.pmicareers.com | Eightfold | FMCG / Tobacco | → tracked in EIGHTFOLD AI COMPANIES section (🔴 API broken) |
| United Breweries | https://careers.theheinekencompany.com/India/ | Workday (Heineken) | Part of Heineken Group | ⬇️ low-priority — FMCG, low tech hiring; check if tenant=heineken wd3 if re-activating; deprioritised 2026-04-19 |
| Wipro Consumer Care | https://wiproconsumercare.com/campus/ | Custom | Separate from Wipro IT — consumer FMCG division | ⬇️ low-priority — consumer goods arm, not tech; deprioritised 2026-04-19 |

---

## CONSUMER SERVICES & E-COMMERCE

| Company | Careers URL | ATS | Notes | Status |
|---------|-------------|-----|-------|--------|
| OYO | https://www.oyorooms.com/about/ | LinkedIn / Instahyre | No dedicated portal currently | 🟡 js-required — use LinkedIn search as fallback |
| Myntra | https://careers.myntra.com | Custom | Flipkart group | 🟡 js-required |
| Nykaa | https://careers.nykaa.com | Custom | Beauty e-commerce | 🟡 js-required |

---

## INFORMATION TECHNOLOGY (IT) — NEW ADDITIONS

*Note: Wipro, TCS, Infosys, Cognizant, HCL Technologies are in existing sections.*

| Company | Careers URL | ATS | Notes | Status |
|---------|-------------|-----|-------|--------|
| BrowserStack | https://www.browserstack.com/careers | Workday | Dev tools SaaS | → tracked in WORKDAY COMPANIES section (🔴 no India UUID) |
| Coforge | https://careers.coforge.com | Custom / SmartRecruiters | Mid-size IT services | ⚠️ antibot blocked — all FC engines failed 2026-04-17; moved to ANTIBOT section |
| EXL Digital | https://www.exlservice.com/careers | Oracle HCM | Analytics & BPO | → tracked in ORACLE HCM COMPANIES section (🔴 API auth-gated) |
| HCL Software | https://www.hcl-software.com/careers | Custom | HCL Group software division | 🟡 js-required |
| HiLabs | https://www.hilabs.com/careers/all-open-positions?location=india | Custom | Health-tech AI | ✅ direct URL with India filter — try GET |
| Sanas | https://www.sanas.ai/careers | Custom | AI / speech-tech | 🟡 js-required |
| Vehere Interactive | https://vehere.com/company/careers/ | Custom | Cybersecurity | 🟡 js-required |
| Yubi (formerly CredAvenue) | https://go-yubi.com/careers | Custom / LinkedIn | Debt platform fintech | ⚠️ antibot blocked — document_antibot 2026-04-17; moved to ANTIBOT section |

---

## RETAIL, PHARMA & REAL ESTATE — NEW ADDITIONS

| Company | Careers URL | ATS | Notes | Status |
|---------|-------------|-----|-------|--------|
| Bluestone Jewellery | https://www.bluestone.com/career | Custom | Online jewellery retail | ⬇️ low-priority — small e-commerce, low tech job volume; deprioritised 2026-04-19 |
| Mankind Pharma | https://www.mankindpharma.com/career/ | Custom | Large India pharma | 🟡 js-required |
| Welspun | https://www.welspuncorp.com/career.php | Custom | Textiles & infrastructure | ⬇️ low-priority — non-tech sector, low hiring volume; deprioritised 2026-04-19 |
| Arvind SmartSpaces | https://www.arvindsmartspaces.com/careers/ | Custom | Real estate developer | 🟡 js-required |
| Lodha Group | https://www.lodhagroup.com/hr/explore-career | Custom | Real estate developer | 🟡 js-required |

---

## 🔒 LOGIN-REQUIRED PORTALS
*These portals require user authentication to view or apply for jobs.*
*Do not attempt to scrape job listings. Users are directed to the careers page to log in.*
*Scraper records a stub entry with the careers URL only.*

| Company | Careers URL | Notes | Last Verified |
|---------|-------------|-------|---------------|
| Goldman Sachs | https://higher.gs.com/roles | TAL.NET — Firecrawl returns no pages; login wall blocks all automated access | 2026-04-11 |
| IBM | https://www.ibm.com/careers/search | IBM Career site — Firecrawl crawl times out (95s+); login likely required for listings | 2026-04-11 |
| ARGA Investment Management | https://www.argainvest.com | Email-only: resumes@argainvest.com — no public job portal | 2026-04-12 |
| Claypond Capital | — | No public portal — apply via LinkedIn or email directly (Manipal Group family office) | 2026-04-12 |
| Everstone Capital | — | No public portal — openings posted on LinkedIn only | 2026-04-12 |
| O3 Capital | http://www.o3capital.com | Email-only: careers@o3capital.com — boutique IB | 2026-04-12 |
| Showtime Consulting | https://showtimeconsulting.in | Email-only: careers@showtimeconsulting.in | 2026-04-12 |
| Purplle | https://www.purplle.com/careers | Email-only: career@purplle.com — no automated portal | 2026-04-12 |

---

## ANTIBOT BLOCKED — DEPRIORITISED

*These portals are blocked by bot-detection (Cloudflare, Akamai, custom antibot) as of last verify.*
*Do not include in regular scrape runs — they waste time and credits with 0 output.*
*Try quarterly: URL may change, antibot config may relax. When reachable, move back to active section.*

| Company | Careers URL | ATS | Block Type | Last Verified |
|---------|-------------|-----|-----------|---------------|
| TCS | https://www.tcs.com/careers | iBegin | document_antibot (Firecrawl) | 2026-04-17 |
| S&P Global | https://www.spglobal.com/en/explore-s-p-global/careers | SmartRecruiters (unconfirmed) | document_antibot | 2026-04-17 |
| Dabur | https://www.dabur.com/join-us/explore-opportunities | Custom / SAP | All FC engines failed | 2026-04-17 |
| Coforge | https://careers.coforge.com | Custom / SmartRecruiters | All FC engines failed | 2026-04-17 |
| Elevation Capital | https://apply.workable.com/elevation-capital-3/ | Workable | All FC engines failed | 2026-04-17 |
| Yubi (formerly CredAvenue) | https://go-yubi.com/careers | Custom | document_antibot | 2026-04-17 |

---

## NO INDIA JOBS — EXCLUDED FROM SCRAPER

*These companies have been verified to have zero India job listings on their careers portals.*
*They are excluded from all scraping runs. Re-check periodically (e.g. quarterly) before re-adding.*
*Parser skips this entire section — entries here will never be scraped.*

| Company | Careers URL | ATS | Last Verified | Notes |
|---------|-------------|-----|---------------|-------|
| Volkswagen | https://jobs.volkswagen-group.com | Workday | 2026-04-02 | 0 India results — all "Indiana" false positives (US/DE/CA locations) |
| RTX (Raytheon) | https://careers.rtx.com/global/en | Workday (globalhr.wd5) | 2026-04-10 | 4,199 global jobs but 0 India facet — no India presence on this portal |
| Syngenta | https://www.syngenta.com/en/careers | SmartRecruiters | 2026-04-11 | SmartRecruiters API returned 0 India postings |
| Solvay | https://careers.solvay.com | SAP SuccessFactors | 2026-04-11 | Portal explicitly confirms "no open positions matching India" |

---

## RUN HISTORY & CURRENT STATE

### Session 2026-04-19 (Part 3) — 37 Bengaluru-focused companies researched and added

**No scrape run.** ATS identification via web search + known patterns. All entries need CXS probes to find India UUIDs before first scrape run.

**New portals added (37 total):**

| Portal | ATS | Confirmed Endpoint | Status |
|--------|-----|--------------------|--------|
| 3M | Workday `3m.wd1/Search` | `3m.wd1.myworkdayjobs.com/Search` | ✅ Location_Country UUID in registry |
| NXP Semiconductors | Workday `nxp.wd3/careers` | `nxp.wd3.myworkdayjobs.com/careers` | ✅ Location_Country UUID in registry |
| Autodesk | Workday `autodesk.wd1/Ext` | `autodesk.wd1.myworkdayjobs.com/Ext` | ✅ locationCountry UUID in registry |
| Roche | Workday `roche.wd3/roche-ext` | `roche.wd3.myworkdayjobs.com/roche-ext` | ✅ locations facet UUID in registry |
| ING Bank | Workday `ing.wd3/ICSGBLCOR` | `ing.wd3.myworkdayjobs.com/ICSGBLCOR` | 🔴 no India locations in this portal |
| Barclays | Workday `barclays.wd3/External_Career_Site_Barclays` | Confirmed | ✅ 12 India office UUIDs in registry |
| Maersk | Workday `maersk.wd3/Maersk_Careers` | Confirmed | ✅ 26 India office UUIDs in registry |
| DXC Technology | Workday `dxctechnology.wd1/DXCJobs` | Confirmed | ✅ locationCountry UUID in registry |
| ABB | Workday `abb.wd3` (suspected) | tenant confirmed, career_site TBD | ⚠️ slug needed |
| Juniper Networks | Workday → HPE merger Jan 2024 | check HPE Workday portal | ⚠️ verify |
| Societe Generale | SmartRecruiters `SocieteGenerale4` | Confirmed | 🟡 API ready |
| Freshworks | SmartRecruiters `freshworks` | Confirmed | 🟡 API ready |
| Publicis Sapient | SmartRecruiters (Publicis Groupe) | company_id TBD | 🟡 probe needed |
| Razorpay | Greenhouse `razorpaysoftwareprivatelimited` | Confirmed | 🟡 API ready |
| PhonePe | Greenhouse `phonepe` | Confirmed | 🟡 API ready |
| Thoughtworks | Greenhouse `thoughtworks` | Confirmed | 🟡 API ready |
| Meesho | Lever `meesho` | `api.lever.co/v0/postings/meesho?mode=json` | 🟡 NEW ATS type |
| CRED | Lever `cred` | `api.lever.co/v0/postings/cred?mode=json` | 🟡 NEW ATS type |
| Paytm | Lever `paytm` | `api.lever.co/v0/postings/paytm?mode=json` | 🟡 NEW ATS type |
| Texas Instruments | Oracle HCM `edbz.fa.us2.oraclecloud.com` | Confirmed | 🟡 India filter TBD |
| Nokia | Oracle HCM `jobs.nokia.com/CX_1` | Confirmed | 🟡 India filter TBD |
| BNY Mellon | Oracle HCM `eofe.fa.us2.oraclecloud.com/BNY-Careers` | Confirmed | 🟡 India filter TBD |
| ARM Holdings | iCIMS `arm.icims.com` | Confirmed early careers; main TBD | 🟡 NEW ATS type |
| Rakuten India | Custom `corp.rakuten.co.in/careers` | Custom portal | 🟡 FC scrape |
| ANZ Bank | Custom `careers.anz.com` | Custom portal | 🟡 FC scrape |
| Swiggy | MyNextHire `careers.swiggy.com` | Confirmed MyNextHire ATS | 🟡 FC scrape |
| Flipkart | Custom `flipkartcareers.com` | Custom portal | 🟡 FC scrape |
| Zoho | Zoho Recruit `careers.zohocorp.com` | Self-hosted | 🟡 FC scrape |
| Tata Elxsi | Custom `tataelxsi.com/careers/job-openings` | Custom portal | 🟡 FC scrape |
| ZS Associates | Custom `jobs.zs.com/all/jobs` | Custom portal | 🟡 FC scrape |
| Virtusa | Custom `virtusa.com/careers` | Custom portal | 🟡 FC scrape |
| Mu Sigma | Custom `mu-sigma.com/careers` | Custom portal | 🟡 FC scrape |
| InMobi | Custom/Greenhouse TBD | probe `boards.greenhouse.io/inmobi` | 🟡 ATS unconfirmed |
| Ola Electric | Custom `olaelectric.com/careers` | Custom portal | 🟡 FC scrape |
| Keysight | Custom/SAP SF `jobs.keysight.com` | ATS probe needed | 🟡 XHR inspection |
| Telefonica | Custom/SAP SF | India presence unclear | ⚠️ verify first |
| Credit Suisse | MERGED → UBS | redirects to UBS | 🔴 skip |

**Already tracked (no change):** Medtronic, Micron, Synopsys, Qualcomm, Schneider Electric, Morgan Stanley, Deutsche Bank, Standard Chartered, UBS, HSBC, Zomato, Myntra, Wipro, Tech Mahindra, HCLTech, Citi, Alstom, LTIMindtree

**Priority next actions:**
1. Add Lever scraper to `scrapers.py` (`GET api.lever.co/v0/postings/{slug}?mode=json`, filter by location)
2. Probe CXS for all new Workday tenants to find India UUIDs
3. Confirm Publicis Sapient SmartRecruiters company_id
4. Confirm InMobi ATS — try Greenhouse board first
5. Verify Juniper/HPE merger — check if separate portal survives
6. ABB: probe `abb.wd3` with career_site slugs (ABB_Careers, External, ABBcareers)

---

### Session 2026-04-19 (Part 2) — 26 new portals added (Hyderabad GCC + Bengaluru MNCs)

**No scrape run.** Portal discovery only via Docker Firecrawl + direct Workday CXS probes.

**New portals added (26 total):**
| Portal | ATS | Status | Notes |
|--------|-----|--------|-------|
| Airbnb | Greenhouse `airbnb` | ✅ | India jobs confirmed (Gurugram, Bangalore) |
| Visa | SmartRecruiters `Visa` | ✅ | 2 India jobs |
| Target | Workday `target.wd5/TargetCareers` | 🟡 | 265 India jobs via searchText="india"; no India UUID |
| Ford | Workday `fordcareers.wd12/Ford_Careers` | 🟡 | CXS 422 → FC fallback |
| Unilever | Workday `unilever.wd3` | 🟡 | CXS 403 → FC fallback via careers.unilever.com |
| Adobe | Workday `adobe.wd5/external_experienced` | 🟡 | CXS 422 → FC fallback |
| Hitachi Vantara | Workday `hitachivantara.wd3/HitachiVantaraCareers` | 🟡 | CXS 422 → FC fallback |
| Thomson Reuters | Workday `thomsonreuters.wd3/tr_External_Applicant` | 🟡 | CXS 422 → FC fallback |
| CGI | Workday `cgicareers.wd3/CGI` | 🟡 | CXS 422 → FC fallback |
| ADP | Workday `adp.wd5/ADP` | 🟡 | CXS 422 → FC fallback |
| Intuit | Workday `intuit.wd5/Intuit` | 🟡 | CXS 422; careers.intuit.com antibot → FC fallback |
| Samsung | Workday `samsungelectronics.wd3` | 🟡 | CXS 422; job.samsung.com FC-blocked; career_site TBD |
| Carelon Global Solutions | Workday `elevancehealth.wd1/carelonglobal_in` | 🟡 | 7 global jobs only; no India UUID; FC fallback |
| Broadcom | Workday `broadcom.wd1` | 🟡 | Career_site slug TBD; all probes 404/422 |
| Amdocs | Workday `amdocs.wd3` | 🟡 | CXS 422; career_site TBD |
| Citibank | Eightfold `citi.eightfold.ai` | 🟡 | Confirmed via jobs.citi.com FC scrape |
| PepsiCo | iCIMS `globalcareers-pepsico.icims.com` | 🟡 | India jobs confirmed on page |
| HP (HPE) | Phenom `careers.hpe.com` (HPE1US) | 🟡 | Phenom confirmed; India-filtered URL works |
| EY India | SAP SuccessFactors | 🟡 | Confirmed via successfactors.com CDN |
| KPMG India | Oracle HCM `ejgk.fa.em2.oraclecloud.com` | 🔴 | Returns 0 items without auth; auth-gated |
| Netflix | Custom SPA `jobs.netflix.com` | 🟡 | No Greenhouse board; JS-rendered |
| Meta | Custom GraphQL `metacareers.com` | 🟡 | FC-blocked; GraphQL 400 |
| Walmart | Custom SPA `careers.walmart.com` | 🟡 | India filter via ?q=india; JS-rendered |
| DE Shaw | Custom `deshawindia.com/careers` | 🟡 | No ATS fingerprint; custom portal |
| LTIMindtree | Custom `ltimindtree.com/careers` | 🟡 | No ATS detected; SmartRecruiters 0 results |
| Genpact | Custom `careers.genpact.com` | 🟡 | No ATS detected; SmartRecruiters 0 results |

**Dropped (already in KNOWN_PORTALS.md):** Google, Amazon, Microsoft, Goldman Sachs, JPMorgan, Bosch, HSBC, Shell, Apple, Salesforce, Intel, Oracle, GE, Philips, Uber, Siemens, SAP, Cisco, Capgemini, IBM, Dell, Accenture, PwC, Deloitte, TCS, Infosys, Wipro, Cognizant

---

### Session 2026-04-17 (Part 2) — Phase 1 full scrape + Phase 2 RAG enrichment in progress

**Phase 1:** `python main.py --skip-enrich` — full fresh scrape of all active portals. Output: 94 jobs.json files, 2,376 total jobs, 1,730 with job_description.

**Phase 2 (in progress):** `python main.py --enrich-only` running as PID 58046. 1,530 jobs to enrich. ETA ~4 hours.

**Code changes this session:**
- `scraper/rag_skills.py` (NEW) — IDF-weighted keyword inverted index over all 35,108 Lightcast L3 skill names; `retrieve(text, k=40)` returns canonical skill candidates in <1ms, no model calls
- `scraper/enricher.py` — RAG integrated: top-40 taxonomy candidates injected into prompt as constrained vocabulary; system prompt removed from code (moved to LM Studio GUI for KV caching); max_tokens 300→150; JD truncation 2000→1500 chars
- `scraper/main.py` — `enrich_only_run()` now uses `ThreadPoolExecutor(max_workers=4)` for parallel LLM calls; `concurrent.futures` added to imports
- `scraper/config.py` — added `ENRICH_WORKERS` env var
- `scraper/.env` — added `ENRICH_WORKERS=4`; dual model presets `MODEL_SPEED=fast|quality`

**LM Studio GUI changes (Gemma 3 4B Inference tab):**
- System prompt set: "You are a precise job data extractor. Return a single valid JSON object. No explanation, no markdown."
- Limit Response Length enabled → 150 tokens
- Temperature → 0.0

**Status after Phase 2 + Phase 3:** Run `python csv_importer.py` once enrichment completes.

---

### Session 2026-04-17 (Part 1) — Full 101-portal validation run (5 jobs each, no enrichment)

**Mode:** `python main.py --validate` | **Duration:** ~12 min | **Result:** 92/101 processed, 9 skipped (0 jobs), 359 total jobs

**✅ Working (92/101):**
All Workday direct API: Accenture, Airbus, Chanel (1 India job), Fidelity, Novartis, Salesforce, Sanofi, Shell, Wells Fargo, Philips, Dell, Haleon — 5 JDs each
Workday→Firecrawl fallback: Engie, Synopsys — 5 each
SmartRecruiters: Continental, LDC, ServiceNow — 5 each; Zomato — 1 (only 1 India posting currently)
Greenhouse: Stripe — 5
Amazon (custom JSON API) — 5
Eightfold via FC: AmEx (5), Morgan Stanley (3), STMicro (5), Philip Morris (5)
Custom via FC: Apple (5), Cognizant (5), Google (4), L'Oréal (5)
SAP via FC: Alstom (5), Monitor Deloitte (5), GMR (5), CMA CGM (5), Volvo (5)
Phenom API: Schneider Electric (5)
All remaining 🌐 portals: reachable, content returned (validate mode shows low counts for JS-heavy — expected without LLM)

**❌ Broken / 0 jobs (9/101):**
| Company | Error | Action |
|---------|-------|--------|
| TCS | document_antibot on tcs.com | Moved to ANTIBOT section |
| CNHI | 404 on careers.cnh.com | Need new CNH Industrial URL |
| BCG | Phenom API empty body | Route via Firecrawl scrape |
| Oliver Wyman | Phenom API 404 (marsh.com redirect) | Route via Firecrawl scrape |
| Elevation Capital | All FC engines blocked | Moved to ANTIBOT section |
| S&P Global | document_antibot | Moved to ANTIBOT section |
| Dabur | All FC engines blocked | Moved to ANTIBOT section |
| Coforge | All FC engines blocked | Moved to ANTIBOT section |
| Yubi | document_antibot | Moved to ANTIBOT section |

**Status changes this session:**
- Eli Lilly: Workday now 404 (was 303) → ⚠️ — Firecrawl fallback only returning 1 link
- Dell ✅ confirmed working via Workday direct API
- Haleon ✅ confirmed working via Workday direct API (new addition)
- 6 portals demoted to new ANTIBOT BLOCKED section

---

### Session 2026-04-12 — First full E2E run (Phase 1 + Phase 2 + Supabase upload)

**Phase 1 results (scrape, --skip-enrich):** 40 portals, 37 min total, 1,628 new jobs
**Phase 2 results (enrich, --enrich-only):** LM Studio enriched all jobs with raw_jd_text
**Phase 3 results (upload):** Upserted to Supabase with quality gate (min_score ≥ 1)

**What worked — jobs saved:**
| Company | Jobs | ATS | Notes |
|---------|------|-----|-------|
| Accenture | 500 | Workday | cap hit; JD fetch 0/500 (Workday API limitation) |
| Airbus | 72 | Workday | JD fetch 0/72 — same limitation |
| Chanel | 1 | Workday | JD fetch 0/1 |
| Eli Lilly | 10 | Workday→Firecrawl | fallback worked; 10 jobs with JD |
| Fidelity | 29 | Workday | JD fetch 0/29 |
| Novartis | 92 | Workday | JD fetch 0/92 |
| Salesforce | 168 | Workday | JD fetch 0/168 |
| Sanofi | 96 | Workday | JD fetch 0/96 |
| Shell | 16 | Workday | JD fetch 0/16 |
| Wells Fargo | 224 | Workday | JD fetch 0/224 |
| Philips | 65 | Workday | JD fetch 0/65 |
| Continental | 99 | SmartRecruiters | ✅ 100% JD coverage |
| LDC | 20 | SmartRecruiters | ✅ 100% JD coverage |
| ServiceNow | 35 | SmartRecruiters | ✅ 100% JD coverage |
| Stripe | 66 | Greenhouse | ✅ 100% JD coverage |
| Amazon | 81 | Custom JSON API | ✅ 100% JD coverage |
| Alstom | 1 | SAP→Firecrawl | Firecrawl extract got 1 job |
| Volvo Group | 33 | SAP→Firecrawl | Firecrawl extract got 33 jobs |
| Schneider Electric | 10 | Phenom API | ✅ 100% JD coverage |
| AstraZeneca | 10 | Phenom→Firecrawl | Firecrawl extract got 10 jobs |

**Broken / 0 jobs this run:**
| Company | Error | Root Cause | Fix Needed |
|---------|-------|------------|------------|
| Mastercard | `[WARN] no India UUID found` | Workday facet discovery failed | Investigate Mastercard Workday tenant facet structure |
| Engie | `422 Unprocessable Entity` | Workday API blocked | Firecrawl fallback ran but LLM got 0 India listings from crawl |
| Synopsys | `422 Unprocessable Entity` | Workday API blocked | Same as Engie |
| American Express | 0 jobs | Eightfold JS — Firecrawl crawl saved raw md but LLM extracted 0 | Inspect XHR on aexp.eightfold.ai for real API endpoint |
| Morgan Stanley | 0 jobs | Eightfold JS — same | Inspect XHR on morganstanley.eightfold.ai |
| STMicroelectronics | Timeout | Firecrawl crawl timed out on st.com | Try scrape instead of crawl; st.com may block |
| Apple | 0 jobs | JS-heavy; Firecrawl crawled but LLM got 0 | Inspect XHR on jobs.apple.com for JSON API |
| Cognizant | 0 jobs | XML feed returned HTML; Firecrawl crawl got 0 | Verify RSS feed URL is still valid |
| Google | 0 jobs | JS-rendered SPA; Firecrawl crawl got 0 this run | Inspect XHR on careers.google.com for JSON API endpoint |
| Infosys | 0 jobs | Angular SPA; Firecrawl crawl got 0 | Inspect XHR for internal API |
| L'Oréal | 403 Forbidden | Direct GET blocked | Route through Firecrawl instead |
| Microsoft | 0 pages | Firecrawl returned no pages (Azure CDN block?) | Try different URL or Playwright |
| Stellantis | 0 jobs | JS-heavy; Firecrawl got 0 this run | Try scrape not crawl |
| Wipro | 429 Too Many Requests | Firecrawl rate limit hit (too many crawls in run) | Add delay between Firecrawl calls or reduce concurrent crawls |
| TCS | 429 Too Many Requests | Same rate limit issue | Same fix |
| CMA CGM | 0 jobs | SAP/JS — Firecrawl crawl saved raw md but LLM got 0 | Inspect what's in firecrawl_raw.md; may need Firecrawl scrape |
| CNHI | 404 Not Found | URL changed: `careers.cnh.com` is dead | Find new CNH Industrial careers URL |
| TotalEnergies | 0 jobs | Avature JS — Firecrawl crawl saved raw md but LLM got 0 | Inspect firecrawl_raw.md; try India-specific search URL |
| Baker Hughes | 402 Payment Required | Firecrawl paid-tier feature limit hit | Check Firecrawl plan — extract endpoint may be capped |
| Dell | 402 Payment Required | Same Firecrawl plan limit | Same fix |

**Key systemic issue — Workday JD fetch (0/N for all Workday companies):**
The individual job detail API (`GET .../wday/cxs/{tenant}/{site}/jobs/{externalPath}`)
returns the full JD, but this fetch is failing silently for all tenants this run.
Root cause likely: rate limiting or auth token expiry on the CXS API during the fetch loop.
Fix: add retry logic + backoff in scrapers.py Workday JD fetch; or batch fewer JDs per run.

---

### Session 2026-04-10 — First full run (interrupted)
- Ran `python main.py` (full run, all portals).
- Run was force-closed mid-way due to memory pressure from running Docker + LM Studio simultaneously.
- **15 companies fully scraped** before interruption:
  Accenture, Airbus, Amazon, American Express, Chanel, Continental, Fidelity Investments,
  LDC (Louis Dreyfus), Morgan Stanley, STMicroelectronics, Sanofi, ServiceNow, Shell, Stripe, Wells Fargo
---

## SCRAPE_QUEUE — TODO

```
# Workday — need to re-run (will now use careers_url for Firecrawl fallback, code fixed)
Engie                [wd-fallback-url-fixed] https://jobs.engie.com
Mastercard           [wd-fallback-url-fixed] https://careers.mastercard.com/us/en/search-results
Novartis             [wd-fallback-url-fixed] https://www.novartis.com/careers
Synopsys             [wd-fallback-url-fixed] https://careers.synopsys.com/

# Needs India-filtered URL (currently pointing to generic homepage)
Baker Hughes         [needs-india-url]       https://careers.bakerhughes.com/global/en/search-jobs/India
Philips              [needs-india-url]       https://www.careers.philips.com/global/search-results?country=in
TotalEnergies        [needs-india-url]       https://jobs.totalenergies.com/en_US/careers/SearchJobs/?location=India
Volvo Group          [needs-india-url]       https://jobs.volvogroup.com/search/?q=&locationsearch=India
Microsoft            [needs-correct-url]     https://careers.microsoft.com/en-us/search?q=&l=india — js-required

# Broken endpoints — need URL investigation
Atlassian            [board-token-changed]   https://www.atlassian.com/company/careers
Michelin             [url-changed]           https://www.michelin.com/en/careers/
CNHI                 [url-changed]           https://www.cnh.com/en-US/our-company/careers
Schneider Electric   [url-changed]           https://careers.se.com
Alstom               [fc-timeout]            https://jobsearch.alstom.com — try scrape not crawl
CMA CGM              [fc-timeout]            https://jobs.cmacgm-group.com — try scrape not crawl
Air France           [fc-timeout]            https://recrutement.airfrance.com — try scrape not crawl
SAP                  [fc-timeout]            https://jobs.sap.com — try scrape not crawl
Dell                 [fc-no-pages]           https://jobs.dell.com/search-jobs/India — verify endpoint
Apple                [api-broken]            https://jobs.apple.com/en-in/search — js-required, use FC

# Workday slugs unconfirmed
Capgemini            [slug-unknown]          https://capgemini.wd3.myworkdayjobs.com
HCL Technologies     [slug-unknown]          https://hcltech.wd3.myworkdayjobs.com
MSCI                 [slug-unknown]          https://msci.wd3.myworkdayjobs.com

# New / not yet added
Cisco                [new]                   https://jobs.cisco.com
Tech Mahindra        [url-changed]           https://www.techmahindra.com/en-in/careers/
```

---

## FIELD MAP — ATS → Canonical Schema

| Canonical Field | Workday | Greenhouse | SmartRecruiters | Amazon Jobs | Eightfold |
|----------------|---------|------------|-----------------|-------------|-----------|
| `job_id` | `jobReqId` | `id` | `id` | `id_icims` | `id` |
| `title` | `title` | `title` | `name` | `title` | `name` |
| `job_url` | built from `externalPath` | `absolute_url` | `ref` | built from `id` | built from `id` |
| `raw_jd_text` | `jobDescription` (HTML) | `content` (HTML) | `jobAd.sections.jobDescription.text` | `description` | `description` |
| `location_city` | `locationsText` | `location.name` | `location.city` | `normalized_location` | `location` |
| `date_posted` | `postedOn` | `updated_at` | `releasedDate` | `posted_date` | `updated_at` |
| `business_unit` | `bulletFields[1]` | `departments[0].name` | `department.label` | `business_category` | `team` |
| `source_platform` | `Workday` | `Greenhouse` | `SmartRecruiters` | `Amazon` | `Eightfold` |
