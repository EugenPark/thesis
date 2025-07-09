import os
import subprocess
import typer


app = typer.Typer()

IMAGE_TAG = "crdb-experiment"
NETWORK = "crdb-net"


def build_image():
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
        IMAGE_TAG,
        context_path,
    ]

    subprocess.run(
        cmd,
        check=True,
    )


def create_network():
    driver = "bridge"

    cmd = ["docker", "network", "create", "-d", driver, NETWORK]

    subprocess.run(cmd, check=False)


def create_join_str(cluster_size: int) -> str:
    cluster_names = []

    for i in range(1, cluster_size + 1):
        cluster_names.append(f"server-{i}:26257")

    return ",".join(cluster_names)


def start_nodes(cluster_size: int):
    logs_dir = "./logs"
    os.makedirs(logs_dir, exist_ok=True)
    join_str = create_join_str(cluster_size)

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
            NETWORK,
            "-p",
            f"{sql_port}:26257",
            "-p",
            f"{dashboard_port}:8080",
            "-v",
            volume_logs,
            IMAGE_TAG,
            "./cockroach",
            "start",
            "--insecure",
            f"--join={join_str}",
            "--store=/app/store",
            "--log-dir=/app/logs",
            "--listen-addr=0.0.0.0:26257",
            f"--advertise-addr={name}:26257",
            "--http-addr=0.0.0.0:8080",
        ]
        subprocess.run(cmd, check=True)


def init_cluster():
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            NETWORK,
            IMAGE_TAG,
            "./cockroach",
            "init",
            "--insecure",
            "--host=server-1:26257",
        ],
        check=True,
    )


def run_experiment():
    # init workload
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            NETWORK,
            IMAGE_TAG,
            "./cockroach",
            "workload",
            "init",
            "ycsb",
            "postgresql://root@server-1:26257?sslmode=disable",
        ],
        check=True,
    )

    # run workload
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            NETWORK,
            IMAGE_TAG,
            "./cockroach",
            "workload",
            "run",
            "ycsb",
            "--duration=1m",
            "postgresql://root@server-1:26257?sslmode=disable",
        ],
        check=True,
    )


def stop_nodes(cluster_size):
    for i in range(1, cluster_size + 1):
        subprocess.run(["docker", "stop", f"server-{i}"])


@app.command()
def local(cluster_size: int):
    build_image()
    create_network()
    start_nodes(cluster_size)
    init_cluster()
    run_experiment()
    stop_nodes(cluster_size)


@app.command()
def remote():
    typer.echo("remote")


if __name__ == "__main__":
    app()
