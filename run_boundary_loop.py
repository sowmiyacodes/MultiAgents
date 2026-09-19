from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent),
)

from slice.config import settings
from slice.runner import advance
from slice.records import RunState
from slice.store import Store

from demo.flow import build_flow


def print_history(store, run_id):

    print()
    print("=" * 70)
    print("RUN HISTORY")
    print("=" * 70)

    for record in store.replay(run_id):

        print()
        print(
            f"[{record.produced_by}] "
            f"{record.kind}"
        )

        for key, value in record.payload.items():
            print(
                f"{key}: {value}"
            )

    print()
    print("-" * 70)


def get_latest(store, run_id, kind):

    records = [
        record
        for record in store.replay(run_id)
        if record.kind == kind
    ]

    if not records:
        return None

    return records[-1].payload


def collect_multiline(prompt):

    print(prompt)
    print(
        "Type END on a separate line when finished."
    )
    print()

    lines = []

    while True:

        line = input()

        if line.strip() == "END":
            break

        lines.append(line)

    return "\n".join(lines).strip()


def collect_student_attempt():

    return collect_multiline(
        "Paste the student's binary-search attempt."
    )


def collect_student_response():

    return collect_multiline(
        "Your answer:"
    )


def display_evaluator(store, run_id):

    evaluator = get_latest(
        store,
        run_id,
        "evaluator",
    )

    if evaluator is None:
        return

    print()
    print("=" * 70)
    print("EVALUATOR")
    print("=" * 70)
    print()

    print(
        f"Outcome: {evaluator.get('outcome')}"
    )

    print(
        f"Confidence: "
        f"{evaluator.get('confidence')}"
    )

    print()

    print("Evidence:")

    for evidence in evaluator.get(
        "evidence",
        [],
    ):
        print(
            f"- {evidence}"
        )

    print()

    print(
        "Reasoning assessment:"
    )

    print(
        evaluator.get(
            "reasoning_assessment",
            "",
        )
    )

    print()
    print("-" * 70)


def display_learning_state(
    store,
    run_id,
):

    state = get_latest(
        store,
        run_id,
        "learning_state",
    )

    if state is None:
        return

    print()
    print("=" * 70)
    print("PERSISTENT LEARNING STATE")
    print("=" * 70)
    print()

    print(
        f"Status: {state.get('status')}"
    )

    print(
        f"Misconception: "
        f"{state.get('misconception')}"
    )

    print(
        f"Transfer passed: "
        f"{state.get('transfer_passed')}"
    )

    print()

    print(
        "Recommended next action:"
    )

    print(
        state.get(
            "recommended_next_action",
            "",
        )
    )

    print()
    print("-" * 70)


def display_tutor(
    store,
    run_id,
):

    tutor = get_latest(
        store,
        run_id,
        "tutor",
    )

    if tutor is None:
        return

    print()
    print("=" * 70)
    print("TUTOR / WORKED EXAMPLE")
    print("=" * 70)
    print()

    print(
        tutor.get(
            "explanation",
            "",
        )
    )

    print()
    print("-" * 70)


def main():

    print()
    print("=" * 70)
    print("THE BOUNDARY LOOP")
    print("Binary Search Misconception Tutor")
    print("=" * 70)
    print()

    student_attempt = collect_student_attempt()

    if not student_attempt:

        print()
        print(
            "No student attempt supplied."
        )

        return

    store = Store(
        "run.db"
    )

    run_id = store.create_run(
        "boundary_loop",
        meta={
            "concept": (
                "binary_search_boundary_updates"
            ),
            "misconception": (
                "M1_INCOMPLETE_ELIMINATION"
            ),
        },
    )

    store.append(
        run_id,
        "student_attempt",
        {
            "text": student_attempt
        },
        produced_by="student",
    )

    print()
    print(
        f"Run ID: {run_id}"
    )
    print()

    flow = build_flow()

    final_state = advance(
        store,
        run_id,
        flow,
        settings(),
    )

    while final_state == RunState.AWAITING_EXPERT:

        transfer = get_latest(
            store,
            run_id,
            "transfer",
        )

        socratic = get_latest(
            store,
            run_id,
            "socratic",
        )

        print()

        if transfer is not None:

            print("=" * 70)
            print("FRESH TRANSFER TASK")
            print("=" * 70)
            print()

            print(
                transfer["prompt"]
            )

        elif socratic is not None:

            print("=" * 70)
            print("SOCRATIC QUESTION")
            print("=" * 70)
            print()

            print(
                socratic["question"]
            )

        else:

            print(
                "ERROR: No pending question found."
            )

            return

        print()
        print("-" * 70)

        student_response = (
            collect_student_response()
        )

        if not student_response:

            print()
            print(
                "No student response supplied."
            )

            return

        store.append(
            run_id,
            "student_response",
            {
                "response":
                    student_response
            },
            produced_by="student",
        )

        print()
        print(
            "Student response recorded."
        )

        store.set_state(
            run_id,
            RunState.EVALUATING,
        )

        final_state = advance(
            store,
            run_id,
            flow,
            settings(),
        )

        display_evaluator(
            store,
            run_id,
        )

    display_learning_state(
        store,
        run_id,
    )

    display_tutor(
        store,
        run_id,
    )

    print_history(
        store,
        run_id,
    )

    print(
        f"Final state: "
        f"{final_state.value}"
    )

    print()

    if final_state == RunState.COMPLETE:

        print(
            "Boundary Loop completed."
        )

    elif final_state == RunState.FAILED:

        print(
            "Boundary Loop failed."
        )

    else:

        print(
            "Boundary Loop stopped in state:"
        )

        print(
            final_state.value
        )

    print()

    print(
        "Replay with:"
    )

    print(
        f"python scripts/smoke.py replay {run_id}"
    )

    print()


if __name__ == "__main__":
    main()