# ---------------------------------------------------------------------------
# Binary Search angles (existing — DO NOT remove)
# ---------------------------------------------------------------------------

ANGLES = [
    {
        "id": "ELIMINATED_RANGE_PROOF",
        "goal": (
            "Reason about which positions are proven impossible after "
            "comparing nums[mid] with target."
        ),
    },
    {
        "id": "COUNTEREXAMPLE_ARRAY",
        "goal": (
            "Use a concrete small array to expose the difference between "
            "moving one step and eliminating the ruled-out range."
        ),
    },
    {
        "id": "INVARIANT_RESTATEMENT",
        "goal": (
            "Reason about what the active search interval must represent "
            "after each binary-search comparison."
        ),
    },
    {
        "id": "OPPOSITE_BRANCH_TRANSFER",
        "goal": (
            "Reason about the corresponding boundary update when the "
            "comparison goes in the opposite direction."
        ),
    },
]


TRANSFER_TASKS = [
    {
        "id": "TRANSFER_1",
        "prompt": (
            "Consider this binary-search step on a sorted ascending array:\n\n"
            "left = 0\n"
            "right = 7\n"
            "mid = 3\n"
            "nums[mid] = 12\n"
            "target = 20\n\n"
            "Explain which indices are now impossible and what the new "
            "left boundary should represent."
        ),
        "target_reasoning": (
            "Because nums[mid] is less than target, every index at or before "
            "mid is impossible. The new search interval must begin at "
            "mid + 1."
        ),
    },
    {
        "id": "TRANSFER_2",
        "prompt": (
            "Consider a sorted array where:\n\n"
            "left = 2\n"
            "right = 10\n"
            "mid = 6\n"
            "nums[mid] = 31\n"
            "target = 14\n\n"
            "Explain which positions can be eliminated and what the right "
            "boundary should become."
        ),
        "target_reasoning": (
            "Because nums[mid] is greater than target, every index at or "
            "after mid is impossible. The new search interval must end at "
            "mid - 1."
        ),
    },
]


TUTOR_EXPLANATION = (
    "In binary search, the important idea is not merely to move a boundary "
    "by one position. The comparison with nums[mid], together with the "
    "sorted-order invariant, proves that an entire range cannot contain "
    "the target. If nums[mid] < target, every index at or before mid is "
    "too small, so the next interval begins at mid + 1. If nums[mid] > "
    "target, every index at or after mid is too large, so the next interval "
    "ends at mid - 1."
)


# ---------------------------------------------------------------------------
# Two Pointers angles (NEW)
# ---------------------------------------------------------------------------

ANGLES_TWO_POINTERS = [
    {
        "id": "TP_SUM_DIRECTION",
        "goal": (
            "Reason about how incrementing left or decrementing right "
            "monotonically changes the pair sum on a sorted array."
        ),
    },
    {
        "id": "TP_ELIMINATION_PROOF",
        "goal": (
            "Use a concrete sorted array to show that when sum > target, "
            "nums[right] cannot pair with ANY remaining left element."
        ),
    },
    {
        "id": "TP_INVARIANT_RESTATEMENT",
        "goal": (
            "Reason about what guarantee sorted order provides for the "
            "pointer movement decision at each step."
        ),
    },
    {
        "id": "TP_COUNTEREXAMPLE",
        "goal": (
            "Produce a concrete example where moving the wrong pointer "
            "causes the algorithm to miss the target pair."
        ),
    },
]

TRANSFER_TASKS_TWO_POINTERS = [
    {
        "id": "TP_TRANSFER_1",
        "prompt": (
            "Consider this two-pointer step on a sorted array:\n\n"
            "nums = [1, 3, 5, 8, 11, 15]\n"
            "left = 0, right = 5\n"
            "nums[left] + nums[right] = 1 + 15 = 16\n"
            "target = 10\n\n"
            "The sum is greater than target. Which pointer must move and "
            "why? Show that the other pointer cannot possibly contribute "
            "to reaching the target from the current right element."
        ),
        "target_reasoning": (
            "Since sum > target and nums[left] is the smallest remaining "
            "value, nums[right] cannot pair with any remaining element to "
            "reach target. Right must decrease (right--)."
        ),
    },
    {
        "id": "TP_TRANSFER_2",
        "prompt": (
            "Consider a two-pointer state:\n\n"
            "nums = [2, 4, 7, 9, 12]\n"
            "left = 1, right = 4\n"
            "nums[left] + nums[right] = 4 + 12 = 16\n"
            "target = 20\n\n"
            "The sum is less than target. Explain why left must increase "
            "and why decreasing right would not help."
        ),
        "target_reasoning": (
            "Since sum < target and nums[right] is already the largest "
            "remaining element, nums[left] cannot pair with any remaining "
            "element to reach target. Left must increase (left++)."
        ),
    },
]

TUTOR_EXPLANATION_TWO_POINTERS = (
    "In two-pointer pair searching on a sorted array, the key insight is "
    "monotonicity: because the array is sorted, incrementing left always "
    "increases the pair sum, while decrementing right always decreases it. "
    "When nums[left] + nums[right] > target, nums[right] cannot possibly "
    "pair with any remaining left element (since all remaining lefts are "
    ">= nums[left], the minimum), so we must decrease right. When the sum "
    "< target, nums[left] cannot pair with any remaining right element, so "
    "we must increase left. Moving the wrong pointer wastes the elimination "
    "guarantee that sorted order provides."
)


# ---------------------------------------------------------------------------
# Sliding Window angles (NEW)
# ---------------------------------------------------------------------------

ANGLES_SLIDING_WINDOW = [
    {
        "id": "SW_WHILE_VS_IF",
        "goal": (
            "Reason about why a single 'if' shrink can leave the window "
            "in an invalid state when more than one element violates the constraint."
        ),
    },
    {
        "id": "SW_INVARIANT_RESTORATION",
        "goal": (
            "Reason about what 'window validity' means and how the while-loop "
            "guarantees the invariant is fully restored before recording the answer."
        ),
    },
    {
        "id": "SW_COUNTEREXAMPLE",
        "goal": (
            "Use a concrete array to show a case where 'if left++' produces "
            "the wrong answer but 'while ... left++' produces the right one."
        ),
    },
    {
        "id": "SW_EXPAND_CONTRACT",
        "goal": (
            "Distinguish the responsibilities of right (expand) and left (contract) "
            "and explain when each pointer should move."
        ),
    },
]

TRANSFER_TASKS_SLIDING_WINDOW = [
    {
        "id": "SW_TRANSFER_1",
        "prompt": (
            "Consider this sliding window state:\n\n"
            "nums = [1, 4, 3, 2, 6]\n"
            "k = 7  (max allowed sum)\n"
            "right = 3, left = 0\n"
            "current_sum = 10 (1 + 4 + 3 + 2)\n\n"
            "We just expanded right to index 3. The window sum is now 10 > 7.\n"
            "Trace through what happens if you use 'if sum > k: left += 1' "
            "versus 'while sum > k: left += 1'. What is the resulting "
            "window state after each approach?"
        ),
        "target_reasoning": (
            "With 'if': left moves to 1, sum = 9 — still invalid. Window "
            "invariant is broken. With 'while': left moves to 1 (sum=9), then "
            "to 2 (sum=5) — valid. The while-loop is required to fully restore "
            "the invariant."
        ),
    },
    {
        "id": "SW_TRANSFER_2",
        "prompt": (
            "Given the array [2, 1, 5, 2, 3, 2] and k = 7, you are finding "
            "the minimum length subarray with sum >= k.\n\n"
            "Suppose your window is [left=0, right=3] with sum = 10.\n"
            "Explain why you must keep shrinking from the left while sum >= k "
            "and why stopping after one shrink would give the wrong minimum length."
        ),
        "target_reasoning": (
            "Stopping after one shrink may still leave a valid window. "
            "Continuing to shrink while sum >= k ensures we find the smallest "
            "window that satisfies the constraint. Each shrink may produce a "
            "new valid minimum, so we must keep shrinking until sum < k."
        ),
    },
]

TUTOR_EXPLANATION_SLIDING_WINDOW = (
    "A sliding window maintains a contiguous subarray [left, right] whose "
    "validity is guaranteed at every step. When we expand right and violate "
    "the window condition (e.g., sum > k), we must restore the invariant by "
    "shrinking from the left using a WHILE loop — not an IF statement. Using "
    "'if' removes only one element, but the condition may still be violated "
    "after that single removal. The while loop keeps shrinking until the "
    "invariant is fully restored. Recording the answer before this full "
    "restoration produces incorrect results."
)


# ---------------------------------------------------------------------------
# Multi-concept lookup helpers (NEW)
# ---------------------------------------------------------------------------

ANGLES_BY_CONCEPT: dict[str, list[dict]] = {
    "binary_search": ANGLES,
    "two_pointers": ANGLES_TWO_POINTERS,
    "sliding_window": ANGLES_SLIDING_WINDOW,
}

TRANSFER_TASKS_BY_CONCEPT: dict[str, list[dict]] = {
    "binary_search": TRANSFER_TASKS,
    "two_pointers": TRANSFER_TASKS_TWO_POINTERS,
    "sliding_window": TRANSFER_TASKS_SLIDING_WINDOW,
}

TUTOR_EXPLANATIONS_BY_CONCEPT: dict[str, str] = {
    "binary_search": TUTOR_EXPLANATION,
    "two_pointers": TUTOR_EXPLANATION_TWO_POINTERS,
    "sliding_window": TUTOR_EXPLANATION_SLIDING_WINDOW,
}


def get_concept_angles(concept_id: str, misconception_id: str | None = None) -> list[dict]:
    """Return the Socratic angle bank for the given concept.

    Falls back to binary_search angles if the concept is not supported.
    """
    return ANGLES_BY_CONCEPT.get(concept_id, ANGLES)


def get_concept_transfer_tasks(concept_id: str) -> list[dict]:
    """Return the transfer task bank for the given concept.

    Falls back to binary_search transfer tasks if the concept is not supported.
    """
    return TRANSFER_TASKS_BY_CONCEPT.get(concept_id, TRANSFER_TASKS)


def get_concept_explanation(concept_id: str) -> str:
    """Return the worked explanation for the given concept.

    Falls back to binary_search explanation if the concept is not supported.
    """
    return TUTOR_EXPLANATIONS_BY_CONCEPT.get(concept_id, TUTOR_EXPLANATION)