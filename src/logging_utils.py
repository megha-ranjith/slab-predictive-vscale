import logging
from pathlib import Path

def setup_logger(name: str, log_dir: Path, to_stdout: bool = True) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )

    fh = logging.FileHandler(log_dir / f"{name}.log")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    if to_stdout:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)

    return logger
