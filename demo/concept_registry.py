"""Central Concept and Misconception Registry for The Boundary Loop: DSA Learning Tutor.

Provides broad DSA topic metadata for general queries and deep misconception definitions
for the full adaptive Boundary Loop.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MisconceptionDefinition:
    """Detailed metadata for a diagnosed reasoning misconception."""

    misconception_id: str
    concept_id: str
    name: str
    description: str
    core_reasoning_flaw: str
    symptom_patterns: list[str]
    pedagogical_goals: list[str]
    default_worked_explanation: str


@dataclass(frozen=True)
class ConceptDefinition:
    """Structured information for a DSA concept in the registry."""

    concept_id: str
    display_name: str
    category: str
    description: str
    core_invariant: str
    common_patterns: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    supported_misconceptions: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Deep Misconception Definitions
# ---------------------------------------------------------------------------

MISCONCEPTIONS: dict[str, MisconceptionDefinition] = {
    "M1_INCOMPLETE_ELIMINATION": MisconceptionDefinition(
        misconception_id="M1_INCOMPLETE_ELIMINATION",
        concept_id="binary_search",
        name="Incomplete Boundary Elimination",
        description=(
            "The student treats boundary movement as moving by one index (left++ or right--) "
            "instead of using sorted order to eliminate the entire proven-impossible range."
        ),
        core_reasoning_flaw=(
            "Treats the binary search interval as a linear scan instead of using the "
            "comparison with nums[mid] to eliminate mid and all elements beyond it."
        ),
        symptom_patterns=[
            "left = left + 1",
            "left++",
            "right = right - 1",
            "right--",
            "left += 1",
            "right -= 1",
        ],
        pedagogical_goals=[
            "Reason about the entire eliminated range invariant",
            "Understand why left must advance to mid + 1",
            "Understand why right must advance to mid - 1",
            "Restate the active search interval invariant",
        ],
        default_worked_explanation=(
            "In binary search, the comparison with nums[mid], combined with sorted order, "
            "proves that an entire subrange is impossible. If nums[mid] < target, then mid "
            "and every element to the left is strictly less than target, so left becomes mid + 1. "
            "If nums[mid] > target, then mid and every element to the right is strictly greater, "
            "so right becomes mid - 1."
        ),
    ),
    "TP1_WRONG_POINTER_MOVEMENT": MisconceptionDefinition(
        misconception_id="TP1_WRONG_POINTER_MOVEMENT",
        concept_id="two_pointers",
        name="Arbitrary or Inverted Pointer Movement",
        description=(
            "The student moves pointers without respecting the monotonicity invariant "
            "(e.g., advancing left when the sum is already too large, or moving right when the sum is too small)."
        ),
        core_reasoning_flaw=(
            "Fails to recognize that sorted order guarantees how the sum or comparison changes: "
            "incrementing left increases the sum; decrementing right decreases the sum."
        ),
        symptom_patterns=[
            "left++ when sum > target",
            "right-- when sum < target",
            "left += 1 when current > target",
            "both pointers moved simultaneously without check",
        ],
        pedagogical_goals=[
            "Understand how pointer movement monotonically affects the pair sum",
            "Recognize search space elimination for the current fixed element",
            "Determine which pointer must move based on comparison with target",
        ],
        default_worked_explanation=(
            "In two-pointer pair searching on a sorted array, nums[left] + nums[right] guides "
            "deterministic elimination. If the sum is greater than target, nums[right] cannot pair "
            "with ANY remaining number (since nums[left] is the smallest remaining value), so right "
            "must decrease (right--). If the sum is less than target, nums[left] cannot pair with any "
            "remaining value, so left must increase (left++)."
        ),
    ),
    "SW1_INCOMPLETE_SHRINK": MisconceptionDefinition(
        misconception_id="SW1_INCOMPLETE_SHRINK",
        concept_id="sliding_window",
        name="Incomplete Window Shrinking",
        description=(
            "The student uses a single 'if' check to shrink the window instead of a 'while' loop, "
            "or fails to shrink until the window invariant is completely restored."
        ),
        core_reasoning_flaw=(
            "Assumes removing a single element from the left restores validity, leaving an invalid "
            "window state when multiple elements must be evicted."
        ),
        symptom_patterns=[
            "if condition: left++",
            "if current_sum > k: left += 1",
            "recording answer before restoring window validity",
        ],
        pedagogical_goals=[
            "Understand the continuous window validity invariant",
            "Recognize why a while-loop is needed to evict elements until valid",
            "Distinguish window expansion (right) from window contraction (left)",
        ],
        default_worked_explanation=(
            "A sliding window represents a contiguous subarray whose validity is guaranteed. "
            "When expanding right violates the window condition, you must shrink from the left "
            "using a while-loop (while invalid: shrink) until validity is restored before considering "
            "the window for maximum/minimum length answers."
        ),
    ),
}


# ---------------------------------------------------------------------------
# Broad DSA Concept Registry
# ---------------------------------------------------------------------------

CONCEPTS: dict[str, ConceptDefinition] = {
    # Searching / Sorting
    "binary_search": ConceptDefinition(
        concept_id="binary_search",
        display_name="Binary Search",
        category="Searching / Sorting",
        description="Search a sorted collection by repeatedly halving the active search space.",
        core_invariant="All elements outside the current [left, right] interval are proven impossible.",
        common_patterns=["Search in sorted array", "Binary search on answer space", "Find first/last occurrence"],
        common_mistakes=["Incomplete elimination (left++)", "Loop condition off-by-one", "Mid calculation overflow"],
        keywords=["binary search", "bsearch", "nums[mid]", "mid =", "left < right", "left <= right", "bisect"],
        aliases=["binary_search", "bsearch", "binary-search"],
        supported_misconceptions=["M1_INCOMPLETE_ELIMINATION"],
    ),
    "linear_search": ConceptDefinition(
        concept_id="linear_search",
        display_name="Linear Search",
        category="Searching / Sorting",
        description="Iterate sequentially through elements to find a target value in O(N) time.",
        core_invariant="Target has not been found in the prefix processed so far.",
        keywords=["linear search", "sequential search"],
    ),
    "merge_sort": ConceptDefinition(
        concept_id="merge_sort",
        display_name="Merge Sort",
        category="Searching / Sorting",
        description="Divide array into halves, recursively sort both, and merge in sorted order in O(N log N).",
        core_invariant="Each merged subsegment is internally sorted.",
        keywords=["merge sort", "divide and conquer", "merge two sorted arrays"],
    ),
    "quick_sort": ConceptDefinition(
        concept_id="quick_sort",
        display_name="Quick Sort",
        category="Searching / Sorting",
        description="Partition array around a pivot such that left <= pivot <= right, then sort recursively.",
        core_invariant="After partition, pivot element is in its final sorted position.",
        keywords=["quick sort", "partition", "pivot", "quicksort"],
    ),

    # Common Patterns
    "two_pointers": ConceptDefinition(
        concept_id="two_pointers",
        display_name="Two Pointers",
        category="Common Patterns",
        description="Maintain two index pointers that converge or move in tandem based on monotonicity.",
        core_invariant="Monotonicity guarantees that elements behind the pointers cannot contribute to a valid solution.",
        common_patterns=["Opposite ends meeting in middle", "Two sum in sorted array", "Container with most water"],
        common_mistakes=["Moving wrong pointer", "Pointers crossing incorrectly", "Assuming array is sorted when it is not"],
        keywords=["two pointers", "two pointer", "left", "right", "two sum sorted", "left < right"],
        aliases=["two_pointers", "two_pointer", "twopointers"],
        supported_misconceptions=["TP1_WRONG_POINTER_MOVEMENT"],
    ),
    "sliding_window": ConceptDefinition(
        concept_id="sliding_window",
        display_name="Sliding Window",
        category="Common Patterns",
        description="Maintain a contiguous window [left, right] over an array or string, expanding and shrinking dynamically.",
        core_invariant="The window invariant holds before and after each expansion/contraction step.",
        common_patterns=["Longest substring with K distinct", "Minimum size subarray sum", "Maximum sum subarray of size K"],
        common_mistakes=["Shrinking with 'if' instead of 'while'", "Updating state in wrong order", "Off-by-one window length"],
        keywords=["sliding window", "window", "subarray sum", "longest substring", "contiguous window"],
        aliases=["sliding_window", "slidingwindow", "windowing"],
        supported_misconceptions=["SW1_INCOMPLETE_SHRINK"],
    ),
    "prefix_sum": ConceptDefinition(
        concept_id="prefix_sum",
        display_name="Prefix Sum",
        category="Common Patterns",
        description="Precompute cumulative sums so any contiguous range sum query runs in O(1) time.",
        core_invariant="prefix[i] stores the sum of all elements in array[0..i-1].",
        keywords=["prefix sum", "cumulative sum", "range sum query"],
    ),
    "fast_slow_pointers": ConceptDefinition(
        concept_id="fast_slow_pointers",
        display_name="Fast & Slow Pointers (Floyd's Cycle Finding)",
        category="Common Patterns",
        description="Advance two pointers at different speeds (1 step vs 2 steps) to detect cycles or find midpoints.",
        core_invariant="Distance between fast and slow increases by 1 step per iteration.",
        keywords=["fast slow", "tortoise and hare", "cycle detection", "linked list cycle"],
    ),
    "greedy": ConceptDefinition(
        concept_id="greedy",
        display_name="Greedy Algorithms",
        category="Common Patterns",
        description="Make the locally optimal choice at each step with the hope of finding a global optimum.",
        core_invariant="Local optimal choices never preclude reaching the global optimum.",
        keywords=["greedy", "interval scheduling", "jump game", "gas station"],
    ),

    # Linear Data Structures
    "stack": ConceptDefinition(
        concept_id="stack",
        display_name="Stack",
        category="Linear Data Structures",
        description="LIFO (Last-In First-Out) linear data structure supporting O(1) push and pop operations.",
        core_invariant="The element popped is always the most recently added element still present.",
        keywords=["stack", "lifo", "push", "pop", "monotonic stack", "valid parentheses"],
    ),
    "queue": ConceptDefinition(
        concept_id="queue",
        display_name="Queue",
        category="Linear Data Structures",
        description="FIFO (First-In First-Out) linear data structure supporting O(1) enqueue and dequeue operations.",
        core_invariant="The element dequeued is always the oldest element added that has not yet been removed.",
        keywords=["queue", "fifo", "enqueue", "dequeue", "bfs queue"],
    ),
    "linked_list": ConceptDefinition(
        concept_id="linked_list",
        display_name="Linked List",
        category="Linear Data Structures",
        description="Sequence of nodes where each node stores data and a pointer to the next node.",
        core_invariant="Each node's next pointer accurately references the subsequent node or null.",
        keywords=["linked list", "singly linked list", "doubly linked list", "head", "next pointer"],
    ),

    # Trees
    "binary_tree": ConceptDefinition(
        concept_id="binary_tree",
        display_name="Binary Tree",
        category="Trees",
        description="Hierarchical tree data structure in which each node has at most two children (left and right).",
        core_invariant="Every node except the root has exactly one parent, with no cycles.",
        keywords=["binary tree", "inorder", "preorder", "postorder", "tree traversal", "lca"],
    ),
    "bst": ConceptDefinition(
        concept_id="bst",
        display_name="Binary Search Tree (BST)",
        category="Trees",
        description="Binary tree where left subtree values are strictly smaller and right subtree values are strictly larger.",
        core_invariant="For every node X, all keys in left subtree < X.key < all keys in right subtree.",
        keywords=["bst", "binary search tree", "inorder is sorted"],
    ),

    # Heaps
    "heap": ConceptDefinition(
        concept_id="heap",
        display_name="Heap / Priority Queue",
        category="Heaps",
        description="Complete binary tree satisfying the heap property (parent is always smaller or larger than children).",
        core_invariant="In a min-heap, root is always the minimum element of the entire heap.",
        keywords=["heap", "priority queue", "min heap", "max heap", "heapq", "top k"],
    ),

    # Graphs
    "graph": ConceptDefinition(
        concept_id="graph",
        display_name="Graphs (BFS / DFS)",
        category="Graphs",
        description="Collection of vertices and edges representing pairwise relationships.",
        core_invariant="Visited set ensures each connected component vertex is processed without infinite loops.",
        keywords=["graph", "bfs", "dfs", "adjacency list", "dijkstra", "topological sort", "cycle"],
    ),

    # Advanced
    "dynamic_programming": ConceptDefinition(
        concept_id="dynamic_programming",
        display_name="Dynamic Programming",
        category="Advanced",
        description="Solve complex problems by breaking them down into overlapping subproblems with optimal substructure.",
        core_invariant="The optimal solution to a subproblem is memoized and reused without redundant calculation.",
        keywords=["dynamic programming", "dp", "memoization", "tabulation", "knapsack", "longest common subsequence"],
    ),
    "recursion": ConceptDefinition(
        concept_id="recursion",
        display_name="Recursion",
        category="Fundamentals",
        description="Solving a problem where a function calls itself on smaller inputs until reaching a base case.",
        core_invariant="Every recursive call moves strictly closer to an explicit base case.",
        keywords=["recursion", "recursive", "base case", "call stack"],
    ),
    "time_complexity": ConceptDefinition(
        concept_id="time_complexity",
        display_name="Time & Space Complexity (Big-O)",
        category="Fundamentals",
        description="Mathematical analysis of algorithm runtime and memory growth as input size N grows.",
        core_invariant="Upper bound O(f(N)) describes asymptotic worst-case scaling.",
        keywords=["time complexity", "space complexity", "big o", "o(n)", "o(log n)", "o(1)"],
    ),
}


def get_concept(concept_id: str) -> ConceptDefinition | None:
    """Retrieve concept definition by ID or alias."""
    if not concept_id:
        return None
    cid = concept_id.lower().strip()
    if cid in CONCEPTS:
        return CONCEPTS[cid]
    for c in CONCEPTS.values():
        if cid in c.aliases or cid == c.display_name.lower():
            return c
    return None


def get_misconception(misconception_id: str) -> MisconceptionDefinition | None:
    """Retrieve misconception definition by ID."""
    return MISCONCEPTIONS.get(misconception_id)


def is_concept_supported(concept_id: str) -> bool:
    """Check if the concept has deep misconception loop support."""
    c = get_concept(concept_id)
    return bool(c and c.supported_misconceptions)


def list_all_concepts() -> list[ConceptDefinition]:
    """Return all registered DSA concepts."""
    return list(CONCEPTS.values())
