from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from slice.config import settings
from slice.runner import advance
from slice.store import Store

from demo.flow import build_flow


def main():
    print()
    print("=" * 60)
    print("THE BOUNDARY LOOP")
    print("Binary Search Misconception Tutor")
    print("=" * 60)
    print()

    print("Paste the student's binary-search attempt.")
    print("Type END on a separate line when finished.")
    print()

    lines = []

    while True:
        line = input()

        if line.strip() == "END":
            break

        lines.append(line)

    student_attempt = "\n".join(lines).strip()

    if not student_attempt:
        print("No student attempt supplied.")
        return

    store = Store("run.db")

    run_id = store.create_run(
        "boundary_loop",
        meta={
            "concept": "binary_search_boundary_updates",
            "misconception": "M1_INCOMPLETE_ELIMINATION",
        },
    )

    store.append(
        run_id,
        "student_attempt",
        {
            "text": student_attempt,
        },
        produced_by="student",
    )

    print()
    print(f"Run ID: {run_id}")
    print()

    # ---------------------------------------------------------
    # PHASE 1: Diagnostic + Socratic
    # ---------------------------------------------------------

    final_state = advance(
        store,
        run_id,
        build_flow(),
        settings(),
    )

    # ---------------------------------------------------------
    # Get the generated Socratic question
    # ---------------------------------------------------------

    socratic_records = [
        record
        for record in store.replay(run_id)
        if record.kind == "socratic"
    ]

    if not socratic_records:
        print()
        print("No Socratic question was generated.")
        return

    socratic = socratic_records[-1].payload

    print()
    print("=" * 60)
    print("SOCRATIC QUESTION")
    print("=" * 60)
    print()
    print(socratic["question"])
    print()
    print("-" * 60)
    print("Your answer:")
    print()

    response_lines = []

    while True:
        line = input()

        if line.strip() == "END":
            break

        response_lines.append(line)

    student_response = "\n".join(response_lines).strip()

    if not student_response:
        print()
        print("No student response supplied.")
        return

    # ---------------------------------------------------------
    # Store student response
    # ---------------------------------------------------------

    store.append(
        run_id,
        "student_response",
        {
            "response": student_response,
        },
        produced_by="student",
    )

    print()
    print("Student response recorded.")
    print()

    # ---------------------------------------------------------
    # PHASE 2: Evaluator
    # ---------------------------------------------------------

    final_state = advance(
        store,
        run_id,
        build_flow(),
        settings(),
    )

    # ---------------------------------------------------------
    # Show complete history
    # ---------------------------------------------------------

    print()
    print("-" * 60)

    for record in store.replay(run_id):
        print()
        print(f"[{record.produced_by}] {record.kind}")

        for key, value in record.payload.items():
            print(f"{key}: {value}")

    print()
    print("-" * 60)
    print(f"Final state: {final_state.value}")
    print()
    print(f"Replay with:")
    print(f"python scripts/smoke.py replay {run_id}")
    print()


if __name__ == "__main__":
    main()