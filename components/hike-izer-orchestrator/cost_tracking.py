#!/usr/bin/env python
"""
Hike-izer API cost tracking.

Sums real usage (tokens + web_search fees) across every Claude API call made
during a single generation run, so the completion log line reports what that
hike's summary actually cost -- a real per-hike number on the dashboard,
not a one-off Console lookup.

Pricing confirmed live 2026-07-28 against docs.claude.com: web search is
billed separately from tokens, per search performed, not per token --
$10/1,000 searches. `usage.output_tokens` is the SDK's own documented
"inclusive, authoritative total used for billing" figure, so it already
includes thinking tokens -- no separate accounting needed for those.
"""

PRICING = {
    "claude-opus-4-8": {"input": 5.00, "output": 25.00},  # $ per 1M tokens
}
WEB_SEARCH_COST_PER_SEARCH = 0.01  # $10 per 1,000 searches


class CostTracker:
    def __init__(self):
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.web_searches = 0
        self.dollars = 0.0

    def record(self, response):
        """Adds one API response's real usage to the running total."""
        usage = response.usage
        pricing = PRICING.get(response.model, PRICING["claude-opus-4-8"])
        searches = usage.server_tool_use.web_search_requests if usage.server_tool_use else 0

        self.calls += 1
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.web_searches += searches
        self.dollars += (
            usage.input_tokens * pricing["input"] / 1_000_000
            + usage.output_tokens * pricing["output"] / 1_000_000
            + searches * WEB_SEARCH_COST_PER_SEARCH
        )

    def summary(self):
        text = (
            f"${self.dollars:.4f} ({self.calls} API calls, "
            f"{self.input_tokens:,} in / {self.output_tokens:,} out tokens"
        )
        if self.web_searches:
            text += f", {self.web_searches} web searches"
        return text + ")"
