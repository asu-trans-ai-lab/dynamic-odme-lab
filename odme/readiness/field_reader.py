"""TAPLite-faithful field reader.

Mirrors CDTACSVParser::GetValueByFieldName (TAPLite.h): the caller supplies a default,
and the value is overwritten ONLY on success. Missing column, empty cell, or parse
failure all keep the default and are recorded as a "filled" note (not an error).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IssueLog:
    """Collects everything the readiness check needs to report."""
    filled: dict = field(default_factory=dict)     # field_name -> count of rows defaulted
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)     # non-fatal, drop-the-row
    fatals: list = field(default_factory=list)     # READY = False

    def note_filled(self, field_name: str) -> None:
        self.filled[field_name] = self.filled.get(field_name, 0) + 1

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def fatal(self, msg: str) -> None:
        self.fatals.append(msg)

    @property
    def ready(self) -> bool:
        return not self.fatals


def get_value(row: dict, field_name: str, default, required: bool = False,
              nonneg: bool = False, log: IssueLog | None = None, row_tag: str = ""):
    """Return parsed value or `default`. `default`'s type drives coercion (int/float/str)."""
    raw = row.get(field_name, None)
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        if required and log is not None:
            log.error(f"missing required field '{field_name}'{(' at ' + row_tag) if row_tag else ''}")
        elif log is not None and not required:
            log.note_filled(field_name)
        return default
    try:
        if isinstance(default, bool):
            val = str(raw).strip().lower() in ("1", "true", "yes")
        elif isinstance(default, int):
            val = int(float(str(raw).strip()))
        elif isinstance(default, float):
            val = float(str(raw).strip())
        else:
            val = str(raw).strip()
    except (ValueError, TypeError):
        if log is not None:
            log.warn(f"could not parse '{field_name}'='{raw}'{(' at ' + row_tag) if row_tag else ''}; using default {default}")
        return default
    if nonneg and isinstance(val, (int, float)) and val < 0:
        return val  # keep but caller may treat <0 as sentinel (e.g. ref_volume)
    return val
