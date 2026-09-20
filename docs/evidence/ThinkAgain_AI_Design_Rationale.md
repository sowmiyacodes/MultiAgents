# Design Rationale — ThinkAgain AI
### Team: MultiAgents

## 1. What It Does

ThinkAgain AI is an AI-powered learning tutor that helps students understand Data Structures and Algorithms through guided questions instead of directly giving answers. It identifies mistakes in a student's explanation or code and provides step-by-step hints to help them think, correct their understanding, and learn independently.

## 2. Why This Shape

We chose a focused learning experience instead of building a general-purpose coding platform. We deliberately did not include a complete online coding judge, a large programming language compiler, or coverage of every DSA topic because our main goal is to identify misconceptions and improve the student's reasoning.

We designed the system around multiple learning stages, including misconception detection, Socratic questioning, progressive hints, and transfer tasks. This allows the tutor to check whether a student has genuinely understood a concept rather than simply memorising the correct answer.

## 3. What It Can't Do

The current system supports selected DSA concepts, including Binary Search, Two Pointers, Sliding Window, and Linked Lists. It may not correctly understand every programming language, complex code structure, or unclear explanation provided by a student.

The tutor also depends on the AI model's interpretation of the student's response, so it may occasionally classify a misconception incorrectly or provide an unsuitable hint. It is a learning assistant, not a replacement for a teacher or a complete code execution and verification system.

## 4. What We'd Do Next

Our next step would be to expand support for more DSA concepts and programming languages while improving misconception detection using a larger collection of student mistakes. We would also add code execution, stronger evaluation of student answers, learning progress tracking, and a visual dashboard for teachers.

These improvements would help ThinkAgain AI move from a focused prototype into a more reliable and personalised learning platform.
