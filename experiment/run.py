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
    name: str, sample_size: int, cluster_size: int, duration: str, workload: Workload
):
    workload_cmd = f"ycsb --duration={duration} --workload={str(workload)}"
    experiment.run(name, sample_size, cluster_size, workload_cmd)


@app.command()
def tpcc(
    name: str, sample_size: int, cluster_size: int, duration: str, warehouses: int
):
    workload_cmd = f"tpcc --duration={duration} --warehouses={warehouses}"
    experiment.run(name, sample_size, cluster_size, workload_cmd)


if __name__ == "__main__":
    app()
