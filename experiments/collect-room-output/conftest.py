"""Keep experiment imports independent of other instrument module names."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
