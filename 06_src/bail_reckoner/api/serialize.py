"""Serialize the frozen report/application dataclasses to JSON-able structures.

Explicit conversions, no repr tricks: dates become ISO strings, Fractions become their
string form ("1/3" stays exact — a float here would reintroduce the rounding this project
avoids), Enums become their VALUE (so the verdict travels as its full sentence, never a
shorthand — D-077 constraint 2), and Mappings become plain dicts.
"""

from __future__ import annotations

import dataclasses
import datetime
import enum
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

__all__ = ["to_jsonable"]


def to_jsonable(value: object) -> Any:  # noqa: ANN401 - genuinely polymorphic by design
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_jsonable(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    return value
