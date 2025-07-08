import subprocess
import typer

from enum import Enum

app = typer.Typer()


class Deployment(Enum):
    LOCAL = "local"
    REMOTE = "remote"


# NOTE: If the linked libraries are outdated and need to be recopied copy
# libresolv_wrapper.so into ../cockroach/artifacts directory
@app.command()
def build():
    image_tag = "cockroach-builder"

    # Build Build-Container
    subprocess.run(
        [
            "docker",
            "build",
            "-f",
            "./../build/crdb/dockerfile",
            "-t",
            image_tag,
            "./..",
        ],
        check=True,
    )

    # Run Build-Container
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-it",
            "-v",
            "./../:/app",
            "--workdir",
            "/app/cockroach",
            "-v",
            "bzlhome:/home/roach:delegated",
            "-u",
            "1000:1000",
            image_tag,
        ],
        check=True,
    )


@app.command()
def run(deployment: Deployment):
    match deployment:
        case Deployment.LOCAL:
            """
            TODO: spin up cluster of a certain size and connect them with each
            other. Then make sure that we gather enough information such as
            the workload and other important parameters. Run the experiment step
            by step
            """
            print("Local")
        case Deployment.REMOTE:
            print("Remote")


if __name__ == "__main__":
    app()
