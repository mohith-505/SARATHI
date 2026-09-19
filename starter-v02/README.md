# Sarathi V0.2 — tested memory components

    pip install numpy
    python3 test_facts.py        # conflict resolution + poisoning defence
    python3 retrieval_demo2.py   # dense vs BM25 vs RRF vs rerank, measured

## facts.py
Semantic memory with provenance, supersession and trust precedence.
Contains the fixes for both bugs described in the plan:
  - untrusted sources are QUARANTINED, never stored live (not just blocked
    from overwriting — blocking overwrites alone leaves the hole open)
  - user_stated -> user_stated is a clean correction, not a "contested" flag

## retrieval_demo2.py
The measurement harness. Swap the LSA embedder for a real neural one and
point CORPUS/QUERIES at your own notes — that is Week 5 of the plan.
The corpus is deliberately hard: near-duplicate chunks differing only in an
identifier, which is where dense-only retrieval actually breaks.
