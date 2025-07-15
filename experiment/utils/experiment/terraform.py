import subprocess
import os
import time
import json
from .config import TF_DIR, PROJECT_ID
from ..common import (
    DeploymentType,
    ExperimentType,
    SQL_PORT,
    DASHBOARD_PORT,
    EXPERIMENT_DIR,
    create_join_str,
    create_remote_host,
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
        remote_host = create_remote_host("server-1")
        remote_connection = (
            f"postgresql://root@{remote_host}:{SQL_PORT}?sslmode=disable"
        )

        client_cmd = (
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
            f"./cockroach workload run "
            f"{config.workload} {config.workload_args} "
            f"--duration={config.duration} "
            f"--seed={seed} "
            f"--histograms={EXPERIMENT_DIR}/data/hdrhistograms.json "
            f"--display-format=incremental-json "
            f"{remote_connection} "
            # Pipe output
            f"> {EXPERIMENT_DIR}/data/client.txt"
        )

        client_cmd = json.dumps(["sh", "-c", client_cmd])

        server_cmds = []
        join_str = create_join_str(DeploymentType.REMOTE, cluster_size)
        print(join_str)

        for i in range(1, cluster_size + 1):
            remote_host = create_remote_host(f"server-{i}")
            server_cmd = [
                "./cockroach",
                "start",
                "--insecure",
                f"--join={join_str}",
                "--store=/app/store",
                f"--log-dir={EXPERIMENT_DIR}/logs",
                f"--listen-addr=0.0.0.0:{SQL_PORT}",
                f"--advertise-addr={remote_host}:{SQL_PORT}",
                f"--http-addr=0.0.0.0:{DASHBOARD_PORT}",
            ]
            server_cmds.append(server_cmd)

        server_cmds = json.dumps(server_cmds)

        return {
            "client_cmd": client_cmd,
            "server_cmds": server_cmds,
            "project_id": PROJECT_ID,
            "cluster_size": cluster_size,
            "experiment_dir": EXPERIMENT_DIR,
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
        probe = (
            f"docker ps -a --filter 'ancestor={image_name}' --filter "
            "'status=exited' -q"
        )

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

    def download(self, name: str, experiment_type: ExperimentType, run: int):
        target_node = "client"
        local_dir = (
            f"./runs/{name}/run-{run}/experiment-{str(experiment_type)}/data"
        )
        os.makedirs(local_dir, exist_ok=True)
        zone = "us-central1-a"

        # Gather overall output
        cmd = [
            "gcloud",
            "compute",
            "scp",
            f"--zone={zone}",
            f"{target_node}:{EXPERIMENT_DIR}/data/client.txt",
            f"{local_dir}/client.txt",
        ]
        subprocess.run(cmd, check=False)

        # Gather histograms
        cmd = [
            "gcloud",
            "compute",
            "scp",
            f"--zone={zone}",
            f"{target_node}:{EXPERIMENT_DIR}/data/hdrhistograms.json",
            f"{local_dir}/hdrhistograms.json",
        ]
        subprocess.run(cmd, check=False)
