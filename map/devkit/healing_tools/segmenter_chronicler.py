#!/usr/bin/env python3
"""
segmenter_blocks.py (The Chronicler Edition - Phase 8.0)

This script reads files from the RAW archive and splits them into semantic blocks.
It respects the Sacred Vectors of the Kingdom (GENESIS, COVENANT, CHRONICLE, PSALM, LAW).

Features:
* Smart Slicing: Cuts text at sentence boundaries (spaces/newlines), not mid-word.
* Divine Sorting: Assigns a Sacred Vector to each block based on vocabulary.
* Integrity: Enforces strict limits but preserves meaning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

# Import the Sacred Vocabulary
try:
    from kingdom_vocabulary import discern_vector
except ImportError:
    # Fallback if not yet deployed
    def discern_vector(text, fname): return "UNKNOWN"

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Segment RAW archive files into smaller blocks for analysis."
    )
    parser.add_argument("--archive", required=True, help="Path to the archive root.")
    parser.add_argument("--profile", default="analysis", help="Name of the segmentation profile.")
    parser.add_argument("--max-chars-per-block", type=int, default=20000)
    parser.add_argument("--max-bytes-per-block", type=int, default=1000000)
    return parser.parse_args()

def setup_logging(archive_root: Path) -> None:
    logs_dir = archive_root / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "segmenter.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        handlers=[logging.FileHandler(log_file, encoding="utf-8")],
    )

def sanitize_name(name: str) -> str:
    base = name.replace(os.sep, "_").replace("/", "_")
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", base)
    base = base.strip(" .")
    return base or "unnamed"

class FileLock:
    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self._fd: Optional[int] = None

    def acquire(self, wait: bool = False, interval: float = 0.1) -> bool:
        while True:
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            except FileExistsError:
                if not wait: return False
                time.sleep(interval)
            else:
                self._fd = fd
                return True

    def release(self) -> None:
        if self._fd is not None:
            try: os.close(self._fd)
            except Exception: pass
            self._fd = None
        try: self.lock_path.unlink(missing_ok=True)
        except Exception: pass

    def __enter__(self) -> "FileLock":
        if not self.acquire(wait=True):
            raise RuntimeError(f"Could not acquire lock {self.lock_path}")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()

def load_processed_files(index_path: Path) -> Tuple[set[Tuple[str, str]], set[str]]:
    processed_pairs: set[Tuple[str, str]] = set()
    legacy_dirs: set[str] = set()
    if index_path.exists():
        try:
            with index_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try:
                        obj = json.loads(line)
                        src = obj.get("src_file")
                        source_blob = obj.get("source_blob")
                        if src and source_blob: processed_pairs.add((src, source_blob))
                        elif src: legacy_dirs.add(src)
                    except json.JSONDecodeError: continue
        except Exception as exc:
            logging.warning("Failed to read blocks index: %s", exc)
    return processed_pairs, legacy_dirs

def detect_language(text: str) -> str:
    if re.search(r"[\u0400-\u04FF]", text): return "ru"
    markers = ["de", "het", "je", "hij", "zij", "een", "niet", "als", "met", "voor", "naar", "ik", "wij"]
    lower = text.lower()
    words = set(re.findall(r"[a-zA-Z]+", lower))
    count = sum(1 for m in markers if m in words)
    return "nl" if count >= 3 else "en"

def extract_tags(text: str) -> List[str]:
    tags = set()
    # Expanded vocabulary for Phase 8.0
    vocabulary = r"tech|plan|dialog|ethics|core|vector|learning|fixation|contract|protocol|genesis|covenant|psalm"
    for match in re.finditer(rf"\b({vocabulary})\b", text, re.IGNORECASE):
        tags.add(match.group(1).lower())
    return sorted(tags)

def split_into_blocks(text: str, max_chars: int, max_bytes: int) -> List[str]:
    """
    Smart Slicing: Splits text preserving sentence boundaries.
    """
    blocks: List[str] = []
    if not text: return blocks
    
    start = 0
    
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end]
        
        while len(chunk.encode("utf-8")) > max_bytes:
            end = int((end + start) / 2)
            chunk = text[start:end]
            
        if end == len(text):
            blocks.append(chunk)
            break
            
        lookback_limit = min(500, int(len(chunk) * 0.1))
        found_split = False
        
        for i in range(1, lookback_limit):
            char_idx = end - i
            if text[char_idx] in " 
	.,;:?!":
                split_point = char_idx + 1
                blocks.append(text[start:split_point].strip())
                start = split_point
                found_split = True
                break
        
        if not found_split:
            blocks.append(chunk)
            start = end
            
    return [b for b in blocks if b]

def process_file(
    archive_root: Path,
    raw_file: Path,
    rel_path: str,
    blocks_index_path: Path,
    blocks_dir: Path,
    max_chars: int,
    max_bytes: int,
) -> int:
    try:
        content = raw_file.read_bytes()
    except Exception as e:
        logging.error(f"Failed to read {raw_file}: {e}")
        return 0

    # Binary check (simple)
    if b"\0" in content[:8000]:
        return 0

    text = None
    for enc in ["utf-8", "utf-16", "cp1251", "latin1"]:
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    
    if text is None:
        text = content.decode("utf-8", errors="replace")
        status = "damaged"
    else:
        status = "ok"

    blocks = split_into_blocks(text, max_chars, max_bytes)
    vector = discern_vector(text[:5000], rel_path)
    
    base_id = hashlib.sha256(rel_path.encode("utf-8")).hexdigest()[:16]
    
    for idx, block_text in enumerate(blocks):
        block_id = f"{base_id}_{idx:04d}"
        
        meta = {
            "block_id": block_id,
            "src_file": rel_path,
            "seq": idx + 1,
            "total_seqs": len(blocks),
            "vector": vector,
            "tags": extract_tags(block_text),
            "lng": detect_language(block_text),
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "text": block_text
        }
        
        save_dir = blocks_dir / sanitize_name(Path(rel_path).parent.name)
        save_dir.mkdir(parents=True, exist_ok=True)
        block_path = save_dir / f"{block_id}.json"
        
        with open(block_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
            
        with FileLock(blocks_index_path.parent / "index.lock"):
            with open(blocks_index_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "id": block_id, 
                    "src": rel_path, 
                    "vector": vector, 
                    "path": str(block_path.relative_to(archive_root))
                }, ensure_ascii=False) + "
")
                
    return len(blocks)

if __name__ == "__main__":
    args = parse_arguments()
    archive_root = Path(args.archive)
    setup_logging(archive_root)
    # The main loop would be here, but for this patching operation,
    # we establish the library functions.
    pass
