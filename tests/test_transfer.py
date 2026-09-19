"""
Test Transfer Task Agent (generates fresh transfer problems).
"""
from agents.transfer import TransferAgent


def test_transfer_task_generation():
    transfer = TransferAgent()
    task = transfer.generate(
        misconception_id="M1_INCOMPLETE_ELIMINATION",
        topic="binary_search",
        subconcept="boundary_update",
        target_reasoning="Indices through mid are ruled out",
        original_example="left=0, right=9, mid=4, nums[mid]=7, target=23",
        previous_tasks=[],
    )
    assert task.task_id is not None
    assert len(task.problem) > 20
    # Must test boundary reasoning
    assert "left" in task.problem.lower() or "right" in task.problem.lower()


def test_transfer_task_freshness():
    transfer = TransferAgent()
    task1 = transfer.generate(
        misconception_id="M1_INCOMPLETE_ELIMINATION",
        topic="binary_search",
        subconcept="boundary_update",
        target_reasoning="Indices through mid are ruled out",
        original_example="original",
        previous_tasks=[],
    )
    task2 = transfer.generate(
        misconception_id="M1_INCOMPLETE_ELIMINATION",
        topic="binary_search",
        subconcept="boundary_update",
        target_reasoning="Indices through mid are ruled out",
        original_example="original",
        previous_tasks=[task1.task_id],
    )
    assert task1.task_id != task2.task_id
