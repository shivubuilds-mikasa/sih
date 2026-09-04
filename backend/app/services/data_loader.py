"""Data loading service for SHARMI demo dataset."""

import json
from pathlib import Path
from typing import Optional

from ..models.domain import DemoDataset


class DataLoader:
    """Loads and validates the Shivapur demo dataset."""

    def __init__(self, data_path: Optional[str] = None) -> None:
        if data_path is None:
            # Locate data directory relative to this file (project root)
            base_dir = Path(__file__).resolve().parents[3]
            data_path = str(base_dir / "data" / "demo_data.json")
        self._data_path = Path(data_path)
        self._dataset: Optional[DemoDataset] = None

    def load(self) -> DemoDataset:
        """Load and validate the demo dataset."""
        if self._dataset is not None:
            return self._dataset

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