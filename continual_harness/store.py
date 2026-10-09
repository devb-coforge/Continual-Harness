from __future__ import annotations

import hashlib
import math
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from renters_benchmark.core import canonical, read_json


class Store:
    def __init__(self, directory: Path, *, create: bool = False):
        self.directory = directory.resolve()
        if create:
            self.directory.mkdir(parents=True, exist_ok=False)
        elif not (self.directory / "runs.sqlite3").is_file():
            raise ValueError("No experiment database at this path")
        self.db = sqlite3.connect(self.directory / "runs.sqlite3")
        self.db.executescript("""
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS prompts (
                id TEXT PRIMARY KEY, strategy TEXT NOT NULL, parent TEXT REFERENCES prompts(id),
                rationale TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS calls (
                id TEXT PRIMARY KEY, role TEXT NOT NULL, phase TEXT NOT NULL,
                prompt_id TEXT REFERENCES prompts(id), task_id TEXT, repetition INTEGER,
                status TEXT NOT NULL, artifact TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS evaluations (
                phase TEXT NOT NULL, prompt_id TEXT REFERENCES prompts(id), task_id TEXT NOT NULL,
                repetition INTEGER NOT NULL, result TEXT NOT NULL,
                PRIMARY KEY (phase, prompt_id, task_id, repetition));
            CREATE TABLE IF NOT EXISTS comparisons (
                phase TEXT PRIMARY KEY, result TEXT NOT NULL);
        """)
        (self.directory / "calls").mkdir(exist_ok=True)

    def close(self) -> None:
        self.db.close()

    def put(self, key: str, value: Any) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)", (key, canonical(value)))

    def get(self, key: str) -> Any:
        import json
        row = self.db.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
        if row is None:
            raise ValueError(f"Missing experiment metadata: {key}")
        return json.loads(row[0])

    def prompt(self, strategy: str, parent: str | None = None, rationale: str = "Baseline") -> str:
        prompt_id = hashlib.sha256(strategy.encode()).hexdigest()
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO prompts VALUES (?, ?, ?, ?)",
                            (prompt_id, strategy, parent, rationale))
        return prompt_id

    def strategy(self, prompt_id: str) -> str:
        row = self.db.execute("SELECT strategy FROM prompts WHERE id = ?", (prompt_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown prompt")
        return row[0]

    def call(self, role: str, phase: str, prompt_id: str | None, task_id: str | None,
             repetition: int | None, artifact: dict[str, Any]) -> None:
        call_id = uuid.uuid4().hex
        relative = f"calls/{call_id}.json"
        (self.directory / relative).write_text(canonical(artifact) + "\n")
        with self.db:
            self.db.execute("INSERT INTO calls VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (call_id, role, phase, prompt_id, task_id, repetition,
                             artifact["status"], relative))

    def evaluation(self, phase: str, prompt_id: str, result: dict[str, Any]) -> None:
        with self.db:
            self.db.execute("INSERT INTO evaluations VALUES (?, ?, ?, ?, ?)",
                            (phase, prompt_id, result["task_id"], result["repetition"], canonical(result)))

    def comparison(self, phase: str, result: dict[str, Any]) -> None:
        with self.db:
            self.db.execute("INSERT INTO comparisons VALUES (?, ?)", (phase, canonical(result)))

    def reserve_test(self) -> None:
        # Atomic reservation survives interrupted or failed runs. Test outcomes cannot select a new prompt.
        try:
            with self.db:
                self.db.execute("INSERT INTO metadata VALUES ('test_started', 'true')")
        except sqlite3.IntegrityError as exc:
            raise ValueError("Test already reserved; this experiment permits one held-out comparison") from exc

    def usage(self) -> dict[str, Any]:
        totals = {r: {"calls": 0, "usage_calls": 0, "input_tokens": 0, "output_tokens": 0,
                      "cost_calls": 0, "recorded_cost_usd": 0.0} for r in ("actor", "judge", "optimizer")}
        for role, path in self.db.execute("SELECT role, artifact FROM calls"):
            total = totals[role]
            total["calls"] += 1
            raw = read_json(self.directory / path).get("raw")
            usage = raw.get("usage") if isinstance(raw, dict) else None
            if not isinstance(usage, dict):
                continue
            tokens = (usage.get("prompt_tokens"), usage.get("completion_tokens"))
            if all(type(t) is int and t >= 0 for t in tokens):
                total["usage_calls"] += 1
                total["input_tokens"] += tokens[0]
                total["output_tokens"] += tokens[1]
            cost = usage.get("cost")
            if type(cost) in (int, float) and math.isfinite(cost) and cost >= 0:
                total["cost_calls"] += 1
                total["recorded_cost_usd"] += cost
        return totals
