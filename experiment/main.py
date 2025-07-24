import typer
import build as b
import warmup as w
import run
import recovery as r


app = typer.Typer()
app.add_typer(run.app, name="run")


# NOTE: If the linked libraries are outdated and need to be recopied copy
# libresolv_wrapper.so into ../cockroach/artifacts directory
@app.command()
def build():
    b.build_container()
    b.run_container()


@app.command()
def warmup():
    w.compare_ycsb_warmup()
    w.compare_tpcc_warmup()


@app.command()
def recovery():
    r.compare_recovery()


if __name__ == "__main__":
    app()
