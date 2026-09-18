"""Deterministic model routing. No LLM in this path — it would add latency and
a failure mode to save forty lines of if-statements."""
from __future__ import annotations
from sarathi.core.types import Complexity, ModelSpec, Privacy, RouteRequest, TaskType


class NoModelFits(Exception): ...


class Router:
    def __init__(self, local: list[ModelSpec], cloud: dict[str, ModelSpec]):
        self.local = local          # best-quality first
        self.cloud = cloud          # keys: mid, reasoning, coding

    def route(self, req: RouteRequest, vram_free_mb: int = 5200) -> ModelSpec:
        # 1. HARD CONSTRAINTS — never overridden by cost preferences
        if req.privacy is Privacy.SECRET or req.offline:
            return self._local_fit(req, vram_free_mb)   # raises if nothing fits.
                                                        # correct: SECRET must not
                                                        # silently fall back to cloud.
        # 2. CAPABILITY FLOOR — don't send work to a model that can't do it
        if req.task_type is TaskType.REASON and req.complexity is Complexity.HARD:
            return self.cloud["reasoning"]
        if req.task_type is TaskType.CODE and req.complexity is not Complexity.TRIVIAL:
            return self.cloud["coding"]

        # 3. CHEAP PATH — genuinely easy work stays home
        if req.task_type in (TaskType.EXTRACT, TaskType.SUMMARIZE):
            try:
                return self._local_fit(req, vram_free_mb)
            except NoModelFits:
                pass

        # 4. DEFAULT
        return self.cloud["mid"]

    def _local_fit(self, req: RouteRequest, vram_free_mb: int) -> ModelSpec:
        for spec in self.local:
            if req.est_input_tokens > spec.max_context:
                continue
            if self._vram_mb(spec, req.est_input_tokens) <= vram_free_mb:
                return spec
        raise NoModelFits(f"no local model fits in {vram_free_mb}MB")

    @staticmethod
    def _vram_mb(spec: ModelSpec, ctx_tokens: int) -> int:
        kv_mb = max(ctx_tokens, 2048) * spec.kv_bytes_per_token / (1024*1024)
        return int(spec.weights_vram_mb + kv_mb + 500)   # 500MB headroom
