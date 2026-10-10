import sys
from pathlib import Path

# Make `import ffdata` work when running `pytest` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
