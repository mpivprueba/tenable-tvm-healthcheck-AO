import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from config.settings import settings

console = Console()

def banner():
    console.print(f"""
[bold blue]╔══════════════════════════════════════════════╗
║   MPIV TVM Advisor  v{settings.VERSION}                  ║
║   Tenable Health Check Platform              ║
╚══════════════════════════════════════════════╝[/bold blue]
""")
    mode = "[yellow]MOCK[/yellow]" if settings.MOCK_MODE else "[green]LIVE[/green]"
    console.print(f"  Mode: {mode}  |  Customer: [bold]{settings.CUSTOMER_NAME}[/bold]  |  ID: {settings.ENGAGEMENT_ID}\n")
    for w in settings.validate():
        console.print(f"  [yellow]⚠  {w}[/yellow]")
    console.print()

@click.group()
def cli():
    """MPIV Tenable TVM Advisor"""
    banner()

@cli.command("assess")
@click.option("--no-pdf", is_flag=True, default=False, help="Skip PDF generation")
@click.option("--verbose", "-v", is_flag=True, default=False)
def run_assessment(no_pdf, verbose):
    """Run full TVM Health Check assessment."""
    from services.assessment_service import AssessmentService
    from reporting.pdf_report import PDFReportGenerator

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Collecting Tenable data...", total=None)
        service = AssessmentService()
        p.update(t, description="Running gap analysis...")
        summary = service.run()
        p.update(t, description="Assessment complete!")

    # Summary panel
    score_color = "green" if summary.maturity_score >= 3.5 else "yellow" if summary.maturity_score >= 2.5 else "red"
    console.print(Panel(
        f"[bold]Customer:[/bold] {summary.customer_name}\n"
        f"[bold]Maturity:[/bold] [{score_color}]{summary.maturity_level.value} ({summary.maturity_score}/5.0)[/{score_color}]\n"
        f"[bold]Assets:[/bold] {summary.total_assets}\n"
        f"[bold]Auth. Coverage:[/bold] {summary.authenticated_scans_pct:.1f}%\n"
        f"[bold]Scanner Health:[/bold] {summary.scanner_health_pct:.1f}%\n"
        f"[bold]Critical:[/bold] [red]{len(summary.critical_findings)}[/red]  "
        f"[bold]High:[/bold] [orange3]{len(summary.high_findings)}[/orange3]  "
        f"[bold]Total:[/bold] {len(summary.findings)}",
        title="[bold blue]Assessment Summary[/bold blue]"
    ))

    # Findings table
    if summary.findings:
        console.print(f"\n[bold]Findings ({len(summary.findings)})[/bold]\n")
        t = Table(box=box.SIMPLE_HEAVY, header_style="bold cyan")
        t.add_column("ID", width=6)
        t.add_column("SEV", width=10)
        t.add_column("Category", width=22)
        t.add_column("Title")
        sev_colors = {"critical": "bold red", "high": "bold orange3",
                      "medium": "bold yellow", "low": "bold green"}
        for f in summary.findings:
            sc = sev_colors.get(f.severity.value, "")
            t.add_row(f.id, f"[{sc}]{f.severity.upper()}[/{sc}]",
                      f.category.value, f.title)
        console.print(t)

    # Recommendations
    if summary.recommendations:
        console.print(f"\n[bold]Recommendations[/bold]\n")
        type_colors = {"quick-win": "green", "strategic": "blue", "roadmap": "magenta"}
        for r in summary.recommendations:
            tc = type_colors.get(r.type, "white")
            console.print(f"  [{tc}]#{r.priority} [{r.type.upper()}][/{tc}] {r.title}")

    # PDF
    if not no_pdf:
        console.print("\n[bold]Generating PDF report...[/bold]")
        pdf_path = PDFReportGenerator(summary).generate()
        console.print(f"\n[green]✔ Report saved:[/green] {pdf_path}\n")

@cli.command("status")
def check_status():
    """Check configuration status."""
    t = Table(box=box.ROUNDED, header_style="bold cyan")
    t.add_column("Component", style="bold")
    t.add_column("Status")
    t.add_column("Details")
    mode = "[yellow]MOCK[/yellow]" if settings.MOCK_MODE else "[green]LIVE[/green]"
    t.add_row("Tenable API", mode, "Simulation mode" if settings.MOCK_MODE else settings.TENABLE_API_URL)
    ai_status = "[green]OK[/green]" if settings.is_openai_configured() else "[yellow]DISABLED[/yellow]"
    t.add_row("OpenAI Narrative", ai_status, settings.OPENAI_MODEL)
    t.add_row("Report Output", "[green]OK[/green]", str(settings.REPORT_OUTPUT_DIR))
    console.print(t)