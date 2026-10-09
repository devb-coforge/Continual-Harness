"""Run with python -m benchmarks.renters after activating .venv."""

import argparse
import json
import sqlite3
from pathlib import Path

from .core import DATASET, audit, grade, load_pair, make_manifest, read_json, render


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline Harborlight dataset utilities")
    parser.add_argument("--dataset", type=Path, default=DATASET)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="Audit all 100 tasks and private answer keys")
    validate.add_argument("--skip-manifest", action="store_true", help="For authoring before freezing checksums")
    sub.add_parser("build-manifest", help="Freeze checksums only after a successful integrity audit")
    prompt = sub.add_parser("render", help="Render model-visible input only; no oracle or split metadata")
    prompt.add_argument("task_id")
    prompt.add_argument("--strategy-file", type=Path)
    score = sub.add_parser("score", help="Check a saved response; semantic results remain pending without judgments")
    score.add_argument("task_id")
    score.add_argument("response_file", type=Path)
    score.add_argument("--judgments", type=Path)
    export = sub.add_parser("export-sqlite", help="Export a NEW local dataset database, including private golds")
    export.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            report = audit(args.dataset, verify_manifest=not args.skip_manifest)
            print(json.dumps(report, indent=2))
            return 0 if report["valid"] else 1
        if args.command == "build-manifest":
            report = audit(args.dataset, verify_manifest=False)
            if not report["valid"]:
                print(json.dumps(report, indent=2))
                return 1
            path = args.dataset / "manifest.json"
            path.write_text(json.dumps(make_manifest(args.dataset), indent=2) + "\n")
            print(f"Wrote {path}")
        elif args.command == "render":
            # Read only the public task. Rendering works without the private-oracle folder.
            if "/" in args.task_id or "\\" in args.task_id or args.task_id.startswith("."):
                raise ValueError("Invalid task ID")
            task = read_json(args.dataset / "tasks" / f"{args.task_id}.json")
            strategy = args.strategy_file.read_text() if args.strategy_file else None
            print(json.dumps(render(task, args.dataset, strategy), indent=2, ensure_ascii=False))
        elif args.command == "score":
            task, oracle = load_pair(args.task_id, args.dataset)
            judgments = read_json(args.judgments) if args.judgments else None
            result = grade(task, oracle, read_json(args.response_file), judgments)
            print(json.dumps(result, indent=2))
            return 1 if result["complete_success"] is False or result["semantic_status"] == "invalid" else 0
        elif args.command == "export-sqlite":
            report = audit(args.dataset)
            if not report["valid"]:
                print(json.dumps(report, indent=2))
                return 1
            # Exclusive create prevents accidentally overwriting user data.
            with args.output.open("xb"):
                pass
            with sqlite3.connect(args.output) as connection:
                connection.executescript("""
                    PRAGMA foreign_keys = ON;
                    CREATE TABLE tasks (
                        id TEXT PRIMARY KEY, track TEXT NOT NULL, family TEXT NOT NULL,
                        split TEXT NOT NULL, scenario_group TEXT NOT NULL,
                        input_json TEXT NOT NULL
                    );
                    CREATE TABLE oracles (
                        task_id TEXT PRIMARY KEY REFERENCES tasks(id), oracle_json TEXT NOT NULL
                    );
                    CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                """)
                for path in sorted((args.dataset / "tasks").glob("*.json")):
                    task, oracle = load_pair(path.stem, args.dataset)
                    connection.execute("INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?)", (
                        task["id"], task["track"], task["family"], task["split"],
                        task["scenario_group"], json.dumps(task["input"])))
                    connection.execute("INSERT INTO oracles VALUES (?, ?)", (task["id"], json.dumps(oracle)))
                connection.execute("INSERT INTO metadata VALUES (?, ?)", ("manifest", json.dumps(make_manifest(args.dataset))))
                connection.execute("INSERT INTO metadata VALUES (?, ?)", ("handbook", (args.dataset / "handbook.md").read_text()))
                connection.execute("INSERT INTO metadata VALUES (?, ?)", ("response_contract", (args.dataset / "response_contract.md").read_text()))
                integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
                if integrity != "ok":
                    raise ValueError(f"SQLite integrity check failed: {integrity}")
            print(f"Exported 100 tasks and private oracles to {args.output}")
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
