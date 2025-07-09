import typer
import build
import run


app = typer.Typer()

app.add_typer(build.app, name="build")
app.add_typer(run.app, name="run")


if __name__ == "__main__":
    app()
