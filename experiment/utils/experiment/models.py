from enum import Enum
from dataclasses import dataclass


class ExperimentType(str, Enum):
    BASELINE = "baseline"
    THESIS = "thesis"

    def __str__(self):
        return self.value


class DeploymentType(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"


# TODO: add some functions that return a specific parameter range that is
# needed for both local and remote calls
@dataclass
class ExperimentConfig:
    name: str
    sample_size: int
    cluster_size: int
    workload: str
    workload_args: str
    duration: int
