import asyncio
import json
import os
from pathlib import Path
from typing import Annotated

import httpx
import typer

from agents.orchestrator import DebateOrchestrator
from core.config import settings
from core.logging import configure_logging, get_logger

app = typer.Typer(name="tribunal", help="FakeNews Tribunal — autonomous fact-checking CLI")

_CONFIG_PATH = Path.home() / ".tribunal" / "config.json"


# ---------------------------------------------------------------------------
# Credentials helpers
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    if _CONFIG_PATH.exists():
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def _save_config(data: dict) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _get_server(server_opt: str | None) -> str:
    cfg = _load_config()
    server = server_opt or cfg.get("server")
    if not server:
        typer.echo(
            "No server URL specified. Run `tribunal login --server <URL>` first or pass --server.",
            err=True,
        )
        raise typer.Exit(1)
    return server.rstrip("/")


def _get_token(server: str) -> str:
    """Return a valid access token, refreshing automatically if needed."""
    cfg = _load_config()
    if cfg.get("server") != server:
        typer.echo("No credentials for this server. Run `tribunal login --server <URL>`.", err=True)
        raise typer.Exit(1)

    access_token = cfg.get("access_token")
    if not access_token:
        typer.echo("Not logged in. Run `tribunal login --server <URL>`.", err=True)
        raise typer.Exit(1)

    # Try to refresh if we have a refresh token stored
    refresh_token = cfg.get("refresh_token")
    if refresh_token:
        try:
            resp = httpx.post(
                f"{server}/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
                timeout=15,
            )
            if resp.status_code == 200:
                tokens = resp.json()
                cfg["access_token"] = tokens["access_token"]
                cfg["refresh_token"] = tokens["refresh_token"]
                _save_config(cfg)
                return tokens["access_token"]
        except Exception:
            pass  # Fall back to stored access token

    return access_token


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command()
def login(
    server: Annotated[str, typer.Option(help="API server base URL (e.g. http://localhost:8000)")],
    email: Annotated[str | None, typer.Option(help="Account email")] = None,
    password: Annotated[str | None, typer.Option(help="Account password")] = None,
    register: Annotated[bool, typer.Option("--register", help="Create a new account")] = False,
):
    """Authenticate against a running FakeNews Tribunal API server."""
    server = server.rstrip("/")

    if not email:
        email = typer.prompt("Email")
    if not password:
        password = typer.prompt("Password", hide_input=True)

    if register:
        resp = httpx.post(
            f"{server}/api/v1/auth/register",
            json={"email": email, "password": password},
            timeout=15,
        )
        if resp.status_code not in (200, 201):
            typer.echo(f"Registration failed: {resp.text}", err=True)
            raise typer.Exit(1)
        typer.echo("Account created. Logging in…")

    resp = httpx.post(
        f"{server}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=15,
    )
    if resp.status_code != 200:
        typer.echo(f"Login failed: {resp.text}", err=True)
        raise typer.Exit(1)

    tokens = resp.json()
    _save_config({
        "server": server,
        "email": email,
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
    })
    typer.echo(f"Logged in as {email} on {server}")


@app.command()
def logout():
    """Clear stored credentials."""
    cfg = _load_config()
    server = cfg.get("server")
    token = cfg.get("access_token")
    refresh = cfg.get("refresh_token")

    if server and token and refresh:
        try:
            httpx.post(
                f"{server}/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {token}"},
                json={"refresh_token": refresh},
                timeout=10,
            )
        except Exception:
            pass

    if _CONFIG_PATH.exists():
        _CONFIG_PATH.unlink()
    typer.echo("Logged out.")


@app.command()
def check(
    claim: Annotated[str, typer.Argument(help="The claim or headline to fact-check")],
    provider: Annotated[str, typer.Option(help="LLM provider")] = settings.DEFAULT_PROVIDER,
    model: Annotated[str | None, typer.Option(help="Model override")] = None,
    rounds: Annotated[int, typer.Option(help="Max debate rounds")] = settings.MAX_DEBATE_ROUNDS,
    language: Annotated[str, typer.Option(help="Search language (ISO 639-1)")] = "it",
    output: Annotated[str, typer.Option(help="Output format: markdown | json")] = "markdown",
    server: Annotated[str | None, typer.Option(help="API server URL (enables server mode)")] = None,
):
    """Fact-check a claim locally (default) or via API server (--server)."""
    configure_logging()

    if server or _load_config().get("server"):
        # Server mode
        asyncio.run(_run_server(claim, provider, model, rounds, language, output, server))
    else:
        # Local mode (no server needed)
        get_logger("cli").info("cli.check.local", provider=provider, rounds=rounds)
        asyncio.run(_run_local(claim, provider, model, rounds, language, output))


# ---------------------------------------------------------------------------
# Local mode
# ---------------------------------------------------------------------------

async def _run_local(
    claim: str,
    provider: str,
    model: str | None,
    rounds: int,
    language: str,
    output: str,
) -> None:
    typer.echo(f"\nFact-checking (local): {claim!r}\n", err=True)
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
        _print_markdown(claim, result.verdict, result.total_rounds, result.processing_time_ms)


# ---------------------------------------------------------------------------
# Server mode
# ---------------------------------------------------------------------------

async def _run_server(
    claim: str,
    provider: str,
    model: str | None,
    rounds: int,
    language: str,
    output: str,
    server_opt: str | None,
) -> None:
    server = _get_server(server_opt)
    token = _get_token(server)
    headers = {"Authorization": f"Bearer {token}"}

    typer.echo(f"\nFact-checking (server {server}): {claim!r}\n", err=True)

    # Submit the claim
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{server}/api/v1/analysis",
            headers=headers,
            json={
                "claim": claim,
                "llm_provider": provider,
                "llm_model": model,
                "language": language,
                "max_rounds": rounds,
            },
        )

    if resp.status_code not in (200, 201, 202):
        typer.echo(f"Submission failed ({resp.status_code}): {resp.text}", err=True)
        raise typer.Exit(1)

    analysis_id = resp.json()["analysis_id"]
    typer.echo(f"Analysis submitted: {analysis_id}", err=True)

    # Stream SSE events
    verdict_raw: dict | None = None
    total_rounds = 0
    processing_ms = 0

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "GET",
            f"{server}/api/v1/analysis/{analysis_id}/stream",
            headers={**headers, "Accept": "text/event-stream"},
        ) as resp:
            if resp.status_code != 200:
                typer.echo(f"Stream failed ({resp.status_code})", err=True)
                raise typer.Exit(1)

            event_name = ""
            async for raw_line in resp.aiter_lines():
                line = raw_line.strip()
                if line.startswith("event:"):
                    event_name = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data_str = line[len("data:"):].strip()
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    _handle_sse_event(event_name, data, output)
                    if event_name == "verdict":
                        verdict_raw = data.get("verdict", {})
                        total_rounds = data.get("total_rounds", 0)
                        processing_ms = data.get("processing_time_ms", 0)
                    elif event_name == "done":
                        break
                    elif event_name == "error":
                        typer.echo(f"\nError: {data.get('message', 'unknown')}", err=True)
                        raise typer.Exit(1)
                    event_name = ""

    if verdict_raw and output == "json":
        typer.echo(json.dumps({
            "verdict": verdict_raw,
            "total_rounds": total_rounds,
            "processing_time_ms": processing_ms,
        }, indent=2, ensure_ascii=False))
    elif verdict_raw and output == "markdown":
        _print_markdown(claim, verdict_raw, total_rounds, processing_ms)


def _handle_sse_event(event: str, data: dict, output: str) -> None:
    """Print real-time progress to stderr during streaming."""
    if output == "json":
        return  # In JSON mode, only print the final verdict

    if event == "round_start":
        typer.echo(f"\n--- Round {data['round']} / {data.get('max_rounds', '?')} ---", err=True)
    elif event == "agent_start":
        agent = data.get("agent", "")
        label = {"researcher": "Researcher", "devil_advocate": "Devil's Advocate", "judge": "Judge"}.get(agent, agent)
        typer.echo(f"  [{label}] thinking…", err=True)
    elif event == "researcher_done":
        typer.echo(f"  [Researcher] done ({len(data.get('sources', []))} sources)", err=True)
    elif event == "advocate_done":
        typer.echo(f"  [Devil's Advocate] done ({len(data.get('sources', []))} sources)", err=True)
    elif event == "judge_continue":
        typer.echo(f"  [Judge] → another round: {data.get('reason', '')[:80]}", err=True)
    elif event == "verdict":
        v = data.get("verdict", {})
        typer.echo(f"\n  [Judge] → Verdict: {v.get('label')} ({v.get('confidence', 0):.0%})", err=True)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _print_markdown(claim: str, verdict: dict, total_rounds: int, processing_ms: int) -> None:
    label = verdict.get("label", "UNVERIFIABLE")
    confidence = verdict.get("confidence", 0.0)
    summary = verdict.get("summary", "")
    reasoning = verdict.get("reasoning", "")

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
        f"**Rounds:** {total_rounds}",
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
