import subprocess
import json
from .config import TF_DIR, PROJECT_ID
from ..common import DeploymentType


class TerraformManager:
    def _build_vars(
        self, cluster_size, workload, workload_args, duration, seed
    ) -> dict:
        remote_output_dir = "/var/experiment/data"
        remote_logs_dir = "/var/experiment/logs"

        client_cmd = (
            f"./cockroach workload run {workload} {workload_args} "
            f"--duration={duration} --seed={seed} "
            f"--histograms={remote_output_dir}/hdrhistograms.json "
            "--display-format=incremental-json "
            "postgresql://root@server-1:26257?sslmode=disable > "
            f"{remote_output_dir}/client.txt"
        )

        server_cmds = []
        join_str = DeploymentType.create_join_str(
            cluster_size, DeploymentType.REMOTE
        )

        for i in range(1, cluster_size + 1):
            server_cmds.append(
                f"./cockroach start --insecure --join={join_str} "
                f"--store=/app/store --log-dir={remote_logs_dir} "
                "--listen-addr=0.0.0.0:26257 "
                f"--advertise-addr=server-{i}:26257 --http-addr=0.0.0.0:8080"
            )

        return {
            "client_cmd": json.dumps(client_cmd),
            "server_cmds": json.dumps(server_cmds),
            "project_id": PROJECT_ID,
            "cluster_size": cluster_size,
        }

    def apply(self, cluster_size, workload, workload_args, duration, seed):
        tf_vars = self._build_vars(
            cluster_size, workload, workload_args, duration, seed
        )
        cmd = ["terraform", "apply", "-auto-approve"] + [
            f"-var={k}={v}" for k, v in tf_vars.items()
        ]
        subprocess.run(cmd, cwd=TF_DIR, check=True)

    def destroy(self, cluster_size, workload, workload_args, duration, seed):
        tf_vars = self._build_vars(
            cluster_size, workload, workload_args, duration, seed
        )
        cmd = ["terraform", "destroy", "-auto-approve"] + [
            f"-var={k}={v}" for k, v in tf_vars.items()
        ]
        subprocess.run(cmd, cwd=TF_DIR, check=True)
