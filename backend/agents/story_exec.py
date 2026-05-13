"""Story Execution Agent — bulletproof parsing."""
from __future__ import annotations
import json
import logging
from core.schemas import AudienceMode, RankedStory, StoryIdea
from core.llm import chat, _clean_json

logger = logging.getLogger(__name__)

_RANK_PROMPT = """Rank these data story ideas by business impact and actionability.
Return ONLY a valid JSON array. Each item must be an object with all original fields
plus a 'score' key (float 0.0-1.0). Sort descending by score.
No markdown. No explanation. Only the JSON array.

{ideas}"""

_EXPAND_PROMPT = """Write a compelling data narrative (200-300 words) for a {audience} audience.
Structure: hook → context with data → surprising finding → actionable solution.
Tone guide: executive=outcomes-focused brief, analyst=data-rich detailed,
investor=ROI and risk focused, general=plain language no jargon.
Return ONLY the narrative text. No titles, no labels, no JSON.

Title: {title}
Hook: {hook}
Context: {context}
Finding: {dispute}
Solution: {solution}"""


def _safe_parse_ranked(raw: str, original_ideas: list[StoryIdea]) -> list[tuple[StoryIdea, float]]:
    """Parse ranked stories with multiple fallback strategies."""
    try:
        cleaned = _clean_json(raw)
        parsed = json.loads(cleaned)

        # Unwrap if wrapped in a dict
        if isinstance(parsed, dict):
            # Try common wrapper keys
            for key in ["stories", "ideas", "ranked", "results", "data"]:
                if key in parsed:
                    parsed = parsed[key]
                    break
            else:
                parsed = list(parsed.values())[0] if parsed else []

        if not isinstance(parsed, list):
            raise ValueError(f"Expected list, got {type(parsed)}")

        results = []
        for item in parsed:
            # Handle case where item is a string instead of dict
            if isinstance(item, str):
                logger.warning(f"Got string item instead of dict: {item[:100]}")
                continue
            if not isinstance(item, dict):
                logger.warning(f"Unexpected item type: {type(item)}")
                continue

            score = float(item.get("score", 0.5))
            # Build StoryIdea from dict, ignoring unknown fields
            idea_fields = {k: v for k, v in item.items()
                          if k in StoryIdea.model_fields and k != "score"}
            try:
                idea = StoryIdea(**idea_fields)
                results.append((idea, score))
            except Exception as e:
                logger.warning(f"Could not parse story item: {e}")
                continue

        if results:
            return sorted(results, key=lambda x: x[1], reverse=True)

    except Exception as e:
        logger.warning(f"Could not parse ranked stories: {e}. Using originals with default scores.")

    # Fallback: return originals with descending scores
    return [(idea, 1.0 - i * 0.1) for i, idea in enumerate(original_ideas)]


async def run(
    ideas: list[StoryIdea],
    audience: AudienceMode = "executive",
    top_n: int = 3,
) -> list[RankedStory]:
    if not ideas:
        return []

    # Rank stories
    try:
        rank_prompt = _RANK_PROMPT.format(
            ideas=json.dumps([i.model_dump() for i in ideas], default=str)
        )
        raw = chat(rank_prompt, json_mode=True)
        ranked = _safe_parse_ranked(raw, ideas)
    except Exception as e:
        logger.warning(f"Ranking failed: {e}. Using original order.")
        ranked = [(idea, 1.0 - i * 0.1) for i, idea in enumerate(ideas)]

    results = []
    for idea, score in ranked[:top_n]:
        # Expand each story into full narrative
        try:
            expand_prompt = _EXPAND_PROMPT.format(
                audience=audience,
                title=idea.title,
                hook=idea.hook,
                context=idea.context,
                dispute=idea.dispute,
                solution=idea.solution,
            )
            narrative = chat(expand_prompt, json_mode=False)
        except Exception as e:
            logger.warning(f"Narrative expansion failed for '{idea.title}': {e}")
            narrative = f"{idea.hook}\n\n{idea.context}\n\n{idea.dispute}\n\n{idea.solution}"

        results.append(RankedStory(
            **idea.model_dump(),
            score=score,
            audience_mode=audience,
            narrative_text=narrative,
        ))

    return results
