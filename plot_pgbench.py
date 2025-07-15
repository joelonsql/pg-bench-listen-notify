#!/usr/bin/env python3
"""
Plot pgbench results comparing different versions.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Constants
COMBINED_CSV_FILE = 'pgbench_results_combined.csv'
PERFORMANCE_MARKDOWN_FILE = 'performance_overview.md'
FIXED_CONNECTIONS_COUNT = 1000
DPI = 300

# Expected CSV columns
EXPECTED_COLUMNS = [
    'test_type',
    'clients', 
    'jobs',
    'version',
    'run_number',
    'scaling_factor',
    'num_clients',
    'num_threads',
    'duration',
    'transactions_processed',
    'failed_transactions',
    'latency_avg',
    'initial_connection_time',
    'tps',
    'transaction_type'
]

# Column names used in analysis
COL_TEST_TYPE = 'test_type'
COL_CLIENTS = 'clients'
COL_JOBS = 'jobs'
COL_VERSION = 'version'
COL_TPS = 'tps'

# Plot configuration
PLOT_CONFIGS = {
    "connections_equal_jobs": {
        "title_suffix": "Connections = Jobs",
        "filename": "performance_overview_connections_equal_jobs.png",
        "x_label": "Number of Clients (= Jobs)"
    },
    "fixed_connections": {
        "title_suffix": f"Connections = {FIXED_CONNECTIONS_COUNT}, Jobs Varying",
        "filename": "performance_overview_fixed_connections.png",
        "x_label": f"Number of Jobs (Connections = {FIXED_CONNECTIONS_COUNT})"
    }
}

# Test layout for grid plotting
TEST_LAYOUT = [
    ['listen_unique', 'listen_unlisten_unique', 'listen_notify_unique'],
    ['listen_common', 'listen_unlisten_common', 'listen_notify_common']
]

# Plot styling
FIGURE_SIZE = (20, 12)
GRID_SHAPE = (2, 3)
SCATTER_SIZE = 40
AVERAGE_MARKER_SIZE = 60
LINE_WIDTH = 2
ANNOTATION_FONT_SIZE = 8
TITLE_FONT_SIZE = 16
X_OFFSET_MULTIPLIER = 0.02
Y_AXIS_PADDING = 0.8  # For log scale min
Y_AXIS_PADDING_MAX = 1.2  # For log scale max

# Set style for better plots
plt.style.use('default')
sns.set_palette("husl")

def validate_dataframe(df: pd.DataFrame) -> None:
    """Validate that the dataframe has all expected columns."""
    missing_columns = set(EXPECTED_COLUMNS) - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing expected columns: {missing_columns}")

    # Validate data types
    numeric_columns = [COL_CLIENTS, COL_JOBS, COL_TPS]
    for col in numeric_columns:
        if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(f"Column '{col}' should be numeric but is {df[col].dtype}")

def load_combined_data() -> Optional[pd.DataFrame]:
    """Load the combined CSV data."""
    if not os.path.exists(COMBINED_CSV_FILE):
        print(f"Combined CSV file {COMBINED_CSV_FILE} not found!")
        print("Please run parse_pgbench_csv.py first to generate the data.")
        return None

    df = pd.read_csv(COMBINED_CSV_FILE)

    try:
        validate_dataframe(df)
    except ValueError as e:
        print(f"Error validating CSV data: {e}")
        return None

    return df

def filter_data_by_plot_type(df: pd.DataFrame, plot_type: str) -> pd.DataFrame:
    """Filter dataframe based on plot type."""
    if plot_type == "connections_equal_jobs":
        return df[df[COL_CLIENTS] == df[COL_JOBS]].copy()
    else:  # fixed_connections
        return df[df[COL_CLIENTS] == FIXED_CONNECTIONS_COUNT].copy()

def get_x_column_for_plot_type(df: pd.DataFrame, plot_type: str) -> str:
    """Get appropriate x-axis column based on plot type."""
    if plot_type == "connections_equal_jobs":
        return COL_CLIENTS
    else:
        return COL_JOBS

def calculate_global_tps_bounds(df: pd.DataFrame, test_layout: List[List[str]]) -> Tuple[float, float]:
    """Calculate global min and max TPS values across all test types."""
    max_tps = 0
    min_tps = float('inf')

    for row in test_layout:
        for test_type in row:
            test_data = df[df[COL_TEST_TYPE] == test_type]
            if not test_data.empty:
                tps_values = test_data[COL_TPS].values
                if len(tps_values) > 0:
                    max_tps = max(max_tps, tps_values.max())
                    min_tps = min(min_tps, tps_values.min())

    return min_tps * Y_AXIS_PADDING, max_tps * Y_AXIS_PADDING_MAX

def plot_version_data(ax, version_data, test_data, version, color, x_col, version_index, num_versions):
    """Plot data for a single version on the given axis."""
    version_data = version_data.sort_values(x_col)
    individual_data = test_data[test_data[COL_VERSION] == version].copy()
    individual_data = individual_data.sort_values(x_col)

    x_positions_avg = []
    y_positions_avg = []

    for _, avg_row in version_data.iterrows():
        x_val = avg_row[x_col]
        avg_tps = avg_row[COL_TPS]

        # Calculate offset for visibility
        x_offset = x_val * X_OFFSET_MULTIPLIER * (version_index - num_versions/2)
        x_positions_avg.append(x_val + x_offset)
        y_positions_avg.append(avg_tps)

        # Get individual points
        individual_points = individual_data[individual_data[x_col] == x_val][COL_TPS].tolist()

        if individual_points:
            # Plot individual data points
            x_positions = [x_val + x_offset] * len(individual_points)
            ax.scatter(x_positions, individual_points, 
                      color=color, s=SCATTER_SIZE, alpha=0.8, zorder=2, 
                      edgecolors='black', linewidth=0.5)

            # Draw range line if multiple points
            if len(individual_points) > 1:
                local_min = min(individual_points)
                local_max = max(individual_points)
                ax.plot([x_val + x_offset, x_val + x_offset], [local_min, local_max], 
                       color=color, linewidth=1, alpha=0.7, zorder=1)

            # Plot average marker
            ax.scatter([x_val + x_offset], [avg_tps], 
                      color=color, s=AVERAGE_MARKER_SIZE, marker='o', 
                      edgecolor='white', linewidth=1, zorder=3)

            # Add annotation
            ax.annotate(f'{int(avg_tps)}', 
                       xy=(x_val + x_offset, avg_tps),
                       xytext=(0, 5), textcoords='offset points',
                       ha='center', va='bottom',
                       fontsize=ANNOTATION_FONT_SIZE, color=color,
                       bbox=dict(boxstyle='round,pad=0.3', 
                               facecolor='white', 
                               edgecolor=color, 
                               alpha=0.8))

    # Connect averages with lines
    if len(x_positions_avg) > 1:
        ax.plot(x_positions_avg, y_positions_avg, 
               color=color, linewidth=LINE_WIDTH, alpha=0.8, zorder=2, label=version)
    else:
        # For single point, just add label
        ax.scatter([], [], color=color, s=AVERAGE_MARKER_SIZE, label=version)

def plot_performance_overview(df: pd.DataFrame, plot_type: str = "connections_equal_jobs"):
    """Create an overview plot showing all test types."""
    config = PLOT_CONFIGS[plot_type]

    # Filter data
    filtered_df = filter_data_by_plot_type(df, plot_type)
    if filtered_df.empty:
        print(f"No data found for plot type: {plot_type}")
        return

    # Calculate global bounds
    y_min, y_max = calculate_global_tps_bounds(filtered_df, TEST_LAYOUT)

    # Create figure
    fig, axes = plt.subplots(*GRID_SHAPE, figsize=FIGURE_SIZE)
    fig.suptitle(f'PostgreSQL Performance Overview - {config["title_suffix"]}', 
                 fontsize=TITLE_FONT_SIZE, fontweight='bold')

    # Get x-axis column
    x_col = get_x_column_for_plot_type(filtered_df, plot_type)

    # Plot each test type
    for row_idx, row in enumerate(TEST_LAYOUT):
        for col_idx, test_type in enumerate(row):
            ax = axes[row_idx, col_idx]

            # Filter data for this test type
            test_data = filtered_df[filtered_df[COL_TEST_TYPE] == test_type].copy()

            if test_data.empty:
                ax.set_visible(False)
                continue

            # Group by version and x-axis variable
            grouped = test_data.groupby([COL_VERSION, x_col])[COL_TPS].mean().reset_index()
            versions = grouped[COL_VERSION].unique()
            colors = plt.cm.Set1(np.linspace(0, 1, len(versions)))

            # Plot each version
            for j, version in enumerate(versions):
                version_data = grouped[grouped[COL_VERSION] == version]
                plot_version_data(ax, version_data, test_data, version, colors[j], 
                                x_col, j, len(versions))

            # Configure axis
            ax.set_xlabel(config["x_label"])
            ax.set_ylabel('TPS')
            ax.set_title(f'{test_type.replace("_", " ").title()}')
            ax.legend()
            ax.grid(True, alpha=0.3)

            # Set scales
            ax.set_xscale('log')
            ax.set_yscale('log')
            ax.set_ylim(y_min, y_max)

            # Set x-axis ticks
            x_values = sorted(grouped[x_col].unique())
            ax.set_xticks(x_values)
            ax.set_xticklabels([str(c) for c in x_values])

    plt.tight_layout()
    plt.savefig(config["filename"], dpi=DPI, bbox_inches='tight')
    print(f"Saved plot: {config['filename']}")
    plt.close()

def get_sql_info(test_type: str) -> Tuple[Optional[str], Optional[str]]:
    """Read SQL file info for the corresponding test type."""
    sql_file = f"{test_type}.sql"
    if os.path.exists(sql_file):
        try:
            with open(sql_file, 'r') as f:
                content = f.read()
            return sql_file, content
        except Exception:
            return None, None
    return None, None

def format_version_stats(version_stats: Dict, version: str, master_avg: float) -> str:
    """Format version statistics for markdown output."""
    stats = version_stats[version]
    avg_tps = stats['avg_tps']
    raw_values = stats['raw_values']

    if version == 'master':
        change_str = "(baseline)"
    else:
        change_pct = ((avg_tps - master_avg) / master_avg) * 100
        change_str = f"(+{change_pct:.1f}%)" if change_pct > 0 else f"({change_pct:.1f}%)"

    raw_str = "{" + ", ".join(f"{int(round(v))}" for v in raw_values) + "}"
    return f"- **{version}**: {int(round(avg_tps))} TPS {change_str} `{raw_str}`\n"

def write_test_results(f, test_type: str, test_data: pd.DataFrame, x_col: str, category_name: str):
    """Write results for a single test type to the markdown file."""
    sql_filename, sql_content = get_sql_info(test_type)

    if sql_filename:
        f.write(f"### TEST `{sql_filename}`\n\n")
        f.write("```sql\n")
        f.write(sql_content.rstrip('\n'))
        f.write("\n```\n\n")
    else:
        f.write(f"### Test: {test_type.replace('_', ' ').title()}\n\n")

    x_values = sorted(test_data[x_col].unique())

    for x_val in x_values:
        # Write header
        if category_name == "Connections = Jobs":
            f.write(f"#### {x_val} Connection{'s' if x_val != 1 else ''}, {x_val} Job{'s' if x_val != 1 else ''}\n\n")
        else:
            f.write(f"#### {FIXED_CONNECTIONS_COUNT} Connections, {x_val} Job{'s' if x_val != 1 else ''}\n\n")

        x_data = test_data[test_data[x_col] == x_val].copy()

        # Calculate version statistics
        version_stats = {}
        for version in x_data[COL_VERSION].unique():
            version_data = x_data[x_data[COL_VERSION] == version]
            tps_values = sorted(version_data[COL_TPS].tolist())
            avg_tps = version_data[COL_TPS].mean()
            version_stats[version] = {
                'avg_tps': avg_tps,
                'raw_values': tps_values
            }

        # Check for master baseline
        if 'master' not in version_stats:
            f.write("- No master baseline found for this configuration\n\n")
            continue

        master_avg = version_stats['master']['avg_tps']

        # Write results for each version
        for version in sorted(version_stats.keys()):
            f.write(format_version_stats(version_stats, version, master_avg))

        f.write("\n")

def print_ascii_results(df: pd.DataFrame):
    """Write Markdown results showing performance changes relative to master baseline."""
    with open(PERFORMANCE_MARKDOWN_FILE, 'w') as f:
        f.write("# Performance Results Summary\n\n")

        # Define categories
        categories = []

        # Category 1: Connections = Jobs
        connections_equal_jobs = filter_data_by_plot_type(df, "connections_equal_jobs")
        if not connections_equal_jobs.empty:
            categories.append(("Connections = Jobs", connections_equal_jobs, COL_CLIENTS))

        # Category 2: Fixed connections
        connections_fixed = filter_data_by_plot_type(df, "fixed_connections")
        if not connections_fixed.empty:
            categories.append((f"Connections = {FIXED_CONNECTIONS_COUNT}", connections_fixed, COL_JOBS))

        # Write results for each category
        for category_name, category_data, x_col in categories:
            f.write(f"## {category_name}\n\n")

            test_types = sorted(category_data[COL_TEST_TYPE].unique())

            for test_type in test_types:
                test_data = category_data[category_data[COL_TEST_TYPE] == test_type].copy()
                write_test_results(f, test_type, test_data, x_col, category_name)

def main():
    """Main function to create both overview plots."""
    # Load data
    df = load_combined_data()
    if df is None:
        return

    print("Loaded data with shape:", df.shape)
    print("Test types found:", df[COL_TEST_TYPE].unique())
    print("Versions found:", df[COL_VERSION].unique())
    print("Columns in data:", df.columns.tolist())

    # Create plots for both configurations
    for plot_type in PLOT_CONFIGS:
        print(f"\nCreating performance overview for {PLOT_CONFIGS[plot_type]['title_suffix']}...")
        plot_performance_overview(df, plot_type)

    print("\nBoth overview plots created successfully!")

    # Generate markdown results summary
    print_ascii_results(df)
    print(f"Markdown results summary saved to: {PERFORMANCE_MARKDOWN_FILE}")

if __name__ == '__main__':
    main() 