import asyncio
import json
from typing import Annotated

import typer

from agents.orchestrator import DebateOrchestrator
from core.config import settings
from core.logging import configure_logging, get_logger

app = typer.Typer(name="tribunal", help="FakeNews Tribunal — autonomous fact-checking CLI")


@app.command()
def check(
    claim: Annotated[str, typer.Argument(help="The claim or headline to fact-check")],
    provider: Annotated[str, typer.Option(help="LLM provider")] = settings.DEFAULT_PROVIDER,
    model: Annotated[str | None, typer.Option(help="Model override")] = None,
    rounds: Annotated[int, typer.Option(help="Max debate rounds")] = settings.MAX_DEBATE_ROUNDS,
    language: Annotated[str, typer.Option(help="Search language (ISO 639-1)")] = "it",
    output: Annotated[str, typer.Option(help="Output format: markdown | json")] = "markdown",
):
    configure_logging()
    logger = get_logger("cli")
    logger.info("cli.check", provider=provider, rounds=rounds)
    asyncio.run(_run(claim, provider, model, rounds, language, output))


async def _run(
    claim: str,
    provider: str,
    model: str | None,
    rounds: int,
    language: str,
    output: str,
) -> None:
    typer.echo(f"\nFact-checking: {claim!r}\n", err=True)
    orchestrator = DebateOrchestrator(provider=provider, model_override=model, max_rounds=rounds)

    try:
        result = await orchestrator.run(claim=claim, language=language)
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    if output == "json":
        typer.echo(json.dumps({
            "verdict": result.verdict,
            "total_rounds": result.total_rounds,
            "processing_time_ms": result.processing_time_ms,
        }, indent=2, ensure_ascii=False))
    else:
        _print_markdown(claim, result)


def _print_markdown(claim: str, result) -> None:
    v = result.verdict
    label = v.get("label", "UNVERIFIABLE")
    confidence = v.get("confidence", 0.0)
    summary = v.get("summary", "")
    reasoning = v.get("reasoning", "")

    label_emoji = {
        "TRUE": "✅",
        "FALSE": "❌",
        "MISLEADING": "⚠️",
        "PARTIALLY_TRUE": "🔶",
        "UNVERIFIABLE": "❓",
    }.get(label, "❓")

    lines = [
        f"# Verdict: {label_emoji} {label}",
        f"**Claim:** {claim}",
        f"**Confidence:** {confidence:.0%}",
        f"**Rounds:** {result.total_rounds}",
        "",
        "## Summary",
        summary,
        "",
        "## Reasoning",
        reasoning,
    ]
    typer.echo("\n".join(lines))


if __name__ == "__main__":
    app()
