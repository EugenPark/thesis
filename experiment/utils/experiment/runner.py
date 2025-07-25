import os
import subprocess
import random
import time
import threading
from .models import ExperimentConfig
from .docker import DockerManager
from .terraform import TerraformManager
from ..analysis import run as run_analysis
from ..common import (
    get_local_output_dir,
    create_join_str,
    convert_duration,
    DeploymentType,
    ExperimentType,
)


class ExperimentRunner:
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.docker = DockerManager()
        self.terraform = TerraformManager()

    def run(self):
        match self.config.deployment_type:
            case DeploymentType.LOCAL:
                self._run_local()
            case DeploymentType.REMOTE:
                self._run_remote()

    def _run_local(self):
        for exp_type in ExperimentType:
            self.docker.build_image(exp_type)

        self.docker.create_network()

        for i in range(1, self.config.sample_size + 1):
            seed = random.randint(1, 2**31 - 1)
            for exp_type in ExperimentType:
                self._run_single_local(i, exp_type, seed)
                time.sleep(15)

        run_analysis(self.config.name, self.config.sample_size)

    def _run_single_local(self, run: int, exp_type: ExperimentType, seed: int):
        # Preparation
        join_str = create_join_str(
            DeploymentType.LOCAL, self.config.cluster_size
        )

        # Cluster
        local_output_dir = get_local_output_dir(
            self.config.name, run, exp_type
        )
        for server in range(1, self.config.cluster_size + 1):
            output_dir = f"{local_output_dir}/logs"
            os.makedirs(output_dir, exist_ok=True)
            self.docker.run_server(run, server, exp_type, join_str, output_dir)

        # 🔁 Optional Restart Thread
        if self.config.restart:

            def restart_container():
                delay = (convert_duration(self.config.duration) / 3) * 4
                time.sleep(delay)
                container_name = "server-2"
                subprocess.run(
                    ["docker", "restart", container_name], check=True
                )
                print(
                    f"[Restart Thread] Restarted container: {container_name}"
                )

            threading.Thread(target=restart_container, daemon=True).start()

        # Client
        output_dir = f"{local_output_dir}/data"
        os.makedirs(output_dir, exist_ok=True)
        self.docker.run_client(
            self.config.workload_config(), output_dir, exp_type, seed
        )

        # Clean up
        self.docker.stop_and_remove_running_containers()

    def _run_remote(self):
        for exp_type in ExperimentType:
            self.docker.build_image(exp_type)
            self.docker.push_image(exp_type)

        for i in range(1, self.config.sample_size + 1):
            for exp_type in ExperimentType:
                self._run_single_remote(exp_type, i)

        run_analysis(self.config.name, self.config.sample_size)

    def _run_single_remote(self, experiment_type: ExperimentType, run: int):
        # Preparation
        seed = random.randint(1, 2**31 - 1)
        workload_config = self.config.workload_config()

        # Start experiment
        self.terraform.apply(
            experiment_type,
            self.config.cluster_size,
            seed,
            workload_config,
        )

        # Wait for experiment to start and finish
        self.terraform.wait_for_experiment_state(
            experiment_type, workload_config, "start"
        )

        # 🔁 Optional Restart Thread
        if self.config.restart:

            def restart_container():
                delay = (convert_duration(self.config.duration) / 3) * 4
                time.sleep(delay)
                container_name = "server-3"

                cmd = "docker restart $(docker ps -q)"

                ssh_cmd = [
                    "gcloud",
                    "compute",
                    "ssh",
                    container_name,
                    "--zone",
                    "us-central1-a",
                    "--command",
                    cmd,
                ]

                subprocess.run(ssh_cmd, check=True)
                print(
                    f"[Restart Thread] Restarted container: {container_name}"
                )

            threading.Thread(target=restart_container, daemon=True).start()

        self.terraform.wait_for_experiment_state(
            experiment_type, workload_config, "end"
        )

        # Download results
        self.terraform.download(self.config.name, experiment_type, run)

        # Clean up
        self.terraform.destroy(
            experiment_type,
            self.config.cluster_size,
            seed,
            workload_config,
        )
