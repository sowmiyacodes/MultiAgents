"""
Terminal Interface for Adaptive DSA Tutoring System.

Features:
- Clean, structured output with clear headers and agent attributions
- Interactive student question & response loop
- Support for CLI commands: history, resume, list-topics, reset-student
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

from runtime.engine import TutoringEngine, TutoringSession
from runtime.store import TutorStore
from slice.state_machine import TutorState

SEP_LINE = "=" * 60
SUB_SEP = "-" * 40


def print_banner() -> None:
    print(SEP_LINE)
    print("ADAPTIVE MULTI-AGENT DSA LEARNING SYSTEM")
    print(SEP_LINE)


def format_agent_header(title: str) -> str:
    return f"\n{SUB_SEP}\n## {title}\n{SUB_SEP}"


def collect_multiline(prompt_text: str) -> str:
    print(prompt_text)
    print("(Type your code/answer below. When finished, type 'END' on a new line and press Enter)\n")
    lines = []
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            break
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def run_interactive_session(
    engine: TutoringEngine,
    student_id: str = "student_001",
    initial_query: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    print_banner()

    if not initial_query:
        print("\nWhat DSA algorithm, code, or concept would you like to analyze today?")
        initial_query = collect_multiline("Paste your code or algorithm attempt:")

    if not initial_query:
        initial_query = "int left = 0;\nint right = nums.length - 1;\nwhile (left <= right) {\n    int mid = (left + right) / 2;\n    if (nums[mid] == target) return mid;\n    if (nums[mid] < target) left++; else right--;\n}\nreturn -1;"

    session = engine.start_session(student_id=student_id, initial_query=initial_query)
    if session_id:
        session.session_id = session_id

    print(f"Session ID: {session.session_id}")

    # Check for previous session JSON state pickup by session_id
    json_summary = engine.store.load_session_json_summary(session.session_id)
    if json_summary:
        print(f"\n[PERSISTENCE PICKUP] Loaded profile from JSON for Session '{session.session_id}':")
        print(f"  - Misconception Detected:    {json_summary.get('misconception_detected') or 'None'}")
        print(f"  - Transfer Problem Passed:   {json_summary.get('transfer_passed')}")
        print(f"  - Socratic Rounds Completed: {json_summary.get('socratic_rounds_count')}")

    print(f"\nSubmitted Algorithm/Code:\n{initial_query}")

    # State loop
    while not session.state.is_terminal:
        # Advance engine until it needs student input or completes
        engine.step(session)
        # Sync session JSON summary after each step
        engine.store.sync_session_json_summary(session.session_id)

        # Print current phase output
        if session.state == TutorState.WAITING_FOR_STUDENT:
            if session.stage == "socratic" and session.current_question:
                # Show classifier info first time
                if session.classification and session.classification.adaptive and not session.messages:
                    print(format_agent_header("CLASSIFIER"))
                    print(f"Topic:      {session.classification.topic.replace('_', ' ').title()}")
                    print(f"Subconcept: {session.classification.subconcept or 'General'}")
                    print(f"Mode:       Adaptive Tutoring")

                if session.diagnosis and not session.messages:
                    print(format_agent_header("DIAGNOSTIC AGENT"))
                    print(f"Detected misconception: {session.diagnosis.misconception_id}")
                    print(f"Invariant:              {session.diagnosis.invariant}")
                    print(f"Evidence:               {session.diagnosis.evidence[0]}")
                    session.messages.append({"type": "diagnostic_shown"})

                print(format_agent_header(f"SOCRATIC AGENT [Angle: {session.current_angle}]"))
                print(f"Question:\n{session.current_question}\n")

            elif session.stage == "transfer" and session.current_transfer:
                print(format_agent_header("TRANSFER TASK AGENT"))
                print("Testing transfer of reasoning to a fresh problem:")
                print(f"{session.current_question}\n")

            # Collect student input (multiline supported, finish with END)
            ans = collect_multiline("Your answer/code:")

            if not ans:
                ans = "I think left should be mid + 1 because all indices through mid are smaller than target."

            # Advance with answer
            engine.step(session, student_input=ans)
            engine.store.sync_session_json_summary(session.session_id)

            # Show evaluation
            if session.current_eval:
                print(format_agent_header("EVALUATOR AGENT"))
                print(f"Result:             {session.current_eval.result.value}")
                print(f"Reasoning correct:  {session.current_eval.reasoning_correct}")
                print(f"Transfer success:   {session.current_eval.transfer_success}")
                print(f"Feedback:           {session.current_eval.feedback}")

                # If incorrect and system returned to socratic back loop, offer learning support options
                if (session.current_eval.result != TutorState.COMPLETE and
                    not session.current_eval.reasoning_correct and
                    session.state == TutorState.WAITING_FOR_STUDENT and
                    session.stage == "socratic"):
                    
                    print("\n" + SUB_SEP)
                    print("STUDENT OPTIONS (Choose how to proceed):")
                    print("  [1] Try Again           - Answer next Socratic question from another angle")
                    print("  [2] Get a Hint          - Receive a progressive hint before answering")
                    print("  [3] See a Worked Example - View direct explanation & worked example from Tutor Agent")
                    
                    try:
                        choice = input("\nSelect option [1-3] (Default: 1): ").strip()
                    except (EOFError, KeyboardInterrupt):
                        choice = "1"

                    if choice == "2":
                        print(format_agent_header("PROGRESSIVE HINT"))
                        hint_msg = (
                            f"HINT: Focus on the invariant: {session.diagnosis.invariant if session.diagnosis else 'Key invariant'}. "
                            "When an element at mid fails the target test, what can you say about ALL elements before/after it?"
                        )
                        print(hint_msg)
                    elif choice == "3":
                        # Fast-track to targeted tutor
                        print(format_agent_header("TARGETED TUTOR AGENT (Requested Worked Example)"))
                        if session.diagnosis:
                            tutor_out = engine.tutor.explain(
                                misconception_id=session.diagnosis.misconception_id,
                                invariant=session.diagnosis.invariant,
                                topic=session.classification.topic if session.classification else "binary_search",
                                subconcept=session.classification.subconcept if session.classification else None,
                                student_input=session.current_query,
                            )
                            print(f"Misconception:  {tutor_out.misconception_stated}")
                            print(f"\nExplanation:\n{tutor_out.explanation}")
                            print(f"\nWorked Example:\n{tutor_out.worked_example}")
                            print(f"\nKey Insight:    {tutor_out.key_insight}")

        elif session.state == TutorState.TARGETED_TUTORING:
            if session.current_tutor:
                print(format_agent_header("TARGETED TUTOR AGENT (Socratic Attempts Exhausted - Escalation)"))
                print(f"Misconception:  {session.current_tutor.misconception_stated}")
                print(f"\nExplanation:\n{session.current_tutor.explanation}")
                print(f"\nWorked Example:\n{session.current_tutor.worked_example}")
                print(f"\nKey Insight:    {session.current_tutor.key_insight}")
                print("\nNow generating a fresh transfer problem to verify your understanding...")


        elif session.state == TutorState.COMPLETE:
            if session.classification and not session.classification.adaptive:
                print(format_agent_header("GENERAL DSA EXPLANATION"))
                print(session.general_response)
            elif session.current_plan:
                print(format_agent_header("PLANNER AGENT"))
                print(f"Next Action: {session.current_plan.action.value}")
                print(f"Reason:      {session.current_plan.reason}")
                print(f"Message:     {session.current_plan.message}")

            print(f"\n{SEP_LINE}\nSESSION COMPLETED SUCCESSFULLY\n{SEP_LINE}")
            json_file = engine.store.sync_session_json_summary(session.session_id)
            print(f"[PERSISTENCE SAVED] Session summary profile saved to: {json_file}")
            break

        elif session.state == TutorState.HUMAN_REVIEW_WAITING:
            print(format_agent_header("ESCALATION"))
            print("The student has reached maximum attempts without successful transfer.")
            print("Session escalated to HUMAN INSTRUCTOR REVIEW.")
            print(f"{SEP_LINE}\nSESSION ESCALATED\n{SEP_LINE}")
            json_file = engine.store.sync_session_json_summary(session.session_id)
            print(f"[PERSISTENCE SAVED] Session summary profile saved to: {json_file}")
            break




def show_history(store: TutorStore, student_id: str) -> None:
    print_banner()
    print(f"LEARNING HISTORY FOR: {student_id}")
    print(SEP_LINE)

    states = store.get_all_student_states(student_id)
    if not states:
        print("No learning records found for this student.")
        return

    for s in states:
        print(f"Topic:            {s['topic']}")
        print(f"Subconcept:       {s['subconcept']}")
        print(f"Mastery Status:   {s['mastery_status']}")
        print(f"Confidence:       {s['confidence']:.2f}")
        print(f"Passed Transfers: {s['successful_transfer_count']}")
        print(f"Failed Transfers: {s['failed_transfer_count']}")
        print(f"Used Angles:      {', '.join(s['used_angles'])}")
        print(SUB_SEP)


def list_topics(kb_dir: Path) -> None:
    print_banner()
    print("SUPPORTED DSA DOMAINS & TOPICS")
    print(SEP_LINE)

    registry_path = kb_dir / "dsa_registry.json"
    if not registry_path.exists():
        print("Registry file not found.")
        return

    data = json.loads(registry_path.read_text())
    topics = data.get("topics", [])
    for idx, t in enumerate(topics, 1):
        name = t.get("display_name", t.get("topic"))
        subconcepts = ", ".join(t.get("subconcepts", []))
        diff = t.get("difficulty", "medium").upper()
        print(f"{idx:2d}. {name:<25} [{diff}]")
        print(f"    Subconcepts: {subconcepts}")
    print(f"\nTotal registered topics: {len(topics)}")
    print("Generic fallback covers any unlisted DSA topic.")
