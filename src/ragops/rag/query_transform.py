"""Query transformer — process user queries before retrieval.

Flow: QueryRequest → QueryTransformer → ProcessedQuery

Keeps both original query (for generation/tracing) and
optimized search query (for retrieval).
"""

from __future__ import annotations

import re

from ragops.core.logging import get_logger
from ragops.core.types import ProcessedQuery, QueryRequest

logger = get_logger(__name__)


class QueryTransformer:
    """Transform user queries for better retrieval.

    Handles:
    - Stopword removal for search optimization
    - Query expansion/rewriting (future)
    - Filter extraction from natural language (future)
    """

    # Common stopwords that hurt vector search
    _STOPWORDS = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "can", "shall",
        "i", "me", "my", "we", "our", "you", "your", "he", "she",
        "it", "they", "them", "what", "which", "who", "whom",
        "this", "that", "these", "those", "how", "please", "help",
        "tell", "explain", "describe",
    }

    TYPO_CORRECTIONS: dict[str, str] = {
        r"\bcrate\b": "create",
        r"\bcrating\b": "creating",
        r"\bloaction\b": "location",
        r"\bloactions\b": "locations",
        r"\blocatons\b": "locations",
        r"\blocatoin\b": "location",
        r"\bpolies\b": "policies",
        r"\bpolices\b": "policies",
        r"\bploicy\b": "policy",
        r"\bdocumnet\b": "document",
        r"\bdocumnets\b": "documents",
        r"\bagnet\b": "agent",
        r"\bagentss\b": "agents",
        r"\bretrival\b": "retrieval",
        r"\bretriv\b": "retrieve",
        r"\bembeding\b": "embedding",
        r"\bembedings\b": "embeddings",
    }

    def transform(self, request: QueryRequest) -> ProcessedQuery:
        """Transform a query request into a processed query.

        Preserves the original query for generation and tracing,
        while creating an optimized search query for retrieval.
        """
        original = request.query.strip()

        # Create search-optimized query
        search_query = self._optimize_for_search(original)

        processed = ProcessedQuery(
            original=original,
            search_query=search_query,
            filters=request.filters,
        )

        logger.debug(
            "query_transformed",
            original=original[:80],
            search_query=search_query[:80],
        )

        return processed

    def _optimize_for_search(self, query: str) -> str:
        """Create a search-optimized version of the query.

        Removes colloquial fillers, common question prefixes, and common typos while
        preserving technical terms and key content.
        """
        optimized = query

        # 1. Correct common typos in search queries
        for pattern, replacement in self.TYPO_CORRECTIONS.items():
            optimized = re.sub(pattern, replacement, optimized, flags=re.IGNORECASE)

        # 2. Repeatedly strip colloquial fillers and question prefixes
        filler_pattern = (
            r"^(?:like|so|and|then|also|bro|plz|please|hey|hi|hlo|can you|could you|"
            r"tell me about|tell me|what is|what are|how do i|how to|explain)\s+"
        )
        while re.search(filler_pattern, optimized, flags=re.IGNORECASE):
            optimized = re.sub(filler_pattern, "", optimized, flags=re.IGNORECASE)

        # Remove question marks and excess whitespace
        optimized = optimized.replace("?", "").strip()
        optimized = re.sub(r"\s+", " ", optimized)

        # If optimization made the query too short (< 2 tokens), fallback to cleaned query
        if len(optimized.split()) < 2:
            cleaned_orig = query.replace("?", "").strip()
            for pattern, replacement in self.TYPO_CORRECTIONS.items():
                cleaned_orig = re.sub(pattern, replacement, cleaned_orig, flags=re.IGNORECASE)
            return cleaned_orig if len(cleaned_orig.split()) >= 1 else query

        return optimized
