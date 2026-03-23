#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import Config
from controller import Controller

def main():
    cfg_path = Path(__file__).resolve().parents[1] / "config.yaml"
    cfg = Config(str(cfg_path))
    controller = Controller(cfg)
    controller.run()

if __name__ == "__main__":
    main()
