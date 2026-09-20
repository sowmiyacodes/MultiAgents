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


ANGLES_TWO_POINTERS = [
    {
        "id": "TP_SUM_DIRECTION",
        "goal": (
            "Use the sorted order to predict how moving the left or right "
            "pointer changes the pair sum."
        ),
    },
    {
        "id": "TP_ELIMINATION_PROOF",
        "goal": (
            "Prove which pairs are impossible after comparing the current "
            "sum with the target."
        ),
    },
    {
        "id": "TP_POINTER_INVARIANT",
        "goal": (
            "State what candidate pairs remain between the two pointers "
            "after each movement."
        ),
    },
]


TRANSFER_TASKS_TWO_POINTERS = [
    {
        "id": "TP_TRANSFER_1",
        "prompt": (
            "In the sorted array [1, 3, 5, 8, 12] with left = 0 and "
            "right = 4, the pair sum is greater than the target 10. "
            "Which pointer should move and why?"
        ),
        "target_reasoning": (
            "Move right left because the current sum is too large; keeping "
            "this right value with any remaining left value cannot produce "
            "a smaller sum by moving left."
        ),
    },
    {
        "id": "TP_TRANSFER_2",
        "prompt": (
            "For sorted values [2, 4, 6, 9] and target 11, the current "
            "pair is 2 + 4. Explain which pointer movement can increase "
            "the sum without discarding a possible solution."
        ),
        "target_reasoning": (
            "Move left rightward because the sum is too small; increasing "
            "the left value is the valid way to increase the sum."
        ),
    },
]


TUTOR_EXPLANATION_TWO_POINTERS = (
    "In a sorted array, pointer movement has a predictable effect on the "
    "pair sum. If the sum is too large, move the right pointer left to "
    "decrease it; if the sum is too small, move the left pointer right to "
    "increase it. Each movement proves a set of pairs impossible."
)


ANGLES_SLIDING_WINDOW = [
    {
        "id": "SW_WHILE_VS_IF",
        "goal": (
            "Recognize when the window must shrink repeatedly rather than "
            "removing only one element."
        ),
    },
    {
        "id": "SW_INVARIANT_RESTORATION",
        "goal": (
            "Restore the window validity invariant before recording an "
            "answer or expanding again."
        ),
    },
    {
        "id": "SW_STATE_UPDATE_ORDER",
        "goal": (
            "Track additions and removals so the window state matches the "
            "current [left, right] interval."
        ),
    },
]


TRANSFER_TASKS_SLIDING_WINDOW = [
    {
        "id": "SW_TRANSFER_1",
        "prompt": (
            "A growing window has sum 17 while the limit is 10. Explain "
            "why a single if-based left move may be insufficient and what "
            "the loop should guarantee."
        ),
        "target_reasoning": (
            "The left side must move in a while loop until the sum is at "
            "most 10; one removal may leave the window invalid."
        ),
    },
    {
        "id": "SW_TRANSFER_2",
        "prompt": (
            "When should a sliding-window algorithm update its best length: "
            "before or after shrinking an invalid window? Explain."
        ),
        "target_reasoning": (
            "Update the best length only after shrinking has restored the "
            "window invariant, so the recorded window is valid."
        ),
    },
]


TUTOR_EXPLANATION_SLIDING_WINDOW = (
    "A sliding window must satisfy its invariant whenever its answer is "
    "evaluated. After expanding the right side, use while, not just if, "
    "to remove elements from the left until the window is valid again. "
    "Then update the result using the restored window."
)


ANGLES_BY_CONCEPT = {
    "binary_search": ANGLES,
    "two_pointers": ANGLES_TWO_POINTERS,
    "sliding_window": ANGLES_SLIDING_WINDOW,
}

TRANSFER_TASKS_BY_CONCEPT = {
    "binary_search": TRANSFER_TASKS,
    "two_pointers": TRANSFER_TASKS_TWO_POINTERS,
    "sliding_window": TRANSFER_TASKS_SLIDING_WINDOW,
}

_TUTOR_EXPLANATIONS_BY_CONCEPT = {
    "binary_search": TUTOR_EXPLANATION,
    "two_pointers": TUTOR_EXPLANATION_TWO_POINTERS,
    "sliding_window": TUTOR_EXPLANATION_SLIDING_WINDOW,
}


def get_concept_angles(concept_id: str):
    """Return the angles for a concept, defaulting to Binary Search."""
    return ANGLES_BY_CONCEPT.get(concept_id, ANGLES)


def get_concept_transfer_tasks(concept_id: str):
    """Return transfer tasks for a concept, defaulting to Binary Search."""
    return TRANSFER_TASKS_BY_CONCEPT.get(concept_id, TRANSFER_TASKS)


def get_concept_explanation(concept_id: str):
    """Return a tutor explanation for a concept, defaulting to Binary Search."""
    return _TUTOR_EXPLANATIONS_BY_CONCEPT.get(concept_id, TUTOR_EXPLANATION)