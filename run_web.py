"""
Entry point to run the THINKAGAIN Flask Web Application.

Usage:
  python run_web.py
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from web.app import create_app

app = create_app()

if __name__ == "__main__":
    print("=" * 60)
    print("THINKAGAIN — Adaptive Multi-Agent DSA Tutoring Web UI")
    print("Open http://127.0.0.1:5000/chatbot in your browser")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True)
