from agents.base_agent import BaseAgent
from core.logging import get_logger
from tools.search import SearchTool

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are the Devil's Advocate agent in a fact-checking tribunal.

Your task:
1. Receive the Researcher's report.
2. Actively challenge every piece of evidence: look for logical fallacies, weak sources, outdated data, missing context, and alternative interpretations.
3. Search for counter-evidence the Researcher may have missed.
4. Do NOT try to be balanced — your role is to stress-test the evidence.

Rules:
- Attack source credibility where warranted (check domain, author, publication date).
- Flag any correlation-vs-causation errors.
- Identify what is missing from the research.
- If a prior round exists, escalate your challenges based on new findings.

Output format:
## Challenge Report — Round {N}
### Challenged Evidence
[point-by-point challenges]
### Counter-Evidence Found
[new sources contradicting the Researcher]
### Critical Gaps
[what is still missing]\
"""


class DevilAdvocateAgent(BaseAgent):
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
        researcher_report: str,
        language: str = "it",
    ) -> tuple[str, list[dict]]:
        logger.info("devil_advocate.start", round=round_number)

        counter_queries = await self._generate_counter_queries(claim, researcher_report)
        counter_sources: list[dict] = []
        for q in counter_queries:
            results = await self._search.search(q, max_results=4, language=language)
            counter_sources.extend(results)

        sources_block = _format_sources_block(counter_sources)
        context = (
            f"**Claim:** {claim}\n\n"
            f"**Round:** {round_number}\n\n"
            f"**Researcher's report:**\n{researcher_report}\n\n"
            f"**Counter-search results:**\n{sources_block}\n\n"
            "Now write your challenge report."
        )

        challenge = await self._call([{"role": "user", "content": context}])
        logger.info("devil_advocate.done", round=round_number, counter_sources=len(counter_sources))
        return challenge, counter_sources

    async def _generate_counter_queries(self, claim: str, researcher_report: str) -> list[str]:
        prompt = (
            f"You are challenging a fact-check report. Generate 3 concise web search queries "
            f"(one per line, no numbering) to find counter-evidence or weaknesses for this claim:\n\n"
            f"\"{claim}\"\n\nReport summary:\n{researcher_report[:800]}"
        )
        raw = await self._call([{"role": "user", "content": prompt}], temperature=0.2)
        queries = [line.strip() for line in raw.strip().splitlines() if line.strip()]
        return queries[:3] or [f"problems with {claim}"]


def _format_sources_block(sources: list[dict]) -> str:
    if not sources:
        return "No counter-results found."
    lines = []
    for i, s in enumerate(sources, 1):
        lines.append(f"{i}. [{s['title']}]({s['url']}) — {s['domain']}\n   {s['snippet'][:300]}")
    return "\n".join(lines)
