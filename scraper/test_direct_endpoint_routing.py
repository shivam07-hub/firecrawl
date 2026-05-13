from __future__ import annotations

from portal_reader import parse_portals


def check(label: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"PASS {label}")


def _portal(company: str) -> dict:
    matches = [p for p in parse_portals() if p.get("company") == company]
    if not matches:
        raise AssertionError(f"portal missing: {company}")
    return matches[0]


def test_direct_endpoint_routes() -> None:
    expected = {
        "Apple": "apple_jobs",
        "Cognizant": "cognizant_xml",
        "Google": "google_careers",
        "STMicroelectronics": "eightfold",
        "American Express": "oracle",
        "Citibank": "talentbrew",
        "AstraZeneca": "talentbrew",
        "Eli Lilly": "phenom_ssr",
        "Cisco": "phenom_ssr",
        "BCG": "phenom_ssr",
        "LTIMindtree": "sap_jobs2web_html",
        "GMR Group": "sap_jobs2web_html",
        "HP (HPE)": "phenom_ssr",
        "HiLabs": "hilabs_careers",
        "Tata Elxsi": "tata_elxsi",
        "Vector Consulting Group": "vector_consulting",
        "DE Shaw": "deshaw_india",
        "IntouchCX": "intouchcx",
        "Microsoft": "microsoft_careers",
        "Black Brix": "blackbrix_jobs",
    }
    for company, ats in expected.items():
        portal = _portal(company)
        check(f"{company} ats", portal["ats"] == ats)
        check(f"{company} no firecrawl", not portal.get("js_required"))


def main() -> None:
    test_direct_endpoint_routes()
    print("All direct endpoint routing tests passed.")


if __name__ == "__main__":
    main()
