import os
import random
import time
from .models import ExperimentConfig
from .docker import DockerManager
from .terraform import TerraformManager
from ..analysis import run as run_analysis
from ..common import (
    get_local_output_dir,
    create_join_str,
    runInParallel,
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
        workload_config = self.config.workload_config()
        experiment_type_per_cluster = []
        seed_per_cluster = []
        run_per_experiment_type = []

        for exp_type in ExperimentType:
            self.docker.build_image(exp_type)
            self.docker.push_image(exp_type)

        for i in range(self.config.sample_size):
            for exp_type in ExperimentType:
                experiment_type_per_cluster.append(exp_type)
                seed = random.randint(1, 2**31 - 1)
                seed_per_cluster.append(seed)

        # Start experiment
        self.terraform.apply(
            experiment_type_per_cluster,
            self.config.cluster_size,
            seed_per_cluster,
            workload_config,
        )

        fns = []
        for i in range(len(experiment_type_per_cluster)):

            def wait_and_download():
                run = run_per_experiment_type[i]
                experiment_type = experiment_type_per_cluster[i]
                self.terraform.block_until_experiment_end(
                    run,
                    experiment_type,
                    workload_config.duration,
                )

                self.terraform.download(
                    self.config.name,
                    experiment_type,
                    run,
                )

            fns.append(wait_and_download)

        runInParallel(*fns)

        # Clean up
        self.terraform.destroy(
            experiment_type_per_cluster,
            self.config.cluster_size,
            seed_per_cluster,
            workload_config,
        )

        # Analyze
        run_analysis(self.config.name, self.config.sample_size)
