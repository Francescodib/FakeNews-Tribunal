from agents.base_agent import BaseAgent
from core.logging import get_logger
from tools.search import SearchTool

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are the Researcher agent in a fact-checking tribunal.

Your task:
1. Analyze the claim provided.
2. Search the web for primary sources, official statements, scientific studies, and reputable journalism.
3. Collect evidence both supporting and contradicting the claim.
4. Produce a structured research report in Markdown.

Rules:
- Prioritize primary and authoritative sources (government sites, peer-reviewed papers, major news outlets).
- Note the publication date of every source.
- Do NOT draw conclusions — only present evidence.
- If a previous round exists, focus your searches on the gaps and challenges raised by the Devil's Advocate.
- Be exhaustive but concise.

Output format:
## Research Report — Round {N}
### Supporting Evidence
[findings]
### Contradicting Evidence
[findings]
### Unresolved Questions
[questions for next round, if any]\
"""


class ResearcherAgent(BaseAgent):
    def __init__(self, provider: str, model_override: str | None = None) -> None:
        super().__init__(provider, model_override)
        self._search = SearchTool()

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    async def run(
        self,
        claim: str,
        round_number: int,
        language: str = "it",
        previous_challenge: str | None = None,
        judge_guidance: str | None = None,
    ) -> tuple[str, list[dict]]:
        logger.info("researcher.start", round=round_number)

        queries = await self._generate_queries(claim, round_number, previous_challenge, judge_guidance)
        all_sources: list[dict] = []
        for q in queries:
            results = await self._search.search(q, max_results=5, language=language)
            all_sources.extend(results)

        sources_block = _format_sources_block(all_sources)
        context = _build_context(claim, round_number, previous_challenge, judge_guidance, sources_block)

        report = await self._call([{"role": "user", "content": context}])
        logger.info("researcher.done", round=round_number, sources=len(all_sources))
        return report, all_sources

    async def _generate_queries(
        self,
        claim: str,
        round_number: int,
        previous_challenge: str | None,
        judge_guidance: str | None,
    ) -> list[str]:
        prompt = f"Generate 3 concise web search queries (one per line, no numbering) to fact-check this claim:\n\n\"{claim}\""
        if round_number > 1 and (previous_challenge or judge_guidance):
            extra = previous_challenge or judge_guidance
            prompt += f"\n\nFocus on addressing these gaps:\n{extra}"
        raw = await self._call([{"role": "user", "content": prompt}], temperature=0.2)
        queries = [line.strip() for line in raw.strip().splitlines() if line.strip()]
        return queries[:3] or [claim]


def _build_context(
    claim: str,
    round_number: int,
    previous_challenge: str | None,
    judge_guidance: str | None,
    sources_block: str,
) -> str:
    parts = [f"**Claim to fact-check:** {claim}", f"**Round:** {round_number}"]
    if previous_challenge:
        parts.append(f"**Devil's Advocate challenge (previous round):**\n{previous_challenge}")
    if judge_guidance:
        parts.append(f"**Judge guidance:**\n{judge_guidance}")
    parts.append(f"**Search results collected:**\n{sources_block}")
    parts.append("Now write your research report.")
    return "\n\n".join(parts)


def _format_sources_block(sources: list[dict]) -> str:
    if not sources:
        return "No results found."
    lines = []
    for i, s in enumerate(sources, 1):
        lines.append(f"{i}. [{s['title']}]({s['url']}) — {s['domain']}\n   {s['snippet'][:300]}")
    return "\n".join(lines)
