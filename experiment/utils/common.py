from enum import Enum


class ExperimentType(Enum):
    BASELINE = "baseline"
    THESIS = "thesis"

    def __str__(self):
        return self.value
