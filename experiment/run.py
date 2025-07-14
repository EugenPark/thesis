import typer

# from utils import experiment
from enum import Enum
from utils.common import DeploymentType
from utils.experiment.runner import ExperimentRunner
from utils.experiment.models import ExperimentConfig


app = typer.Typer()


class Workload(Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"

    def __str__(self):
        return self.value


@app.command()
def ycsb(
    deployment_type: DeploymentType,
    name: str,
    sample_size: int,
    cluster_size: int,
    duration: str,
    ycsb_workload: Workload,
):
    workload = "ycsb"
    workload_args = f"--workload={str(ycsb_workload)}"

    # TODO: integrate deployment type into experiment config
    config = ExperimentConfig(
        name, sample_size, cluster_size, workload, workload_args, duration
    )
    runner = ExperimentRunner(config)
    runner.run(deployment_type)


@app.command()
def tpcc(
    deployment_type: DeploymentType,
    name: str,
    sample_size: int,
    cluster_size: int,
    duration: str,
    warehouses: int,
):
    workload = "tpcc"
    workload_args = f"--warehouses={warehouses}"

    config = ExperimentConfig(
        name, sample_size, cluster_size, workload, workload_args, duration
    )
    runner = ExperimentRunner(config)
    runner.run(deployment_type)


if __name__ == "__main__":
    app()
