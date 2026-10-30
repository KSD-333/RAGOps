"""Lightweight Intent Router — fast regex, keyword, and length-based intent classifier.

Runs in <5ms without calling the LLM.

Intents:
- `greeting`: friendly salutations (English & Hinglish: "hi", "hii", "hlo", "hey bro", "namaste", "kya haal", etc.)
- `smalltalk`: polite chitchat, acknowledgments, exits ("thanks", "bye", "how are you", "ok", "lol", "thx")
- `identity`: system capability & identity queries ("who are you", "what can you do", "help", "about yourself")
- `general_question`: open-domain questions not referencing documents ("what is Kubernetes?", "explain photosynthesis")
- `kb_question`: corporate knowledge base inquiry (default RAG flow)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ragops.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RoutedIntent:
    """Result of intent classification."""
    intent: str  # "greeting" | "smalltalk" | "identity" | "general_question" | "kb_question"
    normalized_query: str
    confidence: float
    metadata: dict[str, Any]


def normalize_intent_text(text: str) -> str:
    """Normalize input text by lowercasing, stripping punctuation, and collapsing repeated characters.
    
    Examples:
    - 'Hiiiii!!!' -> 'hi'
    - 'hloooo bro' -> 'hlo bro'
    - 'Namaste!!' -> 'namaste'
    - 'Thx...' -> 'thx'
    """
    if not text:
        return ""
    # Lowercase & strip
    cleaned = text.strip().lower()
    # Strip non-alphanumeric except spaces
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    # Collapse 3+ consecutive duplicate characters to at most 1 or 2 (e.g. 'hiiii' -> 'hi', 'hlooo' -> 'hlo')
    cleaned = re.sub(r"(.)\1{2,}", r"\1", cleaned)
    # Collapse multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class IntentRouter:
    """Ultra-fast, deterministic rule-based intent router (<5ms execution)."""

    GREETING_PATTERNS = [
        r"^h+i+$",
        r"^h+e+y+$",
        r"^h+e+l+l+o+$",
        r"^h+l+o+$",
        r"^h+e+y+\s+(bro|bhai|buddy|there|assistant|bot|friend)$",
        r"^h+i+\s+(bro|bhai|buddy|there|assistant|bot|friend)$",
        r"^h+l+o+\s+(bro|bhai|buddy|there|assistant|bot|friend)$",
        r"^hello\s+(bro|bhai|buddy|there|assistant|bot|friend)$",
        r"^good\s+(morning|afternoon|evening|day)$",
        r"^greetings$",
        r"^howdy$",
        r"^sup$",
        r"^namaste$",
        r"^namaskar$",
        r"^vanakkam$",
        r"^kya\s+haal$",
        r"^kya\s+haal\s+hai$",
        r"^salaam$",
        r"^ram\s+ram$",
    ]

    SMALLTALK_PATTERNS = [
        r"^(thanks|thank\s+you|thx|ty|thanks\s+a\s+lot|thank\s+you\s+so\s+much|many\s+thanks|appreciate\s+it|shukriya|dhanyawad)$",
        r"^(bye|goodbye|see\s+you|cya|tata|alvida)$",
        r"^(how\s+are\s+you|how\s+r\s+u|how\s+are\s+u|how\s+is\s+it\s+going|kaise\s+ho|kaisa\s+hai)$",
        r"^(ok|okay|k|cool|got\s+it|fine|alright|sure|nice|great|awesome|sahi\s+hai|theek\s+hai|acha)$",
        r"^(lol|haha|lmao|rofl|hehe)$",
    ]

    IDENTITY_PATTERNS = [
        r"^(who\s+are\s+you|who\s+r\s+u|what\s+are\s+you|tum\s+kaun\s+ho|aap\s+kaun\s+hain)$",
        r"^(what\s+can\s+you\s+do|what\s+do\s+you\s+do|tum\s+kya\s+kar\s+sakte\s+ho)$",
        r"^(help|help\s+me|madad|madad\s+karo)$",
        r"^tell\s+me\s+about\s+yourself$",
        r"^introduce\s+yourself$",
    ]

    GENERAL_QUESTION_INDICATORS = [
        r"^what\s+is\s+(kubernetes|docker|react|python|ai|quantum\s+computing|photosynthesis|gravity|dna|machine\s+learning|blockchain)",
        r"^explain\s+(kubernetes|docker|react|python|photosynthesis|relativity|quantum\s+physics)",
        r"^who\s+(won|invented|discovered|wrote)\s+",
        r"^how\s+(does|do)\s+(airplanes?|photons?|gravity|cellular\s+respiration)\s+",
        r"^capital\s+of\s+[a-z]+$",
        r"^recipe\s+for\s+",
    ]

    def __init__(self) -> None:
        self._compiled_greetings = [re.compile(p, re.IGNORECASE) for p in self.GREETING_PATTERNS]
        self._compiled_smalltalk = [re.compile(p, re.IGNORECASE) for p in self.SMALLTALK_PATTERNS]
        self._compiled_identity = [re.compile(p, re.IGNORECASE) for p in self.IDENTITY_PATTERNS]
        self._compiled_general = [re.compile(p, re.IGNORECASE) for p in self.GENERAL_QUESTION_INDICATORS]

    def route(self, query: str) -> RoutedIntent:
        """Classify query intent with priority rules."""
        raw = query.strip()
        norm = normalize_intent_text(raw)

        if not norm:
            return RoutedIntent(intent="greeting", normalized_query="", confidence=1.0, metadata={"rule": "empty"})

        # 1. Check Identity
        for pattern in self._compiled_identity:
            if pattern.search(norm):
                return RoutedIntent(intent="identity", normalized_query=norm, confidence=1.0, metadata={"rule": "identity_regex"})

        # 2. Check Greetings
        for pattern in self._compiled_greetings:
            if pattern.search(norm):
                return RoutedIntent(intent="greeting", normalized_query=norm, confidence=1.0, metadata={"rule": "greeting_regex"})

        # 3. Check Smalltalk
        for pattern in self._compiled_smalltalk:
            if pattern.search(norm):
                return RoutedIntent(intent="smalltalk", normalized_query=norm, confidence=1.0, metadata={"rule": "smalltalk_regex"})

        # 4. Short non-numeric single token heuristic (e.g., 'yo', 'hye', 'heyy', 'namashkar')
        tokens = norm.split()
        if len(tokens) == 1 and len(norm) <= 4 and norm in ("yo", "hye", "hii", "hlo", "hey", "hola", "sup"):
            return RoutedIntent(intent="greeting", normalized_query=norm, confidence=0.95, metadata={"rule": "short_token_greeting"})

        # 5. Check General Open-Domain Question Indicators
        for pattern in self._compiled_general:
            if pattern.search(norm):
                return RoutedIntent(intent="general_question", normalized_query=norm, confidence=0.90, metadata={"rule": "general_regex"})

        # 6. Default to Document / KB inquiry
        return RoutedIntent(intent="kb_question", normalized_query=norm, confidence=0.85, metadata={"rule": "default_kb"})
