#!/usr/bin/env python3
"""
Plot PostgreSQL LISTEN/NOTIFY benchmark results from stats.csv
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
import os

def plot_stats(csv_file='stats.csv', output_file='benchmark_results.png'):
    """Plot the benchmark statistics"""
    
    # Check if file exists
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found. Run the benchmark first.")
        sys.exit(1)
    
    # Read the CSV file
    df = pd.read_csv(csv_file)
    
    if df.empty:
        print(f"Error: {csv_file} is empty.")
        sys.exit(1)
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('PostgreSQL LISTEN/NOTIFY Performance vs Connection Count', fontsize=16)
    
    # Plot 1: Average latency
    ax1 = axes[0, 0]
    ax1.plot(df['connections'], df['avg_ms'], 'b-', linewidth=2, label='Average')
    ax1.fill_between(df['connections'], 
                     df['avg_ms'] - df['stddev_ms'], 
                     df['avg_ms'] + df['stddev_ms'], 
                     alpha=0.3, color='blue', label='±1 StdDev')
    ax1.set_xlabel('Number of Connections')
    ax1.set_ylabel('Latency (ms)')
    ax1.set_title('Average Latency with Standard Deviation')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Min/Max/Avg comparison
    ax2 = axes[0, 1]
    ax2.plot(df['connections'], df['min_ms'], 'g-', linewidth=1.5, label='Min', alpha=0.7)
    ax2.plot(df['connections'], df['avg_ms'], 'b-', linewidth=2, label='Average')
    ax2.plot(df['connections'], df['max_ms'], 'r-', linewidth=1.5, label='Max', alpha=0.7)
    ax2.fill_between(df['connections'], df['min_ms'], df['max_ms'], alpha=0.2, color='gray')
    ax2.set_xlabel('Number of Connections')
    ax2.set_ylabel('Latency (ms)')
    ax2.set_title('Latency Range (Min/Avg/Max)')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Plot 3: Standard deviation
    ax3 = axes[1, 0]
    ax3.plot(df['connections'], df['stddev_ms'], 'purple', linewidth=2)
    ax3.set_xlabel('Number of Connections')
    ax3.set_ylabel('Standard Deviation (ms)')
    ax3.set_title('Latency Variability (Standard Deviation)')
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Latency increase rate
    ax4 = axes[1, 1]
    # Calculate percentage increase from baseline
    baseline_avg = df['avg_ms'].iloc[0]
    pct_increase = ((df['avg_ms'] - baseline_avg) / baseline_avg) * 100
    ax4.plot(df['connections'], pct_increase, 'orange', linewidth=2)
    ax4.set_xlabel('Number of Connections')
    ax4.set_ylabel('% Increase from Baseline')
    ax4.set_title(f'Relative Latency Increase (Baseline: {baseline_avg:.2f}ms)')
    ax4.grid(True, alpha=0.3)
    ax4.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    
    # Add vertical line at peak connections if there's a decrease phase
    max_conn_idx = df['connections'].idxmax()
    if max_conn_idx < len(df) - 1:
        for ax in axes.flat:
            ax.axvline(x=df['connections'].iloc[max_conn_idx], 
                      color='red', linestyle='--', alpha=0.5, 
                      label='Peak connections')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Plot saved to {output_file}")
    
    # Print summary statistics
    print("\nSummary Statistics:")
    print(f"Minimum connections: {df['connections'].min()}")
    print(f"Maximum connections: {df['connections'].max()}")
    print(f"Baseline latency: {df['avg_ms'].iloc[0]:.2f}ms")
    print(f"Peak latency: {df['avg_ms'].max():.2f}ms at {df.loc[df['avg_ms'].idxmax(), 'connections']} connections")
    print(f"Final latency: {df['avg_ms'].iloc[-1]:.2f}ms")
    print(f"Max latency increase: {pct_increase.max():.1f}%")
    
    # Calculate and print linear regression for increasing phase
    max_conn_idx = df['connections'].idxmax()
    increasing_phase = df.iloc[:max_conn_idx+1]
    if len(increasing_phase) > 10:
        from scipy import stats
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            increasing_phase['connections'], 
            increasing_phase['avg_ms']
        )
        print(f"\nLinear regression (increasing phase):")
        print(f"  Slope: {slope*1000:.3f} µs per connection")
        print(f"  R²: {r_value**2:.3f}")
    
    # Show plot if running interactively
    if hasattr(sys, 'ps1'):
        plt.show()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'benchmark_results.png'
        plot_stats(csv_file, output_file)
    else:
        plot_stats()