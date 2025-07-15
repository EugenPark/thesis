import subprocess
import time
import json
from .config import TF_DIR, PROJECT_ID
from ..common import (
    DeploymentType,
    ExperimentType,
    SQL_PORT,
    DASHBOARD_PORT,
    create_join_str,
)
from .models import WorkloadConfig


class TerraformManager:
    def _build_vars(
        self,
        experiment_type: ExperimentType,
        cluster_size: int,
        seed: int,
        config: WorkloadConfig,
    ) -> dict:
        experiment_dir = "/var/experiment"

        # client_cmd = (
        #     f"./cockroach workload run "
        #     f"{config.workload} {config.workload_args} "
        #     f"--duration={config.duration} "
        #     f"--seed={seed} "
        #     f"--histograms={experiment_dir}/data/hdrhistograms.json "
        #     "--display-format=incremental-json "
        #     "postgresql://root@server-1:26257?sslmode=disable > "
        #     f"{experiment_dir}/data/client.txt"
        # )
        client_cmd = [
            "./cockroach",
            "workload",
            "run " f"{config.workload}",
            f"{config.workload_args}",
            f"--duration={config.duration}",
            f"--seed={seed}",
            f"--histograms={experiment_dir}/data/hdrhistograms.json",
            "--display-format=incremental-json",
            "postgresql://root@server-1:26257?sslmode=disable",
            ">",
            f"{experiment_dir}/data/client.txt",
        ]

        server_cmds = []
        join_str = create_join_str(cluster_size, DeploymentType.REMOTE)

        for i in range(1, cluster_size + 1):
            server_cmd = [
                "./cockroach",
                "start",
                "--insecure",
                f"--join={join_str}",
                "--store=/app/store",
                f"--log-dir={experiment_dir}/logs",
                f"--listen-addr=0.0.0.0:{SQL_PORT}",
                f"--advertise-addr=server-{i}:{SQL_PORT}",
                f"--http-addr=0.0.0.0:{DASHBOARD_PORT}",
            ]
            server_cmds.append(server_cmd)

        server_cmds = json.dumps(server_cmds)
        client_cmd = json.dumps(client_cmd)

        return {
            "client_cmd": client_cmd,
            "server_cmds": server_cmds,
            "project_id": PROJECT_ID,
            "cluster_size": cluster_size,
            "experiment_dir": experiment_dir,
            "experiment_type": str(experiment_type),
        }

    def apply(
        self,
        experiment_type: ExperimentType,
        cluster_size: int,
        seed: int,
        config: WorkloadConfig,
    ):
        tf_vars = self._build_vars(experiment_type, cluster_size, seed, config)
        print(tf_vars)
        cmd = ["terraform", "apply", "-auto-approve"] + [
            f"-var={k}={v}" for k, v in tf_vars.items()
        ]
        subprocess.run(cmd, cwd=TF_DIR, check=True)

    def destroy(
        self,
        experiment_type: ExperimentType,
        cluster_size: int,
        seed: int,
        config: WorkloadConfig,
    ):
        tf_vars = self._build_vars(experiment_type, cluster_size, seed, config)
        cmd = ["terraform", "destroy", "-auto-approve"] + [
            f"-var={k}={v}" for k, v in tf_vars.items()
        ]
        subprocess.run(cmd, cwd=TF_DIR, check=True)

    def block_until_experiment_end(
        self, experiment_type: ExperimentType, config: WorkloadConfig
    ):
        duration = (
            int(config.duration[:-1])
            * {"s": 1, "m": 60, "h": 3600, "d": 86400}[config.duration[-1]]
        )
        time.sleep(duration)

        probe_server = "client"
        zone = "us-central1-a"
        image_name = (
            f"us-central1-docker.pkg.dev/{PROJECT_ID}/"
            f"docker-registry/crdb-experiment-{str(experiment_type)}"
        )
        probe = f"docker ps -a --filter 'ancestor={image_name}' --filter 'status=exited' -q"

        # NOTE: In worst case we just tear down after 30 seconds
        for i in range(30):
            cmd = [
                "gcloud",
                "compute",
                "ssh",
                probe_server,
                f"--zone={zone}",
                "--command",
                probe,
                "--quiet",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.stdout.strip() != "":
                break

            time.sleep(1)
