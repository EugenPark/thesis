import subprocess
from .models import WorkloadConfig
from ..common import ExperimentType, EXPERIMENT_DIR, SQL_PORT, DASHBOARD_PORT
from .config import PROJECT_ID, NETWORK


class DockerManager:
    def __init__(self):
        self.image_tags = {}
        self.running_containers = []

    def build_image(self, experiment_type: ExperimentType) -> str:
        image_tag = f"crdb-experiment-{str(experiment_type)}"
        cmd = [
            "docker",
            "build",
            "-f",
            "./../build/local/dockerfile",
            "--build-arg",
            f"BIN_NAME=cockroach-{str(experiment_type)}",
            "-t",
            image_tag,
            "..",
        ]

        subprocess.run(cmd, check=True)

        self.image_tags[experiment_type] = image_tag

    def push_image(self, experiment_type: ExperimentType):
        image_tag = self.image_tags[experiment_type]
        remote_url = (
            f"us-central1-docker.pkg.dev/{PROJECT_ID}/docker-registry"
            f"/{image_tag}"
        )
        subprocess.run(
            ["docker", "tag", image_tag, f"{remote_url}:latest"], check=True
        )
        subprocess.run(["docker", "push", remote_url], check=True)

    def create_network(self):
        subprocess.run(
            ["docker", "network", "create", "-d", "bridge", NETWORK],
            check=False,
        )

    def run_server(
        self,
        run: int,
        server: int,
        experiment_type: ExperimentType,
        join_str: str,
        local_output_dir: str,
    ):
        image_tag = self.image_tags[experiment_type]
        server_name = f"server-{server}"
        remote_output_dir = "/var/experiment/logs"
        remote_store = "/app/store"
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                server_name,
                "--network",
                NETWORK,
                "-p",
                f"{SQL_PORT+server}:{SQL_PORT}",
                "-p",
                f"{DASHBOARD_PORT+server}:{DASHBOARD_PORT}",
                "-v",
                f"{local_output_dir}:{remote_output_dir}",
                image_tag,
                "./cockroach",
                "start",
                "--insecure",
                f"--join={join_str}",
                f"--store={remote_store}",
                f"--log-dir={remote_output_dir}",
                f"--listen-addr=0.0.0.0:{SQL_PORT}",
                f"--advertise-addr=server-{server}:{SQL_PORT}",
                f"--http-addr=0.0.0.0:{DASHBOARD_PORT}",
            ],
            check=True,
        )
        self.running_containers.append(server_name)

    def run_client(
        self,
        config: WorkloadConfig,
        local_output_dir: str,
        experiment_type: ExperimentType,
        seed: int,
    ):
        image_tag = self.image_tags[experiment_type]
        client_name = "client"
        remote_host = "server-1"
        remote_connection = (
            f"postgresql://root@{remote_host}:{SQL_PORT}?sslmode=disable"
        )

        full_cmd = (
            # Init the cluster
            f"./cockroach init --insecure --host={remote_host}:{SQL_PORT} "
            # Wait for initialization
            "&& sleep 5 && "
            # Init workload
            "./cockroach workload init "
            f"{config.workload} {config.workload_args} {remote_connection} "
            # Wait for workload initialization
            "&& sleep 5 && "
            # Run workload
            f"mkdir -p {EXPERIMENT_DIR} && ./cockroach workload run "
            f"{config.workload} {config.workload_args} "
            f"--duration={config.duration} "
            f"--seed={seed} "
            f"--histograms={EXPERIMENT_DIR}/hdrhistograms.json "
            f"--display-format=incremental-json "
            f"{remote_connection} "
            # Pipe output
            f"> {EXPERIMENT_DIR}/client.txt"
        )

        subprocess.run(
            [
                "docker",
                "run",
                "--name",
                client_name,
                "--network",
                NETWORK,
                "-v",
                f"{local_output_dir}:{EXPERIMENT_DIR}",
                image_tag,
                "bash",
                "-c",
                full_cmd,
            ],
            check=True,
        )

        self.running_containers.append(client_name)

    def stop_and_remove_running_containers(self):
        for name in self.running_containers:
            subprocess.run(["docker", "stop", name], check=False)
            subprocess.run(["docker", "rm", name], check=False)
