"""
Streamlit entry point: dashboard/app.py
Delegates directly to unified_dashboard.py
"""

import os
import sys

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import unified_dashboard

if __name__ == "__main__":
    unified_dashboard.main()
