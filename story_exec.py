"""Story Execution Agent.

Ranks story ideas by impact and audience fit, then writes full narrative text
for the top stories. Returns RankedStory objects.
"""
from __future__ import annotations
import json
from openai import AsyncOpenAI
from core.schemas import AudienceMode, ChartSpec, RankedStory, StoryIdea
from core.config import get_settings

_RANK_SYSTEM = """You are an editorial director. Rank the following data story ideas 
by business impact and actionability.

Return ONLY valid JSON — the same list with an added 'score' key (0.0-1.0) for each item,
sorted descending by score. No other changes."""

_EXPAND_SYSTEM = """You are a senior business analyst writing an executive-ready data story.

Write a compelling narrative (200-300 words) that:
1. Opens with the hook to grab attention
2. Establishes context with relevant data points
3. Reveals the surprising dispute/finding with specific numbers
4. Closes with a concrete, actionable solution
5. Adapts tone to the audience: 
   - executive: high-level, outcomes-focused, minimal jargon
   - analyst: detailed, methodology-aware, data-rich
   - investor: ROI-focused, risk-aware, growth-oriented
   - general: plain language, relatable analogies

Return ONLY the narrative text. No titles, no JSON."""


async def _rank_stories(
    ideas: list[StoryIdea], client: AsyncOpenAI, model: str
) -> list[tuple[StoryIdea, float]]:
    payload = [i.model_dump() for i in ideas]
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _RANK_SYSTEM},
            {"role": "user", "content": json.dumps(payload)},
        ],
        max_tokens=800,
        temperature=0,
        response_format={"type": "json_object"},
    )
    raw = json.loads(response.choices[0].message.content)
    if isinstance(raw, dict):
        raw = next(iter(raw.values()))
    return [(StoryIdea(**{k: v for k, v in item.items() if k != "score"}),
             float(item.get("score", 0.5))) for item in raw]


async def _expand_story(
    idea: StoryIdea, audience: AudienceMode,
    client: AsyncOpenAI, model: str
) -> str:
    user_prompt = (
        f"Audience: {audience}\n"
        f"Title: {idea.title}\n"
        f"Hook: {idea.hook}\n"
        f"Context: {idea.context}\n"
        f"Dispute: {idea.dispute}\n"
        f"Solution: {idea.solution}\n"
        "Write the narrative now."
    )
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _EXPAND_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=600,
        temperature=0.6,
    )
    return response.choices[0].message.content.strip()


async def run(
    ideas: list[StoryIdea],
    audience: AudienceMode = "executive",
    top_n: int = 3,
) -> list[RankedStory]:
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    ranked = await _rank_stories(ideas, client, settings.openai_model)
    ranked.sort(key=lambda x: x[1], reverse=True)

    results = []
    for idea, score in ranked[:top_n]:
        narrative = await _expand_story(idea, audience, client, settings.openai_model)
        results.append(RankedStory(
            **idea.model_dump(),
            score=score,
            audience_mode=audience,
            narrative_text=narrative,
        ))
    return results
