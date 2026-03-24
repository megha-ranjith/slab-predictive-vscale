#!/usr/bin/env python3
import sys
from pathlib import Path

# project root: one level above scripts/
ROOT = Path(__file__).resolve().parents[1]
# add src/ to sys.path so we can import serverless_sim, config, etc.
sys.path.insert(0, str(ROOT / "src"))

from serverless_sim import main

if __name__ == "__main__":
    main()
