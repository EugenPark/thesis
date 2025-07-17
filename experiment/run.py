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
    ramp = "400s"

    config = ExperimentConfig(
        name,
        deployment_type,
        sample_size,
        cluster_size,
        workload,
        workload_args,
        duration,
        ramp,
    )
    runner = ExperimentRunner(config)
    runner.run()


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
    ramp = "180s"

    config = ExperimentConfig(
        name,
        deployment_type,
        sample_size,
        cluster_size,
        workload,
        workload_args,
        duration,
        ramp,
    )
    runner = ExperimentRunner(config)
    runner.run()


if __name__ == "__main__":
    app()
