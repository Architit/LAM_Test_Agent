# -*- coding: utf-8 -*-
"""Core memory management for LAM (HEALED - Phase 8.0)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
import os
import tomllib
from math import sqrt

from opentelemetry import trace
from .logging_utils import get_json_logger
from .lam_logging import log as lam_log

REPO_ROOT = Path(__file__).resolve().parent.parent
logger = get_json_logger(__name__)
tracer = trace.get_tracer(__name__)

try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except Exception as e:
    logger.warning("FAISS not available, vector indexing disabled", extra={"error": str(e)})
    FAISS_AVAILABLE = False

DEFAULT_MEMORY_PATH = REPO_ROOT / "memory"

def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _update_paths(base: Path) -> Dict[str, Path]:
    base = base.expanduser()
    return {
        "base_path": base,
        "log_dir": base / "logs",
        "metadata_dir": base / "metadata",
        "data_dir": base / "data",
        "archive_dir": base / "archive",
        "memory_file": base / "data" / "memory_items.json",
        "category_file": base / "metadata" / "categories.json",
        "anchor_file": base / "metadata" / "anchor_memory_phase.json",
    }

def _load_memory_path() -> Path:
    base = None
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" not in line or line.strip().startswith("#"): continue
            key, value = line.split("=", 1)
            if key.strip() == "LAM_MEMORY_PATH":
                base = value.strip()
                break
    base = os.getenv("LAM_MEMORY_PATH", base)
    if not base:
        pyproject = REPO_ROOT / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject, "rb") as fh:
                data = tomllib.load(fh)
            base = data.get("tool", {}).get("lam", {}).get("memory_path")
    if base:
        path = Path(base).expanduser()
        return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()
    return DEFAULT_MEMORY_PATH

@dataclass
class MemoryEntry:
    id: str
    name: str
    timestamp: str
    content: str
    importance: float
    associations: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    embedding: List[float] = field(default_factory=list)
    last_access: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "MemoryEntry":
        return MemoryEntry(**data)

class MemoryCore:
    def __init__(self, memory_path: Optional[Path] | None = None) -> None:
        if memory_path is None: memory_path = _load_memory_path()
        paths = _update_paths(Path(memory_path))
        self.base_path = paths["base_path"].resolve()
        self.log_dir = paths["log_dir"]
        self.metadata_dir = paths["metadata_dir"]
        self.data_dir = paths["data_dir"]
        self.archive_dir = paths["archive_dir"]
        self.memory_file = paths["memory_file"]
        self.category_file = paths["category_file"]
        self.anchor_file = paths["anchor_file"]

        for d in [self.base_path, self.log_dir, self.metadata_dir, self.data_dir, self.archive_dir]:
            d.mkdir(parents=True, exist_ok=True)

        if self.memory_file.exists():
            with open(self.memory_file, "r", encoding="utf-8") as fh:
                self._memories = [MemoryEntry.from_dict(m) for m in json.load(fh)]
        else:
            self._memories = []

        self.categories = {}
        if self.category_file.exists():
            with open(self.category_file, "r", encoding="utf-8") as fh:
                self.categories = json.load(fh)
        else:
            for mem in self._memories: self.categorize(mem)
            self._save()

        self._index = None
        self._index_map = []
        self._build_index()

    def get_memories(self) -> List[MemoryEntry]:
        return list(self._memories)

    def _save(self) -> None:
        with open(self.memory_file, "w", encoding="utf-8") as fh:
            json.dump([m.to_dict() for m in self._memories], fh, ensure_ascii=False, indent=2)
        with open(self.category_file, "w", encoding="utf-8") as fh:
            json.dump(self.categories, fh, ensure_ascii=False, indent=2)

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    def generate_tags(self, content: str) -> List[str]:
        words = [w.strip(".,!?;:") for w in content.split()]
        return list({w.lower() for w in words if len(w) > 3})

    def categorize(self, memory_entry: MemoryEntry) -> None:
        for tag in memory_entry.tags:
            if tag not in self.categories: self.categories[tag] = []
            self.categories[tag].append(memory_entry.id)

    def _build_index(self) -> None:
        if not FAISS_AVAILABLE or not any(m.embedding for m in self._memories):
            self._index = None
            self._index_map = []
            return
        embeddings = [m.embedding for m in self._memories if m.embedding]
        dim = len(embeddings[0])
        self._index = faiss.IndexFlatIP(dim)
        xb = np.array(embeddings, dtype="float32")
        faiss.normalize_L2(xb)
        self._index.add(xb)
        self._index_map = [m.id for m in self._memories if m.embedding]

    def add_memory(self, memory_entry: Dict[str, Any]) -> None:
        memory_entry.setdefault("id", self._generate_id())
        with tracer.start_as_current_span("add_memory"):
            logger.info("add_memory", extra={"entry": memory_entry["id"]})
        memory_entry.setdefault("tags", self.generate_tags(memory_entry.get("content", "")))
        memory_entry.setdefault("importance", 0.5)
        mem = MemoryEntry.from_dict(memory_entry)
        lam_log("info", "mem.write", "add_memory", memory_id=mem.id, tags_count=len(mem.tags or []), has_embedding=bool(mem.embedding))
        self.categorize(mem)
        self._memories.append(mem)
        self._save()
        self._build_index()

    def retrieve_memory(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        with tracer.start_as_current_span("retrieve_memory"):
            logger.info("retrieve_memory", extra={"criteria": criteria})
        for mem in self._memories:
            match = True
            if "time_range" in criteria and not mem.timestamp.startswith(criteria["time_range"]): match = False
            if "tags" in criteria and not set(criteria["tags"]).intersection(mem.tags): match = False
            if "associations" in criteria and not set(criteria["associations"]).intersection(mem.associations): match = False
            if match:
                mem.access_count += 1
                mem.last_access = datetime.now(timezone.utc).isoformat()
                results.append(mem)
        lam_log("info", "mem.read", "retrieve_memory", criteria_keys=sorted(list(criteria.keys())) if isinstance(criteria, dict) else None, results_count=len(results))
        self._save()
        return [m.to_dict() for m in results]

    def retrieve_by_embedding(self, embedding: List[float], k: int = 1) -> List[Dict[str, Any]]:
        with tracer.start_as_current_span("retrieve_by_embedding"):
            logger.info("retrieve_by_embedding", extra={"k": k})
        if not FAISS_AVAILABLE or self._index is None:
            scored = []
            norm_q = sqrt(sum(v * v for v in embedding)) or 1.0
            for mem in self._memories:
                if not mem.embedding: continue
                dot = sum(a * b for a, b in zip(embedding, mem.embedding))
                norm_m = sqrt(sum(v * v for v in mem.embedding)) or 1.0
                score = dot / (norm_q * norm_m)
                scored.append((score, mem))
            scored.sort(key=lambda x: x[0], reverse=True)
            top = [m for _, m in scored[:k] if _ >= 0]
        else:
            xq = np.array([embedding], dtype="float32")
            faiss.normalize_L2(xq)
            distances, indices = self._index.search(xq, k)
            top = []
            for idx in indices[0]:
                if idx == -1: continue
                mem = next((m for m in self._memories if m.id == self._index_map[idx]), None)
                if mem: top.append(mem)
        for mem in top:
            mem.access_count += 1
            mem.last_access = datetime.now(timezone.utc).isoformat()
        lam_log("info", "mem.search", "retrieve_by_embedding", k=k, results_count=len(top), faiss=bool(FAISS_AVAILABLE and self._index is not None))
        self._save()
        return [m.to_dict() for m in top]

    def update_importance(self) -> None:
        now = datetime.now(timezone.utc)
        for mem in self._memories:
            try: ts = datetime.fromisoformat(mem.timestamp.replace("≈", ""))
            except ValueError: continue
            age_days = (now - _to_utc(ts)).days
            decay = age_days / 365
            mem.importance = max(0.0, min(1.0, mem.importance * (1 - decay) + min(mem.access_count / 10, 1) * 0.1))
        self._save()

    def forget(self, min_importance: float = 0.2, max_age: Optional[str] = None) -> None:
        now = datetime.now(timezone.utc)
        keep = []
        archived_count = 0
        for mem in self._memories:
            forget_by_importance = mem.importance < min_importance
            forget_by_age = False
            if max_age:
                try:
                    ts = datetime.fromisoformat(mem.timestamp.replace("≈", ""))
                    if (now - _to_utc(ts)).days > int(max_age): forget_by_age = True
                except ValueError: pass
            if forget_by_importance or forget_by_age:
                self._archive_item(mem)
                archived_count += 1
                continue
            keep.append(mem)
        if archived_count > 0:
            lam_log("info", "mem.archive", f"Moved {archived_count} items to cold storage", count=archived_count)
        self._memories = keep
        self._save()
        self._build_index()

    def _archive_item(self, mem: MemoryEntry) -> None:
        try:
            dt = _to_utc(datetime.fromisoformat(mem.timestamp.replace("≈", "")))
            partition = self.archive_dir / dt.strftime("%Y/%m")
            partition.mkdir(parents=True, exist_ok=True)
            with open(partition / f"{mem.id}.json", "w", encoding="utf-8") as f:
                json.dump(mem.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("archive_item_failed", extra={"error": str(e), "id": mem.id})

    def integrity_check(self) -> bool:
        return all(0.0 <= mem.importance <= 1.0 for mem in self._memories)

__all__ = ["MemoryCore", "MemoryEntry"]
