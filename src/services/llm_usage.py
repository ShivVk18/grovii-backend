"""Per-job LLM token metering and the per-job token budget.

How it works:
- generate_storyboard_job() opens `metered(budget)`, which puts a UsageMeter in
  a context variable for the duration of the job.
- Every LLM built by openai_service.get_llm() carries a UsageCallback. Before a
  call is sent, the callback checks the meter and refuses the call if the job
  has already used its budget. After the call, it adds the reported tokens.
- LangGraph runs the fan-out nodes in worker threads but copies the context
  into them, so all nodes of one job share the same meter object (a lock keeps
  the counters consistent).

Limit: the budget is checked BEFORE each call. Calls already in flight finish,
so a job can overshoot by at most the output caps of its in-flight calls.
"""
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Iterator

from langchain_core.callbacks import BaseCallbackHandler

from src.config import limits


class BudgetExceeded(RuntimeError):
    """The job used its token budget; no more LLM calls are allowed."""


@dataclass
class UsageMeter:
    budget: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    calls: int = 0
    exceeded: bool = False
    by_node: dict[str, int] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def cost_usd(self) -> float:
        return limits.estimate_cost_usd(self.prompt_tokens, self.completion_tokens)

    def check(self) -> None:
        with self._lock:
            if self.total_tokens >= self.budget:
                self.exceeded = True
                raise BudgetExceeded(
                    f"Generation stopped: the job reached its token budget ({self.budget} tokens)."
                )

    def add(self, node: str, prompt: int, completion: int) -> None:
        with self._lock:
            self.prompt_tokens += prompt
            self.completion_tokens += completion
            self.calls += 1
            self.by_node[node] = self.by_node.get(node, 0) + prompt + completion


_current: ContextVar[UsageMeter | None] = ContextVar("grovii_usage_meter", default=None)


def current_meter() -> UsageMeter | None:
    return _current.get()


@contextmanager
def metered(budget: int | None = None) -> Iterator[UsageMeter]:
    meter = UsageMeter(budget=limits.JOB_TOKEN_BUDGET if budget is None else budget)
    token = _current.set(meter)
    try:
        yield meter
    finally:
        _current.reset(token)


def _usage_from(response: Any) -> tuple[int, int]:
    """Read (prompt, completion) tokens from an LLMResult."""
    for gens in getattr(response, "generations", None) or []:
        for gen in gens:
            usage = getattr(getattr(gen, "message", None), "usage_metadata", None)
            if usage:
                return int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))
    usage = (getattr(response, "llm_output", None) or {}).get("token_usage") or {}
    return int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))


class UsageCallback(BaseCallbackHandler):
    # Without this, LangChain logs and swallows exceptions raised in callbacks,
    # and the budget check could not stop a call.
    raise_error = True

    def __init__(self, node: str):
        self.node = node

    def _before_call(self) -> None:
        meter = _current.get()
        if meter is not None:
            meter.check()

    def on_chat_model_start(self, *args: Any, **kwargs: Any) -> None:
        self._before_call()

    def on_llm_start(self, *args: Any, **kwargs: Any) -> None:
        self._before_call()

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        meter = _current.get()
        if meter is not None:
            prompt, completion = _usage_from(response)
            meter.add(self.node, prompt, completion)
