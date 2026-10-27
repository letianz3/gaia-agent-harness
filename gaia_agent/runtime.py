"""Reusable model gateway: bounded calls, request cache, prompt identities and cost."""
import copy
import hashlib
import json
import threading
import time


class BudgetExceeded(RuntimeError):
    pass


class ModelGateway:
    def __init__(self, settings):
        self.settings = settings
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        self.cache = {}
        self.calls = self.hits = self.input_tokens = self.output_tokens = 0
        self.trace = None

    def call(self, create, **request):
        def plain(value):
            if hasattr(value, 'model_dump'):
                return value.model_dump(mode='json')
            if hasattr(value, '__dict__'):
                return vars(value)
            raise TypeError(type(value).__name__)

        raw = json.dumps(request, default=plain, sort_keys=True, ensure_ascii=False)
        key = hashlib.sha256(raw.encode()).hexdigest()
        prompt = json.dumps([m for m in request.get('messages', []) if isinstance(m, dict) and m.get('role') == 'system'], sort_keys=True)
        prompt_id = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        with self.lock:
            if self.settings.llm_cache_enabled and key in self.cache:
                self.hits += 1
                result = copy.deepcopy(self.cache[key])
                result.usage = None  # cached calls must not bill historical tokens again
                if self.trace:
                    self.trace.add('model_cache_hit', request_hash=key, prompt_version=prompt_id)
                return result
            if self.calls >= self.settings.max_llm_calls:
                raise BudgetExceeded('Per-task LLM call budget exhausted')
            self.calls += 1
        started = time.monotonic()
        result = create(**request)
        usage = getattr(result, 'usage', None)
        incoming = int(getattr(usage, 'prompt_tokens', 0) or 0)
        outgoing = int(getattr(usage, 'completion_tokens', 0) or 0)
        with self.lock:
            self.input_tokens += incoming
            self.output_tokens += outgoing
            if self.settings.llm_cache_enabled:
                self.cache[key] = copy.deepcopy(result)
        if self.trace:
            self.trace.add('model_request', request_hash=key, prompt_version=prompt_id,
                           model=getattr(result, 'model', self.settings.model),
                           input_tokens=incoming, output_tokens=outgoing,
                           duration_ms=round((time.monotonic()-started)*1000, 1))
        return result

    def stats(self):
        priced = self.settings.input_price_per_million > 0 and self.settings.output_price_per_million > 0
        return dict(llm_calls=self.calls, cache_hits=self.hits,
                    estimated_chat_cost_usd=(self.input_tokens*self.settings.input_price_per_million +
                        self.output_tokens*self.settings.output_price_per_million)/1_000_000 if priced else None,
                    cost_scope='chat completions only; transcription and external services excluded')
