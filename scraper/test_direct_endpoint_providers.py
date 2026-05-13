from __future__ import annotations

import json
import re

import providers.generic_json as generic_json
from providers.apple_jobs import parse_apple_search_result
from providers.cognizant_xml import parse_cognizant_xml
from providers.deshaw_india import parse_deshaw_next_data
from providers.google_careers import parse_google_careers_html
from providers.hilabs_careers import parse_hilabs_html
from providers.intouchcx import (
    parse_dayforce_next_data,
    parse_intouchcx_feed,
    parse_legacy_intouchcx_detail,
)
from providers.blackbrix_jobs import (
    parse_blackbrix_detail,
    parse_blackbrix_listing_items,
)
from providers.microsoft_careers import (
    parse_microsoft_detail_payload,
    parse_microsoft_search_payload,
)
from providers.tata_elxsi import extract_tata_elxsi_detail, extract_tata_elxsi_listing_items
from providers.talentbrew import _extract_listing_items, _page_url
from providers.vector_consulting import parse_vector_next_data


def check(label: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"PASS {label}")


class _FakeJSONResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.headers = {"Content-Type": "application/json"}
        self.text = json.dumps(payload)

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_radancy_listing_links_parse() -> None:
    html = """
    <li class="sr-job-item">
      <h3 class="sr-job-item__title">
        <a class="sr-job-item__link" href="/job/mumbai/head-of-equites-india-onshore-team/287/94768478096" data-job-id="94768478096">
          Head Of Equites India Onshore Team
        </a>
      </h3>
      <span class="sr-job-item__facet sr-job-location">Mumbai, Maharashtra, India</span>
    </li>
    <li>
      <a class="search-results-link" href="/job/mumbai/head-distribution-and-retail/7684/94758247168" data-job-id="94758247168">
        <div><h2>Head Distribution and Retail</h2><span class="job-location">Mumbai, Maharashtra, India</span></div>
      </a>
    </li>
    """
    items = _extract_listing_items(html)
    check("radancy item count", len(items) == 2)
    check("citi title parsed", items[0]["title"] == "Head Of Equites India Onshore Team")
    check("astrazeneca title parsed", items[1]["title"] == "Head Distribution and Retail")
    check("location parsed", items[1]["listing_loc"] == "Mumbai, Maharashtra, India")


def test_search_jobs_pagination_uses_p_param() -> None:
    url = _page_url("https://jobs.citi.com/search-jobs/India", 2)
    check("search-jobs page param", url == "https://jobs.citi.com/search-jobs/India?p=2")


def test_cognizant_xml_parser_filters_india() -> None:
    xml = """<?xml version="1.0"?>
    <source>
      <job>
        <title><![CDATA[India Engineer]]></title>
        <requisitionid><![CDATA[0001]]></requisitionid>
        <url><![CDATA[https://careers.cognizant.com/india-en/jobs/0001/india-engineer/]]></url>
        <city><![CDATA[BANGALORE]]></city>
        <state><![CDATA[Karnataka]]></state>
        <country><![CDATA[India]]></country>
        <description><![CDATA[<p>Build platforms.</p>]]></description>
        <category><![CDATA[Technology]]></category>
        <date><![CDATA[Fri, 08 May 2026 09:26:46 GMT]]></date>
      </job>
      <job>
        <title><![CDATA[US Engineer]]></title>
        <requisitionid><![CDATA[0002]]></requisitionid>
        <url><![CDATA[https://careers.cognizant.com/us/jobs/0002/us-engineer/]]></url>
        <city><![CDATA[Orlando]]></city>
        <state><![CDATA[Florida]]></state>
        <country><![CDATA[United States]]></country>
        <description><![CDATA[<p>Build platforms.</p>]]></description>
      </job>
    </source>
    """
    jobs = parse_cognizant_xml(xml, {"company": "Cognizant", "industry": "IT Services", "india_only": True})
    check("only india job parsed", len(jobs) == 1)
    check("cognizant title", jobs[0]["title"] == "India Engineer")
    check("cognizant jd stripped", jobs[0]["raw_jd_text"] == "Build platforms.")


def test_apple_search_result_maps_india_job() -> None:
    item = {
        "positionId": "200314033",
        "postingTitle": "IN-Operations Expert",
        "jobSummary": "Retail operations role.",
        "postingDate": "08 May 2026",
        "team": "Apple Retail",
        "locations": [{
            "name": "India",
            "countryName": "India",
            "countryID": "iso-country-IND",
        }],
    }
    job = parse_apple_search_result(item, {"endpoint": "https://jobs.apple.com/api/v1/search", "industry": "Technology"})
    check("apple job parsed", job is not None)
    check("apple title", job["title"] == "IN-Operations Expert")
    check("apple location", "India" in job["location_city"])


def test_tata_elxsi_listing_cards_parse() -> None:
    html = """
    <div id="job_listing">
      <div class="jjbcdeo1 botm1">
        <div class="jjbcdeo11">
          <h5>RFH/06328</h5>
          <h3>RDK-B Developer</h3>
          <p>Bangalore/Chennai | 5 - 10 years | B.E, B.Tech | RDK-B-Developer</p>
        </div>
        <div class="jjbcdeo12">
          <p>07 May 2026</p>
          <a href="https://www.tataelxsi.com/careers/job-openings/rdk-b-developer-2" class="jknmre">Know More</a>
        </div>
      </div>
      <div class="jjbcdeo1 botm1">
        <div class="jjbcdeo11">
          <h5>Functional Safety Engineer</h5>
          <h3>Functional Safety Engineer</h3>
          <p>London / Coventry | 3 - 5 years | Bachelors / Masters | Functional Safety Engineer</p>
        </div>
        <div class="jjbcdeo12">
          <p>04 May 2026</p>
          <a href="/careers/job-openings/functional-safety-engineer" class="jknmre">Know More</a>
        </div>
      </div>
    </div>
    """
    items = extract_tata_elxsi_listing_items(html, "https://www.tataelxsi.com/careers/job-openings")
    check("tata listing count", len(items) == 2)
    check("tata title parsed", items[0]["title"] == "RDK-B Developer")
    check("tata job code parsed", items[0]["job_code"] == "RFH/06328")
    check("tata location parsed", items[0]["location"] == "Bangalore/Chennai")
    check("tata non-india retained for caller filter", items[1]["location"] == "London / Coventry")


def test_tata_elxsi_detail_extracts_jd_and_apply_url() -> None:
    html = """
    <section id="japlicatn">
      <div class="jbpam botm1">
        <h2>RDK-B Developer</h2>
        <div class="aplynw">
          <a href="https://tataelxsi.ramcoes.com/rvw/PortalBroadBeanCalling.aspx?rfhno=15~RFH/06328" class="japlynw">Apply Now</a>
        </div>
      </div>
      <div class="jbpam1">
        <p>Tata Elxsi offers comprehensive services in Media and Communications.</p>
        <p><strong>Job Description:</strong></p>
        <ul>
          <li>5+ years of experience in embedded software development.</li>
          <li>Strong programming skills in C/C++.</li>
        </ul>
      </div>
    </section>
    """
    detail = extract_tata_elxsi_detail(html, "https://www.tataelxsi.com/careers/job-openings/rdk-b-developer-2")
    check("tata detail title", detail["title"] == "RDK-B Developer")
    check("tata detail apply url", detail["apply_url"].startswith("https://tataelxsi.ramcoes.com/"))
    check("tata detail jd", "embedded software development" in detail["raw_jd_text"])


def test_vector_next_data_parser_maps_jobs_and_body_sections() -> None:
    html = """
    <script id="__NEXT_DATA__" type="application/json">
    {
      "props": {
        "pageProps": {
          "jobsData": {
            "dataset": [
              {
                "id": 39,
                "job_title": "Project Management Consultant",
                "slug": "project-management-consultant",
                "job_role": "Project Management Consultant",
                "location": "India",
                "employment_type": "Full time employment",
                "years_of_experience": "5-7 years",
                "description": "<p>Vector Consulting Group overview.</p>",
                "body": "[{\\"title\\":\\"Role & Responsibilities:\\",\\"content\\":\\"<ul><li>Lead consulting workstreams.</li></ul>\\"}]"
              },
              {
                "id": 40,
                "job_title": "Indonesia Consultant",
                "slug": "indonesia-consultant",
                "location": "Indonesia",
                "description": "<p>Non-India role.</p>",
                "body": []
              }
            ]
          }
        }
      }
    }
    </script>
    """
    jobs = parse_vector_next_data(
        html,
        {"company": "Vector Consulting Group", "industry": "Consulting", "india_only": True},
        "https://www.vectorconsulting.in/careers/career-listings/",
    )
    check("vector filters india", len(jobs) == 1)
    check("vector title", jobs[0]["title"] == "Project Management Consultant")
    check("vector body jd", "Lead consulting workstreams" in jobs[0]["raw_jd_text"])
    check("vector job url", jobs[0]["job_url"].endswith("/careers/career-listings/project-management-consultant"))


def test_oracle_nested_scraper_paginates_offsets() -> None:
    calls: list[str] = []
    original_get = generic_json.requests.get

    def fake_get(url: str, headers=None, timeout=None):
        calls.append(url)
        limit = int(re.search(r'limit=(\d+)', url).group(1))
        offset = int(re.search(r'offset=(\d+)', url).group(1))
        total = 140
        page = []
        for idx in range(offset, min(offset + limit, total)):
            page.append({
                "Id": 26000000 + idx,
                "Title": f"Oracle Job {idx}",
                "PrimaryLocation": "Bengaluru, KA, India",
                "ExternalDescriptionStr": f"<p>Role {idx}</p>",
            })
        return _FakeJSONResponse({"items": [{"TotalJobsCount": total, "requisitionList": page}]})

    generic_json.requests.get = fake_get
    try:
        portal = {
            "company": "American Express",
            "ats": "oracle",
            "oracle_nested": True,
            "india_only": True,
            "industry": "Financial Services",
            "endpoint": (
                "https://egug.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/"
                "recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.workLocation,"
                "requisitionList.otherWorkLocations,requisitionList.secondaryLocations,"
                "flexFieldsFacet.values,requisitionList.requisitionFlexFields&finder=findReqs;"
                "siteNumber=CX_1,facetsList=LOCATIONS%3BWORK_LOCATIONS%3BWORKPLACE_TYPES%3BTITLES%3B"
                "CATEGORIES%3BORGANIZATIONS%3BPOSTING_DATES%3BFLEX_FIELDS,limit=25,"
                "locationId=300000000228786,sortBy=POSTING_DATES_DESC"
            ),
        }
        jobs = generic_json.scrape_get(portal, max_jobs=140)
        check("oracle pagination job count", len(jobs) == 140)
        check("oracle pagination second page fetched", len(calls) == 2 and "offset=100" in calls[1])
        check("oracle pagination jd parsed", jobs[0]["raw_jd_text"] == "Role 0")
    finally:
        generic_json.requests.get = original_get


def test_deshaw_next_data_parser_maps_public_regular_jobs() -> None:
    html = """
    <script id="__NEXT_DATA__" type="application/json">
    {
      "props": {
        "pageProps": {
          "regularJobs": [
            {
              "data": {
                "id": 6760,
                "displayName": "Core Tech/Principal Manager, Tech (Treasury Tech)",
                "isActive": true,
                "jobUrl": "Core-Tech-Principal-Manager-Tech-Treasury-Tech-6760",
                "jobHeaders": ["INFORMATION TECHNOLOGY"],
                "department": {"name": "Core Tech"},
                "jobMetadata": {
                  "activeOnWebsite": true,
                  "jobLocations": [{"name": "Bengaluru"}]
                },
                "jobDescription": {
                  "websiteDescription": "We are looking for an exceptional Principal Manager.",
                  "peopleWeAreLookingFor": ["Must have proficiency in Python."],
                  "peopleWeAreLookingForHtml": "<ul><li>8 to 12 years of Software Engineering experience.</li></ul>"
                }
              }
            },
            {
              "data": {
                "id": 10,
                "displayName": "US Role",
                "isActive": true,
                "jobUrl": "US-Role-10",
                "jobMetadata": {
                  "activeOnWebsite": true,
                  "jobLocations": [{"name": "New York"}]
                },
                "jobDescription": {"websiteDescription": "US role."}
              }
            }
          ]
        }
      }
    }
    </script>
    """
    jobs = parse_deshaw_next_data(
        html,
        {"company": "DE Shaw", "industry": "BFSI", "india_only": True},
        "https://www.deshawindia.com/careers",
    )
    check("deshaw filters india", len(jobs) == 1)
    check("deshaw title", jobs[0]["title"] == "Core Tech/Principal Manager, Tech (Treasury Tech)")
    check("deshaw jd sections", "Software Engineering experience" in jobs[0]["raw_jd_text"])
    check("deshaw list jd sections", "proficiency in Python" in jobs[0]["raw_jd_text"])
    check("deshaw apply url", jobs[0]["job_url"].endswith("/recruit/jobs/Ads/Link/Core-Tech-Principal-Manager-Tech-Treasury-Tech-6760"))


def test_intouchcx_feed_filters_india_and_maps_ids() -> None:
    payload = {
        "jobs": [
            {
                "job": "Customer Service Representative",
                "link": "https://apply.intouchcx.com/3",
                "location": "Mesa, Arizona, United States",
            },
            {
                "job": "Customer Service Associate Voice",
                "link": "https://apply.intouchcx.com/153",
                "location": "Bengaluru, India",
            },
            {
                "job": "Full Stack Developer ",
                "link": "https://jobs.dayforcehcm.com/en-CA/intouchcx/CANDIDATEPORTAL/jobs/10082",
                "location": "Hyderabad, India",
            },
        ]
    }
    jobs = parse_intouchcx_feed(
        payload,
        {
            "company": "IntouchCX",
            "endpoint": "https://www.intouchcx.com/wp-json/intouchcx/v1/jobs?country=India",
            "industry": "Customer Experience",
            "india_only": True,
        },
    )
    check("intouchcx india count", len(jobs) == 2)
    check("intouchcx legacy id", jobs[0]["job_id"] == "intouchcx-apply-153")
    check("intouchcx dayforce id", jobs[1]["job_id"] == "intouchcx-dayforce-10082")
    check("intouchcx title stripped", jobs[1]["title"] == "Full Stack Developer")
    check("intouchcx source platform", jobs[1]["source_platform"] == "IntouchCX")


def test_intouchcx_legacy_detail_extracts_application_body() -> None:
    html = """
    <div class="application-body in" style="font-family: Poppins;">
      <p><strong>About the Job</strong></p>
      <p>We are looking for a customer support associate.</p>
      <ul><li>Handle customer calls end to end.</li></ul>
    </div>
    <div class="application-buttons text-center"></div>
    """
    text = parse_legacy_intouchcx_detail(html)
    check("intouchcx legacy jd text", "customer support associate" in text)
    check("intouchcx legacy jd list text", "Handle customer calls" in text)


def test_intouchcx_dayforce_next_data_extracts_detail() -> None:
    html = """
    <script id="__NEXT_DATA__" type="application/json">
    {
      "props": {
        "pageProps": {
          "jobData": {
            "jobPostingId": 10082,
            "jobTitle": "Full Stack Developer ",
            "postingStartTimestampUTC": "2025-05-28T08:00:00+00:00",
            "jobPostingContent": {
              "jobDescriptionHeader": "<p><strong>About IntouchCX</strong></p>",
              "jobDescription": "<p>We are seeking a Full Stack Developer.</p><ul><li>Must have Angular experience.</li></ul>",
              "jobDescriptionFooter": null
            },
            "postingLocations": [
              {
                "formattedAddress": "Hyderabad, Telangana, India",
                "cityName": "Hyderabad",
                "isoCountryCode": "IN"
              }
            ],
            "jobPostingAttributes": [
              {"name": "PayType", "value": "Salary"}
            ]
          }
        }
      }
    }
    </script>
    """
    detail = parse_dayforce_next_data(html)
    check("intouchcx dayforce title", detail["title"] == "Full Stack Developer")
    check("intouchcx dayforce jd", "Angular experience" in detail["raw_jd_text"])
    check("intouchcx dayforce location", detail["location_city"] == "Hyderabad, Telangana, India")
    check("intouchcx dayforce date", detail["date_posted"] == "2025-05-28T08:00:00+00:00")


def test_google_careers_html_parser_maps_embedded_jobs() -> None:
    html = r'''
    <script>
    AF_initDataCallback({key: 'ds:1', hash: '2', data:[[[
      ["107743710602502854","Senior Security Architect, Mandiant, Google Cloud (English)",
       "https://www.google.com/about/careers/applications/signin?jobId=abc&loc=IN&title=Senior+Security+Architect",
       [null,"<ul><li>Identify solution issue trends.</li></ul>"],
       [null,"<h3>Minimum qualifications:</h3><ul><li>Bachelor's degree.</li></ul>"],
       "projects/gweb-careers-proto/tenants/60107626/companies/google",null,"Google","en-US",
       [["India",["India"],null,null,null,"IN"]],
       [null,"<p>Work on client security engagements.</p>"],
       [2],[1778142684,3000000],[1778142684,3000000],[1778142684,224000000],
       [null,""],1,null,[null,"<b>Remote location: India.</b>"],
       [null,"<ul><li>Bachelor's degree.</li></ul>"],2],
      ["999","US Role","https://www.google.com/about/careers/applications/signin?jobId=us",
       [null,"<ul><li>US responsibility.</li></ul>"],[null,"<ul><li>US qualification.</li></ul>"],
       "",null,"Google","en-US",[["New York, NY, USA",["New York"],"New York",null,"NY","US"]],
       [null,"<p>US overview.</p>"],[2],[1778142684,0],[1778142684,0],[1778142684,0],
       [null,""],1,null,[null,""],[null,""],2]
    ]]], sideChannel: {}});
    </script>
    '''
    jobs = parse_google_careers_html(
        html,
        {
            "company": "Google",
            "endpoint": "https://www.google.com/about/careers/applications/jobs/results/?location=India",
            "industry": "Technology",
            "india_only": True,
        },
    )
    check("google parser filters india", len(jobs) == 1)
    check("google native id", jobs[0]["job_id"] == "107743710602502854")
    check("google title", jobs[0]["title"] == "Senior Security Architect, Mandiant, Google Cloud (English)")
    check("google location", jobs[0]["location_city"] == "India")
    check("google jd overview", "Work on client security engagements" in jobs[0]["raw_jd_text"])
    check("google jd responsibilities", "Identify solution issue trends" in jobs[0]["raw_jd_text"])
    check("google date", jobs[0]["date_posted"] == "2026-05-07")


def test_microsoft_pcsx_search_parser_maps_india_positions() -> None:
    payload = {
        "status": 200,
        "data": {
            "count": 2,
            "positions": [
                {
                    "id": 1970393556856063,
                    "displayJobId": "200033959",
                    "atsJobId": "200033959",
                    "name": "Senior Software Engineer",
                    "locations": ["India, Multiple Locations, Multiple Locations"],
                    "postedTs": 1776326224,
                    "department": "Software Engineering",
                    "positionUrl": "/careers/job/1970393556856063",
                },
                {
                    "id": 1970393556000000,
                    "displayJobId": "200000001",
                    "name": "US Engineer",
                    "locations": ["Redmond, Washington, United States"],
                    "positionUrl": "/careers/job/1970393556000000",
                },
            ],
        },
    }
    jobs = parse_microsoft_search_payload(
        payload,
        {
            "company": "Microsoft",
            "endpoint": "https://apply.careers.microsoft.com/api/pcsx/search?domain=microsoft.com&location=India",
            "industry": "Technology",
            "india_only": True,
        },
    )
    check("microsoft parser filters india", len(jobs) == 1)
    check("microsoft search native id", jobs[0]["job_id"] == "microsoft-200033959")
    check("microsoft search title", jobs[0]["title"] == "Senior Software Engineer")
    check("microsoft search location", jobs[0]["location_city"] == "India, Multiple Locations, Multiple Locations")
    check("microsoft search date", jobs[0]["date_posted"] == "2026-04-16")
    check("microsoft search url", jobs[0]["job_url"].endswith("/careers/job/1970393556856063?hl=en"))


def test_microsoft_detail_parser_maps_full_jd() -> None:
    payload = {
        "id": 1970393556864810,
        "name": "Site Reliability Engineer 2",
        "posting_name": "Site Reliability Engineer 2",
        "location": "India, Telangana, Hyderabad",
        "locations": ["India, Telangana, Hyderabad"],
        "department": "Service Engineering",
        "business_unit": "Cloud + AI",
        "t_update": 1778477142,
        "ats_job_id": "200037078",
        "display_job_id": "200037078",
        "job_description": "<b>Overview</b><br><p>Build reliable cloud services.</p>",
    }
    detail = parse_microsoft_detail_payload(payload)
    check("microsoft detail id", detail["job_id"] == "microsoft-200037078")
    check("microsoft detail title", detail["title"] == "Site Reliability Engineer 2")
    check("microsoft detail jd", "Build reliable cloud services" in detail["raw_jd_text"])
    check("microsoft detail location", detail["location_city"] == "India, Telangana, Hyderabad")
    check("microsoft detail business unit", detail["business_unit"] == "Cloud + AI")
    check("microsoft detail date", detail["date_posted"] == "2026-05-11")


def test_hilabs_html_parser_maps_india_jobs() -> None:
    html = r'''
    <script>
    self.__next_f.push([1,"24:[\"$\",\"$f\",null,{\"fallback\":[\"$\",\"div\",null,{}],\"children\":[\"$\",\"$L25\",null,{\"countByDepartmentAndCountry\":{\"india\":{\"All Job Listing\":1},\"usa\":{\"All Job Listing\":1}},\"groupedByPlaceAndDepartments\":{\"india\":{\"All Job Listing\":[{\"id\":27,\"documentId\":\"n1q35av2zmlmrfzi8mfowhmg\",\"Add_description_to_Hilabs_Team\":\"We are seeking a Lead Data Scientist.\",\"Job_Id\":null,\"Job_Title\":\"Lead Data Scientist\",\"Category\":\"Data Science\",\"Job_Location\":\"Pune, Maharashtra, India\",\"createdAt\":\"2025-08-26T11:56:09.834Z\",\"updatedAt\":\"2025-08-26T11:56:16.565Z\",\"publishedAt\":\"2025-08-26T11:56:16.594Z\",\"Job_Description\":[{\"id\":53,\"Heading\":\"Responsibilities\",\"Add_bullet_points_with_heading\":[{\"id\":55,\"Heading\":null,\"Points\":[{\"id\":557,\"Point\":\"Build machine learning algorithms.\"},{\"id\":558,\"Point\":\"Deploy big data workflows.\"}]}]},{\"id\":54,\"Heading\":\"Desired Profile\",\"Add_bullet_points_with_heading\":[{\"id\":56,\"Heading\":null,\"Points\":[{\"id\":568,\"Point\":\"Strong Python skills.\"}]}]}],\"Screening_Questions\":[]}]} ,\"usa\":{\"All Job Listing\":[{\"id\":1,\"documentId\":\"us-role\",\"Add_description_to_Hilabs_Team\":\"US only role\",\"Job_Title\":\"US Data Scientist\",\"Category\":\"Data Science\",\"Job_Location\":\"Austin, Texas, United States\",\"updatedAt\":\"2025-08-27T00:00:00.000Z\",\"Job_Description\":[]}]}},\"tagItems\":{\"india\":[{\"title\":\"All Job Listing\"}],\"usa\":[{\"title\":\"All Job Listing\"}]}}]}]"])\n
    </script>
    '''
    jobs = parse_hilabs_html(
        html,
        {
            "company": "HiLabs",
            "endpoint": "https://www.hilabs.com/careers/all-open-positions?location=india",
            "industry": "Healthcare Technology",
            "india_only": True,
        },
    )
    check("hilabs filters india", len(jobs) == 1)
    check("hilabs id", jobs[0]["job_id"] == "hilabs-n1q35av2zmlmrfzi8mfowhmg")
    check("hilabs title", jobs[0]["title"] == "Lead Data Scientist")
    check("hilabs location", jobs[0]["location_city"] == "Pune, Maharashtra, India")
    check("hilabs jd intro", "Lead Data Scientist" in jobs[0]["raw_jd_text"])
    check("hilabs jd bullet", "Build machine learning algorithms" in jobs[0]["raw_jd_text"])
    check("hilabs date", jobs[0]["date_posted"] == "2025-08-26")
    check("hilabs url", jobs[0]["job_url"].endswith("/careers/all-open-positions/Lead-Data-Scientist/n1q35av2zmlmrfzi8mfowhmg"))


def test_blackbrix_listing_and_detail_parsers() -> None:
    listing_html = """
    <div class="awsm-job-listings awsm-row awsm-grid-col-3" data-listings="18">
      <div class="awsm-job-listing-item awsm-grid-item" id="awsm-grid-item-12225">
        <a href="https://blackbrix.com/jobs/economist/" class="awsm-job-item">
          <div class="awsm-grid-left-col">
            <h2 class="awsm-job-post-title">Economist</h2>
          </div>
          <div class="awsm-grid-right-col">
            <div class="awsm-job-specification-wrapper">
              <div class="awsm-job-specification-item awsm-job-specification-job-location">
                <span class="awsm-job-specification-term">Kolkata West Bengal</span>
              </div>
            </div>
          </div>
        </a>
      </div>
    </div>
    """
    items = parse_blackbrix_listing_items(listing_html, "https://blackbrix.com/job-openings/")
    check("blackbrix listing count", len(items) == 1)
    check("blackbrix listing id", items[0]["job_id"] == "12225")
    check("blackbrix listing title", items[0]["title"] == "Economist")
    check("blackbrix listing location", items[0]["location_city"] == "Kolkata West Bengal")

    detail_html = """
    <body class="single single-awsm_job_openings postid-12225">
      <div class="awsm-job-content">
        <div class="awsm-job-entry-content entry-content">
          <p><strong>About Us</strong></p>
          <p>Black Brix is a management consultancy firm.</p>
          <p><strong>Base Location - Kolkata, West Bengal</strong></p>
          <p><strong>Responsibility.</strong><br>Conduct advanced economic analysis.<br>Translate complex findings into recommendations.</p>
          <p><strong>Desired Candidate Profile</strong><br>Master's degree in Economics.<br>Strong analytical skills.</p>
        </div>
      </div>
      <div class="awsm-job-specification-wrapper">
        <div class="awsm-job-specification-item awsm-job-specification-job-category">
          <span class="awsm-job-specification-term">Economist</span>
        </div>
        <div class="awsm-job-specification-item awsm-job-specification-job-type">
          <span class="awsm-job-specification-term">Full Time</span>
        </div>
        <div class="awsm-job-specification-item awsm-job-specification-job-location">
          <span class="awsm-job-specification-term">Kolkata West Bengal</span>
        </div>
      </div>
      <div class="awsm-job-form">
        <h2>Apply for this position</h2>
      </div>
    </body>
    """
    detail = parse_blackbrix_detail(detail_html, "https://blackbrix.com/jobs/economist/")
    check("blackbrix detail id", detail["job_id"] == "12225")
    check("blackbrix detail title", detail["title"] == "Economist")
    check("blackbrix detail location", detail["location_city"] == "Kolkata West Bengal")
    check("blackbrix detail jd", "advanced economic analysis" in detail["raw_jd_text"])
    check("blackbrix detail apply url", detail["job_url"] == "https://blackbrix.com/jobs/economist/")


def main() -> None:
    test_radancy_listing_links_parse()
    test_search_jobs_pagination_uses_p_param()
    test_cognizant_xml_parser_filters_india()
    test_apple_search_result_maps_india_job()
    test_tata_elxsi_listing_cards_parse()
    test_tata_elxsi_detail_extracts_jd_and_apply_url()
    test_vector_next_data_parser_maps_jobs_and_body_sections()
    test_deshaw_next_data_parser_maps_public_regular_jobs()
    test_intouchcx_feed_filters_india_and_maps_ids()
    test_intouchcx_legacy_detail_extracts_application_body()
    test_intouchcx_dayforce_next_data_extracts_detail()
    test_google_careers_html_parser_maps_embedded_jobs()
    test_microsoft_pcsx_search_parser_maps_india_positions()
    test_microsoft_detail_parser_maps_full_jd()
    test_hilabs_html_parser_maps_india_jobs()
    test_blackbrix_listing_and_detail_parsers()
    test_oracle_nested_scraper_paginates_offsets()
    print("All direct endpoint provider tests passed.")


if __name__ == "__main__":
    main()
