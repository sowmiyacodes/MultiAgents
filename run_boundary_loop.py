import argparse
from pathlib import Path
import sys
import traceback

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent),
)

from slice.config import settings
from slice.runner import advance
from slice.records import RunState
from slice.store import Store

from demo.flow import build_flow


def parse_args():
    parser = argparse.ArgumentParser(
        description="The Boundary Loop: Binary Search Misconception Tutor"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable detailed debug view with run history, planner decisions, and traces.",
    )
    return parser.parse_args()


def format_misconception(code: str) -> str:
    if code == "M1_INCOMPLETE_ELIMINATION":
        return "Incomplete boundary elimination"
    return code.replace("_", " ").title()


def format_outcome(outcome: str) -> str:
    if outcome == "REINFORCE":
        return "NEEDS ANOTHER TRY"
    return outcome


def print_history(store, run_id):
    print()
    print("=" * 60)
    print("RUN HISTORY")
    print("=" * 60)

    for record in store.replay(run_id):
        print()
        print(f"[{record.produced_by}] {record.kind}")
        for key, value in record.payload.items():
            print(f"{key}: {value}")

    print()
    print("-" * 60)


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
    print("Type END on a separate line when finished.")
    print()

    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break

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


def display_diagnosis(store, run_id, debug=False):
    diagnostic = get_latest(store, run_id, "diagnostic")
    if diagnostic is None:
        return

    print("------------------------------------------------------------")
    print("DIAGNOSIS")
    print("------------------------------------------------------------")
    print()
    misconception = format_misconception(diagnostic.get("misconception", ""))
    print("Misconception detected:")
    print(misconception)
    print()

    conf = diagnostic.get("confidence", 0.0)
    if isinstance(conf, (int, float)):
        print(f"Confidence: {int(round(conf * 100))}%")
    else:
        print(f"Confidence: {conf}")

    if debug:
        print()
        print("[DEBUG] Diagnostic Evidence:")
        for ev in diagnostic.get("evidence", []):
            print(f"  - {ev}")
        print(f"[DEBUG] Pattern: {diagnostic.get('reasoning_pattern', '')}")

    print()


def display_evaluator(store, run_id, debug=False):
    evaluator = get_latest(store, run_id, "evaluator")
    if evaluator is None:
        return

    print("------------------------------------------------------------")
    print("EVALUATION")
    print("------------------------------------------------------------")
    print()
    outcome_raw = evaluator.get("outcome", "")
    outcome_formatted = format_outcome(outcome_raw)
    print(f"Result: {outcome_formatted}")
    print()

    evidence = evaluator.get("evidence", [])
    if evidence:
        print("Evidence:")
        for item in evidence:
            print(f"- {item}")
        print()

    if debug:
        print(f"[DEBUG] Confidence: {evaluator.get('confidence')}")
        print(f"[DEBUG] Stage: {evaluator.get('stage')}")
        print(f"[DEBUG] Assessment: {evaluator.get('reasoning_assessment', '')}")
        print()

    print("-" * 60)


def display_backward_loop(store, run_id, debug=False):
    loop = get_latest(store, run_id, "backward_loop")
    if loop is None:
        return False

    student_responses = store.history(run_id, "student_response")
    backward_loops = store.history(run_id, "backward_loop")

    if student_responses and backward_loops:
        if backward_loops[-1].seq > student_responses[-1].seq:
            cycle = loop.get("backward_loop_count", 1) + 1
            misconception = format_misconception(
                loop.get("misconception", "M1_INCOMPLETE_ELIMINATION")
            )

            print()
            print("============================================================")
            print("              <- BACKWARD LOOP")
            print("============================================================")
            print()
            print("Three Socratic attempts were incorrect.")
            print()
            print("Returning to a simpler reasoning angle.")
            print()
            print("Misconception:")
            print(misconception)
            print()
            print(f"Cycle: {cycle}")
            print()
            print("============================================================")
            print()

            if debug:
                print(f"[DEBUG] Loop Reason: {loop.get('reason')}")
                print(f"[DEBUG] Wrong Count: {loop.get('wrong_socratic_count')}")
                print()
            return True

    return False


def display_debug_planner(store, run_id):
    planner = get_latest(store, run_id, "planner")
    if planner is None:
        return

    print()
    print("------------------------------------------------------------")
    print("[DEBUG] PLANNER DECISION")
    print("------------------------------------------------------------")
    print(f"Action:           {planner.get('action')}")
    print(f"Pedagogical Goal: {planner.get('pedagogical_goal')}")
    print(f"Preferred Angle:  {planner.get('preferred_angle')}")
    print(f"Difficulty:       {planner.get('difficulty')}")
    print(f"Focus:            {planner.get('focus')}")
    print(f"Reason:           {planner.get('reason')}")
    print("------------------------------------------------------------")
    print()


def display_debug_tutor(store, run_id):
    tutor = get_latest(store, run_id, "tutor")
    if tutor is None:
        return

    print()
    print("------------------------------------------------------------")
    print("[DEBUG] TUTOR R8 RECORD")
    print("------------------------------------------------------------")
    print(f"Phase:            {tutor.get('phase')}")
    print(f"Angle ID:         {tutor.get('angle_id')}")
    print(f"Pedagogical Goal: {tutor.get('pedagogical_goal')}")
    print(f"Difficulty:       {tutor.get('difficulty')}")
    print("------------------------------------------------------------")
    print()


def display_success(store, run_id, debug=False):
    print()
    print("============================================================")
    print("                 BOUNDARY LOOP COMPLETE")
    print("============================================================")
    print()
    diagnostic = get_latest(store, run_id, "diagnostic")
    misconception = format_misconception(
        diagnostic.get("misconception", "M1_INCOMPLETE_ELIMINATION")
        if diagnostic
        else "Incomplete boundary elimination"
    )

    print("Diagnosis:")
    print(misconception)
    print()
    print("Learning progression:")
    print("[v] Socratic reasoning demonstrated")
    print("[v] Transfer reasoning demonstrated")
    print()
    print("The student successfully applied the boundary invariant")
    print("to a new problem.")
    print()
    print("============================================================")
    print()


def run_session(debug=False):
    cfg = settings()
    model_name = cfg.model or "unknown"

    print()
    print("============================================================")
    print("                    THE BOUNDARY LOOP")
    print("              Binary Search Misconception Tutor")
    print("============================================================")
    print()
    print(f"Model: {model_name}")

    student_attempt = collect_student_attempt()
    if not student_attempt:
        print()
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
        {"text": student_attempt},
        produced_by="student",
    )

    print(f"Run: {run_id}")
    print()

    print("------------------------------------------------------------")
    print("STUDENT ATTEMPT")
    print("------------------------------------------------------------")
    print()
    print(student_attempt)
    print()

    flow = build_flow()
    final_state = advance(
        store,
        run_id,
        flow,
        cfg,
    )

    display_diagnosis(store, run_id, debug=debug)

    if debug:
        display_debug_planner(store, run_id)
        display_debug_tutor(store, run_id)

    while final_state == RunState.AWAITING_EXPERT:
        transfer = get_latest(store, run_id, "transfer")
        socratic = get_latest(store, run_id, "socratic")
        transfer_records = store.history(run_id, "transfer")
        socratic_records = store.history(run_id, "socratic")

        is_transfer = False
        if transfer_records:
            if not socratic_records or transfer_records[-1].seq > socratic_records[-1].seq:
                is_transfer = True

        print()
        if is_transfer and transfer is not None:
            print("============================================================")
            print("              FRESH TRANSFER TASK")
            print("============================================================")
            print()
            print("This is a new problem designed to test whether the idea")
            print("generalizes beyond the previous example.")
            print()
            print(transfer.get("prompt", ""))
            print()
            print("------------------------------------------------------------")
            print("YOUR ANSWER")
            print("------------------------------------------------------------")
            print()
        elif socratic is not None:
            print("------------------------------------------------------------")
            print("TUTOR")
            print("------------------------------------------------------------")
            print()
            print("Socratic Question")
            print()
            print(socratic.get("question", ""))
            print()
            print("------------------------------------------------------------")
            print("YOUR ANSWER")
            print("------------------------------------------------------------")
            print()
        else:
            print("ERROR: No pending question found.")
            return

        student_response = collect_student_response()
        if not student_response:
            print()
            print("No student response supplied.")
            return

        store.append(
            run_id,
            "student_response",
            {"response": student_response},
            produced_by="student",
        )

        store.set_state(
            run_id,
            RunState.EVALUATING,
        )

        final_state = advance(
            store,
            run_id,
            flow,
            cfg,
        )

        print()
        display_evaluator(store, run_id, debug=debug)
        display_backward_loop(store, run_id, debug=debug)

        if debug:
            display_debug_planner(store, run_id)
            display_debug_tutor(store, run_id)

    if final_state == RunState.COMPLETE:
        learning_state = get_latest(store, run_id, "learning_state")
        if learning_state and learning_state.get("transfer_passed"):
            display_success(store, run_id, debug=debug)
        else:
            print()
            print("Boundary Loop completed.")
            print()
    elif final_state == RunState.FAILED:
        print()
        print("Boundary Loop failed.")
        print()
    else:
        print()
        print(f"Boundary Loop stopped in state: {final_state.value}")
        print()

    if debug:
        print_history(store, run_id)
        learning_state = get_latest(store, run_id, "learning_state")
        if learning_state:
            print("Learning State:")
            print(learning_state)
        print(f"Final state: {final_state.value}")
        print()
        print("Replay with:")
        print(f"python scripts/smoke.py replay {run_id}")
        print()


def main():
    args = parse_args()
    try:
        run_session(debug=args.debug)
    except Exception as e:
        if args.debug:
            raise
        print()
        print("============================================================")
        print("ERROR")
        print("============================================================")
        print()
        print(str(e))
        print()
        print("Run with --debug for the full traceback.")
        print()


if __name__ == "__main__":
    main()