#!/usr/bin/env python3
"""
Plot PostgreSQL version comparison using candlestick charts for LISTEN/NOTIFY benchmark results
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from scipy import stats as scipy_stats
import sys
import os
import re
import hashlib

def get_color_from_version(version):
    """Generate a consistent color from version string using hash"""
    # Create hash from version string
    hash_obj = hashlib.md5(version.encode())
    hash_hex = hash_obj.hexdigest()

    # Extract RGB values from hash (use first 6 characters)
    r = int(hash_hex[0:2], 16) / 255.0
    g = int(hash_hex[2:4], 16) / 255.0
    b = int(hash_hex[4:6], 16) / 255.0

    # Return as hex color string
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'

def plot_version_pair(df, version1, version2, output_file):
    """Plot candlestick comparison for a pair of versions"""
    # Filter data for the two versions
    df_pair = df[df['version'].isin([version1, version2])].copy()
    versions = [version1, version2]
    n_versions = 2

    # Create figure with specific layout
    fig = plt.figure(figsize=(16, 10))

    # Create gridspec for layout: legend on top, two plots below
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 4], width_ratios=[1, 1], hspace=0.3, wspace=0.15)
    ax_legend = fig.add_subplot(gs[0, :])  # Legend spans both columns
    ax_left = fig.add_subplot(gs[1, 0])    # Left plot: 0-100 connections
    ax_right = fig.add_subplot(gs[1, 1])   # Right plot: 100-1000 connections

    # Hide the legend axes
    ax_legend.axis('off')

    # Get consistent colors based on version hash
    colors = [get_color_from_version(version1), get_color_from_version(version2)]

    # Store legend handles and regression info
    legend_elements = []
    regression_info = []

    # Process each version
    for idx, version in enumerate(versions):
        version_df = df_pair[df_pair['version'] == version].copy()
        color = colors[idx]

        # Extract data for increasing phase only (before peak)
        max_conn_idx = version_df['connections'].idxmax()
        increasing_df = version_df.iloc[:max_conn_idx+1]

        # Plot candlesticks on both panels
        for _, row in increasing_df.iterrows():
            conn = row['connections']

            # Determine which panel to use
            if conn <= 100:
                ax = ax_left
            else:
                ax = ax_right

            # Candlestick components
            low = row['min_ms']
            q1 = row['q1_ms']
            median = row['median_ms']
            q3 = row['q3_ms']
            high = row['max_ms']

            # Adjust width based on panel
            if conn <= 100:
                box_width = 2  # Narrower boxes for 0-100 range
            else:
                box_width = 10  # Wider boxes for 100-1000 range

            # Offset for multiple versions
            offset = (idx - n_versions/2) * box_width * 0.6 / n_versions
            x = conn + offset

            # Draw the high-low line (whiskers)
            ax.plot([x, x], [low, high], color=color, linewidth=1, alpha=0.5)

            # Draw the box (Q1 to Q3)
            box_height = q3 - q1
            box = mpatches.Rectangle((x - box_width*0.3/n_versions, q1),
                                   box_width*0.6/n_versions, box_height,
                                   facecolor=color, edgecolor=color,
                                   alpha=0.5, linewidth=1)
            ax.add_patch(box)

            # Draw the median line
            ax.plot([x - box_width*0.3/n_versions, x + box_width*0.3/n_versions],
                   [median, median], color='black', linewidth=2)

        # Linear regression on medians for 100-1000 connections only
        regression_df = increasing_df[
            (increasing_df['connections'] >= 100) &
            (increasing_df['connections'] <= 1000)
        ]

        if len(regression_df) > 1:
            slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(
                regression_df['connections'],
                regression_df['median_ms']
            )

            # Plot regression line only on the right panel (100-1000)
            x_reg = np.array([100, 1000])
            y_reg = slope * x_reg + intercept
            ax_right.plot(x_reg, y_reg, color=color, linewidth=2, alpha=0.5, linestyle='--')
        else:
            # Fallback if not enough data points in range
            slope, intercept, r_value = 0, 0, 0

        # Create legend entry with regression formula
        slope_us = slope * 1000  # Convert ms to μs
        formula = f"median = {intercept:.3f} + {slope_us:.3f}×10⁻³ × connections (R²={r_value**2:.3f})"
        legend_label = f"{version}\n  {formula}"

        # Create custom legend element
        from matplotlib.lines import Line2D
        legend_element = Line2D([0], [0], color=color, linewidth=3,
                              marker='s', markersize=8, alpha=0.5,
                              label=legend_label)
        legend_elements.append(legend_element)

        # Store regression info
        regression_info.append({
            'version': version,
            'slope_us': slope_us,
            'intercept': intercept,
            'r_squared': r_value**2
        })

    # Customize left plot (0-100 connections)
    ax_left.set_xlabel('Number of Connections', fontsize=12)
    ax_left.set_ylabel('Latency (ms)', fontsize=12)
    ax_left.set_title('0-100 Connections', fontsize=13, fontweight='bold', pad=10)
    ax_left.grid(True, alpha=0.3, linestyle='--', zorder=1)
    ax_left.set_xlim(-5, 105)

    # Customize right plot (100-1000 connections)
    ax_right.set_xlabel('Number of Connections', fontsize=12)
    ax_right.set_ylabel('Latency (ms)', fontsize=12)
    ax_right.set_title('100-1000 Connections', fontsize=13, fontweight='bold', pad=10)
    ax_right.grid(True, alpha=0.3, linestyle='--', zorder=1)
    ax_right.set_xlim(95, 1005)

    # Add explanation text to left panel
    ax_left.text(0.02, 0.98, 'Box: Q1-Q3\nBlack line: Median\nWhiskers: Min-Max',
                transform=ax_left.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                fontsize=8)

    # Add regression note to right panel
    ax_right.text(0.02, 0.98, 'Dashed lines:\nLinear regression\n(100-1000 range)',
                transform=ax_right.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5),
                fontsize=8)

    # Skip title to save space - version info is in the legend

    # Create legend in the top subplot
    legend = ax_legend.legend(handles=legend_elements,
                            loc='center',
                            ncol=2,
                            fontsize=9,
                            frameon=True,
                            fancybox=True,
                            shadow=True,
                            title='PostgreSQL Version and Linear Regression Formula (100-1000 connections)',
                            title_fontsize=11)

    legend.get_frame().set_alpha(0.9)

    # Save with high DPI
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close to free memory

def plot_candlestick_comparison(csv_file='benchmark_results.csv', output_file='candlestick_comparison.png'):
    """Plot candlestick chart comparison across PostgreSQL versions"""

    # Check if file exists
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found. Run ./run_all_versions.sh first.")
        sys.exit(1)

    # Read the CSV file
    df = pd.read_csv(csv_file)

    if df.empty:
        print(f"Error: {csv_file} is empty.")
        sys.exit(1)

    # Get unique versions in the order they appear
    versions = []
    for version in df['version']:
        if version not in versions:
            versions.append(version)
    n_versions = len(versions)

    # Create figure with specific layout
    fig = plt.figure(figsize=(16, 10))

    # Create gridspec for layout: legend on top, two plots below
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 4], width_ratios=[1, 1], hspace=0.3, wspace=0.15)
    ax_legend = fig.add_subplot(gs[0, :])  # Legend spans both columns
    ax_left = fig.add_subplot(gs[1, 0])    # Left plot: 0-100 connections
    ax_right = fig.add_subplot(gs[1, 1])   # Right plot: 100-1000 connections

    # Hide the legend axes
    ax_legend.axis('off')

    # Get consistent colors based on version hash
    colors = [get_color_from_version(version) for version in versions]

    # Store legend handles and regression info
    legend_elements = []
    regression_info = []

    # Width of each candlestick
    width = 10  # connections between candlesticks

    # Process each version
    for idx, version in enumerate(versions):
        version_df = df[df['version'] == version].copy()
        color = colors[idx]

        # Extract data for increasing phase only (before peak)
        max_conn_idx = version_df['connections'].idxmax()
        increasing_df = version_df.iloc[:max_conn_idx+1]

        # Plot candlesticks on both panels
        for _, row in increasing_df.iterrows():
            conn = row['connections']

            # Determine which panel to use
            if conn <= 100:
                ax = ax_left
            else:
                ax = ax_right

            # Candlestick components
            low = row['min_ms']
            q1 = row['q1_ms']
            median = row['median_ms']
            q3 = row['q3_ms']
            high = row['max_ms']

            # Adjust width based on panel
            if conn <= 100:
                box_width = 2  # Narrower boxes for 0-100 range
            else:
                box_width = 10  # Wider boxes for 100-1000 range

            # Offset for multiple versions
            offset = (idx - n_versions/2) * box_width * 0.6 / n_versions
            x = conn + offset

            # Draw the high-low line (whiskers)
            ax.plot([x, x], [low, high], color=color, linewidth=1, alpha=0.7)

            # Draw the box (Q1 to Q3)
            box_height = q3 - q1
            box = mpatches.Rectangle((x - box_width*0.3/n_versions, q1),
                                   box_width*0.6/n_versions, box_height,
                                   facecolor=color, edgecolor=color,
                                   alpha=0.6, linewidth=1)
            ax.add_patch(box)

            # Draw the median line
            ax.plot([x - box_width*0.3/n_versions, x + box_width*0.3/n_versions],
                   [median, median], color='black', linewidth=2)

        # Linear regression on medians for 100-1000 connections only
        regression_df = increasing_df[
            (increasing_df['connections'] >= 100) &
            (increasing_df['connections'] <= 1000)
        ]

        if len(regression_df) > 1:
            slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(
                regression_df['connections'],
                regression_df['median_ms']
            )

            # Plot regression line only on the right panel (100-1000)
            x_reg = np.array([100, 1000])
            y_reg = slope * x_reg + intercept
            ax_right.plot(x_reg, y_reg, color=color, linewidth=2, alpha=0.8, linestyle='--')
        else:
            # Fallback if not enough data points in range
            slope, intercept, r_value = 0, 0, 0

        # Create legend entry with regression formula
        slope_us = slope * 1000  # Convert ms to μs
        formula = f"median = {intercept:.3f} + {slope_us:.3f}×10⁻³ × connections (R²={r_value**2:.3f})"
        legend_label = f"{version}\n  {formula}"

        # Create custom legend element
        from matplotlib.lines import Line2D
        legend_element = Line2D([0], [0], color=color, linewidth=3,
                              marker='s', markersize=8, alpha=0.6,
                              label=legend_label)
        legend_elements.append(legend_element)

        # Store regression info
        regression_info.append({
            'version': version,
            'slope_us': slope_us,
            'intercept': intercept,
            'r_squared': r_value**2
        })

    # Customize left plot (0-100 connections)
    ax_left.set_xlabel('Number of Connections', fontsize=12)
    ax_left.set_ylabel('Latency (ms)', fontsize=12)
    ax_left.set_title('0-100 Connections', fontsize=13, fontweight='bold', pad=10)
    ax_left.grid(True, alpha=0.3, linestyle='--', zorder=1)
    ax_left.set_xlim(-5, 105)

    # Customize right plot (100-1000 connections)
    ax_right.set_xlabel('Number of Connections', fontsize=12)
    ax_right.set_ylabel('Latency (ms)', fontsize=12)
    ax_right.set_title('100-1000 Connections', fontsize=13, fontweight='bold', pad=10)
    ax_right.grid(True, alpha=0.3, linestyle='--', zorder=1)
    ax_right.set_xlim(95, 1005)

    # Add explanation text to left panel
    ax_left.text(0.02, 0.98, 'Box: Q1-Q3\nBlack line: Median\nWhiskers: Min-Max',
                transform=ax_left.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                fontsize=8)

    # Add regression note to right panel
    ax_right.text(0.02, 0.98, 'Dashed lines:\nLinear regression\n(100-1000 range)',
                transform=ax_right.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5),
                fontsize=8)

    # Skip title to save space - version info is in the legend

    # Create legend in the top subplot
    ncol = min(2, n_versions)  # Use 2 columns if more than 2 versions

    legend = ax_legend.legend(handles=legend_elements,
                            loc='center',
                            ncol=ncol,
                            fontsize=9,
                            frameon=True,
                            fancybox=True,
                            shadow=True,
                            title='PostgreSQL Version and Linear Regression Formula (100-1000 connections)',
                            title_fontsize=11)

    legend.get_frame().set_alpha(0.9)

    # Save with high DPI
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Plot saved to {output_file}")

    # Print summary statistics with regression info
    print("\nLinear Regression Summary (100-1000 connections):")
    print("-" * 100)
    print(f"{'Version':<50} {'Slope (μs/conn)':<15} {'Intercept (ms)':<15} {'R²':<10}")
    print("-" * 100)

    # Sort by slope to show which versions have better scaling
    regression_info.sort(key=lambda x: x['slope_us'])

    for info in regression_info:
        version_short = info['version'].split('on')[0].strip()  # Shorten version for table
        print(f"{version_short:<50} {info['slope_us']:>14.3f} {info['intercept']:>14.3f} {info['r_squared']:>9.3f}")

    print("\n" + "-" * 100)
    print("Note: Lower slope values indicate better performance scaling with connection count.")

    # Show plot if running interactively
    if hasattr(sys, 'ps1'):
        plt.show()

    # Generate plots for consecutive version pairs
    print("\nGenerating consecutive version pair plots...")
    for i in range(len(versions) - 1):
        version1 = versions[i]
        version2 = versions[i + 1]
        pair_output_file = f"candlestick_comparison-{i+1}.png"

        print(f"Plotting {version1} vs {version2}...")

        # Create a plot for this pair using the same logic as the main plot
        plot_version_pair(df, version1, version2, pair_output_file)

        print(f"  Saved to {pair_output_file}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'candlestick_comparison.png'
        plot_candlestick_comparison(csv_file, output_file)
    else:
        plot_candlestick_comparison()