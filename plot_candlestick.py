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
    
    # Get unique versions
    versions = df['version'].unique()
    n_versions = len(versions)
    
    # Create figure with specific layout
    fig = plt.figure(figsize=(14, 10))
    
    # Create gridspec for layout: legend on top, plot below
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 4], hspace=0.3)
    ax_legend = fig.add_subplot(gs[0])
    ax_plot = fig.add_subplot(gs[1])
    
    # Hide the legend axes
    ax_legend.axis('off')
    
    # Colors for different versions
    colors = plt.cm.tab10(np.linspace(0, 1, n_versions))
    
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
        
        # Plot candlesticks
        for _, row in increasing_df.iterrows():
            conn = row['connections']
            
            # Candlestick components
            low = row['min_ms']
            q1 = row['q1_ms']
            median = row['median_ms']
            q3 = row['q3_ms']
            high = row['max_ms']
            
            # Offset for multiple versions
            offset = (idx - n_versions/2) * width * 0.6 / n_versions
            x = conn + offset
            
            # Draw the high-low line (whiskers)
            ax_plot.plot([x, x], [low, high], color=color, linewidth=1, alpha=0.7)
            
            # Draw the box (Q1 to Q3)
            box_height = q3 - q1
            box = mpatches.Rectangle((x - width*0.3/n_versions, q1), 
                                   width*0.6/n_versions, box_height,
                                   facecolor=color, edgecolor=color, 
                                   alpha=0.6, linewidth=1)
            ax_plot.add_patch(box)
            
            # Draw the median line
            ax_plot.plot([x - width*0.3/n_versions, x + width*0.3/n_versions], 
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
            
            # Plot regression line across the full range, but computed only from 100-1000
            x_reg = np.array([increasing_df['connections'].min(), increasing_df['connections'].max()])
            y_reg = slope * x_reg + intercept
            ax_plot.plot(x_reg, y_reg, color=color, linewidth=2, alpha=0.8, linestyle='--')
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
    
    # Customize main plot
    ax_plot.set_xlabel('Number of Connections', fontsize=12)
    ax_plot.set_ylabel('Latency (ms)', fontsize=12)
    ax_plot.set_title('PostgreSQL LISTEN/NOTIFY Latency Distribution by Version', 
                     fontsize=14, fontweight='bold', pad=10)
    ax_plot.grid(True, alpha=0.3, linestyle='--', zorder=1)
    
    # Add explanation text
    ax_plot.text(0.02, 0.98, 'Box: Q1-Q3, Black line: Median, Whiskers: Min-Max\nRegression computed from 100-1000 connections only',
                transform=ax_plot.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                fontsize=9)
    
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


if __name__ == "__main__":
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'candlestick_comparison.png'
        plot_candlestick_comparison(csv_file, output_file)
    else:
        plot_candlestick_comparison()