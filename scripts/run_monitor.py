#!/usr/bin/env python3
import sys
from pathlib import Path

# project root: one level above scripts/
ROOT = Path(__file__).resolve().parents[1]
# add src/ to sys.path so we can import controller, config, etc.
sys.path.insert(0, str(ROOT / "src"))

from controller import Controller
from config import Config

def main():
    cfg_path = ROOT / "config.yaml"
    cfg = Config(str(cfg_path))
    controller = Controller(cfg)
    controller.run()

if __name__ == "__main__":
    main()
