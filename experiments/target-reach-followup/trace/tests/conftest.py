import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))                          # trace/
sys.path.insert(0, str(HERE.parents[2] / "target-reach"))     # the toolkit

collect_ignore = ["fixture"]
