#!/usr/bin/env python3
"""
Plot benchmark results from CSV file.
Shows TPS vs Connections with log scale for connections and different colors for versions.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

def format_tps_value(max_tps):
    """Format TPS value as integer."""
    return f"{int(max_tps)}"

def format_percentage_change(baseline_tps, current_tps):
    """Format percentage change."""
    pct_change = ((current_tps - baseline_tps) / baseline_tps) * 100
    return f"{pct_change:+.1f}%"

def generate_plot():
    """Generate the performance plot."""
    # Read the CSV file
    df = pd.read_csv('benchmark_results.csv')

    # Parse version column to extract base version and threshold
    df['base_version'] = df['version'].apply(lambda x: x.split('-t')[0])
    df['threshold'] = df['version'].apply(lambda x: int(x.split('-t')[1]) if '-t' in x else None)

    # Set up the plot style
    plt.figure(figsize=(12, 8))
    sns.set_style("whitegrid")

    # Get unique versions
    versions = df['version'].unique()
    
    # Sort versions to ensure master comes first
    versions = sorted(versions, key=lambda x: (x != 'master', x))

    # Create a color palette
    colors = sns.color_palette("husl", len(versions))

    # Plot each version
    for i, version in enumerate(versions):
        version_data = df[df['version'] == version]
        
        # Calculate max TPS for each connection count
        grouped = version_data.groupby('connections')['tps'].max()
        
        # Create label
        if '-t' in version:
            base, threshold = version.split('-t')
            label = f"{base} (t={threshold})"
        else:
            label = version
        
        # Plot the max values
        plt.plot(grouped.index, grouped.values, 
                marker='o', markersize=8, linewidth=2,
                label=label, color=colors[i])
        
        # Add value annotations
        for x, y in zip(grouped.index, grouped.values):
            plt.annotate(f'{int(y)}', 
                        xy=(x, y), 
                        xytext=(0, 5), 
                        textcoords='offset points',
                        ha='center', 
                        fontsize=8,
                        color=colors[i])

    plt.xlabel('Number of Extra Listening Connections', fontsize=12)
    plt.ylabel('Transactions Per Second (TPS)', fontsize=12)
    plt.title('PostgreSQL LISTEN/NOTIFY Performance (Maximum TPS)\nwith Different notify_multicast_threshold Values', fontsize=14)
    plt.legend(loc='best', fontsize=10)
    plt.grid(True, alpha=0.3)

    # Add annotations for specific points if needed
    ax = plt.gca()
    
    # Set x-axis to log scale only if we have 0 in connections
    if 0 in df['connections'].values:
        # Replace 0 with 0.5 for log scale
        ax.set_xscale('symlog')
    else:
        ax.set_xscale('log')

    # Adjust layout and save
    plt.tight_layout()
    plt.savefig('plot-v4.png', dpi=300, bbox_inches='tight')
    plt.show()

    # Print summary statistics
    print("\nSummary Statistics (Maximum TPS):")
    print("==================================")
    for version in versions:
        version_data = df[df['version'] == version]
        if '-t' in version:
            base, threshold = version.split('-t')
            print(f"\n{base} (threshold={threshold}):")
        else:
            print(f"\n{version}:")
        for conn_count in sorted(version_data['connections'].unique()):
            conn_data = version_data[version_data['connections'] == conn_count]['tps']
            print(f"  {conn_count} connections: {int(conn_data.max())} TPS (max)")

def generate_table():
    """Generate ASCII table showing benchmark results with master as baseline."""
    # Read the CSV file
    df = pd.read_csv('benchmark_results.csv')

    # Get unique connections and versions
    connections = sorted(df['connections'].unique())
    versions = df['version'].unique()

    # Ensure master is first
    if 'master' in versions:
        versions = ['master'] + sorted([v for v in versions if v != 'master'])

    print("Database Performance Comparison (Maximum TPS)")
    print("=" * 80)
    print()

    for conn in connections:
        print(f"Extra Connections: {conn}")
        print("-" * 80)

        # Find master baseline for this connection level
        master_data = df[(df['version'] == 'master') & (df['connections'] == conn)]['tps']
        if len(master_data) > 0:
            master_max = master_data.max()
        else:
            master_max = None

        # Print header
        print(f"{'Version':<25} {'Max TPS':<15} {'vs Master':<15} {'All Values (sorted)':<30}")
        print("-" * 85)

        # Print each version
        for version in versions:
            version_data = df[(df['version'] == version) & (df['connections'] == conn)]['tps']

            if len(version_data) > 0:
                max_tps = version_data.max()
                all_values = sorted(version_data.tolist())
                
                tps_str = format_tps_value(max_tps)

                if version == 'master':
                    change_str = "baseline"
                elif master_max is not None:
                    change_str = format_percentage_change(master_max, max_tps)
                else:
                    change_str = "N/A"

                # Format version name for display
                display_version = version
                if '-t' in version:
                    base, threshold = version.split('-t')
                    display_version = f"{base} (t={threshold})"
                
                # Format all values as a compact string
                values_str = "{" + ", ".join(f"{int(v)}" for v in all_values) + "}"
                
                # Truncate if too long
                if len(values_str) > 40:
                    values_str = values_str[:37] + "...}"
                
                print(f"{display_version:<25} {tps_str:<15} {change_str:<15} {values_str}")

        print()

if __name__ == "__main__":
    generate_plot()
    print("\n" + "="*80 + "\n")
    generate_table()