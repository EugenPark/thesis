import os
import random
import time
import subprocess
from .models import ExperimentType, DeploymentType, ExperimentConfig
from .docker import DockerManager
from .terraform import TerraformManager
from ..analysis import run as run_analysis
from .config import NETWORK


class ExperimentRunner:
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.docker = DockerManager()
        self.terraform = TerraformManager()
        self.image_tags = {}

    def run(self, deployment_type: DeploymentType):
        if deployment_type == DeploymentType.LOCAL:
            self._run_local()
        else:
            self._run_remote()

    def _run_local(self):
        for exp_type in ExperimentType:
            self.image_tags[exp_type] = self.docker.build_image(exp_type)

        for i in range(1, self.config.sample_size + 1):
            seed = random.randint(1, 2**31 - 1)
            for exp_type in ExperimentType:
                self._run_single_local(i, exp_type, seed)
                time.sleep(15)

        run_analysis(self.config.name, self.config.sample_size)

    def _run_single_local(
        self, run_number: int, exp_type: ExperimentType, seed: int
    ):
        image_tag = self.image_tags[exp_type]
        join_str = ",".join(
            [
                f"server-{i}:26257"
                for i in range(1, self.config.cluster_size + 1)
            ]
        )
        self.docker.create_network()

        for i in range(1, self.config.cluster_size + 1):
            os.makedirs(
                f"./runs/{self.config.name}/logs/server-{i}", exist_ok=True
            )
            subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    f"server-{i}",
                    "--network",
                    NETWORK,
                    "-p",
                    f"{26257+i}:26257",
                    "-p",
                    f"{8080+i}:8080",
                    "-v",
                    f"./runs/{self.config.name}/logs/server-{i}:"
                    "/var/experiment/logs",
                    image_tag,
                    "./cockroach",
                    "start",
                    "--insecure",
                    f"--join={join_str}",
                    "--store=/app/store",
                    "--log-dir=/var/experiment/logs",
                    "--listen-addr=0.0.0.0:26257",
                    f"--advertise-addr=server-{i}:26257",
                    "--http-addr=0.0.0.0:8080",
                ],
                check=True,
            )

        self._run_client(image_tag, exp_type, run_number, seed)

        for i in range(1, self.config.cluster_size + 1):
            self.docker.stop_and_remove(f"server-{i}")
        self.docker.stop_and_remove("client-1")

    def _run_client(
        self, image_tag: str, exp_type: ExperimentType, run: int, seed: int
    ):
        local_output_dir = (
            f"./runs/{self.config.name}/results/data/run-{run}-{str(exp_type)}"
        )
        remote_output_dir = "/var/experiment/data"
        os.makedirs(local_output_dir, exist_ok=True)

        full_cmd = (
            "./cockroach init --insecure --host=server-1:26257 && sleep 5 && "
            f"./cockroach workload init {self.config.workload} "
            f"{self.config.workload_args} "
            "postgresql://root@server-1:26257?sslmode=disable && sleep 5 && "
            f"mkdir -p {remote_output_dir} && ./cockroach workload run "
            f"{self.config.workload} {self.config.workload_args} "
            f"--duration={self.config.duration} --seed={seed} "
            f"--histograms={remote_output_dir}/hdrhistograms.json "
            f"--display-format=incremental-json "
            "postgresql://root@server-1:26257?sslmode=disable > "
            f"{remote_output_dir}/client.txt"
        )

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

    def _run_remote(self):
        for exp_type in ExperimentType:
            image_tag = self.docker.build_image(exp_type)
            self.docker.push_image(image_tag)

        seed = random.randint(1, 2**31 - 1)
        self.terraform.apply(
            self.config.cluster_size,
            self.config.workload,
            self.config.workload_args,
            self.config.duration,
            seed,
        )
        time.sleep(60)
        self.terraform.destroy(
            self.config.cluster_size,
            self.config.workload,
            self.config.workload_args,
            self.config.duration,
            seed,
        )
