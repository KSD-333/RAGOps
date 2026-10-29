"""Security utilities for prompt-injection defense and untrusted content sanitization."""

from __future__ import annotations

import re
from typing import Tuple
from bs4 import BeautifulSoup, Comment

from ragops.core.logging import get_logger

logger = get_logger(__name__)

# Heuristic prompt injection patterns targeting LLM instruction hijacking
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+|previous\s+|prior\s+|above\s+)?instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+|previous\s+|prior\s+|above\s+)?instructions", re.IGNORECASE),
    re.compile(r"forget\s+(all\s+|previous\s+|prior\s+)?instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(an?\s+)?(unrestricted|jailbroken|dan|evil|admin|new)", re.IGNORECASE),
    re.compile(r"system\s+prompt\s*:", re.IGNORECASE),
    re.compile(r"override\s+(all\s+|system\s+)?rules", re.IGNORECASE),
    re.compile(r"new\s+instructions\s*:", re.IGNORECASE),
    re.compile(r"administrative\s+override", re.IGNORECASE),
    re.compile(r"do\s+not\s+follow\s+(the\s+)?(system|above|previous)", re.IGNORECASE),
    re.compile(r"bypass\s+all\s+(filters|guardrails|safety)", re.IGNORECASE),
    re.compile(r"<script.*?>", re.IGNORECASE),
]


def detect_prompt_injection(text: str) -> Tuple[bool, str]:
    """Scan candidate text for known prompt-injection or instruction-override attempts.

    Returns:
        (is_flagged, reason_description)
    """
    if not text:
        return False, ""

    clean = str(text)
    for pattern in PROMPT_INJECTION_PATTERNS:
        match = pattern.search(clean)
        if match:
            reason = f"Suspicious instruction pattern detected: '{match.group(0)}'"
            logger.warning("prompt_injection_pattern_detected", pattern=match.group(0))
            return True, reason

    return False, ""


def sanitize_crawled_html(raw_html: str, max_chars: int = 8000) -> str:
    """Sanitize raw HTML from web crawlers or user uploads:

    1. Decomposes HTML comments (<!-- hidden payload -->).
    2. Decomposes script, style, noscript, svg, form, iframe, and embed elements.
    3. Strips hidden DOM nodes (hidden attribute, aria-hidden, style=display:none, visibility:hidden).
    4. Normalizes whitespace and caps length.
    """
    if not raw_html:
        return ""

    try:
        soup = BeautifulSoup(raw_html, "html.parser")

        # 1. Strip comments
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            comment.extract()

        # 2. Decompose dangerous & non-content tags
        dangerous_tags = [
            "script", "style", "noscript", "svg", "header", "footer",
            "nav", "aside", "form", "iframe", "object", "embed"
        ]
        for tag in soup(dangerous_tags):
            tag.decompose()

        # 3. Strip hidden elements
        for tag in soup.find_all(attrs={"hidden": True}):
            tag.decompose()
        for tag in soup.find_all(attrs={"aria-hidden": "true"}):
            tag.decompose()

        for tag in soup.find_all(style=True):
            style = str(tag.get("style", "")).lower().replace(" ", "")
            if (
                "display:none" in style
                or "visibility:hidden" in style
                or "opacity:0" in style
                or "font-size:0" in style
            ):
                tag.decompose()

        # 4. Clean content text
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        full_text = "\n".join(lines)
        full_text = re.sub(r"\n{3,}", "\n\n", full_text)

        # 5. Cap length
        return full_text[:max_chars]

    except Exception as e:
        logger.warning("html_sanitization_fallback", error=str(e))
        return raw_html[:max_chars]

