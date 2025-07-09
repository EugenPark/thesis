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


@app.command()
def ycsb(cluster_size: int, duration: str, workload: Workload):
    workload_cmd = f"ycsb --duration={duration} --workload={workload}"
    experiment.run_experiment_pipeline(cluster_size, workload_cmd)


@app.command()
def tpcc(cluster_size: int, duration: str, warehouses: int):
    workload_cmd = f"tpcc --duration={duration} --warehouses={warehouses}"
    experiment.run_experiment_pipeline(cluster_size, workload_cmd)


if __name__ == "__main__":
    app()
