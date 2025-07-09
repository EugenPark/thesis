import os
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
def run(deployment: Deployment, cluster_size: int):
    match deployment:
        case Deployment.LOCAL:
            # Build Image
            image_tag = "crdb-experiment"
            subprocess.run(
                [
                    "docker",
                    "build",
                    "-f",
                    "./../build/local/dockerfile",
                    "--build-arg",
                    "BIN_NAME=cockroach-baseline",
                    "-t",
                    image_tag,
                    "./..",
                ],
                check=True,
            )
            # Create network
            network = "crdb-net"
            subprocess.run(
                ["docker", "network", "create", "-d", "bridge", network], check=False
            )

            # Spin up cluster
            logs_dir = "./logs"
            cluster_names = []

            for i in range(1, cluster_size + 1):
                cluster_names.append(f"server-{i}:26257")

            cluster_names = ",".join(cluster_names)
            os.makedirs(logs_dir, exist_ok=True)

            for i in range(1, cluster_size + 1):
                sql_port = 26257 + i
                dashboard_port = 8080 + i
                name = f"server-{i}"
                cmd = [
                    "docker",
                    "run",
                    "--rm",
                    "-d",
                    "--name",
                    name,
                    "--network",
                    network,
                    "-p",
                    f"{sql_port}:26257",
                    "-p",
                    f"{dashboard_port}:8080",
                    "-v",
                    f"./logs/server-{i}:/app/logs",
                    image_tag,
                    "./cockroach",
                    "start",
                    "--insecure",
                    f"--join={cluster_names}",
                    "--store=/app/store",
                    "--log-dir=/app/logs",
                    "--listen-addr=0.0.0.0:26257",
                    f"--advertise-addr={name}:26257",
                    "--http-addr=0.0.0.0:8080",
                ]
                subprocess.run(cmd, check=True)

            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    network,
                    image_tag,
                    "./cockroach",
                    "init",
                    "--insecure",
                    "--host=server-1:26257",
                ],
                check=True,
            )

        case Deployment.REMOTE:
            print("Remote")


if __name__ == "__main__":
    app()
