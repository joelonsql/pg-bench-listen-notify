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
PERFORMANCE_MARKDOWN_FILE = 'performance_overview-v4.md'
FIXED_CONNECTIONS_COUNT = 1000
DPI = 300

# Expected CSV columns
EXPECTED_COLUMNS = [
    'test_type',
    'clients', 
    'jobs',
    'threshold',
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
COL_THRESHOLD = 'threshold'
COL_VERSION = 'version'
COL_TPS = 'tps'

# Plot configuration
PLOT_CONFIGS = {
    "connections_equal_jobs": {
        "title_suffix": "pgbench -f $script -c $jobs -j $jobs -T 3 -n",
        "filename": "performance_overview_connections_equal_jobs-v4.png",
        "x_label": "$jobs"
    },
    "fixed_connections": {
        "title_suffix": f"pgbench -f \$script -c {FIXED_CONNECTIONS_COUNT} -j \$jobs -T 3 -n",
        "filename": "performance_overview_fixed_connections-v4.png",
        "x_label": "$jobs"
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
SCATTER_SIZE = 20
LINE_WIDTH = 2
ANNOTATION_FONT_SIZE = 8
TITLE_FONT_SIZE = 16
Y_AXIS_PADDING = 0.8  # For log scale min
Y_AXIS_PADDING_MAX = 1.2  # For log scale max
ALPHA_VALUE = 0.5  # Transparency for plots

# Set style for better plots
plt.style.use('default')
sns.set_palette("husl")

def validate_dataframe(df: pd.DataFrame) -> None:
    """Validate that the dataframe has all expected columns."""
    # Make threshold optional for backward compatibility
    required_columns = [col for col in EXPECTED_COLUMNS if col != 'threshold']
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing expected columns: {missing_columns}")
    
    # Add threshold column if missing (for backward compatibility)
    if 'threshold' not in df.columns:
        df['threshold'] = None

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

def plot_version_data(ax, version_data, test_data, version, threshold, color, x_col, version_index, num_versions):
    """Plot data for a single version+threshold combination on the given axis."""
    version_data = version_data.sort_values(x_col)
    # Filter individual data by both version and threshold
    # Handle NaN values properly for master version
    if pd.isna(threshold):
        individual_data = test_data[
            (test_data[COL_VERSION] == version) & 
            (test_data[COL_THRESHOLD].isna())
        ].copy()
    else:
        individual_data = test_data[
            (test_data[COL_VERSION] == version) & 
            (test_data[COL_THRESHOLD] == threshold)
        ].copy()
    individual_data = individual_data.sort_values(x_col)

    x_positions_max = []
    y_positions_max = []
    first_scatter = True  # Flag to add label only once
    
    # Create label with threshold info
    if not pd.isna(threshold) and version != 'master':
        label_suffix = f" (t={int(threshold)})"
    else:
        label_suffix = ""

    for _, row in version_data.iterrows():
        x_val = row[x_col]
        avg_tps = row[COL_TPS]  # This is still the mean from the grouped data

        # Get individual points
        individual_points = individual_data[individual_data[x_col] == x_val][COL_TPS].tolist()
        
        if individual_points:
            # Find max value for this x position
            max_tps = max(individual_points)
            x_positions_max.append(x_val)
            y_positions_max.append(max_tps)
            # Plot individual data points
            x_positions = [x_val] * len(individual_points)
            # Add label only for the first scatter to avoid duplicate legend entries
            scatter_label = f'{version}{label_suffix} (data)' if first_scatter else None
            ax.scatter(x_positions, individual_points, 
                      color=color, s=SCATTER_SIZE, alpha=ALPHA_VALUE, zorder=2, 
                      edgecolors='black', linewidth=0.5, label=scatter_label)
            first_scatter = False

            # Add annotation showing max value
            ax.annotate(f'{int(max_tps)}', 
                       xy=(x_val, max_tps),
                       xytext=(0, 5), textcoords='offset points',
                       ha='center', va='bottom',
                       fontsize=ANNOTATION_FONT_SIZE, color=color,
                       bbox=dict(boxstyle='round,pad=0.3', 
                               facecolor='white', 
                               edgecolor=color))

    # Connect max values with lines
    if len(x_positions_max) > 1:
        # Make master line more prominent
        if version == 'master':
            ax.plot(x_positions_max, y_positions_max, 
                   color=color, linewidth=LINE_WIDTH * 1.5, zorder=10, 
                   label=f'{version}{label_suffix} (max)', linestyle='-', alpha=1.0)
        else:
            ax.plot(x_positions_max, y_positions_max, 
                   color=color, linewidth=LINE_WIDTH, zorder=5, 
                   label=f'{version}{label_suffix} (max)', linestyle='-', alpha=0.9)
    else:
        # For single point, just add label
        ax.scatter([], [], color=color, s=SCATTER_SIZE, label=f'{version}{label_suffix} (max)')

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
    fig.suptitle(config["title_suffix"], 
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

            # Group by version, threshold, and x-axis variable
            # Use dropna=False to keep None values for master version
            grouped = test_data.groupby([COL_VERSION, COL_THRESHOLD, x_col], dropna=False)[COL_TPS].mean().reset_index()
            
            # Get unique version+threshold combinations
            version_threshold_combos = grouped[[COL_VERSION, COL_THRESHOLD]].drop_duplicates()
            num_combos = len(version_threshold_combos)
            colors = plt.cm.Set1(np.linspace(0, 1, num_combos))

            # Plot each version+threshold combination
            for j, (_, combo) in enumerate(version_threshold_combos.iterrows()):
                version = combo[COL_VERSION]
                threshold = combo[COL_THRESHOLD]
                
                # Filter data for this specific combination
                if pd.isna(threshold):
                    combo_data = grouped[
                        (grouped[COL_VERSION] == version) & 
                        (grouped[COL_THRESHOLD].isna())
                    ]
                else:
                    combo_data = grouped[
                        (grouped[COL_VERSION] == version) & 
                        (grouped[COL_THRESHOLD] == threshold)
                    ]
                
                plot_version_data(ax, combo_data, test_data, version, threshold, colors[j], 
                                x_col, j, num_combos)

            # Configure axis
            ax.set_xlabel(config["x_label"])
            ax.set_ylabel('TPS')
            ax.set_title(f'$script = {test_type}.sql')
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
    # Keep the plot open for display
    # plt.close()  # Commented out to keep plot open

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

def format_version_stats(version_stats: Dict, key: Tuple[str, any], master_max: float) -> str:
    """Format version statistics for markdown output."""
    version, threshold = key
    stats = version_stats[key]
    max_tps = stats['max_tps']
    raw_values = stats['raw_values']
    
    # Create version label with threshold
    if threshold is not None and version != 'master':
        version_label = f"{version} (t={threshold})"
    else:
        version_label = version

    if version == 'master':
        change_str = "(baseline)"
    else:
        change_pct = ((max_tps - master_max) / master_max) * 100
        change_str = f"(+{change_pct:.1f}%)" if change_pct > 0 else f"({change_pct:.1f}%)"

    raw_str = "{" + ", ".join(f"{int(round(v))}" for v in raw_values) + "}"
    return f"- **{version_label}**: {int(round(max_tps))} TPS {change_str} `{raw_str}`\n"

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
            # Get unique thresholds for this version
            version_thresholds = x_data[x_data[COL_VERSION] == version][COL_THRESHOLD].unique()
            for threshold in version_thresholds:
                # Handle None/NaN values properly
                if pd.isna(threshold):
                    version_data = x_data[
                        (x_data[COL_VERSION] == version) & 
                        (x_data[COL_THRESHOLD].isna())
                    ]
                else:
                    version_data = x_data[
                        (x_data[COL_VERSION] == version) & 
                        (x_data[COL_THRESHOLD] == threshold)
                    ]
                if not version_data.empty:
                    tps_values = sorted(version_data[COL_TPS].tolist())
                    max_tps = version_data[COL_TPS].max()
                    version_stats[(version, threshold)] = {
                        'max_tps': max_tps,
                        'raw_values': tps_values
                    }

        # Check for master baseline
        master_key = None
        for key in version_stats.keys():
            if key[0] == 'master':
                master_key = key
                break
                
        if master_key is None:
            f.write("- No master baseline found for this configuration\n\n")
            continue

        master_max = version_stats[master_key]['max_tps']

        # Write results for each version
        for key in sorted(version_stats.keys()):
            f.write(format_version_stats(version_stats, key, master_max))

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
    
    # Display all plots
    plt.show()

if __name__ == '__main__':
    main() 