# Sarathi V0.1 — verified starter skeleton

These are the modules from the build plan, already executed and tested.
Days 2, 3, 11, 16, 19 and 22 of the plan are done for you.

## Run the tests (no API key, no GPU, no network needed)

    pip install pydantic httpx
    python3 tests/security/test_paths.py    # expect 10/10
    python3 tests/test_loop.py              # expect 5/5

## What's here

    src/sarathi/core/types.py           Day 2  — domain vocabulary, budgets
    src/sarathi/models/base.py          Day 3  — ModelProvider protocol
    src/sarathi/models/openai_compat.py Day 3  — works for Ollama AND cloud
    src/sarathi/models/router.py        Day 11 — deterministic routing
    src/sarathi/security/paths.py       Day 16 — canonicalise-then-check
    src/sarathi/security/audit.py       Day 18 — append-only decision log
    src/sarathi/tools/registry.py       Day 19 — tool = schema + tier + fn
    src/sarathi/tools/gateway.py        Day 19 — THE ONLY PATH TO EXECUTION
    src/sarathi/agents/loop.py          Day 22 — the loop + stall detection

## Still yours to write

    core/config.py      memory/db.py      memory/profile.py
    cli/main.py         tools/impl/*.py   eval/runner.py
    security/policies.yaml

Start at Day 1 of the plan (project skeleton + pyproject.toml), then drop
these files in and keep going from Day 4.
