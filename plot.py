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

if __name__ == "__main__":
    main()