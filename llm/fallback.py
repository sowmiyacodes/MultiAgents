"""
Deterministic fallback logic.

When OpenRouter is unavailable (no API key, network error, or invalid output),
these functions provide fully deterministic behaviour based on:
  - Keyword pattern matching
  - Knowledge base lookup
  - Template-based generation

The system must run fully without any API key.
"""
from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any

from llm.schemas import (
    ClassificationResult,
    DiagnosisResult,
    EvaluationResult,
    EvalResult,
    PlannerAction,
    PlannerOutput,
    SocraticOutput,
    StudentIntent,
    TransferTask,
    TutorOutput,
)

_KB = Path(__file__).parent.parent / "knowledge"
_REGISTRY_CACHE: dict | None = None
_MISCONCEPTION_CACHE: dict[str, list] = {}


def _registry() -> dict:
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is None:
        try:
            _REGISTRY_CACHE = json.loads((_KB / "dsa_registry.json").read_text())
        except Exception:
            _REGISTRY_CACHE = {"topics": [], "generic_socratic_angles": {}}
    return _REGISTRY_CACHE


def _misconceptions(topic: str) -> list:
    if topic in _MISCONCEPTION_CACHE:
        return _MISCONCEPTION_CACHE[topic]
    reg = _registry()
    topic_entry = next((t for t in reg["topics"] if t["topic"] == topic), None)
    if topic_entry and topic_entry.get("misconceptions_file"):
        fp = _KB / topic_entry["misconceptions_file"]
        try:
            data = json.loads(fp.read_text())
            result = data.get("misconceptions", [])
            _MISCONCEPTION_CACHE[topic] = result
            return result
        except Exception:
            pass
    _MISCONCEPTION_CACHE[topic] = []
    return []


# ── Classifier fallback ───────────────────────────────────────────────────────

_ADAPTIVE_KEYWORDS = [
    "wrong", "fail", "error", "incorrect", "why does", "why is", "shouldn't",
    "i thought", "but i", "problem with", "issue with", "my code", "my approach",
    "left++", "right--", "left =", "right =", "off by", "doesn't work",
]

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "binary_search": ["binary search", "left", "right", "mid", "bsearch", "sorted array", "boundary", "loop condition"],
    "arrays": ["array", "subarray", "sliding window", "two pointer", "prefix sum", "kadane"],
    "strings": ["string", "palindrome", "anagram", "substring", "character"],
    "hashing": ["hash", "hashmap", "hashset", "dictionary", "two sum", "frequency"],
    "linked_lists": ["linked list", "node", "next", "fast slow", "cycle", "reverse list"],
    "stacks": ["stack", "push", "pop", "parentheses", "monotonic stack", "next greater"],
    "queues": ["queue", "deque", "bfs", "fifo", "level order"],
    "trees": ["tree", "binary tree", "bst", "inorder", "preorder", "postorder", "root", "leaf", "height", "depth"],
    "graphs": ["graph", "edge", "vertex", "bfs", "dfs", "connected", "cycle", "visited", "dijkstra", "bellman"],
    "heaps": ["heap", "priority queue", "min heap", "max heap", "kth largest"],
    "dynamic_programming": ["dp", "dynamic programming", "memoization", "tabulation", "knapsack", "lis", "lcs"],
    "recursion": ["recursion", "recursive", "base case", "call stack", "factorial", "fibonacci"],
    "greedy": ["greedy", "local optimal", "activity selection", "interval"],
    "sorting": ["sort", "merge sort", "quicksort", "bubble sort", "heap sort", "counting sort"],
    "backtracking": ["backtrack", "permutation", "subset", "n-queens", "combination"],
}


def classify(student_input: str) -> ClassificationResult:
    text = student_input.lower()
    is_adaptive = any(kw in text for kw in _ADAPTIVE_KEYWORDS)

    domain = "binary_search"  # default
    for d, keywords in _DOMAIN_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            domain = d
            break

    intent = StudentIntent.CONCEPTUAL_CONFUSION if is_adaptive else StudentIntent.GENERAL_EXPLANATION

    # Subconcept detection for binary search
    subconcept = None
    if domain == "binary_search":
        if "boundary" in text or "left++" in text or "right--" in text:
            subconcept = "boundary_update"
        elif "loop" in text or "condition" in text:
            subconcept = "loop_condition"
        elif "first" in text and "occurrence" in text:
            subconcept = "first_occurrence"
        elif "last" in text and "occurrence" in text:
            subconcept = "last_occurrence"
        elif "rotat" in text:
            subconcept = "rotated_array"

    return ClassificationResult(
        domain=domain,
        topic=domain,
        subconcept=subconcept,
        difficulty=None,
        intent=intent,
        adaptive=is_adaptive,
        reasoning=f"Keyword-based classification: domain={domain}, adaptive={is_adaptive}",
    )


# ── Diagnostic fallback ───────────────────────────────────────────────────────

_MISCONCEPTION_PATTERNS: list[tuple[str, str, str, str]] = [
    # (pattern_in_text, misconception_id, evidence, invariant)
    ("left++", "M1_INCOMPLETE_ELIMINATION",
     "Student uses left++ which only moves boundary by 1 instead of mid+1",
     "When nums[mid] < target, all indices 0..mid are impossible; left must be mid+1"),
    ("left = left + 1", "M1_INCOMPLETE_ELIMINATION",
     "Student increments left by 1 instead of setting left=mid+1",
     "When nums[mid] < target, all indices 0..mid are impossible; left must be mid+1"),
    ("right--", "M1_INCOMPLETE_ELIMINATION",
     "Student uses right-- which only moves boundary by 1 instead of mid-1",
     "When nums[mid] > target, all indices mid..n-1 are impossible; right must be mid-1"),
    ("while left < right", "M2_INCORRECT_LOOP_CONDITION",
     "Student uses while left < right which misses single-element arrays",
     "Standard binary search loop must be while left <= right"),
    ("left + right", "M3_INCORRECT_MID_UPDATE",
     "Student computes mid as (left+right)/2 which can overflow",
     "Safe mid formula: left + (right - left) / 2"),
    ("return mid", "M4_INCORRECT_FIRST_OCCURRENCE_LOGIC",
     "Student returns immediately when target found, missing earlier occurrences",
     "For first occurrence: record mid and set right=mid-1 to keep searching left"),
]


def diagnose(student_input: str, topic: str = "binary_search", subconcept: str | None = None) -> DiagnosisResult:
    text_lower = student_input.lower()

    if not topic or topic == "general":
        topic = "binary_search"
        for d, keywords in _DOMAIN_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                topic = d
                break

    wants_explanation = any(kw in text_lower for kw in ["explain", "why do we", "tell me about", "teach me", "what is", "how does"])

    # Check for known patterns
    for pattern, mid_id, evidence, invariant in _MISCONCEPTION_PATTERNS:
        if pattern.lower() in text_lower:
            return DiagnosisResult(
                misconception_id=mid_id,
                concept=f"{topic}_{subconcept or 'boundary_update'}",
                evidence=[evidence],
                severity="foundational",
                confidence=0.85,
                invariant=invariant,
                is_known=True,
                topic=topic,
                subconcept=subconcept or "boundary_update",
                intent="GENERAL_EXPLANATION" if wants_explanation else "CONCEPTUAL_CONFUSION",
                wants_direct_explanation=wants_explanation,
            )

    # If student query mentions "don't understand" or "binary search"
    if topic == "binary_search" and any(kw in text_lower for kw in ["don't understand", "dont understand", "confused", "struggling", "help"]):
        return DiagnosisResult(
            misconception_id="M1_INCOMPLETE_ELIMINATION",
            concept=f"{topic}_{subconcept or 'boundary_update'}",
            evidence=["Student expresses general difficulty understanding binary search boundary elimination"],
            severity="foundational",
            confidence=0.80,
            invariant="When nums[mid] < target, all indices <= mid are eliminated; left becomes mid + 1",
            is_known=True,
            topic=topic,
            subconcept=subconcept or "boundary_update",
            intent="CONCEPTUAL_CONFUSION",
            wants_direct_explanation=wants_explanation,
        )

    # Check knowledge base misconceptions
    for m in _misconceptions(topic):
        for pattern in m.get("observable_patterns", []):
            if any(word in text_lower for word in pattern.lower().split() if len(word) > 3):
                return DiagnosisResult(
                    misconception_id=m["id"],
                    concept=f"{topic}_{subconcept or 'general'}",
                    evidence=[f"Pattern matched: {pattern}"],
                    severity=m.get("severity", "moderate"),
                    confidence=0.72,
                    invariant=m.get("invariant", "Not specified"),
                    is_known=True,
                    topic=topic,
                    subconcept=subconcept or "",
                    intent="GENERAL_EXPLANATION" if wants_explanation else "CONCEPTUAL_CONFUSION",
                    wants_direct_explanation=wants_explanation,
                )

    # Generic fallback
    generic_id = f"GENERIC_MISCONCEPTION_{topic.upper()}"
    return DiagnosisResult(
        misconception_id=generic_id,
        concept=f"{topic}_{subconcept or 'general'}",
        evidence=["Student demonstrates confusion about this concept based on their explanation"],
        severity="moderate",
        confidence=0.60,
        invariant=f"The core invariant of {topic} must be maintained throughout",
        is_known=False,
        topic=topic,
        subconcept=subconcept or "",
        intent="GENERAL_EXPLANATION" if wants_explanation else "CONCEPTUAL_CONFUSION",
        wants_direct_explanation=wants_explanation,
    )


# ── Socratic fallback ─────────────────────────────────────────────────────────

_BINARY_SEARCH_ANGLES: dict[str, dict] = {
    "ELIMINATED_RANGE_PROOF": {
        "id": "ELIMINATED_RANGE_PROOF",
        "question": "If nums[mid] is smaller than the target, which indices can you prove can no longer contain the target — including mid itself? List the exact range that is eliminated.",
        "pedagogical_goal": "Student must identify that ALL indices 0..mid are eliminated, not just mid",
    },
    "COUNTEREXAMPLE": {
        "id": "COUNTEREXAMPLE",
        "question": "Consider array [2, 5, 8, 12, 16, 23, 38] with left=0, right=6, mid=3, nums[3]=12, target=23. If you use left++, the new search space is [1, 6] containing 7 elements. But if you use left=mid+1=4, the space is [4, 6] with 3 elements. Which search space could MISS the target?",
        "pedagogical_goal": "Student must see that left++ doesn't skip the definitely-eliminated range",
    },
    "INVARIANT_RESTATEMENT": {
        "id": "INVARIANT_RESTATEMENT",
        "question": "At the START of every binary search iteration, what property must be true about the search interval [left, right]? If target=23 exists in the array, where must it always be?",
        "pedagogical_goal": "Student must articulate the invariant: target is always in [left, right] if it exists",
    },
    "OPPOSITE_BRANCH_TRANSFER": {
        "id": "OPPOSITE_BRANCH_TRANSFER",
        "question": "Using the same elimination reasoning: when nums[mid] > target, which indices are NOW provably impossible — including mid? So what should right become? Why right=mid-1 and not right--?",
        "pedagogical_goal": "Student applies same elimination logic to the right boundary",
    },
}

_GENERIC_ANGLES: list[dict] = [
    {"id": "INVARIANT_RESTATEMENT", "question": "What property must always be true at the start of each iteration? Can you state the invariant?", "pedagogical_goal": "Identify the maintained invariant"},
    {"id": "COUNTEREXAMPLE", "question": "Can you construct a small example (3-5 elements) where your current approach would give the wrong answer?", "pedagogical_goal": "Student identifies a failure case"},
    {"id": "EDGE_CASE", "question": "What happens in the edge case where the input has only ONE element? Does your approach still work?", "pedagogical_goal": "Student tests boundary conditions"},
]


def socratic_question(misconception_id: str, angle_id: str, topic: str, used_questions: list[str]) -> SocraticOutput:
    """Generate a Socratic question deterministically."""
    # Try binary search specific angles first
    if topic == "binary_search" and angle_id in _BINARY_SEARCH_ANGLES:
        angle = _BINARY_SEARCH_ANGLES[angle_id]
        q = angle["question"]
        if q not in used_questions:
            return SocraticOutput(
                angle_id=angle_id,
                question=q,
                pedagogical_goal=angle["pedagogical_goal"],
            )

    # Try knowledge base angles
    for m in _misconceptions(topic):
        if m["id"] == misconception_id:
            for angle in m.get("socratic_angles", []):
                if angle.get("id") == angle_id:
                    q = angle.get("sample_question", "")
                    if q and q not in used_questions:
                        return SocraticOutput(
                            angle_id=angle_id,
                            question=q,
                            pedagogical_goal=angle.get("description", "Deepen understanding"),
                        )

    # Generic fallback — pick any unused angle
    for ga in _GENERIC_ANGLES:
        if ga["question"] not in used_questions:
            return SocraticOutput(
                angle_id=ga["id"],
                question=ga["question"],
                pedagogical_goal=ga["pedagogical_goal"],
            )

    # Last resort
    return SocraticOutput(
        angle_id=angle_id,
        question=f"Can you explain your reasoning for this {topic} problem step by step, focusing on {angle_id.lower().replace('_', ' ')}?",
        pedagogical_goal="Elicit the student's reasoning chain",
    )


# ── Transfer task fallback ────────────────────────────────────────────────────

def transfer_task(misconception_id: str, topic: str, used_task_ids: list[str]) -> TransferTask:
    """Return a fresh transfer task deterministically."""
    # Try knowledge base templates
    for m in _misconceptions(topic):
        if m["id"] == misconception_id:
            for tmpl in m.get("transfer_templates", []):
                if tmpl["id"] not in used_task_ids:
                    ctx = {k: v for k, v in tmpl.items()
                           if k not in ("id", "question", "target_reasoning")}
                    return TransferTask(
                        task_id=tmpl["id"],
                        problem=tmpl["question"],
                        context=ctx,
                        target_reasoning=tmpl.get("target_reasoning", "Apply the correct reasoning"),
                    )

    # Generic transfer for binary search
    if topic == "binary_search":
        arrays = [
            ([1, 3, 7, 15, 21, 40, 55, 72], 3, 7, 55, "TRANSFER_BS_GEN_1"),
            ([4, 8, 13, 17, 25, 31], 0, 5, 25, "TRANSFER_BS_GEN_2"),
            ([2, 6, 9, 14, 18, 27, 33, 41, 50], 4, 8, 33, "TRANSFER_BS_GEN_3"),
        ]
        for arr, l, r, target, tid in arrays:
            if tid not in used_task_ids:
                mid = (l + r) // 2
                return TransferTask(
                    task_id=tid,
                    problem=(
                        f"Array: {arr}\n"
                        f"left={l}, right={r}, mid={mid}, nums[mid]={arr[mid]}, target={target}\n\n"
                        f"Which index range can still contain the target?\n"
                        f"What should left (or right) become, and why?"
                    ),
                    context={"array": arr, "left": l, "right": r, "mid": mid, "target": target},
                    target_reasoning=f"Since nums[{mid}]={arr[mid]} < {target}, all indices 0..{mid} are impossible. left=mid+1={mid+1}.",
                )

    # Completely generic
    return TransferTask(
        task_id=f"TRANSFER_{topic.upper()}_GENERIC",
        problem=(
            f"Apply the correct reasoning for {topic.replace('_', ' ')} to this new scenario: "
            f"imagine you have a similar problem but with different values. "
            f"Explain step by step what the correct approach would be and why."
        ),
        context={},
        target_reasoning="Demonstrate the correct reasoning applied to a new instance",
    )


# ── Evaluator fallback ────────────────────────────────────────────────────────

_PASS_KEYWORDS = [
    "mid+1", "mid-1", "mid + 1", "mid - 1", "eliminate", "impossible", "left = mid", "right = mid",
    "invariant", "proven", "provably", "can't contain", "cannot contain", "ruled out",
    "larger", "23", "23 is larger", "left half", "remove left", "eliminate left", "left side",
    "mid is eliminated", "4", "index 4", "greater"
]
_FAIL_KEYWORDS = ["left++", "right--", "left = left", "right = right", "move by one", "increment", "smaller", "7 is larger", "keep mid", "left = mid\b"]


def evaluate(
    student_response: str,
    misconception_id: str,
    topic: str,
    stage: str,
    target_reasoning: str,
    question_or_task: str = "",
) -> EvaluationResult:
    text_lower = student_response.lower().strip()

    fail_hit = any(kw.lower() in text_lower for kw in _FAIL_KEYWORDS)
    pass_hit = any(kw.lower() in text_lower for kw in _PASS_KEYWORDS)

    # Contextual check for specific Socratic questions
    q_lower = question_or_task.lower()
    if ("smaller or larger" in q_lower or "which is larger" in q_lower):
        if "larger" in text_lower or "23" in text_lower:
            pass_hit = True
            fail_hit = False
    elif "which side" in q_lower or "eliminated" in q_lower:
        if any(w in text_lower for w in [
            "mid + 1", "mid+1", "all indices", "all elements",
            "impossible", "ruled out", "before mid", "0..mid", "first half",
        ]):
            pass_hit = True
            fail_hit = False

    if fail_hit and not pass_hit:
        return EvaluationResult(
            result=EvalResult.FAIL,
            reasoning_correct=False,
            transfer_success=False,
            misconception_recurred=True,
            confidence=0.85,
            feedback=(
                "Your response indicates the misconception is still active. "
                "Notice that elements at or before mid cannot contain the target if nums[mid] < target. "
                "Updating by only 1 index fails to eliminate all impossible values."
            ),
            evidence=[f"Response contains patterns indicating {misconception_id}"],
            reasoning_quality="poor",
            error_type="incomplete_elimination",
            concept=f"{topic}_boundary_updates",
            mastery_delta=-0.1,
            needs_another_attempt=True,
        )
    elif pass_hit:
        return EvaluationResult(
            result=EvalResult.PASS,
            reasoning_correct=True,
            transfer_success=True,
            misconception_recurred=False,
            confidence=0.85,
            feedback="Correct! Your reasoning correctly identifies the search boundaries and eliminated elements.",
            evidence=["Response demonstrates correct reasoning matching target invariant"],
            reasoning_quality="good",
            error_type="none",
            concept=f"{topic}_boundary_updates",
            mastery_delta=0.15,
            needs_another_attempt=False,
        )
    else:
        # Check if length is non-trivial but inconclusive
        return EvaluationResult(
            result=EvalResult.FAIL,
            reasoning_correct=False,
            transfer_success=False,
            misconception_recurred=False,
            confidence=0.60,
            feedback=(
                "Your explanation does not yet clearly demonstrate the boundary invariant. "
                "Consider which elements are strictly ruled out by the comparison."
            ),
            evidence=["Response lacks sufficient reasoning to confirm invariant adherence"],
            reasoning_quality="partial",
            error_type="ambiguous_reasoning",
            concept=f"{topic}_boundary_updates",
            mastery_delta=-0.05,
            needs_another_attempt=True,
        )


# ── Tutor fallback ────────────────────────────────────────────────────────────

_TUTOR_EXPLANATIONS: dict[str, dict] = {
    "M1_INCOMPLETE_ELIMINATION": {
        "misconception_stated": "You are moving the boundary by only 1 step (left++) instead of eliminating the entire confirmed-impossible range.",
        "explanation": (
            "When binary search determines nums[mid] < target, it has PROVEN that the target cannot be at any index from 0 to mid (inclusive). "
            "This is because the array is sorted: if nums[mid] < target, then nums[0], nums[1], ..., nums[mid] are ALL smaller than target. "
            "Therefore, the ENTIRE range [0, mid] is eliminated in one step. The next search should start at mid+1, not mid (or mid-1, left+1)."
        ),
        "worked_example": (
            "Array: [2, 5, 8, 12, 16, 23, 38], target=23\n"
            "Step 1: left=0, right=6, mid=3, nums[3]=12\n"
            "Since 12 < 23: indices 0,1,2,3 are ALL impossible (they're all ≤ 12 < 23).\n"
            "Correct: left = mid+1 = 4 (search [16, 23, 38])\n"
            "Wrong:   left = left+1 = 1 (still includes 5, 8, 12 — wasted work, and can miss target in edge cases)"
        ),
        "apply_prompt": "Now apply this: given [1, 3, 7, 15, 21, 40, 55], left=0, right=6, mid=3, nums[3]=15, target=55. What must left become?",
        "key_insight": "In binary search, every boundary update must eliminate mid itself — never leave it in the search space.",
    },
    "M2_INCORRECT_LOOP_CONDITION": {
        "misconception_stated": "Your loop condition terminates too early, missing valid search intervals.",
        "explanation": (
            "For standard binary search, the loop must continue as long as the interval [left, right] is non-empty. "
            "An interval is non-empty when left <= right. When left > right, the interval is empty and the target doesn't exist. "
            "Using while left < right misses the case where left == right (a one-element interval) which could contain the target."
        ),
        "worked_example": (
            "Array: [5], target=5\n"
            "Initial: left=0, right=0\n"
            "while left < right: 0 < 0 is FALSE — loop doesn't execute. Target not found. WRONG!\n"
            "while left <= right: 0 <= 0 is TRUE — check mid=0, nums[0]=5=target. Found!"
        ),
        "apply_prompt": "Array: [7], target=7. left=0, right=0. With while left < right, does the loop run? With while left <= right?",
        "key_insight": "The search interval [left, right] is empty only when left > right, so the loop continues while left <= right.",
    },
}


def tutor_explanation(misconception_id: str, topic: str, student_input: str) -> TutorOutput:
    """Generate targeted tutor explanation deterministically."""
    if misconception_id in _TUTOR_EXPLANATIONS:
        t = _TUTOR_EXPLANATIONS[misconception_id]
        return TutorOutput(
            misconception_stated=t["misconception_stated"],
            explanation=t["explanation"],
            worked_example=t["worked_example"],
            apply_prompt=t["apply_prompt"],
            key_insight=t["key_insight"],
        )

    # Generic tutor for unknown misconceptions
    return TutorOutput(
        misconception_stated=f"There is a misconception in your understanding of {topic.replace('_', ' ')}.",
        explanation=(
            f"The key principle in {topic.replace('_', ' ')} is to always maintain the core invariant. "
            f"Review the invariant carefully: every step must preserve it. "
            f"When in doubt, trace through a small concrete example to verify your logic."
        ),
        worked_example="Trace through: [1, 3, 5], target=3, step by step with all variable values.",
        apply_prompt="Now apply the correct reasoning to a fresh example of your choice.",
        key_insight=f"Always verify that each step of {topic.replace('_', ' ')} maintains the required invariant.",
    )


# ── Planner fallback ──────────────────────────────────────────────────────────

def plan_next(
    topic: str,
    subconcept: str,
    mastery_status: str,
    transfer_passed: bool,
    failed_count: int,
    success_count: int,
) -> PlannerOutput:
    """Determine next learning action deterministically."""
    if failed_count >= 3:
        return PlannerOutput(
            action=PlannerAction.HUMAN_REVIEW,
            reason="Student has failed transfer tasks 3+ times; human instructor review recommended",
            message="This topic has been challenging. A human instructor can provide additional support.",
        )
    if transfer_passed and success_count >= 2:
        return PlannerOutput(
            action=PlannerAction.MOVE_TO_NEXT_TOPIC,
            reason="Student has successfully passed transfer tasks multiple times",
            next_topic=_suggest_next_topic(topic),
            message=f"Excellent work! You've mastered {topic.replace('_', ' ')}. Let's move on.",
        )
    if transfer_passed:
        return PlannerOutput(
            action=PlannerAction.SPACED_REVIEW,
            reason="Student passed transfer but needs consolidation through spaced practice",
            message=f"Good progress on {topic.replace('_', ' ')}! We'll revisit this in a few days for consolidation.",
            spaced_review_days=3,
        )
    if failed_count >= 2:
        return PlannerOutput(
            action=PlannerAction.REVIEW_MISCONCEPTION,
            reason="Repeated failures suggest misconception needs different approach",
            message=f"Let's approach {topic.replace('_', ' ')} from a different angle.",
        )
    return PlannerOutput(
        action=PlannerAction.PRACTICE_SAME_CONCEPT,
        reason="Student needs more practice on the current concept",
        message=f"Let's continue practicing {topic.replace('_', ' ')} to build confidence.",
    )


def _suggest_next_topic(current: str) -> str | None:
    PROGRESSION = {
        "arrays": "strings",
        "strings": "hashing",
        "hashing": "linked_lists",
        "linked_lists": "stacks",
        "stacks": "queues",
        "queues": "binary_search",
        "binary_search": "trees",
        "trees": "graphs",
        "graphs": "heaps",
        "heaps": "dynamic_programming",
        "dynamic_programming": "greedy",
        "greedy": "backtracking",
    }
    return PROGRESSION.get(current)


# ── General Q&A fallback ──────────────────────────────────────────────────────

def general_answer(student_input: str, topic: str) -> str:
    text_lower = student_input.lower()

    # Binary search
    if "binary search" in text_lower and "what" in text_lower:
        return (
            "Binary search is an efficient algorithm for finding an element in a SORTED array. "
            "It works by repeatedly halving the search space:\n\n"
            "1. Start with left=0, right=n-1\n"
            "2. Compute mid = left + (right-left)//2\n"
            "3. If nums[mid] == target: found!\n"
            "4. If nums[mid] < target: target must be in right half → left = mid+1\n"
            "5. If nums[mid] > target: target must be in left half → right = mid-1\n"
            "6. Repeat until left > right (target not found)\n\n"
            "Time complexity: O(log n). The key invariant: if target exists, it's always in [left, right]."
        )

    # Dijkstra
    if "dijkstra" in text_lower:
        return (
            "Dijkstra's algorithm finds shortest paths from a source node in a weighted graph with non-negative edge weights.\n\n"
            "Algorithm:\n"
            "1. Initialize dist[source]=0, all others=infinity\n"
            "2. Use a min-heap priority queue\n"
            "3. Process node with smallest distance\n"
            "4. For each neighbor: if dist[current]+weight < dist[neighbor], update dist[neighbor]\n"
            "5. Repeat until all nodes processed\n\n"
            "Time: O((V+E) log V) with a heap. Does NOT work with negative edge weights."
        )

    # DP
    if "dynamic programming" in text_lower or " dp " in text_lower:
        return (
            "Dynamic Programming (DP) solves problems by breaking them into overlapping subproblems and storing results.\n\n"
            "Key steps:\n"
            "1. Define the state: what does dp[i] (or dp[i][j]) represent?\n"
            "2. Write the transition: how does dp[i] depend on smaller subproblems?\n"
            "3. Set base cases: what are the boundary values?\n"
            "4. Determine order: bottom-up (tabulation) or top-down (memoization)\n\n"
            "Example: Fibonacci — dp[i] = dp[i-1] + dp[i-2], base: dp[0]=0, dp[1]=1"
        )

    # Generic
    return (
        f"I'll explain {topic.replace('_', ' ')} for you.\n\n"
        "This is a fundamental data structures and algorithms topic. "
        "To get the best explanation, try asking a more specific question, "
        "for example: 'What is the time complexity?' or 'How does it handle edge cases?'\n\n"
        "For a complete walkthrough with examples, configure OPENROUTER_API_KEY in your .env file "
        "to get AI-powered explanations."
    )
