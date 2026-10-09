"""Preserve python -m renters_benchmark for existing callers."""

from benchmarks.renters.renters_benchmark.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
