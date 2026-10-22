"""Universal Company Intelligence Schemas & Section Registry.

Defines standard corporate knowledge dimensions, fact keys, validation rules,
and serialization formats for ANY enterprise (manufacturing, tech, automotive, services, etc.).
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# Standard Company Knowledge Sections
COMPANY_SECTIONS: dict[str, dict[str, Any]] = {
    "identity": {
        "title": "Company Legal Identity & Leadership",
        "description": "Official legal name, parent group, founding date, executive leadership (CEO, Chairman), global headquarters, and business overview.",
        "fact_keys": [
            "legal_name",
            "group_name",
            "founded_year",
            "industry",
            "chairman",
            "ceo",
            "global_headquarters",
            "business_overview",
        ],
    },
    "workforce": {
        "title": "Workforce & Headcount",
        "description": "Global employee count, regional/country workforce figures, reporting fiscal year, and source conflict detection.",
        "fact_keys": [
            "global_headcount",
            "regional_headcount",
            "workforce_reporting_period",
        ],
    },
    "locations": {
        "title": "Locations, Manufacturing Plants & R&D",
        "description": "Complete global inventory of production facilities, tech centers, corporate offices, addresses, cities, and countries.",
        "fact_keys": [
            "manufacturing_plants",
            "rd_centers",
            "branch_offices",
            "global_plant_count",
        ],
    },
    "clients": {
        "title": "Commercial Clients & OEM Partners",
        "description": "Verified commercial clients, OEM manufacturer partners, and client relationship qualification.",
        "fact_keys": [
            "oem_partners",
            "verified_clients",
            "manufacturer_reach_count",
        ],
    },
    "hubs": {
        "title": "Regional Logistics & Spares Hubs",
        "description": "Confirmed spare parts distribution centers, logistics hubs, and warehouse network.",
        "fact_keys": [
            "logistics_spares_hubs",
            "distribution_centers",
        ],
    },
    "products": {
        "title": "Products & Engineering Solutions",
        "description": "Comprehensive portfolio categories, machinery components, digital solutions, and aftermarket support.",
        "fact_keys": [
            "product_portfolio",
            "core_solutions",
            "services_offered",
        ],
    },
    "innovation": {
        "title": "Technology & Innovation",
        "description": "R&D capabilities, electrification, hybrid systems, engineering design, and patent focus.",
        "fact_keys": [
            "technology_focus",
            "electrification_solutions",
            "engineering_capabilities",
        ],
    },
    "financials": {
        "title": "Financial Overview & Markets",
        "description": "Reported turnover, annual revenue, EBITDA, fiscal year, and target industry markets.",
        "fact_keys": [
            "annual_revenue",
            "ebitda",
            "target_markets",
            "financial_reporting_year",
        ],
    },
    "certifications": {
        "title": "Certifications & Quality Standards",
        "description": "ISO quality certifications, environmental compliance, and safety standards.",
        "fact_keys": [
            "iso_certifications",
            "quality_standards",
        ],
    },
    "contacts": {
        "title": "Official Contacts & Portals",
        "description": "Corporate headquarters address, official contact emails, public phone numbers, and country branch websites.",
        "fact_keys": [
            "corporate_address",
            "official_websites",
            "public_contacts",
        ],
    },
}


class CandidateFactItem(BaseModel):
    """A single field-level candidate fact extracted from source pages or search."""
    section_key: str = Field(..., description="Section identifier e.g. identity, workforce, locations")
    fact_key: str = Field(..., description="Fact key e.g. global_headquarters, global_headcount")
    scope_key: str = Field("global", description="Scope e.g. 'global' or 'country:IN'")
    proposed_value: Any = Field(..., description="Structured JSON or string value")
    normalized_value: Optional[Any] = Field(None, description="Cleaned normalized representation")
    validation_status: str = Field("valid", description="'valid', 'conflicting', 'needs_review', 'invalid'")
    review_status: str = Field("pending", description="'pending', 'approved', 'rejected', 'needs_changes'")
    extraction_confidence: float = Field(0.95, ge=0.0, le=1.0)
    evidence_text: str = Field(..., description="Exact verbatim citation quote from source text")
    section_heading: Optional[str] = Field(None, description="Heading of the section where fact was located")
    source_url: Optional[str] = Field(None, description="Canonical page URL where evidence was found")
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None


class CrawledPageDoc(BaseModel):
    """Metadata and content for a crawled company webpage."""
    url: str
    title: str
    clean_text: str
    char_count: int
    matched_section: Optional[str] = None


class AnalysisResult(BaseModel):
    """Comprehensive analysis outcome returned to API and UI."""
    organization_id: str
    company_name: str
    root_url: str
    pages_crawled: int
    search_queries_executed: int
    candidates_count: int
    candidates: list[dict[str, Any]]
    conflicts_detected: int
    message: str
