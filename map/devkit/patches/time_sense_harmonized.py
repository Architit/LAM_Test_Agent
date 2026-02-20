# -*- coding: utf-8 -*-
"""Utility class for parsing and comparing fuzzy timestamps (Harmonized - Phase 8.0)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

@dataclass
class ParsedTime:
    base: Optional[datetime]
    approx: bool = False
    tolerance: int = 0  # in minutes
    fuzzy: Optional[str] = None
    duration: Optional[timedelta] = None

class TimeSense:
    EXACT_RE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})\s*:\s*(\d{2}):(\d{2})$")
    APPROX_RE = re.compile(r"^≈(\d{2})\.(\d{2})\.(\d{4})\s*:\s*≈?(\d{2})$")
    INTERVAL_RE = re.compile(r"^Δ\[(\d{2})\.(\d{2})\.(\d{4}):(\d{2}):(\d{2})±(\d+)мин\]$")
    FUZZY_RE = re.compile(r"^≈([а-яА-Яa-zA-Z/_]+)$")
    DURATION_RE = re.compile(r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$")

    DEFAULT_APPROX_TOLERANCE = 60

    def parse(self, timestamp: str) -> ParsedTime:
        timestamp = timestamp.strip()
        m = self.EXACT_RE.match(timestamp)
        if m:
            dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), int(m.group(4)), int(m.group(5)))
            return ParsedTime(base=dt)
        m = self.APPROX_RE.match(timestamp)
        if m:
            dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), int(m.group(4)))
            return ParsedTime(base=dt, approx=True, tolerance=self.DEFAULT_APPROX_TOLERANCE)
        m = self.INTERVAL_RE.match(timestamp)
        if m:
            dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), int(m.group(4)), int(m.group(5)))
            return ParsedTime(base=dt, tolerance=int(m.group(6)))
        m = self.FUZZY_RE.match(timestamp)
        if m: return ParsedTime(base=None, fuzzy=m.group(1))
        m = self.DURATION_RE.match(timestamp)
        if m:
            delta = timedelta(days=int(m.group("days") or 0), hours=int(m.group("hours") or 0), minutes=int(m.group("minutes") or 0), seconds=int(m.group("seconds") or 0))
            return ParsedTime(base=None, duration=delta)
        raise ValueError(f"Unrecognized timestamp format: {timestamp}")

    def generate_fuzzy(self, exact_time: datetime | str) -> str:
        if isinstance(exact_time, str):
            exact_base = self.parse(exact_time).base
            if exact_base is None: raise ValueError("Exact time required")
            exact_time = exact_base
        hour = exact_time.hour
        if 0 <= hour < 6: return "≈ночь"
        if 6 <= hour < 12: return "≈утро"
        if 12 <= hour < 18: return "≈день"
        return "≈вечер"

    def humanize(self, value: datetime | timedelta, reference: datetime | None = None) -> str:
        if isinstance(value, datetime):
            if value.tzinfo is None: value = value.replace(tzinfo=timezone.utc)
            reference = reference or datetime.now(timezone.utc)
            if reference.tzinfo is None: reference = reference.replace(tzinfo=timezone.utc)
            delta = value - reference
        else:
            delta = value
        seconds = int(delta.total_seconds())
        past = seconds < 0
        seconds = abs(seconds)
        if seconds < 60: num, unit = seconds, "секунда"
        elif seconds < 3600: num, unit = seconds // 60, "минута"
        elif seconds < 86400: num, unit = seconds // 3600, "час"
        else: num, unit = seconds // 86400, "день"
        
        # Минимальная русская грамматика для чистоты
        if num % 10 == 1 and num % 100 != 11: suffix = ""
        elif 2 <= num % 10 <= 4 and (num % 100 < 10 or num % 100 >= 20): suffix = "ы" if unit != "час" else "а"
        else: suffix = "секунд" if unit == "секунда" else "минут" if unit == "минута" else "часов" if unit == "час" else "дней"
        
        if unit == "секунда" and suffix == "секунд": res = f"{num} секунд"
        elif unit == "минута" and suffix == "минут": res = f"{num} минут"
        else: res = f"{num} {unit}{suffix}"

        return f"{res} назад" if past else f"через {res}"

__all__ = ["TimeSense", "ParsedTime"]
