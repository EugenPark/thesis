import seaborn as sns
import matplotlib.pyplot as plt
import json
import pandas as pd


def _load_data(filepath: str, limit: int) -> pd.DataFrame:
    """Load a newline-delimited JSON file and return a DataFrame."""
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
    df["time"] = pd.to_datetime(df["time"])
    start_time = df["time"].min()

    df["time"] = (df["time"] - start_time).dt.total_seconds()

    df = df[df["time"] < limit]

    return df


def compare_ycsb_warmup():
    df_without_ramp = _load_data(
        "./runs/warmup/run-1/experiment-baseline/data/client.txt", 800
    )
    df_with_ramp = _load_data(
        "./runs/warmup-with-ramp-2/run-1/experiment-baseline/data/client.txt",
        800,
    )

    # Set style and create subplots
    sns.set(style="whitegrid")
    sns.set_context("paper", font_scale=1.9)  # Larger font
    fig, axes = plt.subplots(1, 2, figsize=(16, 9), sharey=True)

    # === Plot 1: Without Ramp ===
    sns.lineplot(
        data=df_without_ramp,
        x="time",
        y="avgt",
        label="Avg Throughput",
        linestyle="-",
        linewidth=3,
        ax=axes[0],
    )
    sns.lineplot(
        data=df_without_ramp,
        x="time",
        y="avgl",
        color="orange",
        label="Cumulative Throughput",
        linestyle="--",
        linewidth=3,
        ax=axes[0],
    )
    axes[0].axvline(
        x=300,
        color="red",
        linestyle=":",
        linewidth=3,
        label="Warmed Up",
    )
    axes[0].set_title("Without Ramp-Up")
    axes[0].set_xlabel("Time (s)")
    axes[0].set_ylabel("Throughput (ops/sec)")
    axes[0].legend()
    axes[0].grid(True)

    # === Plot 2: With Ramp ===
    sns.lineplot(
        data=df_with_ramp,
        x="time",
        y="avgt",
        label="Avg Throughput",
        linestyle="-",
        linewidth=3,
        ax=axes[1],
    )
    sns.lineplot(
        data=df_with_ramp,
        x="time",
        y="avgl",
        color="orange",
        label="Cumulative Throughput",
        linestyle="--",
        linewidth=3,
        ax=axes[1],
    )
    axes[1].axvline(
        x=400,
        color="green",
        linestyle=":",
        linewidth=3,
        label="Ramp Finished",
    )
    axes[1].set_title("With Ramp-Up")
    axes[1].set_xlabel("Time (sec)")
    axes[1].legend()
    axes[1].grid(True)

    # Final layout adjustments
    plt.suptitle(
        "Throughput Comparison: With and Without Ramp-Up", fontsize=20
    )
    plt.tight_layout(rect=[0, 0, 1, 0.95])  # leave room for suptitle
    plt.savefig(
        "./runs/warmup/results/warmup.png",
        dpi=500,
        bbox_inches="tight",
    )


def tpcc():
    df_with_ramp = _load_data(
        "./runs/tpcc-local-with-ramp/run-1/experiment-baseline/data/client.txt",
        400,
    )
    df_without_ramp = _load_data(
        "./runs/tpcc-local-without-ramp/run-1/experiment-baseline/data/client.txt",
        400,
    )

    # Filter for only relevant operation types
    df_with_ramp = df_with_ramp[
        df_with_ramp["type"].isin(["newOrder", "orderStatus"])
    ]
    df_without_ramp = df_without_ramp[
        df_without_ramp["type"].isin(["newOrder", "orderStatus"])
    ]

    # Set style and create subplots
    sns.set(style="whitegrid", context="paper")
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)

    # === Plot: With Ramp ===
    for op_type in df_with_ramp["type"].unique():
        subset = df_with_ramp[df_with_ramp["type"] == op_type]
        sns.lineplot(
            data=subset,
            x="time",
            y="avgt",
            ax=axes[0],
            label=f"{op_type} - At Time",
            linewidth=2,
        )
        sns.lineplot(
            data=subset,
            x="time",
            y="avgl",
            ax=axes[0],
            label=f"{op_type} - Cumulative",
            linestyle="--",
            linewidth=2,
        )

    axes[0].axvline(
        x=180, color="red", linestyle=":", linewidth=2, label="Warmup End"
    )
    axes[0].set_title("With Ramp-Up")
    axes[0].set_xlabel("Time (sec)")
    axes[0].set_ylabel("Ops/sec")
    axes[0].legend()
    axes[0].grid(True)

    # === Plot: Without Ramp ===
    for op_type in df_without_ramp["type"].unique():
        subset = df_without_ramp[df_without_ramp["type"] == op_type]
        sns.lineplot(
            data=subset,
            x="time",
            y="avgt",
            ax=axes[1],
            label=f"{op_type} - At Time",
            linewidth=2,
        )
        sns.lineplot(
            data=subset,
            x="time",
            y="avgl",
            ax=axes[1],
            label=f"{op_type} - Cumulative",
            linestyle="--",
            linewidth=2,
        )

    axes[1].set_title("Without Ramp-Up")
    axes[1].set_xlabel("Time (sec)")
    axes[1].legend()
    axes[1].grid(True)

    # Final layout
    plt.suptitle("TPC-C Throughput: With vs. Without Ramp-Up", fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()
