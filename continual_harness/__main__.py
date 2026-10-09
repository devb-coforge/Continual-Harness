from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
from pathlib import Path

from benchmarks.renters.renters_benchmark.core import DATASET
from .config import Config
from .demo import DemoClient, demo_config
from .engine import Harness, initialize
from .prompts import BASELINE
from .provider import OpenRouterClient
from .store import Store


async def run(args: argparse.Namespace) -> dict:
    if args.command in {"optimize", "demo"}:
        config = demo_config() if args.command == "demo" else Config.load(args.config)
        client = DemoClient(args.dataset) if args.command == "demo" else OpenRouterClient(config.timeout_seconds)
        strategy = args.strategy_file.read_text() if args.strategy_file else BASELINE
        if not strategy.strip() or len(strategy) > config.max_strategy_chars:
            raise ValueError("Baseline strategy is empty or exceeds max_strategy_chars")
        store = Store(args.output, create=True)
        try:
            initialize(store, args.dataset, config, "synthetic_offline" if args.command == "demo" else "live_openrouter")
            harness = Harness(args.dataset, config, client, store)
            result = await harness.optimize(store.prompt(strategy))
            if args.command == "demo":
                result["test"] = await harness.final_test()
            return result
        finally:
            store.close()
    store = Store(args.experiment)
    try:
        if args.command == "report":
            result = {"status": store.get("status"), "evidence": store.get("evidence"), "usage": store.usage()}
            result["comparisons"] = {phase: json.loads(value) for phase, value in
                                     store.db.execute("SELECT phase, result FROM comparisons ORDER BY phase")}
            return result
        if store.get("evidence") != "live_openrouter":
            raise ValueError("Synthetic experiments cannot be converted into live test evidence")
        config = Config.from_dict(store.get("config"))
        harness = Harness(Path(store.get("dataset")), config, OpenRouterClient(config.timeout_seconds), store)
        return await harness.final_test()
    finally:
        store.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Fixed-task continual system-prompt optimization")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("optimize", "demo"):
        command = sub.add_parser(name, help="Live optimization" if name == "optimize" else "Synthetic offline end-to-end demo")
        command.add_argument("--dataset", type=Path, default=DATASET)
        command.add_argument("--output", type=Path, required=True, help="New experiment directory; never overwritten")
        command.add_argument("--strategy-file", type=Path)
        if name == "optimize":
            command.add_argument("--config", type=Path, required=True)
    for name in ("test", "report"):
        command = sub.add_parser(name, help="One-shot frozen baseline/final test" if name == "test" else "Read stored results and usage")
        command.add_argument("experiment", type=Path)
    args = parser.parse_args()
    try:
        result = asyncio.run(run(args))
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
