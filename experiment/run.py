import os
import subprocess
import typer


app = typer.Typer()


@app.command()
def local(cluster_size: int):
    # Build Image
    image_tag = "crdb-experiment"
    dockerfile_path = "./../build/local/dockerfile"
    build_arg = "BIN_NAME=cockroach-baseline"
    context_path = "./.."

    cmd = [
        "docker",
        "build",
        "-f",
        dockerfile_path,
        "--build-arg",
        build_arg,
        "-t",
        image_tag,
        context_path,
    ]

    subprocess.run(
        cmd,
        check=True,
    )

    # Create network
    network = "crdb-net"
    driver = "bridge"

    cmd = ["docker", "network", "create", "-d", driver, network]

    subprocess.run(cmd, check=False)

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
        volume_logs = f"./logs/server-{i}:/app/logs"
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
            volume_logs,
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

    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            network,
            image_tag,
            "./cockroach",
            "workload",
            "init",
            "ycsb",
            "postgresql://root@server-1:26257?sslmode=disable",
        ],
        check=True,
    )

    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            network,
            image_tag,
            "./cockroach",
            "workload",
            "run",
            "ycsb",
            "--duration=1m",
            "postgresql://root@server-1:26257?sslmode=disable",
        ],
        check=True,
    )

    for i in range(1, cluster_size + 1):
        subprocess.run(["docker", "stop", f"server-{i}"])


@app.command()
def remote():
    typer.echo("remote")


if __name__ == "__main__":
    app()
