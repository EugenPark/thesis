import typer
from utils import experiment
from enum import Enum


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
    name: str,
    sample_size: int,
    cluster_size: int,
    duration: str,
    ycsb_workload: Workload,
):
    workload = "ycsb"
    workload_args = f"--workload={str(ycsb_workload)}"
    experiment.run(
        name, sample_size, cluster_size, workload, duration, workload_args
    )


@app.command()
def tpcc(
    name: str,
    sample_size: int,
    cluster_size: int,
    duration: str,
    warehouses: int,
):
    workload = "tpcc"
    workload_args = f"--warehouses={warehouses}"
    experiment.run(
        name, sample_size, cluster_size, workload, duration, workload_args
    )


if __name__ == "__main__":
    app()
