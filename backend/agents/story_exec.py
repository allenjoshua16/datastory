"""Story Execution Agent — uses Gemini."""
from __future__ import annotations
import json
import google.generativeai as genai
from core.schemas import AudienceMode, RankedStory, StoryIdea
from core.config import get_settings

_RANK_SYSTEM = """You are an editorial director. Rank these data story ideas by business impact and actionability.
Return ONLY a JSON array — same items with an added 'score' key (0.0-1.0), sorted descending by score."""

_EXPAND_SYSTEM = """You are a senior business analyst writing an executive-ready data story.
Write a compelling narrative (200-300 words) that:
1. Opens with the hook
2. Establishes context with data points
3. Reveals the surprising finding with specific numbers
4. Closes with a concrete actionable solution
5. Adapts tone: executive=outcomes-focused, analyst=data-rich, investor=ROI-focused, general=plain language
Return ONLY the narrative text."""


def _rank_stories(ideas: list[StoryIdea], model) -> list[tuple[StoryIdea, float]]:
    payload = [i.model_dump() for i in ideas]
    prompt = f"{_RANK_SYSTEM}\n\n{json.dumps(payload)}"
    response = model.generate_content(prompt)
    raw = json.loads(response.text.strip())
    if isinstance(raw, dict):
        raw = next(iter(raw.values()))
    return [
        (StoryIdea(**{k: v for k, v in item.items() if k != "score"}), float(item.get("score", 0.5)))
        for item in raw
    ]


def _expand_story(idea: StoryIdea, audience: AudienceMode, model) -> str:
    prompt = (
        f"{_EXPAND_SYSTEM}\n\n"
        f"Audience: {audience}\nTitle: {idea.title}\nHook: {idea.hook}\n"
        f"Context: {idea.context}\nDispute: {idea.dispute}\nSolution: {idea.solution}\n"
        "Write the narrative now."
    )
    response = model.generate_content(prompt)
    return response.text.strip()


async def run(ideas: list[StoryIdea], audience: AudienceMode = "executive", top_n: int = 3) -> list[RankedStory]:
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(
        settings.gemini_model,
        generation_config={"response_mime_type": "application/json"}
    )
    text_model = genai.GenerativeModel(settings.gemini_model)

    ranked = _rank_stories(ideas, model)
    ranked.sort(key=lambda x: x[1], reverse=True)

    results = []
    for idea, score in ranked[:top_n]:
        narrative = _expand_story(idea, audience, text_model)
        results.append(RankedStory(**idea.model_dump(), score=score, audience_mode=audience, narrative_text=narrative))
    return results
