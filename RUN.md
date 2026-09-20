# Run the judge demo

From the repository root:

```powershell
python -m venv venv
venv\Scripts\activate
 python -m pip install -r requirements.txt
python -m pip install flask

python run_web.py
```

Then open http://127.0.0.1:5000/chatbot in a browser.
The demonstrated flow is:

1. Student provides a DSA question/problem and their reasoning or code.
2. Classifier identifies the DSA concept/subconcept.
3. Diagnostic identifies the student's misconception and required reasoning invariant.
4. Socratic Agent guides the student with targeted questions instead of immediately giving the answer.
5. Evaluator checks the student's reasoning after each attempt.
6. If the misconception remains, the workflow continues with another Socratic angle.
7. After repeated failure, the workflow can move backward to a simpler reasoning level before continuing.
8. Once the reasoning is demonstrated, a fresh transfer problem checks whether the student can apply the concept independently.
9. The learning/run state and evidence are recorded for the session.

## Environment

Run from the repository root with the project's Python environment activated.

If the project uses an environment variable for the configured model/API provider, set it before running the command.
