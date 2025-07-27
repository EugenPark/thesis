import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from .common import ExperimentType, get_local_output_dir
from scipy.stats import shapiro, ttest_ind, mannwhitneyu
import numpy as np

DIRECTIONS = {
    "avgl": "greater",
    "p50l": "less",
    "p95l": "less",
    "p99l": "less",
    "maxl": "less",
}

METRIC_MAPPING = {
    "avgl": "ops/s",
    "p50l": "ms",
    "p95l": "ms",
    "p99l": "ms",
    "maxl": "ms",
    "Time": "sec",
}

LABEL_MAPPING = {
    "avgl": "Average Throughput",
    "p50l": "Median Latency",
    "p95l": "95th Percentile Latency",
    "p99l": "99th Percentile Latency",
    "maxl": "Maximum Latency",
}

EXPERIMENT_TYPE_MAP = {"baseline": "CRDB", "thesis": "DO-CRDB"}


# TODO: make this a common function reusable in plotting warmup
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
    df["type"] = df["type"].str.capitalize()
    df["experiment_type"] = EXPERIMENT_TYPE_MAP[str(exp_type)]

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


def _format_ylabel(metric_col: str) -> str:
    if metric_col.startswith("p") and metric_col.endswith("l"):
        percentile = metric_col[1:-1]
        return f"{percentile}th Percentile Latency (ms)"
    return metric_col  # fallback


def _draw_boxplot(output_dir: str, df: pd.DataFrame, metric_col: str):
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
    plt.title(f"{LABEL_MAPPING[metric_col]} by Operation and Experiment Type")
    plt.ylabel(f"{METRIC_MAPPING[metric_col]}")
    plt.xlabel("Operation Type")
    plt.legend(title="Experiment Type")
    plt.tight_layout()
    plt.savefig(f"{output_dir}/{metric_col}.png", dpi=300)
    plt.savefig(
        f"{output_dir}/{metric_col}.pdf", format="pdf", bbox_inches="tight"
    )


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


def _cohen_d(x, y):
    nx, ny = len(x), len(y)
    pooled_std = np.sqrt(
        ((nx - 1) * np.std(x, ddof=1) ** 2 + (ny - 1) * np.std(y, ddof=1) ** 2)
        / (nx + ny - 2)
    )
    return (np.mean(y) - np.mean(x)) / pooled_std


def _compare_groups(x, y, alternative="greater"):
    # Normality test
    _, p_x = shapiro(x)
    _, p_y = shapiro(y)

    use_t = p_x > 0.05 and p_y > 0.05  # assume normal if p > 0.05

    if use_t:
        stat, p_val = ttest_ind(y, x, alternative=alternative)
        test_used = "t-test"
    else:
        stat, p_val = mannwhitneyu(y, x, alternative=alternative)
        test_used = "Mann-Whitney U"

    d = _cohen_d(x, y)
    return test_used, p_val, d


def _analyze(output_dir, df, metric):
    results = []

    for op_type in df["type"].unique():
        df_op = df[df["type"] == op_type]

        baseline = df_op[df_op["experiment_type"] == "CRDB"][metric].dropna()
        thesis = df_op[df_op["experiment_type"] == "DO-CRDB"][metric].dropna()

        if len(baseline) < 2 or len(thesis) < 2:
            continue

        direction = DIRECTIONS.get(metric, "two-sided")
        test, p_val, d = _compare_groups(baseline, thesis, direction)

        results.append(
            {
                "operation": op_type,
                "metric": metric,
                "test": test,
                "p_value": round(p_val, 5),
                "cohens_d": round(d, 3),
                "baseline_mean": round(baseline.mean(), 3),
                "thesis_mean": round(thesis.mean(), 3),
                "n_baseline": len(baseline),
                "n_thesis": len(thesis),
            }
        )

    output_file = f"{output_dir}/test-{metric}.csv"
    pd.DataFrame(results).to_csv(output_file, index=False)
    print(f"Results written to: {output_file}")


def run(name: str, sample_size: int) -> pd.DataFrame:
    """Handle data for both baseline and thesis experiment types."""

    dfs = []
    for exp_type in (ExperimentType.BASELINE, ExperimentType.THESIS):
        df = _get_data(name, sample_size, exp_type)
        dfs.append(df)

    result = _concat_dfs(dfs)

    output_dir = f"./runs/{name}/results"
    os.makedirs(output_dir, exist_ok=True)
    _iterate_metrics(output_dir, result, _analyze)
    _iterate_metrics(output_dir, result, _compute_boxplot)
    _iterate_metrics(output_dir, result, _draw_boxplot)

    return result
