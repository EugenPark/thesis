import subprocess
import typer


app = typer.Typer()


# NOTE: If the linked libraries are outdated and need to be recopied copy
# libresolv_wrapper.so into ../cockroach/artifacts directory
@app.command()
def build():
    image_tag = "cockroach-builder"

    # Build Build-Container
    dockerfile_path = "./../build/crdb/dockerfile"
    context_path = "./.."

    cmd = ["docker", "build", "-f", dockerfile_path, "-t", image_tag, context_path]

    subprocess.run(
        cmd,
        check=True,
    )

    # Run Build-Container
    workdir_path = "/app/cockroach"
    volume_app_path = "./../:/app"
    volume_bzlhome_path = "bzlhome:/home/roach:delegated"
    user = "1000:1000"

    cmd = [
        "docker",
        "run",
        "--rm",
        "-it",
        "--workdir",
        workdir_path,
        "-v",
        volume_app_path,
        "-v",
        volume_bzlhome_path,
        "-u",
        user,
        image_tag,
    ]

    subprocess.run(
        cmd,
        check=True,
    )


if __name__ == "__main__":
    app()
