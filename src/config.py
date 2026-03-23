import yaml
from pathlib import Path

class Config:
    def __init__(self, path: str = "config.yaml"):
        self._path = Path(path)
        with self._path.open() as f:
            self._cfg = yaml.safe_load(f)

    def __getitem__(self, item):
        return self._cfg[item]

    @property
    def sampling_interval_sec(self) -> float:
        return self._cfg["sampling_interval_ms"] / 1000.0

    @property
    def slab_caches(self):
        return self._cfg["slab_caches_of_interest"]

    @property
    def cgroup_root(self) -> Path:
        return Path(self._cfg["cgroup_root"])

    @property
    def functions_parent(self) -> str:
        return self._cfg["functions_parent"]

    @property
    def functions(self):
        return self._cfg["functions"]

    @property
    def vertical(self):
        return self._cfg["vertical_scaling"]

    @property
    def prediction(self):
        return self._cfg["prediction"]

    @property
    def logging_dir(self) -> Path:
        return Path(self._cfg["logging"]["base_dir"])
