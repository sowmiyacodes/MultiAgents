# PRE-EVENT-ASSETS 

This file declares the work and materials prepared before the Agent-a-Thon.

## Pre-event work being brought into the event

Before the event, our team prepared the architecture and workflow plan for **The Boundary Loop**, a persistent adaptive-learning system focused on detecting and addressing a specific binary-search misconception.

The pre-event design includes:

- The overall **Boundary Loop architecture** and deterministic workflow.
- The planned state/transition flow for:
  - misconception diagnosis
  - Socratic guidance
  - student response
  - transfer-task generation
  - evaluation
  - learning-state update
  - retry/reinforcement
- The target misconception:
  - `M1_INCOMPLETE_ELIMINATION`
  - confusing a one-step boundary update such as `left++` or `right--` with eliminating the already-ruled-out range through `mid`.
- The planned Socratic intervention strategy.
- The planned transfer-task and evaluation strategy.
- The planned persistent learning-state concept, including whether the student has demonstrated transfer after intervention.
- The planned bounded retry/correction flow.

## Pre-event Socratic plan

Our pre-event Socratic design uses an **angle bank** to avoid asking semantically repetitive questions.

The planned mechanism is:

1. Diagnose the student's misconception from their attempted solution or explanation.
2. Select a Socratic question from a relevant pedagogical angle.
3. Record the selected `angle_id`.
4. Do not reuse an already-used angle within the same correction sequence.
5. Ask the student to reason about the boundary decision rather than directly providing the corrected code.
6. Give a fresh transfer task after the intervention.
7. Evaluate the transfer attempt for evidence that the misconception has actually been resolved.
8. If the misconception remains, return to Socratic guidance using a different unused angle.
9. If the available angles are exhausted or repeated failure continues, use the planned bounded escalation/tutoring path.

The pre-event angle categories include:

- `ELIMINATED_RANGE_PROOF` — reason about which elements are proven impossible after examining `mid`.
- `COUNTEREXAMPLE_ARRAY` — use a concrete array where a one-step update behaves differently from eliminating the ruled-out half.
- `INVARIANT_RESTATEMENT` — reason about what the search interval must represent after each iteration.
- `OPPOSITE_BRANCH_TRANSFER` — reason about the corresponding boundary update for the opposite comparison branch.

The purpose of the angle bank is to prevent superficial rewording of the same Socratic question from being treated as a genuinely new intervention.

## Pre-event agent/workflow design

The pre-event design included planned roles for the Boundary Loop:

- **Diagnostic** — identifies the likely misconception from student evidence.
- **Socratic** — produces a targeted Socratic intervention using an appropriate unused angle.
- **Transfer** — produces a fresh task that tests whether the student can apply the concept in a new situation.
- **Evaluator** — evaluates the student's response/transfer attempt and determines whether the misconception is still present.
- **Tutor** — provides bounded escalation when repeated Socratic intervention is insufficient.
- **Planner** — uses the student's persistent learning state to determine the next pedagogical step.

The planned implementation keeps the workflow deterministic: the Python control flow manages transitions, persistence, retry limits, and intervention selection rather than allowing an LLM to control the overall execution.

## What we are NOT bringing as pre-event implementation

We are not declaring a pre-event finished implementation of the Agent-a-Thon solution.

In particular, we are **not** bringing a completed pre-event:

- Boundary Loop application
- production frontend
- backend
- database
- authentication system
- pre-event student-testing results
- event-generated evaluation results

The implementation and testing of the system will be developed during the Agent-a-Thon.

## Pre-event datasets and external assets

No pre-event dataset was prepared specifically for this project.

The hackathon-provided `agentic-slice-kit` and its supporting infrastructure are being used as the event starter kit. Our Boundary Loop implementation will be developed on top of it during the event.
