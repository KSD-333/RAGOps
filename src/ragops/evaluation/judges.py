"""LLM-as-judge — use an LLM to evaluate RAG response quality.

Provides more accurate evaluation than heuristics for:
- Faithfulness (is the answer grounded in context?)
- Relevance (does the answer address the question?)
- Completeness (does the answer cover key information?)
"""

from __future__ import annotations

import json

from ragops.core.logging import get_logger
from ragops.generation.llm import GroqClient, LLMClient, MockLLMClient
from ragops.generation.prompts import build_evaluation_prompt

logger = get_logger(__name__)


class LLMJudge:
    """Use an LLM to evaluate RAG response quality.

    More accurate than heuristic methods but adds latency and cost.
    """

    def __init__(self, llm_client: LLMClient | None = None):
        if llm_client is not None:
            self._llm_client = llm_client
        else:
            try:
                self._llm_client = GroqClient()
            except Exception as e:
                logger.warning("llm_judge_fallback_to_mock", error=str(e))
                self._llm_client = MockLLMClient()


    def evaluate(
        self,
        question: str,
        answer: str,
        context: str,
    ) -> dict[str, float]:
        """Evaluate a RAG response using the LLM as judge.

        Returns a dict with scores:
        - faithfulness: 0.0 to 1.0
        - relevance: 0.0 to 1.0
        - completeness: 0.0 to 1.0
        """
        prompt = build_evaluation_prompt(question, answer, context)

        try:
            response = self._llm_client.generate(
                system_prompt="You are an expert evaluator. Respond only in the requested JSON format.",
                user_prompt=prompt,
                temperature=0.0,
                max_tokens=500,
            )

            # Parse the JSON response
            scores = self._parse_scores(response.text)

            logger.debug(
                "llm_judge_evaluation",
                faithfulness=scores.get("faithfulness", 0),
                relevance=scores.get("relevance", 0),
                completeness=scores.get("completeness", 0),
            )

            return scores

        except Exception as e:
            logger.error("llm_judge_failed", error=str(e))
            return {
                "faithfulness": 0.0,
                "relevance": 0.0,
                "completeness": 0.0,
                "error": str(e),
            }

    def _parse_scores(self, text: str) -> dict[str, float]:
        """Parse LLM judge response into score dict."""
        try:
            # Try to extract JSON from the response
            # Handle cases where LLM wraps JSON in markdown code blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text.strip())
            return {
                "faithfulness": float(data.get("faithfulness", 0)),
                "relevance": float(data.get("relevance", 0)),
                "completeness": float(data.get("completeness", 0)),
            }
        except (json.JSONDecodeError, ValueError, IndexError):
            logger.warning("failed_to_parse_judge_response", response=text[:200])
            return {"faithfulness": 0.0, "relevance": 0.0, "completeness": 0.0}
