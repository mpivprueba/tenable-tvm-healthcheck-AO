import typer
from src.core.engine import AssessmentEngine

app = typer.Typer()


@app.command()
def run():
    """Execute MPIV Assessment"""
    engine = AssessmentEngine()
    engine.run()
