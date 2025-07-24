import pandas as pd
import numpy as np
from scipy.stats import shapiro, ttest_ind, mannwhitneyu
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Tuple


def load_data(
    filepath: str = "./runs/restart-remote/results/recovery_times.csv",
) -> pd.DataFrame:
    """Load recovery times data from CSV."""
    return pd.read_csv(filepath)


def select_relevant_columns(
    df: pd.DataFrame, select_all: bool
) -> Tuple[pd.Series, pd.Series]:
    """
    Select relevant recovery columns from the DataFrame.

    Args:
        df: Input DataFrame
        select_all: If True, drop NaNs in both columns.
                    If False, fill NaNs in thesis with 150000.

    Returns:
        Tuple of (baseline, thesis) series.
    """
    baseline = df["recovery_per_replica_baseline"].dropna()
    if select_all:
        thesis = df["recovery_per_replica_thesis"].dropna()
    else:
        thesis = df["recovery_per_replica_thesis"].fillna(150000)
    return baseline, thesis


def cohens_d(x: np.ndarray, y: np.ndarray) -> float:
    """Compute Cohen's d effect size for independent samples."""
    nx, ny = len(x), len(y)
    pooled_std = np.sqrt(
        ((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1))
        / (nx + ny - 2)
    )
    return (np.mean(x) - np.mean(y)) / pooled_std


def one_sided_p_value(t_stat: float, p_two_sided: float) -> float:
    """
    Convert two-sided p-value to one-sided based on t-statistic sign.

    Hypothesis: x > y (thesis > baseline).
    """
    if t_stat > 0:
        return p_two_sided / 2
    else:
        return 1 - (p_two_sided / 2)


def perform_tests(baseline: pd.Series, thesis: pd.Series) -> None:
    """
    Perform normality tests and appropriate hypothesis testing.

    Uses:
    - Shapiro-Wilk for normality
    - Welch's t-test if normal (one-sided)
    - Mann-Whitney U test if not normal (one-sided)
    """
    shapiro_baseline = shapiro(baseline)
    shapiro_thesis = shapiro(thesis)

    print("Shapiro-Wilk Normality Test Results:")
    print(f"  Baseline p-value: {shapiro_baseline.pvalue:.4f}")
    print(f"  Thesis   p-value: {shapiro_thesis.pvalue:.4f}")

    if shapiro_baseline.pvalue >= 0.05 and shapiro_thesis.pvalue >= 0.05:
        print(
            "\n✅ Both distributions are normal. Performing one-sided Welch's t-test (thesis > baseline)..."
        )
        t_stat, p_two_sided = ttest_ind(thesis, baseline, equal_var=False)
        p_val = one_sided_p_value(t_stat, p_two_sided)
        d = cohens_d(thesis.values, baseline.values)

        print(f"  T-statistic: {t_stat:.4f}")
        print(f"  One-sided P-value (thesis > baseline): {p_val:.4f}")
        print(f"  Cohen's d: {d:.4f}")

        if p_val < 0.05:
            print(
                "  ✅ Statistically significant: thesis recovery time is higher."
            )
        else:
            print("  ❌ No statistically significant difference.")
    else:
        print(
            "\n⚠️ Data not normally distributed. Performing one-sided Mann–Whitney U test (thesis > baseline)..."
        )
        # Two-sided test (for reporting)
        u_stat, p_two_sided = mannwhitneyu(
            thesis, baseline, alternative="two-sided"
        )
        # One-sided test
        u_stat_one_sided, p_one_sided = mannwhitneyu(
            thesis, baseline, alternative="greater"
        )

        print(f"  U-statistic (two-sided): {u_stat:.4f}")
        print(
            f"  U-statistic (one-sided) (thesis > baseline): {u_stat_one_sided:.4f}"
        )
        print(f"  Two-sided P-value: {p_two_sided:.4f}")
        print(f"  One-sided P-value (thesis > baseline): {p_one_sided:.4f}")

        if p_one_sided < 0.05:
            print(
                "  ✅ Statistically significant: thesis recovery time is higher."
            )
        else:
            print("  ❌ No statistically significant difference.")


def plot_recovery_boxplots(df: pd.DataFrame) -> None:
    """
    Print descriptive stats and plot boxplots comparing baseline and thesis recovery times.

    Args:
        df: DataFrame containing data
    """
    data = df.copy()

    # Print descriptive statistics before melting
    for col, label in [
        ("recovery_per_replica_baseline", "Baseline"),
        ("recovery_per_replica_thesis", "Thesis"),
    ]:
        print(f"\nDescriptive statistics for {label}:")
        desc = data[col].describe()
        print(desc.to_string())

    df_long = pd.melt(
        data,
        value_vars=[
            "recovery_per_replica_baseline",
            "recovery_per_replica_thesis",
        ],
        var_name="Method",
        value_name="Recovery_per_Replica",
    )

    df_long["Method"] = df_long["Method"].map(
        {
            "recovery_per_replica_baseline": "CRDB",
            "recovery_per_replica_thesis": "DO-CRDB",
        }
    )

    plt.figure(figsize=(8, 6))
    sns.boxplot(x="Method", y="Recovery_per_Replica", data=df_long)
    plt.title("Comparison of Recovery Time per Replica")
    plt.ylabel("Recovery Time per Replica (ms)")
    plt.xlabel("")
    plt.savefig(
        "./runs/restart-remote/results/recovery_comparison.pdf",
        dpi=500,
        format="pdf",
        bbox_inches="tight",
    )
    plt.show()


def compare_recovery() -> None:
    """Load data, perform tests and plot results for both scenarios."""
    df = load_data()

    baseline, thesis = select_relevant_columns(df, select_all=True)
    perform_tests(baseline, thesis)
    plot_recovery_boxplots(df)


if __name__ == "__main__":
    compare_recovery()
