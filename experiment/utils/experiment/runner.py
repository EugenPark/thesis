import os
import random
import time
from .models import ExperimentConfig
from .docker import DockerManager
from .terraform import TerraformManager
from ..analysis import run as run_analysis
from ..common import get_local_output_dir, DeploymentType, ExperimentType


class ExperimentRunner:
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.docker = DockerManager()
        self.terraform = TerraformManager()

    def run(self):
        match self.config.deployment_type:
            case DeploymentType.LOCAL:
                print("local")
                self._run_local()
            case DeploymentType.REMOTE:
                self._run_remote()

    def _run_local(self):
        self._prepare_local_run()

        for i in range(1, self.config.sample_size + 1):
            seed = random.randint(1, 2**31 - 1)
            for exp_type in ExperimentType:
                self._run_single_local(i, exp_type, seed)
                time.sleep(15)

        run_analysis(self.config.name, self.config.sample_size)

    def _prepare_local_run(self):
        for exp_type in ExperimentType:
            self.docker.build_image(exp_type)

        self.docker.create_network()

    def _run_single_local(self, run: int, exp_type: ExperimentType, seed: int):
        # Preparation
        join_str = DeploymentType.create_join_str(
            self.config.cluster_size, DeploymentType.LOCAL
        )

        # Cluster
        local_output_dir = get_local_output_dir(
            self.config.name, run, exp_type
        )
        for server in range(1, self.config.cluster_size + 1):
            output_dir = f"{local_output_dir}/logs"
            os.makedirs(output_dir, exist_ok=True)
            self.docker.run_server(run, server, exp_type, join_str, output_dir)

        # Client
        output_dir = f"{local_output_dir}/data"
        os.makedirs(output_dir, exist_ok=True)
        self.docker.run_client(
            self.config.workload_config(),
            output_dir,
            exp_type,
            seed,
        )

        # Clean up
        self.docker.stop_and_remove_running_containers()

    def _run_remote(self):
        for exp_type in ExperimentType:
            self.docker.build_image(exp_type)
            self.docker.push_image(exp_type)

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
