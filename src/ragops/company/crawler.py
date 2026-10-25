"""Universal Multi-Page Crawler for corporate website intelligence."""

from __future__ import annotations

import re
import urllib.parse
from typing import Optional
import requests
from bs4 import BeautifulSoup

from ragops.company.schema import CrawledPageDoc
from ragops.core.logging import get_logger

logger = get_logger(__name__)

CRAWLER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}

PAGE_PRIORITY_PATTERNS = [
    (re.compile(r"/(about|who-we-are|company-profile|overview|about-us)", re.I), "identity"),
    (re.compile(r"/(location|plants|presence|facilities|worldwide|global-presence|manufacturing)", re.I), "locations"),
    (re.compile(r"/(product|solutions|portfolio|offerings|systems)", re.I), "products"),
    (re.compile(r"/(leadership|management|directors|governance|executives)", re.I), "identity"),
    (re.compile(r"/(spares|spare-parts|aftersales|logistics|distribution|driveservice)", re.I), "hubs"),
    (re.compile(r"/(clients|partners|oem|customers)", re.I), "clients"),
    (re.compile(r"/(innovation|technology|r-and-d|research|electrification)", re.I), "innovation"),
    (re.compile(r"/(contact|offices|reach-us)", re.I), "contacts"),
    (re.compile(r"/(investors|financials|annual-report|reports)", re.I), "financials"),
]


class UniversalCompanyCrawler:
    """Universal multi-page web crawler and internal link discoverer.
    
    Traverses any enterprise corporate domain, discovers high-value informative subpages
    (About, Locations, Products, Leadership, Spares, Contacts), cleans DOM trees,
    and produces versioned text representations.
    """

    def __init__(self, timeout_sec: int = 12, max_pages: int = 7, max_chars_per_page: int = 8000):
        self.timeout_sec = timeout_sec
        self.max_pages = max_pages
        self.max_chars_per_page = max_chars_per_page

    def crawl_website(self, entry_url: str) -> list[CrawledPageDoc]:
        """Crawl the entry page and autonomously discover and fetch the most relevant internal subpages."""
        clean_entry = entry_url.strip()
        if not clean_entry.startswith(("http://", "https://")):
            clean_entry = "https://" + clean_entry

        parsed_entry = urllib.parse.urlparse(clean_entry)
        base_domain = parsed_entry.netloc.lower()
        if base_domain.startswith("www."):
            base_domain = base_domain[4:]

        logger.info("universal_crawler_started", entry_url=clean_entry, domain=base_domain)

        visited_urls: set[str] = set()
        crawled_docs: list[CrawledPageDoc] = []

        # First pass: fetch entry page and extract internal links
        first_doc, discovered_links = self._fetch_and_discover_links(clean_entry, base_domain)
        visited_urls.add(self._normalize_url(clean_entry))

        if first_doc:
            crawled_docs.append(first_doc)

        # Categorize and prioritize discovered links
        prioritized_links = self._prioritize_links(discovered_links, base_domain, visited_urls)

        # Crawl prioritized subpages up to max_pages
        for link_url, section_hint in prioritized_links:
            if len(crawled_docs) >= self.max_pages:
                break
            norm_link = self._normalize_url(link_url)
            if norm_link in visited_urls:
                continue

            visited_urls.add(norm_link)
            doc, more_links = self._fetch_and_discover_links(link_url, base_domain)
            if doc:
                doc.matched_section = section_hint
                crawled_docs.append(doc)

        logger.info(
            "universal_crawler_finished",
            entry_url=clean_entry,
            pages_crawled=len(crawled_docs),
            urls=[d.url for d in crawled_docs],
        )
        return crawled_docs

    def _fetch_and_discover_links(self, url: str, base_domain: str) -> tuple[Optional[CrawledPageDoc], list[str]]:
        """Fetch page text and extract raw internal hrefs."""
        raw_html = ""
        clean_url = url.strip()

        try:
            resp = requests.get(clean_url, headers=CRAWLER_HEADERS, timeout=self.timeout_sec, allow_redirects=True)
            if resp.text and len(resp.text) > 300:
                raw_html = resp.text
            else:
                resp.raise_for_status()
                raw_html = resp.text
        except requests.exceptions.SSLError:
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                resp = requests.get(clean_url, headers=CRAWLER_HEADERS, timeout=self.timeout_sec, verify=False, allow_redirects=True)
                raw_html = resp.text
            except Exception as ssl_err:
                logger.warning("crawler_ssl_retry_failed", url=clean_url, error=str(ssl_err))
                return None, []
        except Exception as e:
            logger.warning("crawler_fetch_failed", url=clean_url, error=str(e))
            return None, []

        if not raw_html:
            return None, []

        try:
            soup = BeautifulSoup(raw_html, "html.parser")

            # Extract title
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else clean_url

            # Discover internal links before stripping tags
            discovered_links: list[str] = []
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].strip()
                if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue
                full_url = urllib.parse.urljoin(clean_url, href)
                parsed = urllib.parse.urlparse(full_url)
                link_domain = parsed.netloc.lower()
                if link_domain.startswith("www."):
                    link_domain = link_domain[4:]

                # Check if it belongs to same company domain
                if base_domain in link_domain or link_domain in base_domain:
                    # Exclude assets and file downloads
                    if not re.search(r"\.(pdf|png|jpg|jpeg|gif|svg|zip|mp4|exe)$", parsed.path, re.I):
                        discovered_links.append(full_url.split("#")[0])

            # Strip non-content DOM elements
            for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "aside", "form"]):
                tag.decompose()

            # Clean content text
            text = soup.get_text(separator="\n")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            full_text = "\n".join(lines)
            full_text = re.sub(r"\n{3,}", "\n\n", full_text)
            truncated_text = full_text[: self.max_chars_per_page]

            doc = CrawledPageDoc(
                url=clean_url,
                title=title,
                clean_text=truncated_text,
                char_count=len(truncated_text),
                matched_section=None,
            )
            return doc, discovered_links

        except Exception as parse_err:
            logger.warning("crawler_parse_failed", url=clean_url, error=str(parse_err))
            return None, []

    def _prioritize_links(self, links: list[str], base_domain: str, visited: set[str]) -> list[tuple[str, str]]:
        """Categorize links and pick the highest-priority subpages covering diverse sections."""
        scored: list[tuple[int, str, str]] = []
        seen = set(visited)

        for link in links:
            norm = self._normalize_url(link)
            if norm in seen:
                continue
            seen.add(norm)

            parsed = urllib.parse.urlparse(link)
            path = parsed.path.lower()

            priority = 10
            section = "overview"

            for pattern, sec_name in PAGE_PRIORITY_PATTERNS:
                if pattern.search(path):
                    priority = 1
                    section = sec_name
                    break

            if priority == 10 and any(kw in path for kw in ["info", "history", "group", "facilities", "site"]):
                priority = 3
                section = "general"

            if priority <= 3:
                scored.append((priority, link, section))

        # Sort by priority score
        scored.sort(key=lambda x: x[0])
        return [(url, sec) for _, url, sec in scored]

    def _normalize_url(self, url: str) -> str:
        """Strip trailing slash and normalize URL scheme/host."""
        parsed = urllib.parse.urlparse(url.strip())
        path = parsed.path.rstrip("/")
        return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"
