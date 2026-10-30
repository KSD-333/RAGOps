"""Unit tests for IntentRouter — verifying 30+ greeting, smalltalk, Hinglish, typo, and question variations."""

import pytest
from ragops.rag.intent_router import IntentRouter, normalize_intent_text


@pytest.fixture
def router():
    return IntentRouter()


def test_normalize_intent_text():
    assert normalize_intent_text("Hiiiii!!!") == "hi"
    assert normalize_intent_text("hloooo bro") == "hlo bro"
    assert normalize_intent_text("Namaste!!") == "namaste"
    assert normalize_intent_text("Thanks a lot...") == "thanks a lot"


def test_greeting_phrases(router):
    greetings = [
        "hi",
        "hii",
        "hiii",
        "hello",
        "hlo",
        "hlooo",
        "hey bro",
        "hii bro",
        "hlo bro",
        "hey bhai",
        "namaste",
        "namaskar",
        "kya haal",
        "kya haal hai",
        "good morning",
        "good evening",
        "howdy",
        "sup",
        "salaam",
        "ram ram",
    ]
    for phrase in greetings:
        res = router.route(phrase)
        assert res.intent == "greeting", f"Failed for phrase: '{phrase}', got {res.intent}"


def test_smalltalk_phrases(router):
    smalltalk = [
        "thanks",
        "thank you",
        "thx",
        "ty",
        "shukriya",
        "dhanyawad",
        "bye",
        "goodbye",
        "tata",
        "how are you",
        "how r u",
        "kaise ho",
        "ok",
        "okay",
        "cool",
        "got it",
        "sahi hai",
        "theek hai",
        "lol",
        "haha",
    ]
    for phrase in smalltalk:
        res = router.route(phrase)
        assert res.intent == "smalltalk", f"Failed for phrase: '{phrase}', got {res.intent}"


def test_identity_phrases(router):
    identity = [
        "who are you",
        "who r u",
        "what are you",
        "tum kaun ho",
        "what can you do",
        "help",
        "help me",
        "introduce yourself",
    ]
    for phrase in identity:
        res = router.route(phrase)
        assert res.intent == "identity", f"Failed for phrase: '{phrase}', got {res.intent}"


def test_general_question_phrases(router):
    general = [
        "what is kubernetes",
        "what is docker",
        "explain photosynthesis",
        "who won the world cup in 2022",
        "how do airplanes generate lift",
    ]
    for phrase in general:
        res = router.route(phrase)
        assert res.intent == "general_question", f"Failed for phrase: '{phrase}', got {res.intent}"


def test_kb_question_phrases(router):
    kb = [
        "What embedding model is used by default in RAGOps?",
        "What are the promotion criteria in operations runbook?",
        "What is the POSH harassment reporting policy?",
        "How is authentication handled in security handbook?",
        "Where are manufacturing facilities located?",
    ]
    for phrase in kb:
        res = router.route(phrase)
        assert res.intent == "kb_question", f"Failed for phrase: '{phrase}', got {res.intent}"
