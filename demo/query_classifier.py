"""Query Classifier for The Boundary Loop: DSA Learning Tutor.

Deterministically classifies student input using keyword/regex matching.
No LLM is used — classification is fast and fully testable offline.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .concept_registry import CONCEPTS, get_concept


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

@dataclass
class QueryClassification:
    """Result of classifying a student query."""

    scope: str           # "DSA" | "OUT_OF_SCOPE"
    concept_id: str | None  # matched DSA concept id, or None
    query_type: str      # "CODE_SUBMISSION" | "MISCONCEPTION_REQUIRES_DIAGNOSIS" |
                         # "GENERAL_QUESTION" | "CONCEPTUAL_DOUBT" | "UNKNOWN"
    confidence: float    # 0.0 – 1.0
    matched_keywords: list[str]  # keywords that drove the match


# ---------------------------------------------------------------------------
# Code-pattern detection
# ---------------------------------------------------------------------------

# Patterns that strongly suggest code is present
_CODE_FENCE_RE = re.compile(r"```", re.IGNORECASE)
_DEF_RE = re.compile(r"\bdef\s+\w+\s*\(", re.IGNORECASE)
_WHILE_RE = re.compile(r"\bwhile\b", re.IGNORECASE)
_FOR_RE = re.compile(r"\bfor\s+\w+\s+in\b", re.IGNORECASE)
_ASSIGNMENT_RE = re.compile(r"\b\w+\s*(\+|-|\*|/)?=\s*[\w\d]+", re.IGNORECASE)
_INDENT_BLOCK_RE = re.compile(r"^\s{4,}", re.MULTILINE)

# Concept-specific code fingerprints: (concept_id, pattern_list)
_CONCEPT_CODE_PATTERNS: list[tuple[str, list[re.Pattern]]] = [
    (
        "binary_search",
        [
            re.compile(r"\bnums\s*\[\s*mid\s*\]", re.IGNORECASE),
            re.compile(r"\bmid\s*=\s*.*left.*right", re.IGNORECASE),
            re.compile(r"\bleft\s*=\s*(left|mid)\s*[+\-]\s*1", re.IGNORECASE),
            re.compile(r"\bright\s*=\s*(right|mid)\s*[+\-]\s*1", re.IGNORECASE),
            re.compile(r"\bleft\s*\+\+|\bright\s*--", re.IGNORECASE),
            re.compile(r"\bbisect\b", re.IGNORECASE),
            re.compile(r"binary.?search", re.IGNORECASE),
        ],
    ),
    (
        "two_pointers",
        [
            re.compile(r"\bleft\b.*\bright\b.*sorted", re.IGNORECASE),
            re.compile(r"\btwo.?pointer", re.IGNORECASE),
            re.compile(r"\bnums\[left\]\s*\+\s*nums\[right\]", re.IGNORECASE),
            re.compile(r"\bcontainer.*water", re.IGNORECASE),
            re.compile(r"\btwo.?sum.*sorted", re.IGNORECASE),
            re.compile(r"\bwhile.*\bleft\s*<\s*right\b", re.IGNORECASE),
        ],
    ),
    (
        "sliding_window",
        [
            re.compile(r"\bsliding.?window", re.IGNORECASE),
            re.compile(r"\bwindow\b.*\bleft\b.*\bright\b", re.IGNORECASE),
            re.compile(r"\blongest.?substring", re.IGNORECASE),
            re.compile(r"\bsubarray.?sum\b", re.IGNORECASE),
            re.compile(r"\bif\s+\w+\s*>\s*k\s*:\s*left\s*\+=", re.IGNORECASE),
            re.compile(r"\bwhile\s+\w+\s*>\s*\w+\s*:\s*left", re.IGNORECASE),
        ],
    ),
    (
        "graph",
        [
            re.compile(r"\bbfs\b|\bdfs\b", re.IGNORECASE),
            re.compile(r"\badjacency.?list", re.IGNORECASE),
            re.compile(r"\bvisited\s*=\s*set\b", re.IGNORECASE),
            re.compile(r"\bdeque\b.*\bappend\b", re.IGNORECASE),
        ],
    ),
    (
        "dynamic_programming",
        [
            re.compile(r"\bdp\s*\[", re.IGNORECASE),
            re.compile(r"\bmemoiz", re.IGNORECASE),
            re.compile(r"\b@\s*cache\b|\b@\s*lru_cache\b", re.IGNORECASE),
            re.compile(r"\bknapsack\b|\blcs\b|\blongest.?common", re.IGNORECASE),
        ],
    ),
    (
        "stack",
        [
            re.compile(r"\bmonotonic.?stack\b", re.IGNORECASE),
            re.compile(r"\bstack\.append\b|\bstack\.pop\b", re.IGNORECASE),
            re.compile(r"\bvalid.?parentheses\b|\bmatching.?brackets\b", re.IGNORECASE),
        ],
    ),
    (
        "heap",
        [
            re.compile(r"\bheapq\b|\bheap\b", re.IGNORECASE),
            re.compile(r"\btop.?k\b|\bkth.?largest\b|\bkth.?smallest\b", re.IGNORECASE),
        ],
    ),
    (
        "linked_list",
        [
            re.compile(r"\bListNode\b|\bhead\.next\b", re.IGNORECASE),
            re.compile(r"\bsingly.?linked\b|\bdoubly.?linked\b", re.IGNORECASE),
        ],
    ),
    (
        "recursion",
        [
            re.compile(r"\brecursive\b|\brecursion\b|\bbase.?case\b", re.IGNORECASE),
        ],
    ),
    (
        "prefix_sum",
        [
            re.compile(r"\bprefix.?sum\b|\bcumulative.?sum\b", re.IGNORECASE),
            re.compile(r"\brange.?sum.?query\b", re.IGNORECASE),
        ],
    ),
]

# ---------------------------------------------------------------------------
# General-question patterns
# ---------------------------------------------------------------------------

_GENERAL_QUESTION_PATTERNS = [
    re.compile(r"\bwhat\s+is\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+are\b", re.IGNORECASE),
    re.compile(r"\bhow\s+does\b", re.IGNORECASE),
    re.compile(r"\bhow\s+do\b", re.IGNORECASE),
    re.compile(r"\bexplain\b", re.IGNORECASE),
    re.compile(r"\bcan\s+you\s+explain\b", re.IGNORECASE),
    re.compile(r"\btime\s+complexity\b", re.IGNORECASE),
    re.compile(r"\bspace\s+complexity\b", re.IGNORECASE),
    re.compile(r"\bbig.?o\b", re.IGNORECASE),
    re.compile(r"\bwhen\s+(to\s+use|should\s+i\s+use)\b", re.IGNORECASE),
    re.compile(r"\bwhy\s+(is|does|do)\b", re.IGNORECASE),
    re.compile(r"\bdifference\s+between\b", re.IGNORECASE),
    re.compile(r"\bdefine\b", re.IGNORECASE),
    re.compile(r"\bmeaning\s+of\b", re.IGNORECASE),
    re.compile(r"\badvantage\b|\bdisadvantage\b", re.IGNORECASE),
]

# Out-of-scope: not a DSA question
_OUT_OF_SCOPE_PATTERNS = [
    re.compile(r"\bweather\b|\brecipe\b|\bcook\b|\bfood\b", re.IGNORECASE),
    re.compile(r"\bpolitics\b|\bsoccer\b|\bfootball\b|\bbasketball\b", re.IGNORECASE),
    re.compile(r"\brelationship\b|\bmarriage\b|\bdating\b", re.IGNORECASE),
    re.compile(r"\bjoke\b|\btell\s+me\s+a\s+story\b", re.IGNORECASE),
]


def _looks_like_code(text: str) -> bool:
    """Return True if text contains recognizable code patterns."""
    if _CODE_FENCE_RE.search(text):
        return True
    if _DEF_RE.search(text):
        return True
    if _INDENT_BLOCK_RE.search(text) and _WHILE_RE.search(text):
        return True
    code_signals = sum([
        bool(_WHILE_RE.search(text)),
        bool(_FOR_RE.search(text)),
        bool(_ASSIGNMENT_RE.search(text)),
        bool(_INDENT_BLOCK_RE.search(text)),
    ])
    return code_signals >= 2


def _detect_concept_from_code(text: str) -> tuple[str | None, list[str]]:
    """Detect concept from code fingerprints. Returns (concept_id, matched_keywords)."""
    best_concept: str | None = None
    best_count = 0
    best_keywords: list[str] = []

    for concept_id, patterns in _CONCEPT_CODE_PATTERNS:
        matched = [p.pattern for p in patterns if p.search(text)]
        if len(matched) > best_count:
            best_count = len(matched)
            best_concept = concept_id
            best_keywords = matched

    return best_concept, best_keywords


def _detect_concept_from_keywords(text: str) -> tuple[str | None, list[str]]:
    """Detect concept from concept registry keywords (for general questions)."""
    text_lower = text.lower()
    best_concept: str | None = None
    best_score = 0
    best_keywords: list[str] = []

    for concept_id, concept in CONCEPTS.items():
        matched = [kw for kw in concept.keywords if kw.lower() in text_lower]
        if len(matched) > best_score:
            best_score = len(matched)
            best_concept = concept_id
            best_keywords = matched

    return best_concept, best_keywords


def classify_query(text: str) -> QueryClassification:
    """Classify a student query into scope, concept, and query type.

    Uses deterministic keyword/regex matching — no LLM involved.
    Priority order:
      1. Out-of-scope rejection
      2. Code submission detection (concept from fingerprints)
      3. General question detection (concept from keyword registry)
      4. Unknown / fallback
    """
    if not text or not text.strip():
        return QueryClassification(
            scope="OUT_OF_SCOPE",
            concept_id=None,
            query_type="UNKNOWN",
            confidence=0.0,
            matched_keywords=[],
        )

    stripped = text.strip()

    # 1. Out-of-scope check
    for pattern in _OUT_OF_SCOPE_PATTERNS:
        if pattern.search(stripped):
            return QueryClassification(
                scope="OUT_OF_SCOPE",
                concept_id=None,
                query_type="UNKNOWN",
                confidence=0.9,
                matched_keywords=[pattern.pattern],
            )

    # 2. Code submission detection
    if _looks_like_code(stripped):
        concept_id, kws = _detect_concept_from_code(stripped)
        if concept_id:
            concept = get_concept(concept_id)
            has_misconception = bool(concept and concept.supported_misconceptions)
            return QueryClassification(
                scope="DSA",
                concept_id=concept_id,
                query_type=(
                    "MISCONCEPTION_REQUIRES_DIAGNOSIS"
                    if has_misconception
                    else "CODE_SUBMISSION"
                ),
                confidence=min(0.5 + 0.1 * len(kws), 0.95),
                matched_keywords=kws,
            )
        # Code detected but concept unknown
        return QueryClassification(
            scope="DSA",
            concept_id=None,
            query_type="CODE_SUBMISSION",
            confidence=0.6,
            matched_keywords=[],
        )

    # 3. General / conceptual question detection
    general_matches = [
        p.pattern for p in _GENERAL_QUESTION_PATTERNS if p.search(stripped)
    ]
    if general_matches:
        concept_id, kws = _detect_concept_from_keywords(stripped)
        return QueryClassification(
            scope="DSA" if concept_id else "OUT_OF_SCOPE",
            concept_id=concept_id,
            query_type="GENERAL_QUESTION" if concept_id else "UNKNOWN",
            confidence=min(0.5 + 0.1 * len(kws), 0.9) if concept_id else 0.4,
            matched_keywords=general_matches + kws,
        )

    # 4. No code, no question words — check if it contains strong DSA keywords
    concept_id, kws = _detect_concept_from_keywords(stripped)
    if concept_id and len(kws) >= 2:
        return QueryClassification(
            scope="DSA",
            concept_id=concept_id,
            query_type="CONCEPTUAL_DOUBT",
            confidence=min(0.4 + 0.1 * len(kws), 0.8),
            matched_keywords=kws,
        )

    return QueryClassification(
        scope="OUT_OF_SCOPE",
        concept_id=None,
        query_type="UNKNOWN",
        confidence=0.3,
        matched_keywords=[],
    )
