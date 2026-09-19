"""
Test Question Classification Agent (deterministic fallback and schema validation).
"""
from agents.classifier import QuestionClassifier
from llm.schemas import StudentIntent


def test_classify_adaptive_binary_search():
    classifier = QuestionClassifier()
    res = classifier.classify("Why does left++ fail in binary search?")
    assert res.domain == "binary_search"
    assert res.topic == "binary_search"
    assert res.subconcept == "boundary_update"
    assert res.adaptive is True
    assert res.intent in (StudentIntent.CONCEPTUAL_CONFUSION, StudentIntent.WRONG_ANSWER)


def test_classify_general_explanation():
    classifier = QuestionClassifier()
    res = classifier.classify("What is binary search?")
    assert res.topic == "binary_search"
    assert res.adaptive is False
    assert res.intent == StudentIntent.GENERAL_EXPLANATION


def test_classify_unknown_topic():
    classifier = QuestionClassifier()
    res = classifier.classify("Can you explain Tarjan's strongly connected components algorithm?")
    # Must not crash or fail merely because topic is unlisted
    assert res is not None
    assert isinstance(res.reasoning, str)
