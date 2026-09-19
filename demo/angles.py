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