from __future__ import annotations

from providers.apple_jobs import parse_apple_search_result
from providers.cognizant_xml import parse_cognizant_xml
from providers.deshaw_india import parse_deshaw_next_data
from providers.tata_elxsi import extract_tata_elxsi_detail, extract_tata_elxsi_listing_items
from providers.talentbrew import _extract_listing_items, _page_url
from providers.vector_consulting import parse_vector_next_data


def check(label: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"PASS {label}")


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


def main() -> None:
    test_radancy_listing_links_parse()
    test_search_jobs_pagination_uses_p_param()
    test_cognizant_xml_parser_filters_india()
    test_apple_search_result_maps_india_job()
    test_tata_elxsi_listing_cards_parse()
    test_tata_elxsi_detail_extracts_jd_and_apply_url()
    test_vector_next_data_parser_maps_jobs_and_body_sections()
    test_deshaw_next_data_parser_maps_public_regular_jobs()
    print("All direct endpoint provider tests passed.")


if __name__ == "__main__":
    main()
