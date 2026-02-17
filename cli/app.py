import typer
from rich import print

app = typer.Typer(help="MPIV TVM Advisor Platform")

@app.command()
def run():
    """
    Run a new assessment (simulation mode).
    """
    print("[bold green]Starting MPIV Assessment Engine...[/bold green]")
    print("Simulation mode active. No Tenable connection yet.")
