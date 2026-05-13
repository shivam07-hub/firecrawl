# KNOWN_PORTALS.md — Careers Portal Registry
**Last verified: 2026-05-02.** Crack session history → `RUN_HISTORY.md`.

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
| Philips | https://www.careers.philips.com/global/en | philips | wd3 | jobs-and-careers | ~48 | ✅ working — uses locationHierarchy1 facet (not locationCountry); facet + UUIDs in workday_registry.json |
| BrowserStack | https://www.browserstack.com/careers | browserstack | wd3 | External | ? | 🔴 no India UUID — India facet not found in tenant; skip |
| Baker Hughes | https://careers.bakerhughes.com/global/en/search-results?qcountry=India | bakerhughes | wd5 | BakerHughes | ? | 🔴 no India UUID — India facet not found in tenant; skip |
| Dell | https://jobs.dell.com/en-us/search-jobs/India | dell | wd1 | External | ? | ✅ Workday tenant confirmed via XHR inspection 2026-04-16 |
| Deutsche Bank | https://careers.db.com | db | wd3 | DBWebsite | ~521 | ✅ cracked 2026-04-29 — Country facet UUID in workday_registry.json; 521 India jobs |
| Capgemini | https://www.capgemini.com/in-en/careers/job-search/ | ⚠️ NOT Workday | ⚠️ | ⚠️ NOT Workday — custom Azure API; see CUSTOM section | 921 | ✅ CRACKED — see CUSTOM / PROPRIETARY section |
| HCL Technologies | https://careers.hcltech.com/go/India/9553955/ | hcltech | wd3 | — | 60 | 🔴 wrong ATS — endpoint confirmed as SAP SuccessFactors/Jobs2Web v1 (`/services/recruiting/v1/jobs`); moved to TALEO COMPANIES on 2026-04-30 |
| MSCI | https://careers.msci.com/ | msci | wd3 | ⚠️ career site name unconfirmed | ? | ⚠️ Old portal (careers.msci.com) is 404. Moved to Workday (msci.wd3) — career_site slug unknown. Try: MSCI, MSCIExternal, MSCI_External |
| Coca-Cola | https://www.coca-colacompany.com/careers | coke | wd1 | coca-cola-careers | 68 | ✅ CRACKED 2026-05-13 — searchText="india" mode (no India UUID needed); override in workday_registry.json; is_india() Python filter applied |
| Nike | https://careers.nike.com/jobs?q=india | nike | wd1 | nke | 46 | ✅ CRACKED 2026-05-13 — searchText="india" mode (no India UUID in tenant); override in workday_registry.json; is_india() Python filter applied |
| Intel | https://jobs.intel.com/en/search | intel | wd1 | External | ~84 | ✅ working — searchText="india" mode (no India UUID in tenant); override in workday_registry.json; is_india() Python filter applied |
| State Street | https://careers.statestreet.com | statestreet | wd1 | Global | 351 | ✅ working — 351 India jobs scraped with full JDs via CXS; probed 2026-04-19 |
| DBS Bank | https://www.dbs.com/dbstechindia/index.html | dbs | wd3 | DBS_Careers | 285 | ✅ working — 285 India jobs scraped with full JDs via CXS; probed 2026-04-19 |
| BlackBerry | https://www.blackberry.com/us/en/company/careers | bb | wd3 | BlackBerry | 5+ | ✅ CRACKED 2026-05-07 — India UUID in `workday_registry.json` (`Country=c4f78be1...`); inventory probe returned live India jobs; targeted run scraped 5 raw with 5/5 JDs |
| Lloyds Banking Group | https://www.lloydsbankinggroup.com/careers | lbg | wd3 | LBG_Careers | ~128 total | 🟡 Workday CXS confirmed wd3/LBG_Careers — India UUID TBD; probed 2026-04-19 |
| EA (Electronic Arts) | https://www.ea.com/careers | ea | wd5 | EA_Global | ? | 🟡 Workday confirmed via FC scrape — CXS returns 401; Firecrawl fallback via careers_url; probed 2026-04-19 |
| GE Aerospace | https://www.gecareers.com | ge | wd5 | GE_ExternalSite | ? | 🟡 Workday confirmed via FC scrape — CXS returns 422 (Cloudflare); Firecrawl fallback via careers_url; probed 2026-04-19 |
| Medtronic | https://www.medtronic.com/en-us/about/careers.html | medtronic | wd3 | MedtronicCareers | ? | 🟡 Workday confirmed via FC scrape — CXS returns 422 (Cloudflare); Firecrawl fallback via careers_url; probed 2026-04-19 |
| Oracle | https://careers.oracle.com/en/sites/jobsearch | oracle | wd1 | OracleJobs | ? | 🔴 wrong ATS — Oracle CE confirmed via XHR cURL 2026-05-13; moved to ORACLE HCM section; endpoint: eeho.fa.us2.oraclecloud.com / CX_45001 / location=India text filter |
| Bank of America | https://careers.bankofamerica.com | bankofamerica | wd1 | Global | ? | 🟡 Workday confirmed via FC scrape — CXS returns 422 (Cloudflare); Firecrawl fallback via careers_url; probed 2026-04-19 |
| Siemens | https://new.siemens.com/global/en/company/jobs.html | siemens | wd3 | External | ? | 🔴 wrong ATS — jobs.siemens.com runs Siemens ExternalJobs (`/en_US/externaljobs/SearchJobs` + `/JobDetail/{id}`), not Workday CXS; moved to OTHER PLATFORMS on 2026-05-01 |
| Inspire Brands | https://careers.inspirebrands.com | inspirebrands | wd1 | InspireBrandsCareers | ? | 🟡 Workday confirmed via FC scrape — CXS returns 422 (Cloudflare); Firecrawl fallback via careers_url; probed 2026-04-19 |
| Ford | https://www.ford.com/careers/ | fordcareers | wd12 | Ford_Careers | ? | 🟡 Workday confirmed via FC scrape — CXS 422; FC fallback via `https://fordcareers.wd12.myworkdayjobs.com/en-US/Ford_Careers?q=india`; probed 2026-04-19 |
| Unilever | https://careers.unilever.com/en/location/india-jobs/34155/1269750/2 | ⚠️ NOT Workday | — | — | ? | ⚠️ moved — TalentBrew route now in CONSUMER GOODS section; listing JS-rendered so talentbrew provider will attempt FC fallback |
| Adobe | https://careers.adobe.com/us/en/search-results | adobe | wd5 | external_experienced | ? | 🔴 wrong ATS for listing flow — careers.adobe.com is Phenom SSR (`refNum=ADOBUS`, `content-us.phenompeople.com`); moved to OTHER PLATFORMS on 2026-05-01 |
| Hitachi Vantara | https://hitachivantara.wd3.myworkdayjobs.com/HitachiVantaraCareers | hitachivantara | wd3 | HitachiVantaraCareers | ? | 🟡 Workday confirmed — CXS 422 blocked; FC fallback via en-US URL with India filter; probed 2026-04-19 |
| Thomson Reuters | https://thomsonreuters.com/en/careers.html | thomsonreuters | wd5 | External_Career_Site | 67 | ✅ cracked 2026-05-01 — CXS POST confirmed from browser (`/wday/cxs/thomsonreuters/External_Career_Site/jobs`); India facet `Location_Country=c4f78be1a8f14da0ab49ce1162348a5e` |
| CGI | https://www.cgi.com/en/careers | cgicareers | wd3 | CGI | ? | 🟡 Workday confirmed (`cgicareers.wd3/CGI`) — CXS 422; FC fallback via careers_url; probed 2026-04-19 |
| ADP | https://jobs.adp.com | adp | wd5 | ADP | ? | 🔴 wrong ATS — jobs.adp.com is Happydance/TalentBrew flow (server-rendered listings + detail pages); moved to OTHER PLATFORMS on 2026-05-01 |
| Intuit | https://careers.intuit.com/job-search-results/?location=India | intuit | wd5 | Intuit | ? | 🔴 wrong ATS — jobs now confirmed on TalentBrew/Avature surface (`jobs.intuit.com`); moved to OTHER PLATFORMS on 2026-05-01 |
| Samsung | https://job.samsung.com/en/search/?search_keyword=&career_type=1&search_country=IND | samsungelectronics | wd3 | ⚠️ career_site unconfirmed | ? | 🟡 Workday suspected (`samsungelectronics.wd3`) — CXS 422 blocked; job.samsung.com also FC-blocked; FC fallback via careers_url TBD; probed 2026-04-19 |
| Carelon Global Solutions | https://www.carelonglobal.in/careers | elevancehealth | wd1 | carelonglobal_in | ? | 🟡 Workday confirmed (`elevancehealth.wd1/carelonglobal_in`) — only 7 total jobs, no India UUID found; FC fallback via careers_url; probed 2026-04-19 |
| Target | https://careers.target.com/jobs | target | wd5 | TargetCareers | ~265 | ✅ working — searchText="india" mode (no India UUID in tenant); override in workday_registry.json; is_india() Python filter applied |
| Broadcom | https://careers.broadcom.com/careers?query=&location=India | broadcom | wd1 | ⚠️ career_site unconfirmed | ? | 🟡 Workday suspected — all career_site slugs 404; broadcom.wd1 tenant confirmed; correct slug TBD (try: External, BroadcomCareers, BCICareers); FC-blocked; probed 2026-04-19 |
| 3M | https://www.3m.com/3M/en_US/careers-us/ | 3m | wd1 | Search | 81 | ✅ working — 81 India jobs, 100% JD; facet=Location_Country; scraped 2026-04-19 |
| NXP Semiconductors | https://careers.nxp.com | nxp | wd3 | careers | 161 | ✅ working — 161 India jobs, 100% JD; facet=Location_Country; scraped 2026-04-19 |
| Autodesk | https://careers.autodesk.com | autodesk | wd1 | Ext | 111 | ✅ working — 111 India jobs, 100% JD; facet=locationCountry; scraped 2026-04-19 |
| Roche | https://careers.roche.com | roche | wd3 | roche-ext | 1 | 🔴 only 1 India job — low volume, skip; locations facet uuid=54c59631...; verified 2026-04-19 |
| ING Bank | https://careers.ing.com | ing | wd3 | ICSGBLCOR | 0 | 🔴 no India locations in ICSGBLCOR portal; skip; verified 2026-04-19 |
| Barclays | https://search.jobs.barclays | barclays | wd3 | External_Career_Site_Barclays | 500+ | ✅ working — 500 India jobs (cap), 100% JD; 12 India office UUIDs via locations facet; scraped 2026-04-19 |
| Maersk | https://www.maersk.com/careers/vacancies | maersk | wd3 | Maersk_Careers | 97 | ✅ working — 97 India jobs, 100% JD; 26 India office UUIDs via locations facet; scraped 2026-04-19 |
| DXC Technology | https://careers.dxc.com | dxctechnology | wd1 | DXCJobs | 211 | ✅ working — 211 India jobs, 100% JD; facet=locationCountry; scraped 2026-04-19 |
| ABB | https://careers.abb/global/en | abb | wd3 (suspected) | — | 261 | 🔴 wrong ATS for listing flow — careers.abb runs Phenom SSR (`refNum=ABB1GLOBAL`) with embedded `phApp.ddo.eagerLoadRefineSearch.data.jobs`; moved to OTHER PLATFORMS on 2026-05-02 |
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
| Dr. Reddy's | https://careers.drreddys.com | DrReddysLaboratoriesLtdSBX | 142 | ✅ cracked 2026-04-29 — slug found via smrtr.io shortlink redirect on career page; 142 India jobs; API public, no auth; SmartRecruiters Attrax (Springboard) platform |

---

## GREENHOUSE COMPANIES
*API pattern: `GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`*
*Filter: check `location.name` field for India cities in the response*

| Company | Careers URL | Board Token | India Jobs | Status |
|---------|-------------|-------------|-----------|--------|
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
*API pattern: `GET https://{tenant}.eightfold.ai/api/apply/v2/jobs?query=&count=20&start=0&location=India&domain={api_domain}`*
*JD fetch: `GET https://{tenant}.eightfold.ai/api/apply/v2/jobs/{id}?domain={api_domain}`*
*Note: API uses `count`+`start` params (NOT `num`). Companies with API Domain set use direct API; others fall back to Firecrawl.*

| Company | Careers URL | Eightfold Domain | API Domain | Status |
|---------|-------------|-----------------|------------|--------|
| Netflix | https://explore.jobs.netflix.net/careers | netflix.eightfold.ai | netflix.com | ✅ cracked 2026-04-29 — direct API working; 7 India jobs |
| American Express | https://aexp.eightfold.ai/careers/?location=India&domain=aexp.com&hl=en | aexp.eightfold.ai | | 🔴 migrated off Eightfold — live page source now points to Oracle Candidate Experience on `careers.americanexpress.com` / `egug.fa.us2.oraclecloud.com`; use ORACLE HCM row added 2026-05-13 |
| Morgan Stanley | https://morganstanley.eightfold.ai/careers?location=INDIA&domain=morganstanley.com | morganstanley.eightfold.ai | | 🔴 wrong route — Eightfold API 403; actual route is PCSX on same host; moved to PHENOM CX (PCSX) section 2026-05-13 |
| STMicroelectronics | https://stmicroelectronics.eightfold.ai/careers?location=India&hl=en | stmicroelectronics.eightfold.ai | stmicroelectronics.com | ✅ CRACKED 2026-05-13 — Eightfold API works with `domain=stmicroelectronics.com`; 4 India jobs in live probe; full JD via `/api/apply/v2/jobs/{id}`; no Firecrawl needed |
| Philip Morris International | https://join.pmicareers.com/search-results | join.pmicareers.com (Eightfold hosted) | | 🔴 API broken — "Tenant not identified"; Firecrawl path |
| Micron Technology | https://micron.eightfold.ai/careers?location=India&hl=en | micron.eightfold.ai | | 🟡 API 403 — Firecrawl path |
| Qualcomm | https://careers.qualcomm.com | careers.qualcomm.com (Qualcomm PCSX) | | 🔴 wrong route — Eightfold API blocked; actual route is PCSX at careers.qualcomm.com; moved to PHENOM CX (PCSX) section 2026-05-13 |
| HSBC | https://hsbc.eightfold.ai/careers?location=India&hl=en | hsbc.eightfold.ai | hsbc.com | ✅ CRACKED 2026-05-13 — direct Eightfold API works; domain=hsbc.com; 250 India jobs confirmed |
| Citibank | https://jobs.citi.com/search-jobs/India | citi.eightfold.ai | | ✅ CRACKED 2026-05-08 — route via Radancy/TalentBrew HTML (`ats=talentbrew`); direct listing + JSON-LD detail pages; Eightfold API remains 403 |

---

## ICIMS CUSTOM CAREER SITES
*API pattern: `GET https://{careers_domain}/api/jobs?country=India&page=N&limit=100&sortBy=relevance&descending=false&internal=false`*
*Response: `{"jobs": [{"data": {...}}], "totalCount": N}` — full JD included, 100 jobs/page with limit param, no auth required.*

| Company | Careers URL | India Jobs | Status |
|---------|-------------|-----------|--------|
| AMD | https://careers.amd.com/careers-home/jobs | 304 | ✅ cracked 2026-04-29 — full JD; no auth; 100/page; ats=icims_custom |
| Keysight Technologies | https://jobs.keysight.com/external/jobs | 109 | ✅ cracked 2026-04-29 — same iCIMS pattern; icims_location_param=location; no auth |

---

## DARWINBOX COMPANIES
*API: `POST https://{tenant}.darwinbox.in/ms/candidateapi/job/alljobs?companyId=main`*
*Body: `{"companyId":"main","page":N,"sort_option":"new","limit":50}`*
*CF requirement: set `DARWINBOX_CF_BM` + `DARWINBOX_SESSION` env vars (from browser, expires 30min) → fallback Firecrawl*

| Company | Careers URL | India Jobs | Status |
|---------|-------------|-----------|--------|
| IIFL Finance | https://iifl.darwinbox.in/ms/candidate/careers | 41 | ✅ cracked 2026-04-29 — API found; full JD; CF cookie required; ats=darwinbox |
| Flipkart | https://flipkart.darwinbox.com/ms/candidate/careers | ? | 🟡 Darwinbox confirmed — CF protected; verify India job count |

---

## MYNEXTHIRE COMPANIES
*API: `POST https://{tenant}.mynexthire.com/employer/careers/reqlist/get`*
*Body: `{"source":"careers","code":"","filterByBuId":-1,"filterByCustomField":{"career_page_category":"{cat}"}}`*
*Iterates all categories: Technology, Business, Operations, etc. No auth required.*

| Company | Careers URL | Tenant Domain | India Jobs | Status |
|---------|-------------|--------------|-----------|--------|
| Swiggy | https://careers.swiggy.com | swiggy.mynexthire.com | 83 | ✅ cracked 2026-04-30 — no auth; Technology(10)+Business(73); full JD in jdDisplay; ats=mynexthire |

---

## SPIRE2GROW COMPANIES
*API: `GET https://io.spire2grow.com/ies/v1/p/requisition/_search?page=N&size=100`*
*Required headers: `Workspaceid`, `Workflowid`, `Origin`*
*Response: `{"entities":[...],"total":N}` — full JD in jobDescription; no auth required.*

| Company | Careers URL | Workspace ID | Workflow ID | India Jobs | Status |
|---------|-------------|-------------|------------|-----------|--------|
| Myntra | https://jobs.myntra.com | MYNTRA-93as3 | WFU_1777489282823000 | 16 | ✅ cracked 2026-04-30 — Spire2Grow IES ATS; no auth; full JD; all India jobs; ats=spire2grow |

---

## ZWAYAM COMPANIES
*API: `POST https://apic2.zwayam.com/jobs/search` (multipart/form-data)*
*Fields: filterCri (JSON), domain, companyId (base64)*
*Response: Elasticsearch hits in data.data[]; _source has jobTitle, location, shortDescription*

| Company | Careers URL | Zwayam Domain | Company ID (b64) | India Jobs | Status |
|---------|-------------|--------------|-----------------|-----------|--------|
| Rakuten India | https://rakuten.openings.co | rakuten.openings.co | MTUxMjQ= | 10 | ✅ cracked 2026-04-30 — Zwayam ATS; no auth; full JD in shortDescription; India-only portal; ats=zwayam |

---

## TALEO COMPANIES
*Classic TBE: `POST https://{careers_domain}/services/jobs/search/` with `{"locationsearch":"india","recordsperpage":100}`*
*v1 REST: `POST https://{careers_domain}/services/recruiting/v1/jobs` with `{"location":"india","pageNumber":N}` — auto-detected from endpoint path `/recruiting/v1/`.*
*JD: fetched from individual HTML page `/job/{urltitle}/{id}/`. No auth required.*

| Company | Careers URL | India Jobs | Status |
|---------|-------------|-----------|--------|
| ANZ Bank | https://careers.anz.com | 7 | ✅ cracked 2026-04-30 — Oracle Taleo TBE; no auth; JD from HTML page fetch; ats=taleo |
| Wipro | https://careers.wipro.com/services/recruiting/v1/jobs | 9176 | ✅ CRACKED 2026-04-30 — Taleo v1 REST; no auth; `location=india`; paginated 10/page; JD from HTML job page; ats=taleo; taleo_use_location=True |
| HCL Technologies | https://careers.hcltech.com/services/recruiting/v1/jobs | 42 | ✅ cracked 2026-04-30 — SAP SuccessFactors/Jobs2Web v1 REST; JD URL format is `/job/{urltitle}/{id}-en_US` (plain `/id/` redirects to error page); full JDs now extracted |

---

## MCKINSEY COMPANIES
*API: `GET https://gateway.mckinsey.com/apigw-x0cceuow60/v1/api/jobs/search?countries=India&pageSize=200&lang=en`*
*No auth required. Origin header: `https://www.mckinsey.com`. JD in whoYouWillWorkWith + whatYouWillDo + yourBackground.*

| Company | Careers URL | India Jobs | Status |
|---------|-------------|-----------|--------|
| McKinsey & Company | https://www.mckinsey.com/careers/search-jobs?countries=India | 46 | ✅ cracked 2026-04-30 — custom gateway API; no auth; full JD from 3 fields; ats=mckinsey |

---

## CUSTOM / PROPRIETARY APIs

| Company | Careers URL | ATS / Platform | Scraping Endpoint | India Filter | India Jobs | Status |
|---------|-------------|----------------|------------------|-------------|-----------|--------|
| Amazon | https://www.amazon.jobs | Custom (AWS Jobs) | `GET https://www.amazon.jobs/en/search.json?base_query=&loc_query=India&country=IND&result_limit=100` | `country=IND` param | ~2,963 | ✅ working — clean JSON API |
| Atlassian | https://www.atlassian.com/company/careers/all-jobs?team=Interns%2CGraduates&location=&search= | Atlassian Careers API (iCIMS-backed) | `GET https://www.atlassian.com/endpoint/careers/listings` | Python `is_india()` on `locations[]` strings | 1 | ✅ CRACKED 2026-05-02 — direct JSON array (82 global jobs in snapshot); fields include `id`, `title`, `locations`, `overview`, `responsibilities`, `qualifications`, `applyUrl`; no auth required |
| Apple | https://jobs.apple.com/en-in/search | Apple Jobs API | `POST https://jobs.apple.com/api/v1/search` | Python `is_india()` on `locations[]`; JD via `GET /api/v1/jobDetails/{positionId}` | ~100+ | ✅ CRACKED 2026-05-08 — direct JSON API; routed to `ats=apple_jobs`; no Firecrawl needed |
| Cognizant | https://careers.cognizant.com/india-en/jobs | XML Feed | `GET https://careers.cognizant.com/india-en/jobs/xml/?rss=true` | Python `is_india()` on city/state/country | 437 | ✅ CRACKED 2026-05-08 — public XML feed with full descriptions; routed to `ats=cognizant_xml`; no Firecrawl needed |
| Google | https://www.google.com/about/careers/applications/jobs/results/?location=India | Google Careers embedded HTML | `GET https://www.google.com/about/careers/applications/jobs/results/?location=India&page=N` | `location=India` param + Python `is_india()` on embedded locations | 371 | ✅ CRACKED 2026-05-11 — user-supplied careers URL works without cookies; HTML embeds full job records in `AF_initDataCallback`; paginate with `page=N` until empty; routed to `ats=google_careers`; no Firecrawl needed |
| Infosys | https://career.infosys.com/joblist | Custom (Infosys gateway) | `GET https://intapgateway.infosysapps.com/careersci/search/intapjbsrch/getCareerSearchJobs?sourceId=1,21&searchText=ALL` | India-only portal (all 1285 jobs are India) | 1285 | ✅ CRACKED 2026-04-29 — flat JSON array, no auth; fields: postingTitle/referenceCode/postingDescription/location/createdOn/unit; JD in listing (no separate fetch needed); apply_url=career.infosys.com/jobdesc?referenceCode={code}; india_only=False |
| IntouchCX | https://www.intouchcx.com/careers/ | IntouchCX WP JSON + Dayforce/legacy apply | `GET https://www.intouchcx.com/wp-json/intouchcx/v1/jobs?country=India` | `country=India` param | 40 | ✅ CRACKED 2026-05-10 — user-supplied WP JSON feed; listing fields are `job`, `link`, `location`; full JD fetched from `apply.intouchcx.com/{id}` `.application-body` or Dayforce SSR `__NEXT_DATA__.props.pageProps.jobData`; routed to `ats=intouchcx`; no Firecrawl needed |
| L'Oréal | https://careers.loreal.com/en_US/jobs/SearchJobs?3_110_3=18031 | TalentBrew (NOT Phenom) | `https://careers.loreal.com/en_US/jobs/SearchJobs?3_110_3=18031` | 9 | ✅ CRACKED 2026-05-13 — India facet param `3_110_3=18031`; 9 India jobs (Mumbai/Pune); CF-blocked on direct HTTP (FC required for listing); job detail at `/en_US/jobs/JobDetail/{slug}/{id}`; ats=talentbrew |
| Microsoft | https://careers.microsoft.com/v2/global/en/locations/india.html | Microsoft Careers PCSX + apply API | `GET https://apply.careers.microsoft.com/api/pcsx/search?domain=microsoft.com&query=&location=India&start=0&hl=en` | `location=India` param + `standardizedLocations=["IN"]` / Python `is_india()` | 158 | ✅ CRACKED 2026-05-11 — user-supplied location page works without cookies; full search comes from PCSX `/api/pcsx/search` pagination (`start += 10`); JD via `GET https://apply.careers.microsoft.com/api/apply/v2/jobs/{id}?domain=microsoft.com`; routed to `ats=microsoft_careers`; no Firecrawl needed |
| Stellantis | https://www.stellantis.com/en/careers | Custom | careers page | JS-rendered | 3 | ✅ working via Firecrawl — 3 India jobs extracted + enriched 2026-04-11 |
| TCS | https://www.tcs.com/careers | iBegin (custom) | `GET https://ibegin.tcs.com/iBegin/...` — inspect XHR | — | 0 | ⬇️ deprioritized — career page shows no visible jobs; antibot block (document_antibot); investigated 2026-04-30 |
| Capgemini | https://www.capgemini.com/in-en/careers/job-search/ | Custom Azure API | `GET https://cg-jobstream-api.azurewebsites.net/api/job-search?country_code=in-en&page=1&size=100` | country_code=in-en | 921 | ✅ CRACKED 2026-04-30 — no auth; full JD in description field; apply_job_url included; ats=custom |
| ZS Associates | https://jobs.zs.com/all/jobs | Custom (iCIMS) | `GET https://jobs.zs.com/api/jobs?page=1&country=India&sortBy=relevance&descending=false&internal=false` | country=India | 89 | ✅ CRACKED 2026-04-30 — no auth; full JD in jobs[].data.description; slug → apply URL; ats=custom |

---

## SAP SUCCESSFACTORS / JOBS2WEB COMPANIES
*API pattern varies — most return HTML, route through Firecrawl*

| Company | Careers URL | ATS | Scraping Endpoint | India Jobs | Status |
|---------|-------------|-----|------------------|-----------|--------|
| Alstom | https://jobsearch.alstom.com | SAP SuccessFactors / Jobs2Web (HTML) | `GET https://jobsearch.alstom.com/search/?createNewAlert=false&q=&locationsearch=india&optionsFacetsDD_country=&optionsFacetsDD_department=&optionsFacetsDD_shifttype=&startrow=N` | `locationsearch=india` | ✅ CRACKED 2026-05-02 — routed to `ats=sap_jobs2web_html`; direct HTML table parse + per-job detail JD extraction; run validated with 196 saved jobs |
| Monitor Deloitte | https://southasiacareers.deloitte.com/go/Deloitte-India/718244/ | SAP SuccessFactors / Jobs2Web (HTML) | `GET https://southasiacareers.deloitte.com/search/?createNewAlert=false&q=&locationsearch=india&optionsFacetsDD_city=&optionsFacetsDD_customfield2=` | ~1,772 | ✅ CRACKED 2026-05-02 — direct paginated HTML listing (`startrow=N`) + detail `/job/.../{id}` pages with full JD (`data-careersite-propertyid=\"description\"`) and apply URL; routed to `ats=sap_jobs2web_html` |
| GMR Group | https://careers.gmrgroup.in | SAP SuccessFactors / Jobs2Web (HTML) | `GET https://careers.gmrgroup.in/search/?q=&locationsearch=india&startrow=N` | 7+ | ✅ CRACKED 2026-05-13 — direct Jobs2Web HTML table parse + per-job detail JD extraction; targeted provider probe returned full JDs; routed to `ats=sap_jobs2web_html` |
| CMA CGM | https://jobs.cmacgm-group.com | SAP SuccessFactors / Jobs2Web (HTML) | `GET https://jobs.cmacgm-group.com/search/jobs?optionsFacetsDD_country=IN&startrow=N&sortColumn=referencedate&sortDirection=desc` | 4 | ✅ CRACKED 2026-05-07 — recovered from Market Data V1; old `country=India` URL is stale and returns global/US false positives; direct Jobs2Web HTML route uses country facet `optionsFacetsDD_country=IN` + per-job detail JDs; routed to `ats=sap_jobs2web_html` |
| CNHI | https://join.cnh.com | SAP SuccessFactors / JS SPA | `https://join.cnh.com/search/?q=india` | India-filtered search URL | ✅ working — careers.cnh.com + join.cnh.com both live; India filter via q=india; Firecrawl extract; updated 2026-04-28 |
| Volvo Group | https://www.volvogroup.com/en/careers | SAP SuccessFactors / Jobs2Web (HTML) | `GET https://jobs.volvogroup.com/search/?q=&locationsearch=India&startrow=N` | 27 | ✅ CRACKED 2026-05-07 — recovered from Market Data V1; direct Jobs2Web HTML table parse + per-job detail JD extraction; routed to `ats=sap_jobs2web_html` |
| Deloitte India | https://apply.deloitte.com/en_US/careersUSI/SearchJobs | Avature SearchJobs HTML (USI mirror) | `GET https://apply.deloitte.com/en_US/careersUSI/SearchJobs/?jobRecordsPerPage=10&jobOffset=N` | India feed (268 listings in latest snapshot) | ✅ CRACKED 2026-05-03 — direct paginated HTML listings + JobDetail pages with JSON-LD JD and apply URL; routed to `ats=deloitte_usi` |
| EY India | https://eyglobal.yello.co/job_boards/c1riT--B2O-KySgYWsZO1Q | Yello (Recsolu) | `GET https://eyglobal.yello.co/job_boards/c1riT--B2O-KySgYWsZO1Q/search?query=&filters=30009&page_number=N` | Country/Region filter id `30009` (India) | ✅ CRACKED 2026-05-02 — direct JSON listing (`/search`) + full JD on `/jobs/{token}` detail pages; ats=yello |
| EY India Experienced | https://careers.ey.com/ey/search/?createNewAlert=false&q=india&optionsFacetsDD_country=IN | SAP SuccessFactors / Jobs2Web (HTML) | `GET https://careers.ey.com/ey/search/?createNewAlert=false&q=india&optionsFacetsDD_customfield1=&optionsFacetsDD_country=IN&optionsFacetsDD_city=&startrow=N` | `optionsFacetsDD_country=IN` | ✅ CRACKED 2026-05-02 — `ats=sap_jobs2web_html`; detail JDs parsed from `data-careersite-propertyid=\"description\"`; quality gate drops postings where JD is only requisition-id stub |
| PepsiCo | https://www.pepsicojobs.com/main/jobs?location=India | PepsiCo Jobs API (JSON) | `GET https://www.pepsicojobs.com/api/jobs?page=1&sortBy=relevance&descending=false&internal=false&country=India` | `country=India` | ✅ CRACKED 2026-05-02 — direct paginated JSON listing (`jobs[].data`) includes full JD (`description`) + apply URL (`apply_url`); routed to `ats=pepsico_jobs_api` |

---

## ORACLE HCM COMPANIES
*API pattern (basic): `GET https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?limit=25&offset=0&onlyData=true`*
*API pattern (finder/cracked): `?onlyData=true&expand=requisitionList.workLocation,...&finder=findReqs;siteNumber={Site Number},facetsList=LOCATIONS%3B...,limit=25,locationId={India Location ID},sortBy=POSTING_DATES_DESC`*
*Response shape (finder): nested — jobs at `items[0].requisitionList[]`; fields: `Id`, `Title`, `PrimaryLocation`*

| Company | Careers URL | Oracle Host | Site Number | India Location ID | India Jobs | Status |
|---------|-------------|------------|-------------|------------------|-----------|--------|
| Technip Energies | https://www.technipenergies.com/careers/ | hcxg.fa.em2.oraclecloud.com | CX_1 | 300000000345142 | 9+ | ✅ CRACKED 2026-04-29 — finder=findReqs India locationId confirmed; response nested at `items[0].requisitionList[]` |
| American Express | https://careers.americanexpress.com/en/sites/CX_1/jobs | egug.fa.us2.oraclecloud.com | CX_1 | 300000000228786 | 73 | ✅ CRACKED 2026-05-13 — Oracle Candidate Experience (`recruitingCEJobRequisitions?finder=findReqs`) discovered from live page source + Firecrawl cloud; India facet `locationsFacet -> India (Id=300000000228786)`; `TotalJobsCount=73` live |
| EXL Digital | https://www.exlservice.com/careers | fa-ewjt-saasfaprod1.fa.ocs.oraclecloud.com | | | ? | 🔴 API auth-gated — base URL returns 200 but count=0 items=0 even without India filter; public API not exposed; route via Firecrawl scrape |
| JP Morgan Chase | https://careers.jpmorgan.com | jpmc.fa.oraclecloud.com | CX_1001 | 300000000289360 | 25+ | ✅ CRACKED 2026-04-29 — finder=findReqs India locationId confirmed; response nested at `items[0].requisitionList[]` |
| Honeywell | https://careers.honeywell.com/us/en | ibqbjb.fa.ocs.oraclecloud.com | CX_1 | 300000000469485 | 392 | ✅ CRACKED 2026-04-29 — 392 India jobs; JD empty (ShortDescriptionStr/ExternalDescriptionStr absent); `items[0].requisitionList[]` |
| KPMG India | https://home.kpmg/in/en/home/careers.html | ejgk.fa.em2.oraclecloud.com | CX_1 | 300000000296042 | 752 | ✅ CRACKED 2026-05-13 — finder=findReqs India locationId=300000000296042; 752 India jobs; JD empty in list API (JS-rendered candidate experience at oraclecloud.com/hcmUI/CandidateExperience); response at `items[0].requisitionList[]` |
| Texas Instruments | https://careers.ti.com | edbz.fa.us2.oraclecloud.com | CX | 300000000361484 | 114 | ✅ cracked 2026-04-29 — finder=findReqs+locationId; 114 India jobs; JD empty in list API (ExternalDescriptionStr absent) |
| Nokia | https://jobs.nokia.com | fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com | CX_1 | 300000000471745 | 261 | ✅ cracked 2026-04-29 — finder=findReqs+locationId; 261 India jobs; JD=ShortDescriptionStr (477–770 chars) |
| BNY Mellon | https://www.bny.com/corporate/global/en/about-us/careers | eofe.fa.us2.oraclecloud.com | CX_3001 | 300000000378365 | 15+ | ✅ CRACKED 2026-04-29 — finder=findReqs India locationId confirmed; response nested at `items[0].requisitionList[]`; Chennai/Pune GCC |
| WESCO | https://www.wesco.com/us/en/careers.html | eklm.fa.us2.oraclecloud.com | CX | 300000000302954 | 7 | ✅ CRACKED 2026-05-07 — recovered from Market Data V1; Oracle HCM finder=findReqs with India locationId; response nested at `items[0].requisitionList[]`; targeted run saved 7 jobs; candidate URL uses `/sites/CX/job/{Id}` |
| Adani Group | https://www.adani.com/careers | eibd.fa.em2.oraclecloud.com | CX_2027 | | ? | ✅ CRACKED 2026-04-30 — finder=findReqs; India-only portal (no locationId needed); is_india() Python filter applied; response nested at `items[0].requisitionList[]` |
| Adani Solar | https://www.adani.com/careers | eibd.fa.em2.oraclecloud.com | CX_2033 | | ? | ✅ CRACKED 2026-04-30 — same Oracle host; India-only; no locationId |
| Adani Power Transmission | https://www.adani.com/careers | eibd.fa.em2.oraclecloud.com | CX_2023 | | ? | ✅ CRACKED 2026-04-30 — same Oracle host; India-only; no locationId |
| Adani Thermal Power | https://www.adani.com/careers | eibd.fa.em2.oraclecloud.com | CX_3003 | | ? | ✅ CRACKED 2026-04-30 — same Oracle host; India-only; no locationId |
| Adani Gas | https://www.adani.com/careers | eibd.fa.em2.oraclecloud.com | CX_2025 | | 61 | ✅ CRACKED 2026-04-30 — same Oracle host; India-only; no locationId |
| Oracle | https://careers.oracle.com/en/sites/jobsearch | eeho.fa.us2.oraclecloud.com | CX_45001 | | 5+ | ✅ CRACKED 2026-05-13 — Oracle CE confirmed via XHR cURL; uses `location=India` text param (not locationId); endpoint override in portal_reader.py; India jobs live (Bengaluru/Hyderabad) |

---

## iCIMS COMPANIES
*API: iCIMS REST not publicly documented — inspect XHR on careers page for `sc` (site config ID)*
*Typical search URL: `https://{company}.icims.com/jobs/search?ss=1&in_iframe=1&hashed=-1&mobile=false&country=IN&location=india`*

| Company | Careers URL | iCIMS Tenant | India Jobs | Status |
|---------|-------------|-------------|-----------|--------|
| ARM Holdings | https://careers.arm.com | arm | ? | ⚠️ standard iCIMS (arm.icims.com) — NOT icims_custom; careers.arm.com returns HTML; needs XHR inspection to find correct endpoint; probed 2026-04-30 |

---

## PHENOM REST API COMPANIES
*Direct paginated JSON API with location + category filters. Full JDs included in response.*
*API pattern: `GET {API Endpoint}&page=N` — paginate until jobs array empty*

| Company | Careers URL | API Endpoint | Status |
|---------|-------------|-------------|--------|
| Schneider Electric | https://www.se.com/en/careers/ | `https://careers.se.com/api/jobs?location=India&categories=Digital+Innovation+%26+Technology&pageSize=10` | ✅ working — Phenom/iCIMS JSON REST API; ~132 India IT jobs; verified 2026-04-02 |
| BCG | https://careers.bcg.com/global/en/locations/india | `https://careers.bcg.com/global/en/search-results?keywords=india` | ✅ CRACKED 2026-05-08 — Phenom SSR HTML embeds `phApp.ddo.eagerLoadRefineSearch.data.jobs`; direct detail pages provide JSON-LD JDs; routed to `ats=phenom_ssr` |
| Oliver Wyman | https://www.oliverwyman.com/careers.html | `https://mmc.phenompeople.com/global/en/oliver-wyman-search` | ⚠️ Phenom API returns 404 on careers.marsh.com redirect as of 2026-04-17; route via Firecrawl Docker scrape on mmc.phenompeople.com page |
| HP (HPE) | https://careers.hpe.com/us/en/search-results?qcountry=India | `https://careers.hpe.com/us/en/search-results?qcountry=India` | ✅ CRACKED 2026-05-13 — Phenom SSR embedded listings; `qcountry=IN` returned 0 but `qcountry=India` returns 363 India jobs in live probe; direct detail pages provide full JSON-LD JDs; routed to `ats=phenom_ssr` |
| Procter & Gamble | https://www.pgcareers.com/in/en/search-results?qcountry=India | `https://www.pgcareers.com/in/en/search-results?qcountry=India` | ✅ CRACKED 2026-05-02 — Phenom SSR HTML with embedded `phApp.ddo.eagerLoadRefineSearch.data.jobs`; country facet India=23 in snapshot; routed to `ats=phenom_ssr` (no Firecrawl needed) |

---

## PHENOM CX (PCSX) COMPANIES
*API: `GET https://{base}/api/pcsx/search?domain={domain}&query=&location=india&start={N}` — 10/page, no auth*
*JD: per-job HTML at `{base}/careers/job/{id}` → JSON-LD `<script type="application/ld+json">` — server-rendered, no JS*
*Pagination: `start` param increments by 10. Stop when `start >= data.count`.*

| Company | Careers URL | Base URL | Domain | India Jobs | Status |
|---------|-------------|----------|--------|-----------|--------|
| Haleon | https://careers.haleon.com | https://careers.haleon.com | haleon.com | 25 | ✅ cracked 2026-04-29 — pcsx list API + JSON-LD per-job JD; 6482 chars/job; no auth |
| Morgan Stanley | https://morganstanley.eightfold.ai/careers?location=INDIA&domain=morganstanley.com | https://morganstanley.eightfold.ai | morganstanley.com | 124 | ✅ CRACKED 2026-05-13 — PCSX search API on Eightfold host; 124 India jobs; India cities confirmed (Mumbai); no auth |
| Qualcomm | https://careers.qualcomm.com/careers?location=India&domain=qualcomm.com | https://careers.qualcomm.com | qualcomm.com | 709 | ✅ CRACKED 2026-05-13 — PCSX search API; 709 India jobs; JD via JSON-LD at /careers/job/{id} (4747 chars); no auth |

---

## PINPOINT ATS COMPANIES
*API pattern: `GET https://{domain}/en/postings.json?location_id[]=<india_id>`*
*Returns `{"data": [...]}` — full JD in `description` field, no auth required.*
*India location IDs vary per tenant — enumerate via GET /en/postings.json (no filter) and filter names containing "India".*

| Company | Careers URL | Base URL | India Location IDs | India Jobs | Status |
|---------|-------------|----------|-------------------|-----------|--------|
| Align Technology | https://jobs.aligntech.com/en/search-job | https://jobs.aligntech.com | 40427,40404,40480,40518,40520,40522 | 44 | ✅ cracked 2026-04-29 — Pinpoint ATS; 6 India location IDs; full JD; no auth |

---

## SENSEHQ COMPANIES
*ATS: SenseHQ Next.js SSR — jobs embedded in `__NEXT_DATA__.props.pageProps.jobsData.rows[]`*
*Fields: `id`, `title`, `location`, `description_external`, `department`, `job_type`*
*No pagination — all jobs in single page load.*

| Company | Careers URL | India Jobs | Status |
|---------|-------------|-----------|--------|
| Marico | https://marico.sensehq.com/careers | 8 | ✅ CRACKED 2026-05-13 — SenseHQ Next.js SSR; 8 India jobs (mostly manufacturing); jobsData.rows[] in NEXT_DATA; no auth; low priority — small volume |

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
| AstraZeneca | https://careers.astrazeneca.com/search-jobs/India | Radancy / TalentBrew | URL-based India filter; listing `data-total-pages`; detail pages provide JSON-LD JDs | ✅ CRACKED 2026-05-08 — routed to `ats=talentbrew`; no Firecrawl needed |
| ADP | https://jobs.adp.com/en/jobs/?mylocation=India&orderby=0&page=1&pagesize=20&rType=0&radius=100 | Happydance / TalentBrew-style | Direct India query URL; paginate via `page=N`; per-job detail URL `/en/jobs/{job_id}/{slug}/`; apply link from `recruiting.adp.com` button | ✅ cracked 2026-05-01 — ats=talentbrew; no Workday UUID needed; direct HTML scrape with India filter |
| H&M | https://career.hm.com/in-en/search/?l=cou%3Ain | HM Careers API (WordPress + SmartRecruiters backend) | `POST https://career.hm.com/in-en/wp-json/hm/v1/sr/jobs/search?_locale=user` with payload `{\"locations\":[\"cou:in\"],\"page\":N}`; parse `jobs[]` (`sr_id`, `title`, `job_description_text`, `apply_on_web_url`) | ✅ cracked 2026-05-02 — 111 India jobs in snapshot; routed to `ats=hm_wp_jobs` |
| Intuit | https://jobs.intuit.com/location/india-jobs/27595/1269750/2 | TalentBrew (Avature feed) | Direct India country facet URL (no Workday UUID needed); paginated path `/.../2/{page}`; JD + apply URL from job detail page | ✅ cracked 2026-05-01 — ats=talentbrew; no auth; direct HTML/JSON-LD scrape |
| Adobe | https://careers.adobe.com/us/en/search-results | Phenom SSR (`ADOBUS`) | Search/listing is server-rendered via `phApp.ddo.eagerLoadRefineSearch`; full JD in job page JSON-LD at `/us/en/job/{jobSeqNo}` | ✅ cracked 2026-05-01 — ats=phenom_ssr; Workday CXS not required |
| ABB | https://careers.abb/global/en/search-results?keywords=india | Phenom SSR (`ABB1GLOBAL`) | Search page embeds `phApp.ddo.eagerLoadRefineSearch.data.jobs`; full JD available on detail pages `/global/en/job/{jobId}/{title}` with JobPosting JSON-LD | ✅ cracked 2026-05-02 — ats=phenom_ssr; no Workday UUID needed |
| Siemens | https://jobs.siemens.com/en_US/externaljobs/SearchJobs/?42386=%5B812053%5D&42386_format=17546&listFilterMode=1&folderRecordsPerPage=6& | Siemens ExternalJobs | India filter is `42386=[812053]`; paginate via `folderOffset`; fetch full JD from `/en_US/externaljobs/JobDetail/{job_id}` and apply URL from `/ApplicationMethods?folderId={job_id}` | ✅ cracked 2026-05-01 — ats=siemens_externaljobs; no Workday UUID needed |
| Eli Lilly | https://careers.lilly.com/us/en/india | Phenom People | India-filtered URL — Phenom SSR page embeds listing JSON; apply URLs point to Workday candidate pages | ✅ CRACKED 2026-05-08 — routed to `ats=phenom_ssr`; direct listing + JSON-LD JD extraction; no Firecrawl needed |
| Cisco | https://careers.cisco.com/global/en/search-results?qcountry=India | Phenom SSR (`CISCISGLOBAL`) | Direct India URL (`qcountry=India`); parse listings from `phApp.ddo.eagerLoadRefineSearch.data.jobs`; paginate via `from={offset}&s=1`; use `jobId/reqId`, `title`, `location`, `descriptionTeaser`, `applyUrl` | ✅ cracked 2026-05-02 — direct SSR route; Docker inventory 2026-05-08 also sampled 3 usable India jobs/JDs |
| Michelin | https://jobs.michelin.in/job-offer-result-list | Michelin Astro/CXF | India criteria JSON on `jobLocation` facets | ✅ CRACKED 2026-05-07 — recovered from Market Data V1; current India careers site is server-rendered Astro/CXF at `jobs.michelin.in`; provider applies legacy India `criteria` JSON, paginates `page=N`, and fetches full JD from detail pages; routed to `ats=michelin_astro` |
| Philips | https://www.careers.philips.com/global/en | Phenom / TalentBrew | India filter in URL | ⚠️ broken — Firecrawl crawled generic homepage (no India listing); needs India-filtered URL 2026-04-11 |
| SAP | https://jobs.sap.com | SAP (own platform) | `GET https://jobs.sap.com/search/?q=&locationsearch=India` | 🟡 js-required | ⚠️ broken — Firecrawl crawl timeout (95s) as of 2026-04-11 |
| Tech Mahindra | https://www.techmahindra.com/careers/ | Custom ASP.NET WebForms | Main site `Join Us` points to `https://careers.techmahindra.com/`; listings include `JobDetails.aspx?JobCode=...` links with full JD on detail page; filter India jobs via location text in listing/detail | ✅ cracked 2026-05-02 — old `/en-in/careers/` path is 404; use `/careers/` |
| Boeing | https://jobs.boeing.com | Custom | `https://jobs.boeing.com/boeing/jobs/India` — custom career portal (TalentNet integration) | 🟡 js-required — custom ATS; probed 2026-04-19 |
| Uber | https://www.uber.com/careers/list/ | Custom | `https://www.uber.com/careers/list/` — custom SPA; no ATS fingerprint detected | 🟡 js-required — custom ATS; probed 2026-04-19 |
| Mondee Holdings | https://jobs.ashbyhq.com/mondee | Ashby | `https://jobs.ashbyhq.com/mondee` — Ashby ATS; no active India listings found as of probe | 🟡 js-required — Ashby ATS confirmed; may have 0 India jobs currently; probed 2026-04-19 |
| Syneriq Global | https://www.syneriqglobal.com | Custom | No dedicated careers page found — small company; check LinkedIn or main site footer | 🟡 js-required — no careers page detected; probed 2026-04-19 |
| ZF Lifetec | https://www.zf.com/global/en/careers | SAP SuccessFactors (suspected) | zf.com antibot-blocked; zf-lifetec.com/career.html is 404 — parent ZF Group uses SAP SF | ⚠️ blocked — antibot on zf.com; zf-lifetec.com has no careers page; re-probe via zf.com direct browser visit |
| HMIE | https://hmie.in | Custom | hmie.in/careers and hmie.in/jobs both 404 — no independent career portal found | 🔴 no career portal — Hyundai Motor India Engineering hires via parent or LinkedIn; skip |
| Meta | https://www.metacareers.com/jobs/?locations[0]=India | Custom (GraphQL) | `https://www.metacareers.com/jobs/?locations[0]=India` — custom React+GraphQL app; GraphQL 400 without session cookies | 🟡 js-required — FC-blocked; try FC scrape with stealth mode; probed 2026-04-19 |
| Walmart | https://careers.walmart.com/results?q=india | Custom SPA | `https://careers.walmart.com/results?q=india` — custom Next.js SPA (Walmart Global Tech India) | 🟡 js-required — FC scrape returns 7K chars (JS shell, no listings); all `/_next/` API attempts redirect to HTML; needs XHR inspection via Docker browser; only 1 job returned currently; investigated 2026-04-19 |
| DE Shaw | https://www.deshawindia.com/careers | D.E. Shaw Next.js SSR | Embedded `__NEXT_DATA__.props.pageProps.regularJobs`; full JD in `jobDescription`; apply redirect via `/recruit/jobs/Ads/Link/{jobUrl}` | ✅ CRACKED 2026-05-08 — routed to `ats=deshaw_india`; 76 public India roles in live probe; no Firecrawl needed |
| Adidas | https://jobs.adidas-group.com/search/?q=&optionsFacetsDD_country=IN | SAP SuccessFactors / Jobs2Web (HTML) | `GET https://jobs.adidas-group.com/search/?q=&optionsFacetsDD_country=IN&startrow=N` | `optionsFacetsDD_country=IN` | 7 | ✅ CRACKED 2026-05-13 — SAP Jobs2Web HTML at jobs.adidas-group.com; 7 India jobs; routed to `ats=sap_jobs2web_html` |
| LTIMindtree | https://careers.ltimindtree.com/search/?createNewAlert=false&q=&locationsearch=india | SAP Jobs2Web HTML | India-filtered URL returns ~2 India jobs; parse direct table cards and detail pages | ✅ CRACKED 2026-05-08 — routed to `ats=sap_jobs2web_html`; no Firecrawl needed |
| Genpact | https://careers.genpact.com | Custom | `https://careers.genpact.com` — Genpact custom career portal; SmartRecruiters 0 results; Workday 422 | 🟡 js-required — custom ATS; FC scrape of open-positions page; probed 2026-04-19 |
| Amdocs | https://www.amdocs.com/about/careers | Workday (suspected) | `https://amdocs.wd3.myworkdayjobs.com` — Workday CXS 422 blocked; SmartRecruiters 0 results | 🟡 Workday tenant `amdocs.wd3` confirmed but CXS blocked and career_site slug TBD; FC fallback; probed 2026-04-19 |
| Zoho | https://careers.zohocorp.com/jobs/careers | Zoho Recruit (self-hosted) | `https://careers.zohocorp.com/jobs/careers` — Zoho uses own Zoho Recruit product; Chennai HQ | ⬇️ deprioritized — only 2 India jobs visible 2026-04-30 |
| Tata Elxsi | https://www.tataelxsi.com/careers/job-openings | Tata Elxsi HTML | Server-rendered listing cards at `/careers/job-openings?page=N`; full JD/apply URL on detail pages | ✅ CRACKED 2026-05-08 — routed to `ats=tata_elxsi`; live direct probe returned India jobs with JDs; no Firecrawl needed |
| Virtusa | https://www.virtusa.com/careers | Custom | `https://www.virtusa.com/careers` — custom portal; IT services; India offices in Chennai/Bengaluru/Hyderabad | 🟡 js-required — custom ATS; FC scrape; probed 2026-04-19 |
| Mu Sigma | https://www.mu-sigma.com/careers | Custom | `https://www.mu-sigma.com/careers` — Mu Sigma custom portal; analytics firm; Bengaluru HQ; India-only | 🟡 js-required — custom ATS; FC scrape; probed 2026-04-19 |
| InMobi | https://www.inmobi.com/company/careers/ | Custom/Greenhouse (TBD) | `https://www.inmobi.com/company/careers/` — InMobi custom portal or Greenhouse; Bengaluru HQ; probe XHR | 🟡 js-required — ATS unconfirmed; check `boards.greenhouse.io/inmobi`; FC scrape fallback; probed 2026-04-19 |
| Ola Electric | https://www.olaelectric.com/careers | Custom | `https://www.olaelectric.com/careers` — Ola Electric custom portal; EV company; Bengaluru HQ; India-only | 🟡 js-required — custom ATS; FC scrape; probed 2026-04-19 |
| Telefonica | https://www.telefonica.com/en/careers/ | Custom/SAP SF | Europe/LatAm focused — India presence minimal; no confirmed India GCC | ⚠️ India presence unclear — Telefónica Tech has some India ops; verify India jobs before adding; probed 2026-04-19 |
| Credit Suisse | — | MERGED → UBS | Acquired by UBS (March 2023); no standalone portal | 🔴 Merged into UBS — use UBS entry; careers.credit-suisse.com redirects to UBS; skip |

---

## CONSULTING COMPANIES
*ATS varies — most route through Firecrawl extract until direct API is confirmed.*

| Company | Careers URL | ATS | Status |
|---------|-------------|-----|--------|
| Bain & Company | https://careers.bain.com/jobs/SearchJobs/india/?folderRecordsPerPage=10&folderOffset=0 | ExternalJobs (SilkRoad) | ✅ CRACKED 2026-05-13 — 96 India jobs; listing JS-rendered (FC required); JD at `/jobs/FolderDetail/{slug}/{id}` via FC scrape; paginate via folderOffset=0,10,20...; NOT Workday |
| Nestlé | https://www.nestle.in/jobs/search-jobs | SAP SuccessFactors / Jobs2Web (HTML) | ✅ CRACKED 2026-05-13 — SAP Jobs2Web HTML at `jobdetails.nestle.com`; `locationsearch=india` filter; 31 India jobs across 4 pages (10/page, startrow=0/10/20/30); job detail at `/job/{city-slug}/{id}/` via direct HTTP; JD in `data-careersite-propertyid="description"`; apply URL `/talentcommunity/apply/{id}/?locale=en_US`; routed to `ats=sap_jobs2web_html`; endpoint override in `portal_reader.py:_SAP_ENDPOINT_OVERRIDES` |
| BDO India | https://www.bdo.in/en-gb/careers/new-job-openings | Custom CMS (React SSR) | ✅ CRACKED 2026-05-13 — 100+ India jobs; all on bdo.in (India-only portal, no country filter needed); detail pages at `/en-gb/careers/new-job-openings/{slug}` are HTML-scrapable; listing JS-rendered (use FC map or sitemap to enumerate slugs); JD in `<p>` tags |
| BCG | https://careers.bcg.com/global/en/search-results?keywords=india | Phenom SSR | moved to PHENOM section — direct `phenom_ssr` route parses embedded listings and detail JDs; no Firecrawl needed |
| EY Parthenon | https://www.ey.com/en_in/careers/parthenon | SmartRecruiters (unconfirmed) | 🟡 js-required |
| Kearney | https://www.kearney.com/about/locations/india/careers/india-people-careers | Custom | 🟡 js-required |
| L.E.K. Consulting | https://www.lek.com/careers | Custom | 🟡 js-required |
| Deloitte India (BrassRing) | https://usijobs.deloitte.com/en_US/careersUSI/SearchJobs?jobRecordsPerPage=10&jobOffset=0 | Avature SearchJobs HTML (USI) | ✅ CRACKED 2026-05-03 — direct paginated HTML listings (`SearchJobs?jobOffset=N`) + detail pages (`/JobDetail/.../{id}`) with JSON-LD JD (`JobPosting.description`) and apply URL (`/Login?jobId={id}`); routed to `ats=deloitte_usi` |
| Oliver Wyman | https://mmc.phenompeople.com/global/en/oliver-wyman-search | Phenom (mmc.phenompeople.com) | ✅ working via Firecrawl — 5 jobs via FC scrape on mmc.phenompeople.com; verified 2026-04-17 |
| Practus | https://roibypractus.com/people-careers/ | Custom | ⬇️ low-priority — small boutique consulting firm; likely genuine low job count; deprioritised 2026-04-19 |
| Praxis Global Alliance | https://www.praxisga.com/career | Custom | ⬇️ low-priority — small boutique firm; deprioritised 2026-04-19 |
| PwC India | https://www.pwc.in/careers/experienced-jobs.html | Workday (pwc.wd3 / Global_Experienced_Careers) | ✅ CRACKED 2026-05-13 — searchText="india" mode; 221 India jobs; override in workday_registry.json as "PwC India"; JD at `pwc.wd3.myworkdayjobs.com`; ats=workday |
| Simon-Kucher & Partners | https://www.simon-kucher.com/en/careers | Custom | 🟡 js-required |
| Strategy& (PwC) | https://www.strategyand.pwc.com/gx/en/careers.html | Custom | 🟡 js-required |
| Takshashila Consulting | https://tkc.firm.in/career.html | Custom | 🟡 js-required |
| TransformationX | https://transformationx.com/join-us/ | Custom | ⬇️ low-priority — small boutique firm; deprioritised 2026-04-19 |
| Vector Consulting Group | https://www.vectorconsulting.in/careers/career-listings/ | Vector Next.js SSR | ✅ CRACKED 2026-05-08 — embedded `__NEXT_DATA__.props.pageProps.jobsData.dataset`; 2 India roles with full JD sections; routed to `ats=vector_consulting`; no Firecrawl needed |
| Black Brix | https://blackbrix.com/job-openings/ | WordPress Job Openings HTML | ✅ CRACKED 2026-05-13 — direct server-rendered listing cards + detail page JD/apply form; targeted run saved 1 Kolkata role with 2.4k-char JD; routed to `ats=blackbrix_jobs` |

---

## BFSI — INVESTMENT BANKING & ASSET MANAGEMENT

| Company | Careers URL | ATS | Notes | Status |
|---------|-------------|-----|-------|--------|
| ARGA Investment Management | https://www.argainvest.com | None (email: resumes@argainvest.com) | No public portal | 🔒 email-only |
| Arpwood Capital | https://www.arpwood.com/careers | Custom | Small boutique IB | ⬇️ low-priority — small firm, genuine low job count; deprioritised 2026-04-19 |
| Avendus Capital | https://www.avendus.com/careers/apply-now | Custom | India-based IB | 🟡 js-required |
| Claypond Capital | — | None (LinkedIn / email) | Manipal Group family office | 🔒 no public portal |
| Everstone Capital | — | None (LinkedIn) | PE firm — no dedicated portal | 🔒 no public portal |
| HSBC | https://hsbc.eightfold.ai/careers?location=India&hl=en | Eightfold | direct API works with domain=hsbc.com; see EIGHTFOLD section | ✅ CRACKED 2026-05-13 — 250 India jobs; ats=eightfold |
| O3 Capital | http://www.o3capital.com | None (email: careers@o3capital.com) | Boutique IB | 🔒 email-only |
| Premji Invest | https://in.premjiinvest.com | Custom | Family office / PE | 🟡 js-required |
| Standard Chartered Bank | https://jobs.standardchartered.com/services/recruiting/v1/jobs | Taleo v1 | 530 India jobs; POST + keywords=india; no auth | ✅ CRACKED 2026-04-30 — ats=taleo taleo_v1=True; per-job JD via /job/{urltitle}/{id}/; totalJobs=530 |
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
| IndusInd Bank | https://www.indusind.bank.in | Custom | Private sector bank | 🟡 js-required |
| L&T Finance | https://www.ltfs.com/careers.html | Custom | NBFC | ⬇️ low-priority — small NBFC, limited tech roles; deprioritised 2026-04-19 |
| Navi Technologies | https://navi.com/careers/jobs | Custom | Fintech NBFC | 🟡 js-required — direct jobs page confirmed via Firecrawl discovery 2026-04-16 |
| FinIQ | https://www.finiq.com/JobsPage/jobs.html | Custom HTML | Fintech SaaS | ✅ working — direct HTML page |

---

## CONGLOMERATES

| Company | Careers URL | ATS | Notes | Status |
|---------|-------------|-----|-------|--------|
| Aditya Birla Group | https://careers.adityabirla.com/job-search | Custom (aditya_birla) | India-only; 793 jobs; static Bearer token; per-job JD fetch /api/v3/job/{jobCode} | ✅ CRACKED 2026-04-30 — ats=aditya_birla; Bearer token static (no auth flow); pagination via offset |
| CK Birla Group | https://www.ckabirlagroup.com/workingwithus | Custom | Mid-size Indian conglomerate | 🟡 js-required |
| Lodha Ventures | https://www.instahyre.com/jobs-at-lodha-ventures/ | Instahyre | Lodha family ventures arm | 🟡 js-required |
| Tata Administrative Services | https://www.tata.com/careers/programs/tas | Custom | Tata Group management programme | 🟡 js-required |
| ITC Limited | https://recruitment.itcportal.com/jobs/Careers | Zoho Recruit (SSR HTML) | `page_id=48611000000181149`; 62 India jobs embedded in SSR HTML as entity-encoded JSON array; fields: Posting_Title, Job_Description, City, State, Country, id; apply URL /recruit/SingleJobDetail.na?sys_id={id}&page_id=48611000000181149 | ✅ CRACKED 2026-05-13 — routed to ats=zoho_recruit; provider at providers/zoho_recruit.py |

---

## CONSUMER GOODS (FMCG)


| Company | Careers URL | ATS | Notes | Status |
|---------|-------------|-----|-------|--------|
| Coromandel International | https://www.coromandel.biz/careers/ | Custom | Agri-inputs; part of Murugappa Group | 🟡 js-required |
| Godrej Consumer Products | https://careers.godrejindustries.com/in/en/search-results?qcountry=India | Phenom SSR | `careers.godrejcp.com` DNS-dead (2026-05-13); real portal: `careers.godrejindustries.com`; FC scrape returns India jobs (34 GCPL jobs seen); `utm_medium=phenom-feeds`; apply URL `/in/en/job/{id}/`; probe PCSX: `domain=godrejindustries.com` | 🟡 Phenom — needs PCSX or Phenom SSR probe to confirm listing API |
| United Breweries | https://careers.theheinekencompany.com/India/ | Workday (Heineken) | Part of Heineken Group | ⬇️ low-priority — FMCG, low tech hiring; check if tenant=heineken wd3 if re-activating; deprioritised 2026-04-19 |
| Wipro Consumer Care | https://wiproconsumercare.com/campus/ | Custom | Separate from Wipro IT — consumer FMCG division | ⬇️ low-priority — consumer goods arm, not tech; deprioritised 2026-04-19 |
| Unilever | https://careers.unilever.com/en/location/india-jobs/34155/1269750/2 | TalentBrew (TMP/Radancy) | company_id=34155; 2 India pages (path-paged /2 then /3); listing JS-rendered (FC fallback needed); job detail `/en/job/{city}/{slug}/34155/{job_id}` direct HTTP with JSON-LD JD | ✅ CRACKED 2026-05-13 — routed to ats=talentbrew; endpoint override in portal_reader.py |

---

## CONSUMER SERVICES & E-COMMERCE

| Company | Careers URL | ATS | Notes | Status |
|---------|-------------|-----|-------|--------|
| Nykaa | https://careers.nykaa.com | Skima Careers (SSR HTML) | Direct HTML listing + `?page=N` pagination + per-job UUID detail page with full JD panel | ✅ CRACKED 2026-05-02 — no auth/cookies required; 11 India jobs observed; routed to `ats=skima_careers` |

---

## INFORMATION TECHNOLOGY (IT) — NEW ADDITIONS

*Note: Wipro, TCS, Infosys, Cognizant, HCL Technologies are in existing sections.*

| Company | Careers URL | ATS | Notes | Status |
|---------|-------------|-----|-------|--------|
| HCL Software | https://www.hcl-software.com/careers | Custom | HCL Group software division | 🟡 js-required |
| HiLabs | https://www.hilabs.com/careers/all-open-positions?location=india | Next.js SSR payload | Health-tech AI | ✅ CRACKED 2026-05-13 — jobs embedded in `self.__next_f.push` under `groupedByPlaceAndDepartments.india["All Job Listing"]`; targeted run saved 3 India jobs with 2.8k-3.3k-char JDs; routed to `ats=hilabs_careers` |
| Sanas | https://www.sanas.ai/careers | Custom | AI / speech-tech | 🟡 js-required |
| Vehere Interactive | https://vehere.com/company/careers/ | Custom | Cybersecurity | 🟡 js-required |

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
