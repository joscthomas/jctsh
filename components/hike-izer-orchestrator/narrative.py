#!/usr/bin/env python
"""
Hike-izer narrative generation (CARD-0086 stage 2).

The one place in the automated pipeline that genuinely needs an LLM: turning
a day's structured hike data into readable narrative prose (SKILL.md step
4a). Everything else (stats, tables, coverage) is deterministic templating
in templating.py. Reads the deployed SKILL.md copy at call time rather than
duplicating its narrative-writing rules here, so future edits to the real
Skill automatically apply to the automated path too.
"""

import sys
import time
from typing import List

import anthropic
from pydantic import BaseModel

MODEL = "claude-opus-4-8"
# CARD-0112: the SDK itself already retries transient errors (default 2
# attempts) before raising -- a 529 surviving that already means a real,
# if brief, overload window, not a one-off blip. Found necessary against a
# real step-2 run (2026-07-29) where the SDK's own retries were exhausted
# and the whole run died, discarding the photo/place-context work already
# done. Backoff grows well past what the SDK's own short internal retry
# spacing covers, to actually ride out a longer overload window.
NARRATIVE_MAX_RETRIES = 3
NARRATIVE_RETRY_BACKOFF_S = [15, 30, 60]

SYSTEM_PROMPT_PREFIX = """You are writing part (a), "Narrative story of the hike," of a Hike-izer \
summary. Below is the full hike-izer Skill instructions document (SKILL.md) for context -- \
follow its "Write the narrative" guidance (step 4, part a) exactly, including the \
non-redundancy rule (don't restate numbers that belong in the data tables -- interpret and \
connect instead) and the hike_confirmed:false handling if applicable. Ignore every other step \
in this document (data fetching, HTML mechanics, photos, publishing) -- those are \
handled elsewhere; your only job is the narrative paragraphs.

--- SKILL.md ---
{skill_md}
--- end SKILL.md ---

Return only the narrative as a list of paragraphs (plain text, no Markdown formatting, no \
headers) via the narrative_paragraphs field. Write 2-5 paragraphs depending on how much \
happened that day -- a quiet short walk doesn't need padding to hit a paragraph count, and an \
eventful all-day hike can run longer."""


class NarrativeOutput(BaseModel):
    narrative_paragraphs: List[str]


def _trim_for_narrative(hike_data: dict) -> dict:
    """The narrative only needs a subset of hike_data.json -- the raw
    Environmental Data/GPS Track rows are already summarized into stats and
    aren't useful raw (and would bloat the request for no benefit)."""
    return {
        "coverage": hike_data["coverage"],
        "stats": hike_data["stats"],
        "sun_position_samples": hike_data["sun_position_samples"],
        "hiking_observations": hike_data["hiking_observations"],
        "hike_start_forecast": hike_data.get("hike_start_forecast", []),
    }


def generate_narrative(hike_data: dict, skill_md_text: str, api_key: str, place_context=None, cost_tracker=None) -> List[str]:
    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = SYSTEM_PROMPT_PREFIX.format(skill_md=skill_md_text)

    import json
    trimmed = _trim_for_narrative(hike_data)
    # CARD-0108: grounded facts about where the hike happened (place
    # ownership/history, answers to whatever was voiced aloud) -- gathered
    # by place_context.py, passed in already-deduped-as-best-effort. Woven
    # into the narrative per SKILL.md's guidance, not a separate section.
    trimmed["place_context"] = place_context or []
    user_content = (
        "Here is the day's hike data (JSON):\n\n"
        + json.dumps(trimmed, indent=2)
    )

    response = None
    for attempt in range(NARRATIVE_MAX_RETRIES + 1):
        try:
            response = client.messages.parse(
                model=MODEL,
                max_tokens=4096,
                thinking={"type": "adaptive"},
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
                output_format=NarrativeOutput,
            )
            break
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
            if attempt == NARRATIVE_MAX_RETRIES:
                raise
            delay = NARRATIVE_RETRY_BACKOFF_S[attempt]
            print(
                f"generate_narrative attempt {attempt + 1} failed ({e}) -- retrying in {delay}s",
                file=sys.stderr,
            )
            time.sleep(delay)

    if cost_tracker:
        cost_tracker.record(response)
    return response.parsed_output.narrative_paragraphs
