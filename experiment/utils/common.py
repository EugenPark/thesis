from enum import Enum
from .experiment.config import PROJECT_ID
from multiprocessing import Process

SQL_PORT = 26257
DASHBOARD_PORT = 8080
EXPERIMENT_DIR = "/var/experiment"


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


def get_local_output_dir(name: str, run: int, exp_type: ExperimentType):
    return f"./runs/{name}/run-{run}/experiment-{str(exp_type)}"


def create_remote_host(name: str):
    return f"{name}.us-central1-a.c.{PROJECT_ID}.internal"


def create_join_str(
    deployment_type: DeploymentType,
    cluster_size: int,
    run=None,
    experiment_type=None,
) -> str:
    match deployment_type:
        case DeploymentType.LOCAL:
            return ",".join(
                [f"server-{i}:{SQL_PORT}" for i in range(1, cluster_size + 1)]
            )
        case DeploymentType.REMOTE:
            return ",".join(
                [
                    f"{create_remote_host(f'experiment-{run}-{str(experiment_type)}-server-{i}')}:{SQL_PORT}"  # noqa: E501
                    for i in range(1, cluster_size + 1)
                ]
            )


def runInParallel(*fns):
    proc = []
    for fn in fns:
        p = Process(target=fn)
        p.start()
        proc.append(p)
    for p in proc:
        p.join()
