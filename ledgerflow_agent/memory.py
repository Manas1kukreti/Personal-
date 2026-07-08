from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

MEMORY_PATH = Path(__file__).resolve().parent / "runtime_memory.json"
ARCHIVE_PATH = Path(__file__).resolve().parent / "memory_archive.jsonl"
MAX_RECENT_RUNS = 20
MAX_TOP_ITEMS = 10
# When recent_runs exceeds this, the oldest entries are flushed to the archive.
ARCHIVE_THRESHOLD = 30

DEFAULT_MEMORY: dict[str, Any] = {
    "version": 1,
    "run_count": 0,
    "last_run_at": None,
    "uploads": {"success": 0, "failed": 0},
    "entities": {},
    "validation_failures": {},
    "recent_runs": [],
    "user_preferences": {},
}


def load_memory() -> dict[str, Any]:
    if not MEMORY_PATH.exists():
        return deepcopy(DEFAULT_MEMORY)

    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as memory_file:
            data = json.load(memory_file)
    except Exception:
        return deepcopy(DEFAULT_MEMORY)

    memory = deepcopy(DEFAULT_MEMORY)
    if isinstance(data, dict):
        memory.update(data)
    return memory



def save_memory(memory: dict[str, Any]) -> None:
    with open(MEMORY_PATH, "w", encoding="utf-8") as memory_file:
        json.dump(memory, memory_file, indent=2, default=str)



def _extract_rows(state: dict[str, Any]) -> list[dict[str, Any]]:
    validation_result = state.get("validation_result") or {}
    rows = validation_result.get("data") or []
    return [row for row in rows if isinstance(row, dict)]



def _extract_entities(rows: list[dict[str, Any]]) -> Counter:
    counter: Counter = Counter()
    candidate_fields = ("merchant", "party_name", "sub_account", "account", "details")

    for row in rows:
        for field in candidate_fields:
            value = str(row.get(field, "")).strip()
            if value:
                counter[f"{field}:{value}"] += 1
                break

    return counter



def _extract_failure_signatures(state: dict[str, Any]) -> Counter:
    counter: Counter = Counter()
    validation_result = state.get("validation_result") or {}
    for error in validation_result.get("errors", []):
        message = str(error.get("error", "unknown_error")).strip()
        if message:
            counter[message] += 1
    return counter



def summarise_memory(memory: dict[str, Any]) -> dict[str, Any]:
    entities = Counter(memory.get("entities") or {})
    failures = Counter(memory.get("validation_failures") or {})
    recent_runs = list(memory.get("recent_runs") or [])[-5:]

    return {
        "run_count": int(memory.get("run_count", 0)),
        "last_run_at": memory.get("last_run_at"),
        "top_entities": entities.most_common(5),
        "top_validation_failures": failures.most_common(5),
        "recent_runs": recent_runs,
        "user_preferences": dict(memory.get("user_preferences") or {}),
    }



def update_memory(memory: dict[str, Any], state: dict[str, Any], final_output: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(memory)
    updated["run_count"] = int(updated.get("run_count", 0)) + 1
    updated["last_run_at"] = final_output.get("completed_at")

    upload_status = str((state.get("ui_result") or {}).get("status", "")).lower()
    if upload_status == "success":
        updated["uploads"]["success"] = int(updated["uploads"].get("success", 0)) + 1
    elif upload_status:
        updated["uploads"]["failed"] = int(updated["uploads"].get("failed", 0)) + 1

    entity_counter = Counter(updated.get("entities") or {})
    entity_counter.update(_extract_entities(_extract_rows(state)))
    updated["entities"] = dict(entity_counter.most_common(MAX_TOP_ITEMS))

    failure_counter = Counter(updated.get("validation_failures") or {})
    failure_counter.update(_extract_failure_signatures(state))
    updated["validation_failures"] = dict(failure_counter.most_common(MAX_TOP_ITEMS))

    preferences = dict(updated.get("user_preferences") or {})
    preferences.update(dict(state.get("user_preferences") or {}))
    updated["user_preferences"] = preferences

    recent_runs = list(updated.get("recent_runs") or [])
    recent_runs.append(
        {
            "completed_at": final_output.get("completed_at"),
            "status": final_output.get("status"),
            "tools_used": list(final_output.get("tools_used") or []),
            "upload_status": (state.get("ui_result") or {}).get("status"),
            "validation_error_count": len((state.get("validation_result") or {}).get("errors", [])),
        }
    )
    updated["recent_runs"] = recent_runs[-MAX_RECENT_RUNS:]
    return updated


def archive_memory() -> int:
    """Flush the oldest recent_runs entries to memory_archive.jsonl to prevent
    runtime_memory.json from bloating over many pipeline runs.

    Returns the number of entries archived.
    """
    memory = load_memory()
    recent_runs = list(memory.get("recent_runs") or [])

    if len(recent_runs) <= ARCHIVE_THRESHOLD:
        return 0

    # Entries beyond ARCHIVE_THRESHOLD are moved to the archive file.
    to_archive = recent_runs[:-MAX_RECENT_RUNS]
    memory["recent_runs"] = recent_runs[-MAX_RECENT_RUNS:]

    with open(ARCHIVE_PATH, "a", encoding="utf-8") as archive_file:
        for entry in to_archive:
            archive_file.write(json.dumps(entry, default=str) + "\n")

    save_memory(memory)
    print(f"[Memory] Archived {len(to_archive)} old run(s) to {ARCHIVE_PATH}")
    return len(to_archive)
