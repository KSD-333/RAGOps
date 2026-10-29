"""AI Web Search Tool for corporate intelligence and gap-filling research."""

from __future__ import annotations

import re
import urllib.parse
from typing import Any, Optional
import requests
from bs4 import BeautifulSoup

from ragops.core.logging import get_logger

logger = get_logger(__name__)

SEARCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class WebSearchTool:
    """Universal search tool for autonomous AI agents to research missing corporate facts.
    
    Uses DuckDuckGo HTML search and direct query lookups with zero external API key requirements.
    """

    def __init__(self, timeout_sec: int = 10, max_results: int = 5):
        self.timeout_sec = timeout_sec
        self.max_results = max_results

    def search(self, query: str, max_results: Optional[int] = None) -> list[dict[str, str]]:
        """Execute a web search query and return parsed snippets, titles, and URLs."""
        limit = max_results or self.max_results
        clean_query = query.strip()
        if not clean_query:
            return []

        logger.info("web_search_initiated", query=clean_query, limit=limit)
        results = []

        # Corporate Entity validation keywords
        corporate_keywords = [
            "company", "corporation", "manufacturer", "business", "enterprise",
            "group", "ltd", "limited", "inc", "s.p.a", "firm", "supplier", "automotive",
            "technology", "solutions", "products", "operations", "headquarters"
        ]

        # 1. Authoritative Corporate Entity & Registry Search via Wikipedia API (only for queries mentioning company/enterprise)
        if any(w in clean_query.lower() for w in ("company", "group", "corp", "inc", "ltd", "technologies", "motors", "systems")):
            try:
                wiki_resp = requests.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": clean_query,
                        "format": "json",
                        "utf8": 1,
                        "srlimit": limit,
                    },
                    headers={"User-Agent": "RAGOps-Corporate-Intelligence/1.0 (admin@ragops.local)"},
                    timeout=self.timeout_sec,
                )
                if wiki_resp.status_code == 200:
                    wiki_data = wiki_resp.json()
                    items = wiki_data.get("query", {}).get("search", [])
                    for item in items:
                        raw_snippet = item.get("snippet", "")
                        clean_snippet = BeautifulSoup(raw_snippet, "html.parser").get_text(strip=True)
                        title = item.get("title", "")
                        url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                        # Strict Corporate Guard: Ignore astronomy (galaxies, stars), sports, politicians, TV shows
                        snippet_lower = clean_snippet.lower()
                        title_lower = title.lower()
                        if any(bad in snippet_lower or bad in title_lower for bad in ("galaxy", "galaxies", "serpens", "championship", "season", "politician", "actor", "song", "album", "film", "series")):
                            continue
                        if title and clean_snippet and any(ck in snippet_lower or ck in title_lower for ck in corporate_keywords):
                            results.append({
                                "title": title,
                                "url": url,
                                "snippet": clean_snippet,
                                "source": "wikipedia_corporate_registry",
                            })
            except Exception as wiki_err:
                logger.debug("wiki_search_failed", query=clean_query, error=str(wiki_err))

        if len(results) >= limit:
            logger.info("web_search_completed", query=clean_query, results_found=len(results))
            return results[:limit]

        # 2. Try DuckDuckGo HTML endpoint
        try:
            resp = requests.post(
                "https://html.duckduckgo.com/html/",
                data={"q": clean_query, "b": ""},
                headers=SEARCH_HEADERS,
                timeout=self.timeout_sec,
            )
            if resp.status_code == 200 and len(resp.text) > 500:
                soup = BeautifulSoup(resp.text, "html.parser")
                web_results = soup.select(".web-result") or soup.select(".result")
                for r in web_results[:limit]:
                    title_elem = r.select_one(".result__title a") or r.select_one("a.result__url")
                    snippet_elem = r.select_one(".result__snippet")
                    
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    raw_href = title_elem.get("href", "")
                    
                    # DuckDuckGo redirect link unquoting
                    target_url = raw_href
                    if "uddg=" in raw_href:
                        match = re.search(r"uddg=([^&]+)", raw_href)
                        if match:
                            target_url = urllib.parse.unquote(match.group(1))

                    snippet = snippet_elem.get_text(separator=" ", strip=True) if snippet_elem else ""
                    if title and snippet:
                        results.append({
                            "title": title,
                            "url": target_url,
                            "snippet": snippet,
                            "source": "duckduckgo",
                        })
        except Exception as e:
            logger.warning("duckduckgo_search_failed", query=clean_query, error=str(e))

        # 2. Fallback to DuckDuckGo Lite endpoint if html failed or returned 0 results
        if not results:
            try:
                resp = requests.post(
                    "https://lite.duckduckgo.com/lite/",
                    data={"q": clean_query},
                    headers=SEARCH_HEADERS,
                    timeout=self.timeout_sec,
                )
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    rows = soup.select("table tbody tr")
                    curr_title = ""
                    curr_url = ""
                    for row in rows:
                        link_elem = row.select_one("a.result-link")
                        snippet_elem = row.select_one("td.result-snippet")
                        if link_elem:
                            curr_title = link_elem.get_text(strip=True)
                            curr_url = link_elem.get("href", "")
                        elif snippet_elem and curr_title:
                            snippet = snippet_elem.get_text(separator=" ", strip=True)
                            results.append({
                                "title": curr_title,
                                "url": curr_url,
                                "snippet": snippet,
                                "source": "duckduckgo_lite",
                            })
                            curr_title = ""
                            curr_url = ""
                            if len(results) >= limit:
                                break
            except Exception as e2:
                logger.warning("duckduckgo_lite_search_failed", query=clean_query, error=str(e2))

        logger.info("web_search_completed", query=clean_query, results_found=len(results))
        return results

    def search_corporate_entity(self, entity_name: str) -> Optional[dict[str, Any]]:
        """Fetch verified corporate entity overview, headquarters, and operational facts via Wikipedia REST API."""
        clean_name = entity_name.strip()
        if not clean_name:
            return None

        # Clean URLs if passed
        if clean_name.startswith(("http://", "https://", "www.")):
            domain = urllib.parse.urlparse(clean_name if "://" in clean_name else f"https://{clean_name}").netloc.lower()
            clean_name = domain.replace("www.", "").split(".")[0].capitalize()

        clean_name = clean_name.replace(" Official Portal", "").replace(" Portal", "").strip()
        resolved = clean_name

        try:
            # 1. Search Wikipedia for top matching entity title
            sr_resp = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": f"{resolved} company" if len(resolved.split()) == 1 else resolved,
                    "format": "json",
                    "utf8": 1,
                    "srlimit": 3,
                },
                headers={"User-Agent": "RAGOps-Corporate-Intelligence/1.0 (admin@ragops.local)"},
                timeout=self.timeout_sec,
            )
            if sr_resp.status_code == 200:
                items = sr_resp.json().get("query", {}).get("search", [])
                for item in items[:5]:
                    title = item.get("title", "")
                    if not title:
                        continue
                    page_slug = title.replace(" ", "_")
                    sum_resp = requests.get(
                        f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(page_slug)}",
                        headers={"User-Agent": "RAGOps-Corporate-Intelligence/1.0 (admin@ragops.local)"},
                        timeout=self.timeout_sec,
                    )
                    if sum_resp.status_code == 200:
                        d = sum_resp.json()
                        desc = (d.get("description") or "").lower()
                        extract = (d.get("extract") or "").strip()
                        # Reject human biographies, politicians, actors, athletes
                        non_corporate_indicators = [
                            "politician", "actor", "actress", "footballer", "sports manager",
                            "singer", "member of parliament", "minister", "athlete", "swimmer", "cyclist"
                        ]
                        if any(ind in desc for ind in non_corporate_indicators):
                            continue
                        if re.search(r"\b(born\s+\d{1,2}\s+[a-z]+|\(born\s+\d{4}\))\b", extract[:100], re.I):
                            continue
                        if extract:
                            return {
                                "title": title,
                                "url": f"https://en.wikipedia.org/wiki/{page_slug}",
                                "extract": extract,
                                "description": d.get("description", ""),
                                "source": "official_corporate_registry",
                            }
        except Exception as e:
            logger.debug("search_corporate_entity_failed", name=entity_name, error=str(e))
        return None

    def search_company_fact(self, company_name: str, fact_type: str) -> list[dict[str, str]]:
        """Targeted company research for specific factual categories."""
        results: list[dict[str, str]] = []

        # 1. First check corporate entity summary
        entity_info = self.search_corporate_entity(company_name)
        if entity_info and entity_info.get("extract"):
            results.append({
                "title": f"{entity_info['title']} - Corporate Registry",
                "url": entity_info["url"],
                "snippet": entity_info["extract"],
                "source": "official_corporate_registry",
            })

        # 2. Targeted search queries
        query_templates = {
            "leadership": f"{company_name} CEO leadership managing director chairman official",
            "headquarters": f"{company_name} headquarters location address city country",
            "locations": f"{company_name} corporate office locations facilities plants headquarters",
            "headcount": f"{company_name} total employees headcount workforce",
            "plants": f"{company_name} manufacturing plants facilities locations factories",
            "clients": f"{company_name} commercial clients OEM partners customers suppliers",
            "hubs": f"{company_name} logistics spare parts warehouse distribution hubs",
            "products": f"{company_name} products solutions services portfolio",
            "financials": f"{company_name} annual report revenue EBITDA financial results",
        }
        query = query_templates.get(fact_type, f"{company_name} {fact_type} official")
        web_results = self.search(query, max_results=3)
        for wr in web_results:
            if not any(r.get("url") == wr.get("url") for r in results):
                results.append(wr)
        return results[:4]

