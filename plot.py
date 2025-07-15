#!/usr/bin/env python3
"""
Plot benchmark results from CSV file.
Shows TPS vs Connections with log scale for connections and different colors for versions.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def main():
    # Read the CSV file
    df = pd.read_csv('benchmark_results.csv')

    # Get unique versions for colors
    versions = df['version'].unique()

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 8))

    # Color map for versions
    colors = plt.cm.tab10(np.linspace(0, 1, len(versions)))

    # Plot each version
    for i, version in enumerate(versions):
        version_data = df[df['version'] == version]

        # Calculate mean TPS for each connection count
        grouped = version_data.groupby('connections')['tps'].mean()

        # Handle connections = 0 by replacing with a small positive value for log scale
        conn_values = grouped.index.copy()
        conn_values = conn_values.to_series().replace(0, 0.1)  # Replace 0 with 0.1 for log scale

        # Plot the averaged data points
        ax.scatter(conn_values, grouped.values,
                  color=colors[i], label=version, alpha=0.7, s=60)

        # Add text annotations for exact averaged values
        for conn, tps in grouped.items():
            conn_val = 0.1 if conn == 0 else conn
            ax.annotate(f'{tps:.0f}',
                       (conn_val, tps),
                       xytext=(5, 5), textcoords='offset points',
                       fontsize=8, alpha=0.8,
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))

        # Draw lines connecting the averaged points
        ax.plot(conn_values, grouped.values, color=colors[i], alpha=0.8, linewidth=2)

    # Set log scale for both axes
    ax.set_xscale('log')
    ax.set_yscale('log')

    # Set labels and title
    ax.set_xlabel('Connections (log scale)', fontsize=12)
    ax.set_ylabel('Transactions per Second (TPS) (log scale)', fontsize=12)
    ax.set_title('Database Performance Comparison by Version', fontsize=14)

    # Add legend
    ax.legend(title='Version', fontsize=10, title_fontsize=12)

    # Add grid
    ax.grid(True, alpha=0.3)

    # Custom x-axis ticks to show the actual connection values
    unique_connections = sorted(df['connections'].unique())
    tick_positions = [0.1 if x == 0 else x for x in unique_connections]
    tick_labels = [f'{x}' if x != 0 else '0' for x in unique_connections]

    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels)

    # Adjust layout and save
    plt.tight_layout()
    plt.savefig('plot.png', dpi=300, bbox_inches='tight')

def format_tps_with_stddev(mean_tps, std_tps):
    """Format TPS with standard deviation."""
    return f"{mean_tps:.2f} ± {std_tps:.2f}"

def format_percentage_change(baseline_tps, current_tps, baseline_std, current_std):
    """Format percentage change with error propagation."""
    pct_change = ((current_tps - baseline_tps) / baseline_tps) * 100

    # Error propagation for percentage change
    # δ(%) = 100 * sqrt((δcurrent/baseline)² + (current*δbaseline/baseline²)²)
    if baseline_tps != 0:
        error = 100 * np.sqrt((current_std/baseline_tps)**2 + (current_tps*baseline_std/baseline_tps**2)**2)
        return f"{pct_change:+.1f}% ± {error:.1f}%"
    else:
        return "N/A"

def generate_table():
    """Generate ASCII table showing benchmark results with master as baseline."""
    # Read the CSV file
    df = pd.read_csv('benchmark_results.csv')

    # Group by connections and version, calculate mean and std
    grouped = df.groupby(['connections', 'version'])['tps'].agg(['mean', 'std']).reset_index()

    # Get unique connections and versions
    connections = sorted(df['connections'].unique())
    versions = df['version'].unique()

    # Ensure master is first
    if 'master' in versions:
        versions = ['master'] + [v for v in versions if v != 'master']

    print("Database Performance Comparison")
    print("=" * 80)
    print()

    for conn in connections:
        print(f"Connections: {conn}")
        print("-" * 60)

        # Get data for this connection level
        conn_data = grouped[grouped['connections'] == conn]

        # Find master baseline for this connection level
        master_data = conn_data[conn_data['version'] == 'master']
        if len(master_data) > 0:
            master_tps = master_data['mean'].iloc[0]
            master_std = master_data['std'].iloc[0]
        else:
            master_tps = None
            master_std = None

        # Print header
        print(f"{'Version':<25} {'TPS (mean ± std)':<25} {'vs Master':<20}")
        print("-" * 70)

        # Print each version
        for version in versions:
            version_data = conn_data[conn_data['version'] == version]

            if len(version_data) > 0:
                mean_tps = version_data['mean'].iloc[0]
                std_tps = version_data['std'].iloc[0]

                tps_str = format_tps_with_stddev(mean_tps, std_tps)

                if version == 'master':
                    change_str = "baseline"
                elif master_tps is not None:
                    change_str = format_percentage_change(master_tps, mean_tps, master_std, std_tps)
                else:
                    change_str = "N/A"

                print(f"{version:<25} {tps_str:<25} {change_str:<20}")

        print()

if __name__ == "__main__":
    main()
    print("\n" + "="*80 + "\n")
    generate_table()