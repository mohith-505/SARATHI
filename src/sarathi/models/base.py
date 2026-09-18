import time
from typing import Callable, Any
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type
import httpx
from sarathi.core.types import Context, ModelResponse, Usage

class CircuitBreakerOpen(Exception): ...

class CircuitBreaker:
    def __init__(self, max_failures=3, reset_timeout=300):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = 0.0

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.monotonic()

    def record_success(self):
        self.failures = 0

    def check(self):
        if self.failures >= self.max_failures:
            if time.monotonic() - self.last_failure_time > self.reset_timeout:
                # Half-open, allow one attempt
                self.failures = self.max_failures - 1
            else:
                raise CircuitBreakerOpen("Circuit breaker is open. Skipping provider.")


class ModelClient:
    """Wrapper that adds resilience (retries, circuit breaker, usage logging)"""
    def __init__(self, provider, db_conn=None):
        self.provider = provider
        self.circuit_breaker = CircuitBreaker()
        self.db_conn = db_conn

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
    )
    async def _call_with_retry(self, *args, **kwargs):
        self.circuit_breaker.check()
        try:
            res = await self.provider.complete(*args, **kwargs)
            self.circuit_breaker.record_success()
            return res
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise e

    async def complete(self, messages, spec, tools=None, temperature=0.7, ctx: Context = None, task_type="chat") -> ModelResponse:
        start_time = time.monotonic()
        try:
            resp = await self._call_with_retry(messages, spec, tools, temperature)
            ok = True
        except Exception as e:
            ok = False
            # Return empty response with error or raise, here we'll just log and raise
            self._log_usage(ctx, spec.name, task_type, Usage(), start_time, ok=False)
            raise e

        # Log success
        self._log_usage(ctx, spec.name, task_type, resp.usage, start_time, ok=True)
        return resp

    def _log_usage(self, ctx, model, task_type, usage, start_time, ok):
        if not self.db_conn or not ctx:
            return
        
        latency = int((time.monotonic() - start_time) * 1000)
        self.db_conn.execute(
            """INSERT INTO usage_log (ts, session_id, model, task_type, tokens_in, tokens_out, cost_inr, latency_ms, ok)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (time.time(), ctx.session_id, model, task_type, usage.input_tokens, usage.output_tokens, usage.cost_inr, latency, int(ok))
        )
        self.db_conn.commit()
