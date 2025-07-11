import os
import random
import time
import subprocess
from .analysis import run as run_analysis
from .common import ExperimentType


NETWORK = "crdb-net"


def _build_image(experiment_type: ExperimentType) -> str:
    dockerfile_path = "./../build/local/dockerfile"
    build_arg = f"BIN_NAME=cockroach-{str(experiment_type)}"
    image_tag = f"crdb-experiment-{str(experiment_type)}"
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

    return image_tag


def _create_network():
    driver = "bridge"

    cmd = ["docker", "network", "create", "-d", driver, NETWORK]

    subprocess.run(cmd, check=False)


def _create_join_str(cluster_size: int) -> str:
    cluster_names = []

    for i in range(1, cluster_size + 1):
        cluster_names.append(f"server-{i}:26257")

    return ",".join(cluster_names)


def _start_nodes(experiment_name: str, image_tag: str, cluster_size: int):
    join_str = _create_join_str(cluster_size)

    for i in range(1, cluster_size + 1):
        sql_port = 26257 + i
        dashboard_port = 8080 + i
        server_name = f"server-{i}"
        logs_output_dir = f"./runs/{experiment_name}/logs/{server_name}"
        os.makedirs(logs_output_dir, exist_ok=True)
        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            server_name,
            "--network",
            NETWORK,
            "-p",
            f"{sql_port}:26257",
            "-p",
            f"{dashboard_port}:8080",
            "-v",
            f"{logs_output_dir}:/app/logs",
            image_tag,
            "./cockroach",
            "start",
            "--insecure",
            f"--join={join_str}",
            "--store=/app/store",
            "--log-dir=/app/logs",
            "--listen-addr=0.0.0.0:26257",
            f"--advertise-addr={server_name}:26257",
            "--http-addr=0.0.0.0:8080",
        ]
        subprocess.run(cmd, check=True)


def _run_experiment(
    name: str,
    run: int,
    experiment_type: ExperimentType,
    image_tag: str,
    workload: str,
    duration: int,
    workload_args: str,
    seed: int,
):
    local_output_dir = (
        f"./runs/{name}/results/data/run-{run}-{str(experiment_type)}"
    )
    os.makedirs(local_output_dir, exist_ok=True)
    remote_output_dir = "/tmp/data"

    # Init cluster command
    init_cluster_cmd = "./cockroach init --insecure --host=server-1:26257"

    # Init workload command
    init_cmd = (
        f"./cockroach workload init {workload} {workload_args} "
        f"postgresql://root@server-1:26257?sslmode=disable"
    )

    # Run workload command
    run_cmd = (
        f"mkdir -p {remote_output_dir} "
        f"&& ./cockroach workload run {workload} {workload_args} "
        f"--duration={duration} "
        f"--seed={seed} "
        f"--histograms={remote_output_dir}/hdrhistograms.json "
        f"--display-format=incremental-json "
        f"postgresql://root@server-1:26257?sslmode=disable "
        f"> {remote_output_dir}/client.txt"
    )

    # Combine all into one bash command
    full_cmd = (
        f"{init_cluster_cmd} && sleep 5 && {init_cmd} && sleep 5 && {run_cmd}"
    )

    # Docker run command
    subprocess.run(
        [
            "docker",
            "run",
            "--name",
            "client-1",
            "--network",
            NETWORK,
            "-v",
            f"{local_output_dir}:{remote_output_dir}",
            image_tag,
            "bash",
            "-c",
            full_cmd,
        ],
        check=True,
    )


def _stop_and_remove_container(name: str):
    subprocess.run(["docker", "stop", name])
    subprocess.run(["docker", "rm", name])


def _stop_nodes(cluster_size):
    for i in range(1, cluster_size + 1):
        _stop_and_remove_container(f"server-{i}")
    _stop_and_remove_container("client-1")


def _pipeline(
    image_tag: str,
    name: str,
    run: int,
    experiment_type: ExperimentType,
    cluster_size: int,
    workload: str,
    duration: int,
    workload_args: str,
    seed: int,
):
    _create_network()
    _start_nodes(name, image_tag, cluster_size)
    _run_experiment(
        name,
        run,
        experiment_type,
        image_tag,
        workload,
        duration,
        workload_args,
        seed,
    )
    _stop_nodes(cluster_size)


def run(
    name: str,
    sample_size: int,
    cluster_size: int,
    workload: str,
    duration: int,
    workload_args: str,
):
    image_tags = {}
    for experiment_type in ExperimentType:
        image_tags[experiment_type] = _build_image(experiment_type)

    for i in range(1, sample_size + 1):
        seed = random.randint(1, 2**31 - 1)
        for experiment_type in ExperimentType:
            image_tag = image_tags[experiment_type]
            _pipeline(
                image_tag,
                name,
                i,
                experiment_type,
                cluster_size,
                workload,
                duration,
                workload_args,
                seed,
            )
            # Cooldown
            time.sleep(15)

    run_analysis(name, sample_size)
