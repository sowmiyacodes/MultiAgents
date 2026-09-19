"""
Main Entry Point for the Adaptive Multi-Agent DSA Tutoring System.

Usage:
  python main.py
  python main.py --student student_001
  python main.py --history
  python main.py --list-topics
  python main.py --demo binary-search
  python main.py --demo recurrence
  python main.py --demo escalation
  python main.py --demo second-encounter
  python main.py --reset-student student_001
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project directory is in pythonpath
ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

from cli.interface import list_topics, run_interactive_session, show_history
from runtime.engine import TutoringEngine
from runtime.store import TutorStore
from slice.config import settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Adaptive Multi-Agent DSA Learning System (Terminal Interface)",
    )
    parser.add_argument(
        "--student",
        type=str,
        default="student_001",
        help="Student identifier (default: student_001)",
    )
    parser.add_argument(
        "--demo",
        type=str,
        choices=["binary-search", "recurrence", "escalation", "second-encounter"],
        help="Run a specific automated demonstration scenario",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="Display persistent learning history for the student",
    )
    parser.add_argument(
        "--list-topics",
        action="store_true",
        help="List all supported DSA topics and concepts in the registry",
    )
    parser.add_argument(
        "--reset-student",
        type=str,
        metavar="STUDENT_ID",
        help="Clear all persistent history and learning records for a student",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable detailed debug view with run history, planner decisions, and traces.",
    )
    return parser.parse_args()


def main() -> None:
    cfg = settings()
    args = parse_args()

    # 1. Demo scenarios
    if args.demo:
        if args.demo == "binary-search":
            from demos.binary_search_demo import run_demo
            run_demo(db_path=cfg.database_path)
        elif args.demo == "recurrence":
            from demos.recurrence_demo import run_demo
            run_demo(db_path=cfg.database_path)
        elif args.demo == "escalation":
            from demos.escalation_demo import run_demo
            run_demo(db_path=cfg.database_path)
        elif args.demo == "second-encounter":
            from demos.second_encounter_demo import run_demo
            run_demo(db_path=cfg.database_path)
        return

    # 2. Reset Student flag
    if args.reset_student:
        from runtime.store import TutorStore
        store = TutorStore(db_path=cfg.database_path)
        store.reset_student(args.reset_student)
        print(f"All records for student '{args.reset_student}' have been cleared from {cfg.database_path}.")
        return

    # 3. List Topics flag
    if args.list_topics:
        from cli.interface import list_topics
        list_topics(ROOT_DIR / "knowledge")
        return

    # 4. History flag
    if args.history:
        from cli.interface import show_history
        from runtime.store import TutorStore
        store = TutorStore(db_path=cfg.database_path)
        show_history(store, args.student)
        return

    # 5. Default: Run the Interactive Multi-Agent Tutoring Session
    from cli.interface import run_interactive_session
    from runtime.engine import TutoringEngine
    engine = TutoringEngine(db_path=cfg.database_path)
    run_interactive_session(engine, student_id=args.student)



if __name__ == "__main__":
    main()

