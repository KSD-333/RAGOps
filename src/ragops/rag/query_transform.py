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

        Removes common question prefixes and stopwords while
        preserving technical terms and key content.
        """
        # Remove common question prefixes
        prefixes = [
            r"^(can you |could you |please |how do i |how to |what is |what are |tell me about |explain )",
        ]
        optimized = query
        for pattern in prefixes:
            optimized = re.sub(pattern, "", optimized, flags=re.IGNORECASE)

        # Remove question marks and excess whitespace
        optimized = optimized.replace("?", "").strip()
        optimized = re.sub(r"\s+", " ", optimized)

        # If optimization made the query too short, use original
        if len(optimized.split()) < 2:
            return query

        return optimized
