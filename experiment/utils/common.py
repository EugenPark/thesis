from enum import Enum
from .experiment.config import PROJECT_ID


class ExperimentType(str, Enum):
    BASELINE = "baseline"
    THESIS = "thesis"

    def __str__(self):
        return self.value


class DeploymentType(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"

    def __str__(self):
        return self.value

    @classmethod
    def create_join_str(
        cls, deployment_type: "DeploymentType", cluster_size: int
    ) -> str:
        match deployment_type:
            case cls.LOCAL:
                return ",".join(
                    [f"server-{i}:26257" for i in range(1, cluster_size + 1)]
                )
            case cls.REMOTE:
                return ",".join(
                    [
                        f"server-{i}.us-central1-a.c.{PROJECT_ID}.internal:"
                        "26257"
                        for i in range(1, cluster_size + 1)
                    ]
                )


def get_local_output_dir(name: str, run: int, exp_type: ExperimentType):
    return f"./runs/{name}/run-{run}/experiment-{str(exp_type)}"
