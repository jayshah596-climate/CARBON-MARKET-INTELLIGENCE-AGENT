"""
Carbon Market Intelligence Agent — CLI Entry Point.

Usage
-----
  python main.py analyze --auto
  python main.py analyze --auto --excel --word
  python main.py analyze --input "EU ETS EUR 65 per tonne..."
  python main.py analyze --input report.txt --excel --word
  python main.py serve
  python main.py serve --port 9000
"""

from __future__ import annotations
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from rich.columns import Columns
from rich.rule import Rule

# Configure logging before any imports that use it
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

console = Console()


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

COLOR_MAP = {"Green": "green", "Yellow": "yellow", "Red": "red"}
EMOJI_MAP = {"Green": "✅", "Yellow": "⚠️", "Red": "🔴"}


def _rich_color(color_code: str) -> str:
    return COLOR_MAP.get(color_code, "yellow")


def _emoji(color_code: str) -> str:
    return EMOJI_MAP.get(color_code, "⚠️")


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _print_header() -> None:
    console.print()
    console.print(
        Panel.fit(
            "[bold white]🌍 CARBON MARKET INTELLIGENCE AGENT[/bold white]\n"
            "[dim]AI-Powered ESG Analytics & Carbon Pricing Platform[/dim]",
            border_style="blue",
            padding=(1, 4),
        )
    )
    console.print()


def _print_market_overview(report) -> None:
    ov = report.market_overview
    color = _rich_color(ov.color_code)
    emoji = _emoji(ov.color_code)

    panel_content = (
        f"[bold]Market Type:[/bold] {ov.market_type}\n"
        f"[bold]Region:[/bold] {ov.region}\n"
        f"[bold]Latest Price:[/bold] {ov.latest_price.value} "
        f"{ov.latest_price.currency} {ov.latest_price.unit}\n"
        f"[bold]Price Trend:[/bold] {ov.price_trend}\n"
        f"[bold]Volatility:[/bold] {ov.volatility}\n"
        f"[bold]Performance:[/bold] [{color}]{emoji} {ov.performance_rating}[/{color}]"
    )
    console.print(Panel(panel_content, title="[bold blue]📊 Market Overview[/bold blue]", border_style="blue"))

    if ov.insight and ov.insight != "missing":
        console.print(f"[dim italic]💡 {ov.insight}[/dim italic]")
    console.print()


def _print_compliance_markets(report) -> None:
    if not report.compliance_markets:
        return
    console.print(Rule("[bold blue]Compliance Carbon Markets[/bold blue]"))
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold white on dark_blue")
    table.add_column("Market", style="bold", min_width=24)
    table.add_column("Region", min_width=14)
    table.add_column("Price", justify="right", min_width=10)
    table.add_column("Currency", min_width=8)
    table.add_column("Trend", min_width=12)
    table.add_column("Signal", justify="center", min_width=10)

    for mkt in report.compliance_markets:
        color = _rich_color(mkt.color_code)
        emoji = _emoji(mkt.color_code)
        table.add_row(
            mkt.market_name,
            mkt.region,
            mkt.price,
            mkt.currency,
            mkt.trend,
            f"[{color}]{emoji} {mkt.color_code}[/{color}]",
        )
    console.print(table)
    console.print()


def _print_vcm(report) -> None:
    vcm = report.voluntary_carbon_market
    color = _rich_color(vcm.color_code)
    emoji = _emoji(vcm.color_code)
    console.print(Rule("[bold green]Voluntary Carbon Market (VCM)[/bold green]"))
    console.print(
        f"  Average Price: [bold]{vcm.average_price} {vcm.currency}/tCO2e[/bold]\n"
        f"  Price Range:   {vcm.price_range}\n"
        f"  Demand Trend:  {vcm.demand_trend}\n"
        f"  Condition:     [{color}]{emoji} {vcm.market_condition}[/{color}]"
    )
    if vcm.insight and vcm.insight != "missing":
        console.print(f"  [dim italic]💡 {vcm.insight}[/dim italic]")
    console.print()


def _print_risk_summary(report) -> None:
    risk = report.risk_analysis
    color = _rich_color(risk.color_code)
    emoji = _emoji(risk.color_code)
    console.print(Rule("[bold red]Risk Analysis[/bold red]"))
    console.print(
        f"  Overall Risk: [{color}]{emoji} {risk.overall_risk_level.upper()}[/{color}]\n"
    )

    if risk.market_risks:
        console.print("  [bold]Market Risks:[/bold]")
        for r in risk.market_risks[:3]:
            console.print(f"    • {r}")

    if risk.policy_risks:
        console.print("  [bold]Policy Risks:[/bold]")
        for r in risk.policy_risks[:3]:
            console.print(f"    • {r}")
    console.print()


def _print_forecast(report) -> None:
    fc = report.forecast
    console.print(Rule("[bold yellow]Forecast & Outlook[/bold yellow]"))
    console.print(
        f"  Direction:       [bold]{fc.price_direction}[/bold]\n"
        f"  Short-Term (1-2y): {fc.short_term_outlook}\n"
        f"  Short-Term Target: {fc.price_target_short_term}\n"
        f"  Long-Term (5-10y): {fc.long_term_outlook}\n"
        f"  Long-Term Target:  {fc.price_target_long_term}\n"
        f"  Confidence:        {fc.confidence}"
    )
    console.print()


def _print_opportunities(report) -> None:
    opp = report.opportunity_analysis
    console.print(Rule("[bold green]Investment Opportunities[/bold green]"))
    for item in (opp.investment_opportunities or [])[:4]:
        console.print(f"  ✓ {item}")
    console.print()


def _print_data_quality(report) -> None:
    dq = report.data_quality
    console.print(
        f"[dim]Data Quality: {dq.confidence} | "
        f"Freshness: {dq.data_freshness} | "
        f"{dq.notes or ''}[/dim]"
    )


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

@click.group()
def cli() -> None:
    """Carbon Market Intelligence Agent — AI-powered ESG analytics platform."""


@cli.command()
@click.option("--input", "input_text", default="", help="Input text or path to a text file to analyse.")
@click.option("--auto", is_flag=True, default=False, help="Autonomous mode: agent searches for live market data.")
@click.option("--excel", is_flag=True, default=False, help="Generate colour-coded Excel dashboard.")
@click.option("--word", is_flag=True, default=False, help="Generate professional Word report.")
@click.option("--json-output", "json_output", default="", help="Save raw JSON report to this path.")
@click.option("--output-dir", "output_dir", default="./outputs", help="Directory for generated report files.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose debug logging.")
def analyze(
    input_text: str,
    auto: bool,
    excel: bool,
    word: bool,
    json_output: str,
    output_dir: str,
    verbose: bool,
) -> None:
    """
    Analyse carbon markets and generate intelligence reports.

    Examples:

      python main.py analyze --auto --excel --word

      python main.py analyze --input "EU ETS EUR 65, UK ETS GBP 45..."

      python main.py analyze --input data.txt --excel --word --json-output report.json
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    _print_header()

    # Resolve input
    text = ""
    if auto:
        text = "auto"
        console.print("[bold cyan]Mode:[/bold cyan] Autonomous web-search (fetching live data)")
    elif input_text:
        p = Path(input_text)
        if p.exists() and p.is_file():
            text = p.read_text(encoding="utf-8")
            console.print(f"[bold cyan]Mode:[/bold cyan] File input — {p}")
        else:
            text = input_text
            console.print("[bold cyan]Mode:[/bold cyan] Text input")
    else:
        text = "auto"
        console.print("[bold cyan]Mode:[/bold cyan] Autonomous web-search (no input provided — defaulting to auto)")

    # Run analysis
    from agent import CarbonMarketAgent
    from config import settings

    try:
        settings.validate()
    except ValueError as exc:
        console.print(f"[bold red]Configuration Error:[/bold red] {exc}")
        console.print("[dim]Set ANTHROPIC_API_KEY in your .env file or environment.[/dim]")
        sys.exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        task = progress.add_task("🤖  Analysing carbon markets with Claude...", total=None)
        try:
            agent = CarbonMarketAgent()
            report = agent.analyze(text)
        except Exception as exc:
            console.print(f"[bold red]Analysis failed:[/bold red] {exc}")
            sys.exit(1)
        progress.update(task, description="✅  Analysis complete!")

    console.print("[bold green]✅  Analysis complete![/bold green]\n")

    # Display results
    _print_market_overview(report)
    _print_compliance_markets(report)
    _print_vcm(report)
    _print_risk_summary(report)
    _print_forecast(report)
    _print_opportunities(report)
    _print_data_quality(report)

    # Output directory
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON export
    if json_output:
        json_path = Path(json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"[green]📄  JSON saved:[/green] {json_path.resolve()}")

    # Excel export
    if excel:
        from tools.excel_generator import ExcelGenerator
        xl_path = out_dir / f"Carbon_Intelligence_{timestamp}.xlsx"
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=True, console=console) as p:
            t = p.add_task("📊  Generating Excel dashboard...", total=None)
            try:
                ExcelGenerator().generate(report, xl_path)
                p.update(t, description="✅  Excel generated!")
            except Exception as exc:
                console.print(f"[red]Excel generation failed:[/red] {exc}")
        console.print(f"[green]📊  Excel saved:[/green] {xl_path.resolve()}")

    # Word export
    if word:
        from tools.word_generator import WordGenerator
        docx_path = out_dir / f"Carbon_Intelligence_{timestamp}.docx"
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=True, console=console) as p:
            t = p.add_task("📝  Generating Word report...", total=None)
            try:
                WordGenerator().generate(report, docx_path)
                p.update(t, description="✅  Word report generated!")
            except Exception as exc:
                console.print(f"[red]Word generation failed:[/red] {exc}")
        console.print(f"[green]📝  Word saved:[/green] {docx_path.resolve()}")

    console.print()
    console.print(
        Panel(
            "[bold green]Report generation complete.[/bold green]\n"
            "Review the outputs above for the full intelligence analysis.",
            border_style="green",
            padding=(0, 2),
        )
    )


@cli.command()
@click.option("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
@click.option("--port", default=8000, type=int, help="Port to listen on (default: 8000)")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload for development")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the FastAPI REST API server."""
    import uvicorn

    _print_header()
    console.print(f"[bold cyan]🚀  Starting API server on http://{host}:{port}[/bold cyan]")
    console.print(f"[dim]  Docs: http://{host}:{port}/docs[/dim]")
    console.print(f"[dim]  Health: http://{host}:{port}/health[/dim]")
    console.print()

    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    cli()
