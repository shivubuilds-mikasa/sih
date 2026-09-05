"""Data loading service for SHARMI demo dataset."""

import json
import os
from pathlib import Path
from typing import Optional

from ..models.domain import DemoDataset


class DataLoader:
    """Loads and validates the Shivapur demo dataset."""

    def __init__(self, data_path: Optional[str] = None) -> None:
        if data_path is None:
            data_path = self._resolve_data_path()
        self._data_path = Path(data_path)
        self._dataset: Optional[DemoDataset] = None

    def _resolve_data_path(self) -> str:
        """Resolve the data file path with multiple fallback strategies."""
        # Strategy 1: Environment variable (highest priority for deployment)
        env_path = os.environ.get("SHARMI_DATA_PATH")
        if env_path and Path(env_path).exists():
            return env_path

        # Strategy 2: Relative to this file (local development)
        # data_loader.py -> services -> app -> backend -> project_root
        base_dir = Path(__file__).resolve().parents[3]
        local_path = base_dir / "data" / "demo_data.json"
        if local_path.exists():
            return str(local_path)

        # Strategy 3: Docker/Render standard location
        docker_path = Path("/app/data/demo_data.json")
        if docker_path.exists():
            return str(docker_path)

        # Strategy 4: Current working directory /data
        cwd_path = Path.cwd() / "data" / "demo_data.json"
        if cwd_path.exists():
            return str(cwd_path)

        # Fallback: return the local development path (will error clearly if not found)
        return str(local_path)

    def load(self) -> DemoDataset:
        """Load and validate the demo dataset."""
        if self._dataset is not None:
            return self._dataset

        if not self._data_path.exists():
            raise FileNotFoundError(
                f"Demo data file not found at {self._data_path}. "
                f"Set SHARMI_DATA_PATH environment variable or ensure data/demo_data.json exists."
            )

        with self._data_path.open("r", encoding="utf-8") as f:
            raw_data = json.load(f)

        self._dataset = DemoDataset.model_validate(raw_data)
        return self._dataset

    def get_dataset(self) -> DemoDataset:
        """Get the loaded dataset, loading it first if necessary."""
        if self._dataset is None:
            return self.load()
        return self._dataset

    def reload(self) -> DemoDataset:
        """Force reload the dataset from disk."""
        self._dataset = None
        return self.load()


# Module-level instance for easy access
_data_loader: Optional[DataLoader] = None


def get_data_loader() -> DataLoader:
    """Get the global data loader instance."""
    global _data_loader
    if _data_loader is None:
        _data_loader = DataLoader()
    return _data_loader