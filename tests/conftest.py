"""
Shared pytest setup: puts the repo root on sys.path so tests import
project modules exactly the way the app does (from brain import ...),
no packaging or install step needed.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
