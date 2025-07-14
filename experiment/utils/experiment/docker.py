import subprocess
from .models import ExperimentType
from .config import PROJECT_ID, NETWORK


class DockerManager:
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
        return image_tag

    def push_image(self, image_tag: str):
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

    def stop_and_remove(self, name: str):
        subprocess.run(["docker", "stop", name], check=False)
        subprocess.run(["docker", "rm", name], check=False)
