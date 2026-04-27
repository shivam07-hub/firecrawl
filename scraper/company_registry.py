"""
company_registry.py — Hardcoded endpoint knowledge from Market Data scrapers.

Facet IDs sourced from Market Data/Job_Scrapers/All_Scripts/run_*.py (verified 2026-04-02).

scrape_workday() checks WORKDAY_REGISTRY before dynamic UUID discovery.
This bypasses Cloudflare-protected discovery endpoints and fixes tenants
that use non-standard facet parameter names (e.g. Philips: locationHierarchy1).

WORKDAY_REGISTRY entry schema:
  india_facet_param  str   Workday facet parameter for country filter.
                           Most tenants: "locationCountry". Philips: "locationHierarchy1".
  india_uuid         str   UUID for India in that facet.
  it_facet_param     str   (optional) Facet parameter for job-family IT filter.
  it_uuids           list  (optional) UUIDs of IT/Digital job families.
  search_text        str   (optional) Use searchText filter instead of facets — for tenants
                           with no India UUID. Results are Python-filtered by is_india().

NOTE: Airbus and Shell share India UUID c4f78be1a8f14da0ab49ce1162348a5e.
This is Workday's standard India country reference ID used across many tenants.
"""

WORKDAY_REGISTRY: dict[str, dict] = {
    # searchText mode — no India UUID in tenant facets; Python-side is_india() filter applied
    "Intel": {
        # locationMainGroup facet exists but no India UUID exposed; searchText="india" returns ~84 India jobs
        "search_text": "india",
    },
    "Target": {
        # No India facet UUID; searchText="india" returns ~265 Bangalore jobs confirmed 2026-04-19
        "search_text": "india",
    },
    # Verified 2026-04-19 ─────────────────────────────────────────────────────
    "3M": {
        "india_facet_param": "Location_Country",
        "india_uuid":        "c4f78be1a8f14da0ab49ce1162348a5e",
    },
    "NXP Semiconductors": {
        "india_facet_param": "Location_Country",
        "india_uuid":        "c4f78be1a8f14da0ab49ce1162348a5e",
    },
    "Autodesk": {
        "india_facet_param": "locationCountry",
        "india_uuid":        "c4f78be1a8f14da0ab49ce1162348a5e",
    },
    "DXC Technology": {
        "india_facet_param": "locationCountry",
        "india_uuid":        "c4f78be1a8f14da0ab49ce1162348a5e",
    },
    "Roche": {
        # Uses 'locations' facet (not locationCountry) with a single India country-level UUID
        "india_facet_param": "locations",
        "india_uuid":        "54c59631019f01c479dfb787a377c235",
    },
    "Barclays": {
        # No locationCountry facet; filter by 12 India office location UUIDs
        "india_facet_param": "locations",
        "india_uuids": [
            "1110a9ca6540100196e1f0c315e90000",  # Bengaluru, Maruthi Onyx
            "112c0542820110016378a0a3e68d0000",  # Ceejay House, Mumbai
            "112c05428201100163788a5627320000",  # Chennai, DLF IT Park
            "253dfca5ccfc10016b1361f46cfe0000",  # Gurugram, DLF Downtown
            "c58206e6ec7510011bb86a010cff0000",  # Gurugram, TEC DLF Downtown
            "1ab48a98eb7c1001634cf23b210c0000",  # Mumbai, Altimus
            "b8f75d1cb9781000cd91027a85e30000",  # Mumbai, Nirlon Knowledge Park (BX)
            "1ab48a98eb7c100163423aff71b80000",  # Mumbai, Nirlon Knowledge Park (IB)
            "112c0542820110016377af553b050000",  # New Delhi, Eros Corporate Tower
            "112c0542820110016377c02c6ef00000",  # Noida, Candor TechSpace
            "1ab48a98eb7c100163465bf6c3310000",  # Prestige Meridian, Bengaluru
            "112c05428201100163763bd6ad400000",  # Pune, Gera Commerzone SEZ
        ],
    },
    "Maersk": {
        # No locationCountry facet; filter by 26 India office location UUIDs
        "india_facet_param": "locations",
        "india_uuids": [
            "4e4d26638c45010787a24d3a78f50000",  # IN - Bangalore
            "8df45049b43810013bfc511ded230000",  # INBLR08 - Bangalore - LF Logistics
            "4e4d26638c45010787a25209b00e0000",  # IN - Chennai
            "26c4d72049dc10009e0daf1507aa0000",  # India, Bengaluru, 560025
            "853120f5cc8a10009e388f5d2aec0000",  # India, Bengaluru, 560064
            "15350d48499210009e07c02b134d0000",  # India, Bengaluru, 562114 (a)
            "ddba4775944910009e1b192970560000",  # India, Bengaluru, 562114 (b)
            "d8801e5af43d10009dfa3a8079340000",  # India, Bengaluru, 562123
            "5fb6db3471ab10009df11e5466840000",  # India, Chennai, 600032
            "d8801e5af43d10009e0f6cca3a670000",  # India, Chennai, 600116
            "ddba4775944910009e424afe3f850000",  # India, Chennai, 601203
            "7a38998ecd771001354b00da72100000",  # India, Gujarat, Mehsana
            "e27b2cd8aca310009e0d527ac7650000",  # India, Gurgaon
            "d8801e5af43d10009e04f442bf430000",  # India, Haryana, Farukh Nagar
            "f37d2115b2fa1001e2ef05dbcdc00000",  # India, Haryana, Sonipat
            "614482d9d2ed1000c19c822fe2b50000",  # India, Maharashtra, Pune
            "e78dddcb583810009e1299afb33f0000",  # India, Mumbai
            "5fb6db3471ab10009e1c4676598a0000",  # India, Pipavav
            "d8801e5af43d10009e1bfb079d6e0000",  # India, Pune
            "4140682c689310014db3b323f82e0000",  # India, Tamil Nadu, Kancheepuram
            "4e4d26638c450107879f5562654c0000",  # INDJZ03 - Pune - Weikfield IT
            "4e4d26638c45010787a37d5e5ad00000",  # INMAA15 - Chennai - RMZ One Paramount
            "0829310dd78f100197add0dc5cc90000",  # IN - Mehsana
            "4e4d26638c45010787a25b0edea60000",  # IN - Mumbai
            "4e4d26638c45010787a25f43fa5f0000",  # IN - Navi Mumbai
            "4e4d26638c45010787a265e08d260000",  # IN - Pune
        ],
    },
    # Verified 2026-04-02 ─────────────────────────────────────────────────────
    "Airbus": {
        "india_facet_param": "locationCountry",
        "india_uuid":        "c4f78be1a8f14da0ab49ce1162348a5e",
        "it_facet_param":    "jobFamilyGroup",
        "it_uuids":          ["f5811cef9cb5015323ad7f3f550a1df2"],  # Digital <FU-IM>
    },
    "Shell": {
        "india_facet_param": "locationCountry",
        "india_uuid":        "c4f78be1a8f14da0ab49ce1162348a5e",
        "it_facet_param":    "jobFamilyGroup",
        "it_uuids":          ["a87fe1bd64b8016d9c737d3fa72c300c"],  # Information Technology
    },
    "Philips": {
        # CRITICAL: Philips uses locationHierarchy1, not locationCountry
        "india_facet_param": "locationHierarchy1",
        "india_uuid":        "6e1b2a934716103c2adde1d57e7700ea",
        "it_facet_param":    "jobFamilyGroup",
        "it_uuids":          [
            "94eec23a3cab01216af07777df6a8d29",  # RD Software
            "169c3da8f7270169c0ee692fbd324709",  # RD Systems
            "40b79030b3e0100163f33cd03cff0000",  # SY Information Security
            "58aeacb31cc0011e54561931bd325829",  # RD Artificial Intelligence
            "358cbd5a2fcc01e0783eb441a1012864",  # IT Platforms
            "a05309e84f810165f53b47218532188d",  # SY Product Security
        ],
    },
}
