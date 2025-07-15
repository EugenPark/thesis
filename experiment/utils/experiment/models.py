from dataclasses import dataclass
from ..common import DeploymentType


@dataclass(frozen=True)
class WorkloadConfig:
    workload: str
    workload_args: str
    duration: int


@dataclass
class ExperimentConfig:
    name: str
    deployment_type: DeploymentType
    sample_size: int
    cluster_size: int
    workload: str
    workload_args: str
    duration: int

    def workload_config(self) -> WorkloadConfig:
        return WorkloadConfig(self.workload, self.workload_args, self.duration)
