"""Story Execution Agent."""
from __future__ import annotations
import json
from core.schemas import AudienceMode, RankedStory, StoryIdea
from core.llm import chat, _clean_json

_RANK_PROMPT = """Rank these data story ideas by business impact and actionability.
Return ONLY a JSON array — same items with an added 'score' key (0.0-1.0), sorted descending.
No markdown. Only the JSON array.

{ideas}"""

_EXPAND_PROMPT = """Write a compelling data narrative (200-300 words) for a {audience} audience.
Open with the hook, establish context with data, reveal the finding, close with action.
Tone: executive=outcomes-focused, analyst=data-rich, investor=ROI-focused, general=plain language.
Return ONLY the narrative text, no titles or labels.

Title: {title}
Hook: {hook}
Context: {context}
Finding: {dispute}
Solution: {solution}"""


async def run(ideas: list[StoryIdea], audience: AudienceMode = "executive", top_n: int = 3) -> list[RankedStory]:
    # Rank
    rank_prompt = _RANK_PROMPT.format(ideas=json.dumps([i.model_dump() for i in ideas]))
    raw = chat(rank_prompt, json_mode=True)
    ranked_raw = json.loads(_clean_json(raw))
    if isinstance(ranked_raw, dict):
        ranked_raw = next(iter(ranked_raw.values()))

    ranked = sorted(ranked_raw, key=lambda x: float(x.get("score", 0.5)), reverse=True)

    results = []
    for item in ranked[:top_n]:
        score = float(item.pop("score", 0.5))
        idea = StoryIdea(**{k: v for k, v in item.items() if k in StoryIdea.model_fields})
        expand_prompt = _EXPAND_PROMPT.format(
            audience=audience, title=idea.title, hook=idea.hook,
            context=idea.context, dispute=idea.dispute, solution=idea.solution
        )
        narrative = chat(expand_prompt, json_mode=False)
        results.append(RankedStory(**idea.model_dump(), score=score,
                                   audience_mode=audience, narrative_text=narrative))
    return results
