from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Type, TypeVar

from pydantic import BaseModel, TypeAdapter

T = TypeVar("T", bound=BaseModel)


def read_csv_rows(path: Path, model: Type[T]) -> list[T]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        raw: Iterable[dict] = list(reader)
    adapter = TypeAdapter(list[model])
    return adapter.validate_python(raw)
