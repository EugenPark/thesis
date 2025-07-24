import subprocess
import os
import time
import json
from .config import TF_DIR, PROJECT_ID, USER, remote_dir
from ..common import (
    DeploymentType,
    ExperimentType,
    SQL_PORT,
    DASHBOARD_PORT,
    EXPERIMENT_DIR,
    create_join_str,
    create_remote_host,
    convert_duration,
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
            f"{config.workload} {config.workload_args} {remote_connection} && "
            # Wait for workload initialization
            # f"mkdir -p {EXPERIMENT_DIR} && "
            f"sleep 5 && "
            # Run workload
            f"./cockroach workload run "
            f"{config.workload} {config.workload_args} "
            f"--duration={config.duration} "
            f"--ramp={config.ramp} "
            f"--seed={seed} "
            f"--histograms={EXPERIMENT_DIR}/hdrhistograms.json "
            f"--display-format=incremental-json "
            f"{remote_connection} "
            # Pipe output
            f"> {EXPERIMENT_DIR}/client.txt"
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
                f"--log-dir={EXPERIMENT_DIR}",
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

    def wait_for_experiment_state(
        self,
        experiment_type: ExperimentType,
        config: WorkloadConfig,
        target_state: str,
    ):
        duration = convert_duration(config.duration)
        retries = 20
        wait = 30

        probe_server = "client"
        zone = "us-central1-a"
        image_name = (
            f"us-central1-docker.pkg.dev/{PROJECT_ID}/"
            f"docker-registry/crdb-experiment-{str(experiment_type)}"
        )

        # Command to check if the container is running or exited
        if target_state == "start":
            probe_cmd = f"docker ps --filter 'ancestor={image_name}' -q"
        elif target_state == "end":
            time.sleep(duration)
            probe_cmd = f"docker ps -a --filter 'ancestor={image_name}' --filter 'status=exited' -q"
        else:
            raise ValueError("target_state must be 'start' or 'end'")

        for i in range(retries):
            cmd = [
                "gcloud",
                "compute",
                "ssh",
                probe_server,
                f"--zone={zone}",
                "--command",
                probe_cmd,
                "--quiet",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.stdout.strip() != "":
                print(f"✅ Experiment reached state: {target_state}")
                return

            time.sleep(wait)

    def download(self, name: str, experiment_type: ExperimentType, run: int):
        zone = "us-central1-a"
        remote_files = ["client.txt", "hdrhistograms.json"]

        local_dir = (
            f"./runs/{name}/run-{run}/experiment-{str(experiment_type)}"
        )
        local_data_dir = f"{local_dir}/data"
        local_logs_dir = f"{local_dir}/logs"
        os.makedirs(local_data_dir, exist_ok=True)
        os.makedirs(local_logs_dir, exist_ok=True)

        def try_download(
            target_node: str,
            remote_path: str,
            local_path: str,
            max_attempts=20,
            delay=30,
        ):
            for attempt in range(1, max_attempts + 1):
                try:
                    subprocess.run(
                        [
                            "gcloud",
                            "compute",
                            "scp",
                            f"--zone={zone}",
                            f"{target_node}:{remote_path}",
                            local_path,
                        ],
                        check=True,
                        capture_output=True,
                    )
                    print(f"✅ Downloaded {remote_path}")
                    return
                except subprocess.CalledProcessError as e:
                    if b"No such file or directory" in e.stderr:
                        print(
                            f"⏳ {remote_path} not ready (attempt {attempt}/{max_attempts}), retrying..."
                        )
                        time.sleep(delay)
                    else:
                        print(f"❌ Unexpected error: {e.stderr.decode()}")
                        raise
            raise TimeoutError(
                f"File {remote_path} was not found after {max_attempts} attempts."
            )

        # Get data
        target_node = "client"
        remote_experiment_dir = remote_dir(target_node)
        for filename in remote_files:
            local_file = f"{local_data_dir}/{filename}"
            remote_file = f"{remote_experiment_dir}/{filename}"
            try_download(target_node, remote_file, str(local_file))

        # Get logs
        target_node = "server-3"
        remote_experiment_dir = remote_dir(target_node)
        subprocess.run(
            [
                "gcloud",
                "compute",
                "ssh",
                "server-3",
                "--command",
                f"sudo chown {USER}:{USER} {remote_experiment_dir}/cockroach.log",
            ],
            check=True,
        )

        try_download(
            target_node,
            f"{remote_experiment_dir}/cockroach.log",
            local_logs_dir,
        )
