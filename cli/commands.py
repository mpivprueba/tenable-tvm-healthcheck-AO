import os
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from config.settings import settings

console = Console()

LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'mpiv_logo.png')


def banner():
    console.print(f"""
[bold blue]╔══════════════════════════════════════════════╗
║   MPIV TVM Advisor  v{settings.VERSION}                  ║
║   Tenable Health Check Platform              ║
╚══════════════════════════════════════════════╝[/bold blue]
""")
    mode = "[yellow]MOCK[/yellow]" if settings.MOCK_MODE else "[green]LIVE[/green]"
    console.print(
        f"  Mode: {mode}  |  "
        f"Customer: [bold]{settings.CUSTOMER_NAME}[/bold]  |  "
        f"ID: {settings.ENGAGEMENT_ID}\n"
    )
    for w in settings.validate():
        console.print(f"  [yellow]⚠  {w}[/yellow]")
    console.print()


@click.group()
def cli():
    """MPIV Tenable TVM Advisor — Health Check CLI"""
    banner()


@cli.command("assess")
@click.option("--no-pdf", is_flag=True, default=False, help="Skip PDF generation")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Show finding details")
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

    score_color = (
        "green" if summary.maturity_score >= 3.5
        else "yellow" if summary.maturity_score >= 2.5
        else "red"
    )
    console.print(Panel(
        f"[bold]Customer:[/bold] {summary.customer_name}\n"
        f"[bold]Maturity:[/bold] [{score_color}]{summary.maturity_level.value} "
        f"({summary.maturity_score}/5.0)[/{score_color}]\n"
        f"[bold]Assets:[/bold] {summary.total_assets}\n"
        f"[bold]Auth. Coverage:[/bold] {summary.authenticated_scans_pct:.1f}%\n"
        f"[bold]Scanner Health:[/bold] {summary.scanner_health_pct:.1f}%\n"
        f"[bold]Critical:[/bold] [red]{len(summary.critical_findings)}[/red]  "
        f"[bold]High:[/bold] [orange3]{len(summary.high_findings)}[/orange3]  "
        f"[bold]Total:[/bold] {len(summary.findings)}",
        title="[bold blue]Assessment Summary[/bold blue]"
    ))

    if summary.findings:
        console.print(f"\n[bold]Findings ({len(summary.findings)})[/bold]\n")
        tbl = Table(box=box.SIMPLE_HEAVY, header_style="bold cyan")
        tbl.add_column("ID", width=6)
        tbl.add_column("SEV", width=10)
        tbl.add_column("Category", width=22)
        tbl.add_column("Title")
        sev_colors = {
            "critical": "bold red", "high": "bold orange3",
            "medium": "bold yellow", "low": "bold green",
        }
        for f in summary.findings:
            sc = sev_colors.get(f.severity.value, "")
            tbl.add_row(f.id, f"[{sc}]{f.severity.upper()}[/{sc}]",
                        f.category.value, f.title)
        console.print(tbl)

        if verbose:
            console.print("\n[bold]Finding Details[/bold]\n")
            border_colors = {
                "critical": "red", "high": "orange3",
                "medium": "yellow", "low": "green",
            }
            for f in summary.findings:
                bc = border_colors.get(f.severity.value, "white")
                console.print(Panel(
                    f"[bold]Description:[/bold] {f.description}\n\n"
                    f"[bold]Evidence:[/bold] {f.evidence or 'N/A'}\n\n"
                    f"[bold]Recommendation:[/bold] {f.recommendation}\n\n"
                    f"[bold]Effort:[/bold] {f.effort.upper()}",
                    title=f"[bold]{f.id} — {f.title}[/bold]",
                    border_style=bc,
                ))

    if summary.recommendations:
        console.print(f"\n[bold]Recommendations[/bold]\n")
        type_colors = {"quick-win": "green", "strategic": "blue", "roadmap": "magenta"}
        for r in summary.recommendations:
            tc = type_colors.get(r.type, "white")
            console.print(f"  [{tc}]#{r.priority} [{r.type.upper()}][/{tc}] {r.title}")

    if verbose and summary.executive_narrative:
        console.print("\n[bold]Executive Narrative[/bold]\n")
        console.print(Panel(summary.executive_narrative,
                            title="[bold blue]AI-Generated Summary[/bold blue]"))

    if not no_pdf:
        console.print("\n[bold]Generating PDF report...[/bold]")
        try:
            logo = LOGO_PATH if os.path.exists(LOGO_PATH) else None
            if not logo:
                console.print("  [yellow]⚠  Logo not found at assets/mpiv_logo.png — generating without logo[/yellow]")
            pdf_path = PDFReportGenerator(summary, logo_path=logo).generate()
            console.print(f"\n[green]✔ Report saved:[/green] {pdf_path}\n")
        except Exception as e:
            console.print(f"\n[red]✘ PDF generation failed:[/red] {e}\n")


@cli.command("status")
def check_status():
    """Check configuration and connectivity status."""
    tbl = Table(box=box.ROUNDED, header_style="bold cyan")
    tbl.add_column("Component", style="bold")
    tbl.add_column("Status")
    tbl.add_column("Details")

    if settings.MOCK_MODE:
        tbl.add_row("Tenable API", "[yellow]MOCK[/yellow]", "Simulation mode active")
    elif settings.TENABLE_ACCESS_KEY:
        tbl.add_row("Tenable API", "[green]CONFIGURED[/green]", settings.TENABLE_API_URL)
    else:
        tbl.add_row("Tenable API", "[red]NOT CONFIGURED[/red]",
                    "Set TENABLE_ACCESS_KEY in .env")

    if settings.is_openai_configured():
        tbl.add_row("OpenAI Narrative", "[green]CONFIGURED[/green]", settings.OPENAI_MODEL)
    else:
        tbl.add_row("OpenAI Narrative", "[yellow]DISABLED[/yellow]",
                    "Set OPENAI_API_KEY in .env")

    tbl.add_row("Report Output", "[green]OK[/green]", str(settings.REPORT_OUTPUT_DIR))

    logo_status = "[green]OK[/green]" if os.path.exists(LOGO_PATH) else "[yellow]NOT FOUND[/yellow]"
    tbl.add_row("MPIV Logo", logo_status, "assets/mpiv_logo.png")

    mode_label = "MOCK (safe)" if settings.MOCK_MODE else "LIVE (real API)"
    mode_color = "yellow" if settings.MOCK_MODE else "green"
    tbl.add_row("Current Mode", f"[{mode_color}]{mode_label}[/{mode_color}]", "")
    console.print(tbl)
    console.print()


@cli.command("connect")
def test_connection():
    """Test real Tenable API connection."""
    if settings.MOCK_MODE:
        console.print("[yellow]⚠  Currently in MOCK MODE.[/yellow]")
        console.print("Set [bold]MOCK_MODE=false[/bold] in your .env to test real connection.\n")
        return

    if not settings.TENABLE_ACCESS_KEY or not settings.TENABLE_SECRET_KEY:
        console.print("[red]✘ API Keys not configured.[/red]")
        console.print("Set TENABLE_ACCESS_KEY and TENABLE_SECRET_KEY in your .env\n")
        return

    console.print("\n[bold]Testing Tenable API connection...[/bold]\n")
    try:
        from integrations.tenable_client import TenableClient
        client = TenableClient()

        with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                      console=console) as p:
            task = p.add_task("Fetching scanners...", total=None)
            scanners = client.get_scanners()
            p.update(task, description="Fetching assets...")
            assets = client.get_assets()
            p.update(task, description="Fetching scans...")
            scans = client.get_scans()
            p.update(task, description="Done!")

        tbl = Table(box=box.ROUNDED, header_style="bold cyan")
        tbl.add_column("Resource")
        tbl.add_column("Count", justify="right")
        tbl.add_column("Status")
        tbl.add_row("Scanners", str(len(scanners)), "[green]✔[/green]")
        tbl.add_row("Assets",   str(len(assets)),   "[green]✔[/green]")
        tbl.add_row("Scans",    str(len(scans)),    "[green]✔[/green]")
        console.print(tbl)
        console.print("\n[green]✔ Connection successful! Ready to run assessments.[/green]\n")

    except ConnectionError as e:
        console.print(f"\n[red]✘ Connection failed:[/red] {e}\n")
        console.print("Troubleshooting:")
        console.print("  1. Verify your API Keys in .env")
        console.print("  2. Check outbound access to cloud.tenable.com:443")
        console.print("  3. Confirm your user has API access permissions\n")
    except Exception as e:
        console.print(f"\n[red]✘ Unexpected error:[/red] {e}\n")


@cli.command("mock")
def toggle_mock():
    """Show how to switch between MOCK and LIVE mode."""
    console.print("\n[bold]Mode Switching Guide[/bold]\n")
    console.print(Panel(
        "[bold]MOCK MODE[/bold] — Safe for demos, no real API calls\n"
        "  In your .env:\n"
        "  [green]MOCK_MODE=true[/green]\n\n"
        "[bold]LIVE MODE[/bold] — Real Tenable API\n"
        "  In your .env:\n"
        "  [yellow]MOCK_MODE=false[/yellow]\n"
        "  TENABLE_ACCESS_KEY=your_key\n"
        "  TENABLE_SECRET_KEY=your_secret\n\n"
        "After editing .env, run:\n"
        "  [cyan]python main.py connect[/cyan]   ← verify connection\n"
        "  [cyan]python main.py assess[/cyan]    ← run full assessment",
        title="[bold blue]Mode Configuration[/bold blue]"
    ))
    console.print()