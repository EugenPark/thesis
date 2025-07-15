import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from .common import ExperimentType, get_local_output_dir


def _load_data(name: str, run: int, exp_type: ExperimentType) -> pd.DataFrame:
    """Load a newline-delimited JSON file and return a DataFrame."""

    local_output_dir = get_local_output_dir(name, run, exp_type)
    filepath = f"{local_output_dir}/data/client.txt"
    with open(filepath, "r") as f:
        raw_lines = f.readlines()

    # Convert file to json
    lines = [
        line.strip()
        for line in raw_lines
        if line.strip().startswith("{") and line.strip().endswith("}")
    ]
    json_array = "[" + ",".join(lines) + "]"
    data = json.loads(json_array)

    df = pd.DataFrame(data)
    df["experiment_type"] = str(exp_type)

    # NOTE: We only return the last rows of each operation as the data contains
    # cumulative results
    return df.groupby("type", group_keys=False).tail(1)


def _concat_dfs(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    """Merge the dataframes of all runs together"""
    return pd.concat(dfs, axis=0, ignore_index=True)


def _get_data(
    name: str, sample_size: int, exp_type: ExperimentType
) -> pd.DataFrame:
    """Collect DataFrames for each run of a given experiment type."""
    all_runs = []

    for i in range(1, sample_size + 1):
        df = _load_data(name, i, exp_type)
        all_runs.append(df)

    merged_df = _concat_dfs(all_runs)

    return merged_df


def _draw_boxplot(
    output_dir: str, df: pd.DataFrame, metric_col: str, title=None
):
    """
    Create a boxplot for the specified latency metric across experiment types
    and operations.

    Parameters:
    - df: pandas DataFrame containing at least ['type', 'experiment_type',
                                                metric_col]
    - metric_col: string, the column to plot (e.g., 'p50l', 'p95l', 'p99l')
    - title: optional string to set as the plot title
    """
    # Convert Enums or other objects to strings (if necessary)
    df = df.copy()

    # Set plot style
    sns.set(style="whitegrid")

    # Create plot
    plt.figure(figsize=(10, 6))
    sns.boxplot(
        data=df, x="type", y=metric_col, hue="experiment_type", palette="Set2"
    )

    # Titles and labels
    plt.title(title or f"{metric_col} by Operation and Experiment Type")
    plt.ylabel(metric_col)
    plt.xlabel("Operation Type")
    plt.legend(title="Experiment Type")
    plt.tight_layout()
    plt.savefig(f"{output_dir}/{metric_col}.png", dpi=300)


def _compute_boxplot(output_dir: str, df: pd.DataFrame, metric_col: str):
    """
    Returns summary statistics (min, Q1, median, Q3, max) grouped by operation
    and experiment.
    """
    df = df.copy()
    df["experiment_type"] = df["experiment_type"].astype(str)
    df["type"] = df["type"].astype(str)

    summary = df.groupby(["experiment_type", "type"])[metric_col].describe(
        percentiles=[0.25, 0.5, 0.75]
    )[["min", "25%", "50%", "75%", "max"]]

    # Optional: rename columns for clarity
    summary = summary.rename(
        columns={"25%": "q1", "50%": "median", "75%": "q3"}
    )

    output_path = f"{output_dir}/{metric_col}.csv"
    # Write summary to file
    with open(output_path, "w") as f:
        f.write(summary.to_csv())


def _iterate_metrics(output_dir: str, df: pd.DataFrame, fn):
    for metric in ["avgl", "p50l", "p95l", "p99l", "maxl"]:
        fn(output_dir, df, metric)


def run(name: str, sample_size: int) -> pd.DataFrame:
    """Handle data for both baseline and thesis experiment types."""

    dfs = []
    for exp_type in (ExperimentType.BASELINE, ExperimentType.THESIS):
        df = _get_data(name, sample_size, exp_type)
        dfs.append(df)

    result = _concat_dfs(dfs)

    output_dir = f"./runs/{name}/results"
    os.makedirs(output_dir, exist_ok=True)
    _iterate_metrics(output_dir, result, _compute_boxplot)
    _iterate_metrics(output_dir, result, _draw_boxplot)

    return result
