import sys
from pathlib import Path

LABELS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LABELS))


def pytest_configure(config):
    # temporary files stay in the work folder of this part unless --basetemp is given
    if not config.option.basetemp:
        config.option.basetemp = str(LABELS.parent / "work" / "labels" / "pytest-tmp")
