import os
import seaborn as sns
import matplotlib.pyplot as plt
import json
import pandas as pd


def _load_data(filepath: str, limit: int) -> pd.DataFrame:
    with open(filepath, "r") as f:
        raw_lines = f.readlines()

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
    return df[df["time"] < limit]


def _plot_throughput_comparison(
    df1,
    df2,
    ax1_title,
    ax2_title,
    vline1,
    vline2,
    suptitle,
    save_path=None,
    group_by_type=False,
):
    sns.set(style="whitegrid", context="paper")
    fig, axes = plt.subplots(1, 2, figsize=(16, 9), sharey=True)

    def _plot(ax, df, title, vline):
        if group_by_type and "type" in df.columns:
            for op_type in df["type"].unique():
                subset = df[df["type"] == op_type]
                sns.lineplot(
                    data=subset,
                    x="time",
                    y="avgt",
                    ax=ax,
                    label=f"{op_type} - At Time",
                    linewidth=2,
                )
                sns.lineplot(
                    data=subset,
                    x="time",
                    y="avgl",
                    ax=ax,
                    label=f"{op_type} - Cumulative",
                    linestyle="--",
                    linewidth=2,
                )
        else:
            sns.lineplot(
                data=df,
                x="time",
                y="avgt",
                label="Avg Throughput",
                ax=ax,
                linewidth=3,
            )
            sns.lineplot(
                data=df,
                x="time",
                y="avgl",
                label="Cumulative Throughput",
                color="orange",
                linestyle="--",
                linewidth=3,
                ax=ax,
            )

        if vline is not None:
            ax.axvline(
                x=vline,
                color="red",
                linestyle=":",
                linewidth=2,
                label="Ramp/Warmup End",
            )
        ax.set_title(title)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Throughput (ops/s)")
        ax.grid(True)
        ax.legend()

    _plot(axes[0], df1, ax1_title, vline1)
    _plot(axes[1], df2, ax2_title, vline2)

    plt.suptitle(suptitle, fontsize=20)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    if save_path:
        os.makedirs(save_path, exist_ok=True)
        plt.savefig(f"{save_path}/warmup.png", dpi=500, bbox_inches="tight")
    else:
        plt.show()


def compare_ycsb_warmup():
    df_no_ramp = _load_data(
        "./runs/ycsb-local-warmup-without-ramp/run-1/experiment-baseline/data/client.txt",
        limit=800,
    )
    df_with_ramp = _load_data(
        "./runs/ycsb-local-warmup-with-ramp/run-1/experiment-baseline/data/client.txt",
        limit=800,
    )

    _plot_throughput_comparison(
        df1=df_no_ramp,
        df2=df_with_ramp,
        ax1_title="Without Ramp-Up",
        ax2_title="With Ramp-Up",
        vline1=None,
        vline2=400,
        suptitle="YCSB Throughput Comparison: With and Without Ramp-Up",
        save_path="./runs/ycsb-local-warmup-with-ramp/results",
    )


def compare_tpcc_warmup():
    df_no_ramp = _load_data(
        "./runs/tpcc-local-warmup-without-ramp/run-1/experiment-baseline/data/client.txt",
        limit=400,
    )

    df_ramp = _load_data(
        "./runs/tpcc-local-warmup-with-ramp/run-1/experiment-baseline/data/client.txt",
        limit=400,
    )

    # Keep only relevant types
    op_filter = ["newOrder", "orderStatus"]
    df_ramp = df_ramp[df_ramp["type"].isin(op_filter)]
    df_no_ramp = df_no_ramp[df_no_ramp["type"].isin(op_filter)]

    _plot_throughput_comparison(
        df1=df_no_ramp,
        df2=df_ramp,
        ax1_title="Without Ramp-Up",
        ax2_title="With Ramp-Up",
        vline1=None,
        vline2=180,
        suptitle="TPC-C Throughput Comparison: With and Without Ramp-Up",
        save_path="./runs/tpcc-local-warmup-with-ramp/results",
        group_by_type=True,
    )
