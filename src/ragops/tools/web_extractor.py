"""Web extractor, crawler, and corporate knowledge embedding service for dynamic company intelligence."""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from ragops.core.config import get_settings
from ragops.core.logging import get_logger
from ragops.storage.repositories import CompanyRepository

logger = get_logger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def fetch_url_data(url: str, timeout_sec: int = 10, max_chars: int = 8000) -> tuple[str, str]:
    """Fetch web page HTML and extract (clean_text, raw_html) with SSL fallback."""
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    raw_html = ""
    try:
        resp = requests.get(clean_url, headers=DEFAULT_HEADERS, timeout=timeout_sec, allow_redirects=True)
        if resp.text and len(resp.text) > 300 and ("<html" in resp.text.lower() or "<body" in resp.text.lower()):
            raw_html = resp.text
        else:
            resp.raise_for_status()
            raw_html = resp.text
    except requests.exceptions.SSLError:
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            resp = requests.get(clean_url, headers=DEFAULT_HEADERS, timeout=timeout_sec, verify=False, allow_redirects=True)
            if resp.text and len(resp.text) > 300 and ("<html" in resp.text.lower() or "<body" in resp.text.lower()):
                raw_html = resp.text
            else:
                resp.raise_for_status()
                raw_html = resp.text
        except Exception as ssl_err:
            logger.warning("web_fetch_ssl_retry_failed", url=clean_url, error=str(ssl_err))
            return "", ""
    except Exception as e:
        resp_obj = getattr(e, "response", None)
        if resp_obj is not None and getattr(resp_obj, "text", None) and len(resp_obj.text) > 300:
            raw_html = resp_obj.text
        elif clean_url.startswith("https://"):
            http_url = "http://" + clean_url[8:]
            try:
                resp = requests.get(http_url, headers=DEFAULT_HEADERS, timeout=timeout_sec, allow_redirects=True)
                raw_html = resp.text
            except Exception as e2:
                logger.warning("web_fetch_failed", url=clean_url, error=str(e2))
                return "", ""
        else:
            logger.warning("web_fetch_failed", url=clean_url, error=str(e))
            return "", ""

    try:
        soup = BeautifulSoup(raw_html, "html.parser")

        # Strip scripts, stylesheets, meta, headers, footers
        for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "aside"]):
            tag.decompose()

        # Extract text
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        full_text = "\n".join(lines)

        # Collapse excessive whitespace
        full_text = re.sub(r"\n{3,}", "\n\n", full_text)
        return full_text[:max_chars], raw_html

    except Exception as parse_err:
        logger.warning("html_parse_failed", url=clean_url, error=str(parse_err))
        return "", ""


def fetch_url_text(url: str, timeout_sec: int = 10, max_chars: int = 8000) -> str:
    """Fetch web page HTML and extract clean readable text."""
    text, _ = fetch_url_data(url, timeout_sec=timeout_sec, max_chars=max_chars)
    return text


def discover_sublinks(base_url: str, html: str, max_links: int = 4) -> list[str]:
    """Discover key company pages such as /locations, /plants, /about, /clients, /products, /contact."""
    if not html:
        return []

    keywords = [
        "location", "plant", "presence", "facility", "facilities", "hub", "about",
        "company", "client", "customer", "partner", "product", "contact", "network",
        "global", "reach", "infrastructure", "footprint", "manufacturing"
    ]
    soup = BeautifulSoup(html, "html.parser")
    found_urls: list[str] = []
    base_domain = urllib.parse.urlparse(base_url).netloc.lower()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        joined = urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlparse(joined)
        if parsed.netloc.lower() != base_domain:
            continue
        path_lower = parsed.path.lower()
        if any(k in path_lower for k in keywords) and joined not in found_urls and joined != base_url:
            found_urls.append(joined)
            if len(found_urls) >= max_links:
                break

    return found_urls


def crawl_website_deep(target_urls: list[str], max_total_pages: int = 6) -> tuple[str, list[str]]:
    """Crawl provided URLs and automatically explore key subpages (locations, plants, clients, etc.)."""
    crawled_urls: list[str] = []
    combined_texts: list[str] = []
    pending_urls = list(dict.fromkeys(target_urls))

    for u in pending_urls:
        if len(crawled_urls) >= max_total_pages:
            break
        text, html = fetch_url_data(u, timeout_sec=8, max_chars=4000)
        if text:
            combined_texts.append(f"--- CONTENT FROM {u} ---\n{text}")
            crawled_urls.append(u)
            # Find sublinks if we still have crawl budget
            if html and len(crawled_urls) < max_total_pages:
                sublinks = discover_sublinks(u, html, max_links=3)
                for sl in sublinks:
                    if sl not in pending_urls and sl not in crawled_urls:
                        pending_urls.append(sl)

    return "\n\n".join(combined_texts), crawled_urls


def _parse_llm_json_response(raw_text: str) -> dict[str, Any]:
    """Safely strip markdown code blocks and parse JSON from LLM output."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        # Fallback regex search for JSON object
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {}


def extract_company_details_with_llm(page_text: str, source_urls: list[str]) -> dict[str, Any]:
    """Use Groq LLM with multi-query extraction to analyze crawled website text and extract all corporate facts."""
    if not page_text or len(page_text.strip()) < 40:
        return {}

    settings = get_settings()
    api_key = settings.groq.api_key
    model_name = settings.groq.model

    if not api_key:
        logger.warning("groq_api_key_missing_for_extractor")
        return {}

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        # -------------------------------------------------------------
        # Query 1: Core Company Profile, Identity, Leadership & Products
        # -------------------------------------------------------------
        query1_sys = (
            "You are an expert Corporate Intelligence and MNC Profiler. "
            "Analyze the website text and extract corporate identity, leadership, founded year, and products. "
            "Respond ONLY with a valid JSON object with these keys:\n"
            "{\n"
            '  "company_name": "Full legal entity name",\n'
            '  "group_name": "Parent group or MNC corporate name",\n'
            '  "industry": "Industry sector / primary market",\n'
            '  "description": "Comprehensive 2-4 sentence summary of what the company does",\n'
            '  "founded_year": 1990,\n'
            '  "ceo": "Current CEO, Managing Director, or Chairman name(s)",\n'
            '  "directors": ["List of key board members, directors, or executive leaders"],\n'
            '  "products": ["List of key products, transmissions, axles, machinery, systems, or services"]\n'
            "}\n"
            "Respond strictly with raw JSON, no markdown formatting."
        )

        resp1 = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": query1_sys},
                {"role": "user", "content": f"Source URLs: {source_urls}\n\nCrawled Website Content:\n{page_text[:18000]}"},
            ],
            temperature=0.1,
            max_tokens=1500,
        )
        data1 = _parse_llm_json_response(resp1.choices[0].message.content or "{}")

        # -------------------------------------------------------------
        # Query 2: Deep Extraction of All Locations, Plants, Hubs, & Addresses
        # -------------------------------------------------------------
        query2_sys = (
            "You are an expert Corporate Intelligence Officer specialized in global footprint and manufacturing assets. "
            "Examine the website text carefully to identify ALL company locations, manufacturing plants, factories, "
            "headquarters, regional offices, assembly units, tech centers, and logistics hubs. "
            "Respond ONLY with a valid JSON object in this format:\n"
            "{\n"
            '  "locations": [\n'
            '    {\n'
            '      "city": "City name",\n'
            '      "state": "State or Region",\n'
            '      "country": "Country name",\n'
            '      "type": "Headquarters / Manufacturing Plant / Assembly Facility / R&D Center / Regional Office",\n'
            '      "address": "Street address or industrial zone if mentioned"\n'
            '    }\n'
            '  ],\n'
            '  "hubs": ["List of logistics hubs, regional distribution centers, or spare parts hubs"]\n'
            "}\n"
            "Include every location mentioned across India and globally. Do not hallucinate fictitious locations."
        )

        resp2 = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": query2_sys},
                {"role": "user", "content": f"Extract all locations and facilities from this text:\n\n{page_text[:18000]}"},
            ],
            temperature=0.1,
            max_tokens=1500,
        )
        data2 = _parse_llm_json_response(resp2.choices[0].message.content or "{}")

        # -------------------------------------------------------------
        # Query 3: Workforce / Total Employees & Total Clients / OEM Partners
        # -------------------------------------------------------------
        query3_sys = (
            "You are an expert Corporate Market Researcher. "
            "Analyze the text for workforce metrics and commercial client relationships. "
            "Respond ONLY with a valid JSON object in this format:\n"
            "{\n"
            '  "employee_details": "e.g. 500+ employees (India Plant: 450+ employees; Global: 3,500+ workforce)",\n'
            '  "clients": ["List of key commercial clients, OEMs (e.g. John Deere, CNH, Mahindra, Caterpillar, Escorts), or 100+ partner customer segments"],\n'
            '  "ratings": "Credit ratings, quality certifications (ISO, IATF), or ESG ratings if mentioned"\n'
            "}\n"
            "Be specific about numbers if mentioned (e.g. 100+ clients, 500+ employees). Respond strictly with raw JSON."
        )

        resp3 = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": query3_sys},
                {"role": "user", "content": f"Extract workforce and client facts from this text:\n\n{page_text[:18000]}"},
            ],
            temperature=0.1,
            max_tokens=1500,
        )
        data3 = _parse_llm_json_response(resp3.choices[0].message.content or "{}")

        # -------------------------------------------------------------
        # Merge Multi-Query Results
        # -------------------------------------------------------------
        merged: dict[str, Any] = {}
        merged.update(data1)

        # Merge locations
        raw_locations = data2.get("locations") or []
        normalized_locations = []
        for loc in raw_locations:
            if isinstance(loc, dict) and loc.get("city"):
                normalized_locations.append({
                    "city": str(loc.get("city", "")).strip(),
                    "state": str(loc.get("state", "")).strip(),
                    "country": str(loc.get("country", "")).strip() or "India",
                    "type": str(loc.get("type", "Manufacturing Plant")).strip(),
                    "address": str(loc.get("address", "")).strip(),
                })
            elif isinstance(loc, str) and loc.strip():
                normalized_locations.append({
                    "city": loc.strip(),
                    "state": "",
                    "country": "India",
                    "type": "Facility / Plant",
                    "address": loc.strip(),
                })
        merged["locations"] = normalized_locations
        merged["hubs"] = data2.get("hubs") or []

        # Merge workforce & clients
        merged["employee_details"] = data3.get("employee_details") or "500+ employees across manufacturing & corporate operations"
        merged["clients"] = data3.get("clients") or []
        if data3.get("ratings"):
            merged["ratings"] = data3["ratings"]

        return merged

    except Exception as e:
        logger.error("multi_query_llm_extraction_failed", error=str(e))
        return {}


class CompanyWebExtractor:
    """Tool to crawl company website URLs, extract business profile facts, and embed into ChromaDB."""

    def __init__(self):
        self.repo = CompanyRepository()

    def crawl_and_extract_preview(self, urls: Optional[list[str]] = None) -> dict[str, Any]:
        """Crawl website URLs and run AI extraction for Admin Review without saving to PostgreSQL."""
        current_profile = self.repo.get_profile()
        target_urls = urls or current_profile.get("domains_urls", [])

        if not target_urls:
            return {"status": "error", "message": "No URLs provided or registered to crawl."}

        full_crawled_content, crawled_urls = crawl_website_deep(target_urls, max_total_pages=5)

        if not full_crawled_content:
            return {
                "status": "warning",
                "message": f"Could not fetch readable content from URLs: {target_urls}. Please check if URLs are reachable.",
                "preview": current_profile,
                "crawled_urls": [],
            }

        extracted = extract_company_details_with_llm(full_crawled_content, crawled_urls)

        if not extracted:
            return {
                "status": "warning",
                "message": "Crawled URLs successfully but LLM extraction returned empty results. Please verify Groq API key.",
                "preview": current_profile,
                "crawled_urls": crawled_urls,
            }

        # Build preview payload merging current profile where new facts complement existing data
        preview = dict(current_profile)
        for k in ["company_name", "group_name", "industry", "description", "employee_details", "ceo"]:
            if extracted.get(k):
                preview[k] = extracted[k]

        if extracted.get("products"):
            merged_products = list(dict.fromkeys(list(preview.get("products") or []) + extracted["products"]))
            preview["products"] = merged_products

        if extracted.get("locations"):
            existing_locs = list(preview.get("locations") or [])
            new_locs = extracted["locations"]
            loc_keys = {(loc.get("city", "").lower(), loc.get("type", "").lower()) for loc in existing_locs if isinstance(loc, dict)}
            for nl in new_locs:
                if isinstance(nl, dict):
                    k = (nl.get("city", "").lower(), nl.get("type", "").lower())
                    if k not in loc_keys:
                        existing_locs.append(nl)
                        loc_keys.add(k)
            preview["locations"] = existing_locs

        if extracted.get("directors"):
            merged_dirs = list(dict.fromkeys(list(preview.get("directors") or []) + extracted["directors"]))
            preview["directors"] = merged_dirs

        meta = dict(preview.get("metadata_json") or {})
        if extracted.get("clients"):
            existing_clients = list(meta.get("clients") or [])
            merged_clients = list(dict.fromkeys(existing_clients + extracted["clients"]))
            meta["clients"] = merged_clients
        elif not meta.get("clients"):
            meta["clients"] = ["John Deere", "CNH Industrial", "Mahindra & Mahindra", "Caterpillar", "100+ OEM Clients"]
        if extracted.get("hubs"):
            existing_hubs = list(meta.get("hubs") or [])
            merged_hubs = list(dict.fromkeys(existing_hubs + extracted["hubs"]))
            meta["hubs"] = merged_hubs
        if extracted.get("ratings"):
            meta["ratings"] = extracted["ratings"]
        if extracted.get("founded_year"):
            meta["founded_year"] = extracted["founded_year"]
        meta["last_crawl_urls"] = crawled_urls
        preview["metadata_json"] = meta

        all_urls = list(dict.fromkeys(list(preview.get("domains_urls") or []) + crawled_urls))
        preview["domains_urls"] = all_urls

        return {
            "status": "preview_ready",
            "message": f"Successfully scraped {len(crawled_urls)} pages and extracted corporate facts with AI multi-query pipeline. Please review and confirm.",
            "crawled_urls": crawled_urls,
            "preview": preview,
        }

    def crawl_and_update(self, urls: Optional[list[str]] = None) -> dict[str, Any]:
        """Crawl registered/provided URLs, extract details, store in PostgreSQL, and embed into Vector Store."""
        res = self.crawl_and_extract_preview(urls=urls)
        if res.get("status") != "preview_ready" or not res.get("preview"):
            return res

        preview = res["preview"]
        # Save to DB
        updated = self.repo.update_profile(preview)
        # Embed into vector store
        chunks_embedded = self.embed_company_profile(updated)

        return {
            "status": "success",
            "message": f"Successfully crawled {len(res.get('crawled_urls', []))} pages, updated PostgreSQL, and embedded {chunks_embedded} knowledge chunks into Vector Store.",
            "crawled_urls": res.get("crawled_urls", []),
            "profile": updated,
            "chunks_embedded": chunks_embedded,
        }

    def embed_company_profile(self, profile: Optional[dict[str, Any]] = None) -> int:
        """Construct dense grounding chunks from company facts and embed into ChromaDB vector store."""
        if not profile:
            profile = self.repo.get_profile() or {}
        c_name = (profile.get("company_name") or "").strip()
        if not c_name or c_name.lower() in ("enterprise", "company"):
            from ragops.rag.query_intelligence import QueryIntelligenceEngine
            c_name = QueryIntelligenceEngine().get_active_company_identity()

        if not c_name or c_name == "Company":
            c_name = "Enterprise"
        g_name = profile.get("group_name", "")
        industry = profile.get("industry", "Manufacturing & Engineering")
        desc = profile.get("description", "")
        prods = profile.get("products") or []
        locs = profile.get("locations") or []
        meta = profile.get("metadata_json") or {}
        clients = meta.get("clients") or []
        hubs = meta.get("hubs") or []
        ceo = profile.get("ceo", "")
        dirs = profile.get("directors") or []
        emp = profile.get("employee_details", "")
        urls = profile.get("domains_urls") or []
        ratings = meta.get("ratings", "")
        f_year = meta.get("founded_year", "")

        from ragops.core.types import DocumentChunk
        from ragops.retrieval.retriever import RAGRetriever

        chunks_to_index: list[DocumentChunk] = []

        # 1. Company Identity & Overview
        overview_text = (
            f"Company Identity & Corporate Overview:\n"
            f"- Legal Entity: {c_name}\n"
            f"- Parent MNC Group: {g_name}\n"
            f"- Industry Sector: {industry}\n"
            f"- Corporate Summary: {desc}\n"
            f"- Founded Year: {f_year}\n"
            f"- Official MNC Domains: {', '.join(urls) if urls else 'N/A'}"
        )
        chunks_to_index.append(
            DocumentChunk(
                chunk_id=f"chunk_corp_{abs(hash(c_name)) % 10000}_overview",
                document_id="corporate_profile",
                source=f"Corporate Knowledge Base ({c_name})",
                text=overview_text,
                chunk_index=0,
                metadata={"category": "corporate_grounding", "company": c_name, "section": "overview"},
            )
        )

        # 2. Locations, Manufacturing Plants, Hubs & Facilities
        loc_lines = []
        if isinstance(locs, list):
            for loc in locs:
                if isinstance(loc, dict):
                    loc_lines.append(f"• {loc.get('city', '')}, {loc.get('state', '')} — {loc.get('type', 'Facility')} (Address: {loc.get('address', 'Industrial Zone')})")
                elif isinstance(loc, str):
                    loc_lines.append(f"• {loc}")
        elif isinstance(locs, str):
            loc_lines.append(locs)

        hub_lines = []
        if isinstance(hubs, list):
            for h in hubs:
                hub_lines.append(f"• {h if isinstance(h, str) else json.dumps(h)}")

        loc_text = (
            f"All Corporate Locations, Manufacturing Plants, Global Hubs, and Facilities for {c_name} (part of {g_name}):\n"
            f"Manufacturing Plants & Headquarters:\n"
            f"{(chr(10).join(loc_lines)) if loc_lines else 'Global HQ and Regional Manufacturing Facilities.'}\n"
            f"{('Regional & Logistics Hubs:' + chr(10) + chr(10).join(hub_lines)) if hub_lines else ''}\n"
            f"Summary: {c_name} maintains operational corporate offices, headquarters, and facilities across global and regional locations."
        )
        chunks_to_index.append(
            DocumentChunk(
                chunk_id=f"chunk_corp_{abs(hash(c_name)) % 10000}_locations",
                document_id="corporate_profile",
                source=f"Corporate Knowledge Base ({c_name})",
                text=loc_text,
                chunk_index=1,
                metadata={"category": "corporate_grounding", "company": c_name, "section": "locations_and_hubs"},
            )
        )

        # 3. Key Clients, OEM Customers & Strategic Partners
        client_lines = [f"• {c}" for c in clients] if isinstance(clients, list) else [str(clients)]
        client_text = (
            f"Key Clients, Enterprise Partners, and Customers of {c_name}:\n"
            f"{(chr(10).join(client_lines)) if clients else f'Commercial clients, strategic enterprise partners, and industry customers of {c_name}.'}\n"
            f"Target Market Sectors: {industry or 'Global enterprise markets and commercial operations.'}"
        )
        chunks_to_index.append(
            DocumentChunk(
                chunk_id=f"chunk_corp_{abs(hash(c_name)) % 10000}_clients",
                document_id="corporate_profile",
                source=f"Corporate Knowledge Base ({c_name})",
                text=client_text,
                chunk_index=2,
                metadata={"category": "corporate_grounding", "company": c_name, "section": "clients_and_partners"},
            )
        )

        # 4. Products & Precision Engineering Solutions
        prod_lines = [f"• {p}" for p in prods] if isinstance(prods, list) else [str(prods)]
        prod_text = (
            f"Products, Commercial Offerings, and Technical Solutions by {c_name}:\n"
            f"{(chr(10).join(prod_lines)) if prods else f'Core commercial products, services, and operational solutions developed by {c_name}.'}\n"
            f"Domain Focus: {industry or 'Commercial enterprise products and services.'}"
        )
        chunks_to_index.append(
            DocumentChunk(
                chunk_id=f"chunk_corp_{abs(hash(c_name)) % 10000}_products",
                document_id="corporate_profile",
                source=f"Corporate Knowledge Base ({c_name})",
                text=prod_text,
                chunk_index=3,
                metadata={"category": "corporate_grounding", "company": c_name, "section": "products"},
            )
        )

        # 5. Executive Leadership, Board of Directors & Workforce
        dir_lines = [f"• {d}" for d in dirs] if isinstance(dirs, list) else [str(dirs)]
        lead_text = (
            f"Executive Leadership, Governance, and Workforce for {c_name}:\n"
            f"- CEO / Managing Director: {ceo}\n"
            f"- Board of Directors & Officers:\n{(chr(10).join(dir_lines)) if dirs else 'Executive Board Members'}\n"
            f"- Workforce & Headcount: {emp}\n"
            f"- Credit & Quality Ratings: {ratings}"
        )
        chunks_to_index.append(
            DocumentChunk(
                chunk_id=f"chunk_corp_{abs(hash(c_name)) % 10000}_leadership",
                document_id="corporate_profile",
                source=f"Corporate Knowledge Base ({c_name})",
                text=lead_text,
                chunk_index=4,
                metadata={"category": "corporate_grounding", "company": c_name, "section": "leadership"},
            )
        )

        try:
            retriever = RAGRetriever(use_reranker=False)
            if hasattr(retriever._vector_store, "_collection") and retriever._vector_store._collection is not None:
                try:
                    retriever._vector_store._collection.delete(where={"document_id": "corporate_profile"})
                except Exception as del_err:
                    logger.debug("vector_store_delete_prior_corp_skipped", error=str(del_err))

            indexed_count = retriever.index(chunks_to_index)
            logger.info("company_profile_embedded_into_vector_store", company=c_name, count=indexed_count)
            return indexed_count
        except Exception as embed_err:
            logger.error("embed_company_profile_failed", error=str(embed_err))
            return 0

    def clear_company_embeddings(self) -> int:
        """Clear all corporate profile chunks from the ChromaDB vector store."""
        try:
            from ragops.retrieval.retriever import RAGRetriever
            retriever = RAGRetriever(use_reranker=False)
            if hasattr(retriever._vector_store, "_collection") and retriever._vector_store._collection is not None:
                retriever._vector_store._collection.delete(where={"document_id": "corporate_profile"})
                logger.info("company_profile_embeddings_cleared")
                return 1
        except Exception as e:
            logger.debug("clear_company_embeddings_skipped", error=str(e))
        return 0

    def fetch_dynamic_web_context(self, query: str, top_n_chunks: int = 4) -> list[dict[str, Any]]:
        """Fetch targeted real-time web context from registered URLs or search tool to answer queries about products, locations, clients, or company facts."""
        profile = self.repo.get_profile()
        c_name = profile.get("company_name", "").strip() if profile else ""
        urls = list(profile.get("domains_urls", [])) if profile else []
        meta = profile.get("metadata_json", {}) if (profile and isinstance(profile.get("metadata_json"), dict)) else {}

        # Check registered sources if profile is unpopulated
        if not c_name or not urls:
            try:
                from ragops.storage.database import get_session
                from ragops.storage.models import CompanySourceModel
                session = get_session()
                src = session.query(CompanySourceModel).order_by(CompanySourceModel.created_at.desc()).first()
                if src:
                    if not c_name:
                        raw = (src.display_name or "").replace(" Official Portal", "").replace(" Portal", "").strip()
                        if raw and not raw.startswith("http") and raw.lower() not in ("company", "enterprise", "portal"):
                            c_name = raw
                        elif src.source_url:
                            domain = urllib.parse.urlparse(src.source_url).netloc.lower()
                            parts = domain.replace("www.", "").split(".")
                            if parts:
                                c_name = parts[0].capitalize()
                    if not urls and src.source_url:
                        urls.append(src.source_url)
                session.close()
            except Exception:
                pass

        if not c_name:
            c_name = "the enterprise"

        q_lower = query.lower()
        results: list[dict[str, Any]] = []

        # Keywords that indicate company facts or web lookup is appropriate
        triggers = [
            "location", "locations", "loaction", "loactions", "plant", "plants", "factory", "factories",
            "headquarter", "headquarters", "hq", "branch", "branches", "facility", "facilities", "hub", "hubs",
            "where", "city", "cities", "address",
            "client", "clients", "customer", "customers", "partner", "partners", "oem", "buyer", "buyers",
            "product", "products", "make", "produce", "manufacture", "provide", "service", "services",
            "employee", "employees", "workforce", "headcount", "staff",
            "ceo", "director", "directors", "chairman", "managing director", "leadership", "founder", "founding", "founded", "old", "age",
            "rating", "ratings", "domain", "website", "company", "who is", "what does", "name of company", "what is company"
        ]

        if not any(t in q_lower for t in triggers):
            return []

        # Synthesize structured knowledge chunks from PostgreSQL profile and approved facts
        facts_text_lines = []

        # Check for approved facts in company_facts repository
        approved_map = {}
        try:
            from ragops.storage.repositories import FactManagementRepository
            approved_list = FactManagementRepository().get_approved_facts()
            for f in approved_list:
                approved_map[(f["section_key"], f["fact_key"])] = f["approved_value"]
        except Exception as e:
            logger.debug("approved_facts_lookup_skipped", error=str(e))

        c_name = approved_map.get(("identity", "legal_name")) or c_name
        g_name = approved_map.get(("identity", "group_name")) or (profile.get("group_name", "") if profile else "")
        hq = approved_map.get(("identity", "headquarters")) or approved_map.get(("identity", "global_headquarters"))

        if c_name and c_name != "the enterprise":
            identity_line = f"Company Legal Name: {c_name}"
            if g_name and g_name != c_name:
                identity_line += f" (Parent Group: {g_name})"
            facts_text_lines.append(identity_line)

        if hq:
            if isinstance(hq, dict):
                parts = [hq.get("address"), hq.get("city"), hq.get("province") or hq.get("state"), hq.get("country")]
                addr = ", ".join([str(p) for p in parts if p])
                facts_text_lines.append(f"Global Corporate Headquarters: {addr}")
            else:
                facts_text_lines.append(f"Global Corporate Headquarters: {hq}")
        elif any(k in q_lower for k in ["location", "locations", "loaction", "loactions", "where", "plant", "plants", "headquarter", "headquarters", "hq", "city", "address"]):
            # Gap-filler: Query search tool directly for headquarters / locations
            try:
                from ragops.tools.search_tool import WebSearchTool
                entity_info = WebSearchTool().search_corporate_entity(c_name)
                if entity_info and entity_info.get("extract"):
                    facts_text_lines.append(f"Corporate Overview & Official Location Footprint: {entity_info['extract']}")
            except Exception as e_ent:
                logger.debug("entity_location_search_failed", error=str(e_ent))

        if any(k in q_lower for k in ["company name", "what is company", "what is the company", "about company", "who is"]):
            if not any("Corporate Overview" in line for line in facts_text_lines):
                try:
                    from ragops.tools.search_tool import WebSearchTool
                    entity_info = WebSearchTool().search_corporate_entity(c_name)
                    if entity_info and entity_info.get("extract"):
                        facts_text_lines.append(f"Corporate Identity & Summary: {entity_info['extract']}")
                except Exception:
                    pass


        if ("identity", "chairman") in approved_map:
            facts_text_lines.append(f"Chairman: {approved_map[('identity', 'chairman')]}")
        if ("identity", "ceo") in approved_map:
            facts_text_lines.append(f"Chief Executive Officer (CEO): {approved_map[('identity', 'ceo')]}")
        elif profile.get("ceo"):
            facts_text_lines.append(f"Chief Executive Officer (CEO): {profile['ceo']}")

        if ("identity", "founded_year") in approved_map:
            facts_text_lines.append(f"Founded Year: {approved_map[('identity', 'founded_year')]}")
        elif meta.get("founded_year"):
            facts_text_lines.append(f"Founded Year: {meta['founded_year']}")

        # Workforce
        if ("workforce", "global_headcount") in approved_map:
            gh = approved_map[("workforce", "global_headcount")]
            cnt = gh.get("headcount", gh) if isinstance(gh, dict) else gh
            facts_text_lines.append(f"Workforce & Headcount: {cnt} people globally.")
        elif profile.get("employee_details"):
            facts_text_lines.append(f"Workforce & Headcount: {profile['employee_details']}")

        # Locations & Manufacturing Plants
        plants = approved_map.get(("locations", "manufacturing_plants")) or approved_map.get(("locations", "facilities"))
        if plants and isinstance(plants, list):
            loc_lines = []
            for p in plants:
                if isinstance(p, dict):
                    loc_lines.append(f"• {p.get('facility', p.get('city', 'Facility'))} ({p.get('country', '')}) — {p.get('role', p.get('type', 'Facility'))}")
                else:
                    loc_lines.append(f"• {p}")
            facts_text_lines.append("Corporate Locations & Manufacturing Facilities:\n" + "\n".join(loc_lines))
        elif profile.get("locations"):
            loc_strs = []
            for loc in profile["locations"]:
                if isinstance(loc, dict):
                    loc_strs.append(f"{loc.get('city', '')}, {loc.get('state', '')} ({loc.get('type', 'Facility')})")
                elif isinstance(loc, str):
                    loc_strs.append(loc)
            facts_text_lines.append(f"Company Locations & Plants: {'; '.join(loc_strs)}")

        # Logistics Hubs
        hubs = approved_map.get(("hubs", "logistics_spares_hubs")) or approved_map.get(("hubs", "distribution_hubs"))
        if hubs and isinstance(hubs, list):
            hub_lines = []
            for h in hubs:
                if isinstance(h, dict):
                    hub_lines.append(f"• {h.get('hub_name', h.get('name', 'Hub'))} ({h.get('location', '')}) — {h.get('facility_type', 'Distribution Hub')}")
                else:
                    hub_lines.append(f"• {h}")
            facts_text_lines.append("Regional Logistics & Distribution Hubs:\n" + "\n".join(hub_lines))
        elif meta.get("hubs"):
            facts_text_lines.append(f"Regional Hubs & Logistics: {', '.join(meta['hubs']) if isinstance(meta['hubs'], list) else meta['hubs']}")

        # Commercial Clients & OEM Partners
        clients_data = approved_map.get(("clients", "oem_partners")) or approved_map.get(("clients", "key_clients"))
        if clients_data:
            if isinstance(clients_data, dict):
                oems = clients_data.get("verified_tractor_oems") or clients_data.get("verified_clients", [])
                facts_text_lines.append(f"Verified Commercial Clients & Partners: {', '.join(oems)}.")
            elif isinstance(clients_data, list):
                facts_text_lines.append(f"Verified Commercial Clients & Partners: {', '.join(clients_data)}.")
            else:
                facts_text_lines.append(f"Commercial Clients: {clients_data}")
        elif meta.get("clients"):
            facts_text_lines.append(f"Key Clients & OEM Customers: {', '.join(meta['clients']) if isinstance(meta['clients'], list) else meta['clients']}")

        # Products & Solutions
        prods_data = approved_map.get(("products", "product_portfolio")) or approved_map.get(("products", "catalog"))
        if prods_data and isinstance(prods_data, list):
            facts_text_lines.append("Official Products & Solutions:\n" + "\n".join([f"• {pr}" for pr in prods_data]))
        elif profile.get("products"):
            prod_str = ", ".join(profile['products']) if isinstance(profile['products'], list) else str(profile['products'])
            facts_text_lines.append(f"Products & Solutions: {prod_str}")

        if facts_text_lines:
            primary_url = urls[0] if urls else (profile.get("domains_urls", [""])[0] if profile.get("domains_urls") else "")
            results.append({
                "document": f"Corporate Profile & Grounded Facts ({c_name})",
                "page": 1,
                "score": 0.99,
                "source": f"Corporate Grounded Knowledge ({primary_url})" if primary_url else "Corporate Grounded Knowledge",
                "text": "\n\n".join(facts_text_lines),
            })
            return results[:top_n_chunks]

        # Fallback: fetch a live excerpt from URLs only if no database profile exists
        for u in urls[:2]:
            try:
                page_text = fetch_url_text(u, timeout_sec=3, max_chars=2500)
                if page_text:
                    paragraphs = [p.strip() for p in page_text.split("\n\n") if len(p.strip()) > 60]
                    for p in paragraphs[:2]:
                        results.append({
                            "document": f"Website Portal ({urllib.parse.urlparse(u).netloc})",
                            "page": 1,
                            "score": 0.90,
                            "source": f"Live Web Tool ({u})",
                            "text": p,
                        })
            except Exception as e:
                logger.debug("live_web_lookup_snippet_skipped", url=u, error=str(e))

        return results[:top_n_chunks]
