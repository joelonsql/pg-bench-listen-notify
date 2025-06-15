#!/usr/bin/env python3
"""
Plot PostgreSQL version comparison with filtered data points for better visibility
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from scipy import stats as scipy_stats
import sys
import os
import re

# Global color mapping to ensure consistency across all plots
VERSION_COLORS = {}

def get_color_from_version(version):
    """Get a distinct color for each version using matplotlib's tab10 colormap"""
    global VERSION_COLORS
    
    # If we haven't assigned a color to this version yet
    if version not in VERSION_COLORS:
        # Use matplotlib's 'tab10' colormap for distinct colors
        # tab10 has 10 distinct colors that work well together
        cmap = plt.cm.get_cmap('tab10')
        color_idx = len(VERSION_COLORS) % 10
        VERSION_COLORS[version] = cmap(color_idx)
    
    # Convert RGBA to hex format
    color = VERSION_COLORS[version]
    return f'#{int(color[0]*255):02x}{int(color[1]*255):02x}{int(color[2]*255):02x}'

def filter_data_points(df, range_type):
    """Filter data points based on range type"""
    if range_type == '0-10':
        # Show all points from 0-10
        return df[df['connections'] <= 10]
    elif range_type == '10-100':
        # Show 10, 20, 30, ..., 100
        df_filtered = df[(df['connections'] > 10) & (df['connections'] <= 100)]
        # Filter to multiples of 10
        return df_filtered[df_filtered['connections'] % 10 == 0]
    elif range_type == '100-1000':
        # Show 100, 200, 300, ..., 1000
        df_filtered = df[(df['connections'] >= 100) & (df['connections'] <= 1000)]
        # Filter to multiples of 100
        return df_filtered[df_filtered['connections'] % 100 == 0]
    return df

def plot_candlestick_comparison(csv_file='benchmark_results.csv', output_file='candlestick_comparison.png'):
    """Plot candlestick chart comparison across PostgreSQL versions with filtered data"""
    
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
    
    # Create figure with specific layout - three panels
    fig = plt.figure(figsize=(20, 10))
    
    # Create gridspec for layout: legend on top, three plots below
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 4], width_ratios=[1, 1, 1], hspace=0.3, wspace=0.15)
    ax_legend = fig.add_subplot(gs[0, :])  # Legend spans all columns
    ax_0_10 = fig.add_subplot(gs[1, 0])    # Left plot: 0-10 connections
    ax_10_100 = fig.add_subplot(gs[1, 1])  # Middle plot: 10-100 connections
    ax_100_1000 = fig.add_subplot(gs[1, 2]) # Right plot: 100-1000 connections
    
    # Hide the legend axes
    ax_legend.axis('off')
    
    # Get consistent colors based on version hash
    colors = [get_color_from_version(version) for version in versions]
    
    # Store legend handles and regression info
    legend_elements = []
    regression_info = []
    
    # Process each version
    for idx, version in enumerate(versions):
        version_df = df[df['version'] == version].copy()
        color = colors[idx]
        
        # Extract data for increasing phase only (before peak)
        max_conn_idx = version_df['connections'].idxmax()
        increasing_df = version_df.iloc[:max_conn_idx+1]
        
        # Filter and plot for each range
        for range_type, ax in [('0-10', ax_0_10), ('10-100', ax_10_100), ('100-1000', ax_100_1000)]:
            filtered_df = filter_data_points(increasing_df, range_type)
            
            # Plot candlesticks for filtered data
            for _, row in filtered_df.iterrows():
                conn = row['connections']
                
                # Candlestick components
                low = row['min_ms']
                q1 = row['q1_ms']
                median = row['median_ms']
                q3 = row['q3_ms']
                high = row['max_ms']
                
                # Adjust width based on range
                if range_type == '0-10':
                    box_width = 0.3
                elif range_type == '10-100':
                    box_width = 3
                else:  # 100-1000
                    box_width = 30
                
                # Offset for multiple versions
                offset = (idx - n_versions/2 + 0.5) * box_width * 0.8 / n_versions
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
            
            # Plot regression line only on the 100-1000 panel
            x_reg = np.array([100, 1000])
            y_reg = slope * x_reg + intercept
            ax_100_1000.plot(x_reg, y_reg, color=color, linewidth=2, alpha=0.5, linestyle='--')
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
    
    # Customize 0-10 plot
    ax_0_10.set_xlabel('Number of Connections', fontsize=12)
    ax_0_10.set_ylabel('Latency (ms)', fontsize=12)
    ax_0_10.set_title('0-10 Connections', fontsize=13, fontweight='bold', pad=10)
    ax_0_10.grid(True, alpha=0.3, linestyle='--', zorder=1)
    ax_0_10.set_xlim(-0.5, 10.5)
    ax_0_10.set_xticks(range(0, 11))
    
    # Customize 10-100 plot
    ax_10_100.set_xlabel('Number of Connections', fontsize=12)
    ax_10_100.set_ylabel('Latency (ms)', fontsize=12)
    ax_10_100.set_title('10-100 Connections', fontsize=13, fontweight='bold', pad=10)
    ax_10_100.grid(True, alpha=0.3, linestyle='--', zorder=1)
    ax_10_100.set_xlim(5, 105)
    ax_10_100.set_xticks(range(10, 101, 10))
    
    # Customize 100-1000 plot
    ax_100_1000.set_xlabel('Number of Connections', fontsize=12)
    ax_100_1000.set_ylabel('Latency (ms)', fontsize=12)
    ax_100_1000.set_title('100-1000 Connections', fontsize=13, fontweight='bold', pad=10)
    ax_100_1000.grid(True, alpha=0.3, linestyle='--', zorder=1)
    ax_100_1000.set_xlim(50, 1050)
    ax_100_1000.set_xticks(range(100, 1001, 100))
    
    # Add explanation text to first panel
    ax_0_10.text(0.02, 0.98, 'All data\npoints shown',
                transform=ax_0_10.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                fontsize=8)
    
    # Add explanation text to middle panel
    ax_10_100.text(0.02, 0.98, 'Every 10th\nconnection',
                transform=ax_10_100.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                fontsize=8)
    
    # Add regression note to right panel
    ax_100_1000.text(0.02, 0.98, 'Every 100th\nconnection\n+ regression',
                transform=ax_100_1000.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5),
                fontsize=8)
    
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

def plot_version_pair(df, version1, version2, output_file):
    """Plot candlestick comparison for a pair of versions with filtered data"""
    # Filter data for the two versions
    df_pair = df[df['version'].isin([version1, version2])].copy()
    versions = [version1, version2]
    n_versions = 2
    
    # Create figure with specific layout - three panels
    fig = plt.figure(figsize=(20, 10))
    
    # Create gridspec for layout: legend on top, three plots below
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 4], width_ratios=[1, 1, 1], hspace=0.3, wspace=0.15)
    ax_legend = fig.add_subplot(gs[0, :])  # Legend spans all columns
    ax_0_10 = fig.add_subplot(gs[1, 0])    # Left plot: 0-10 connections
    ax_10_100 = fig.add_subplot(gs[1, 1])  # Middle plot: 10-100 connections
    ax_100_1000 = fig.add_subplot(gs[1, 2]) # Right plot: 100-1000 connections
    
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
        
        # Filter and plot for each range
        for range_type, ax in [('0-10', ax_0_10), ('10-100', ax_10_100), ('100-1000', ax_100_1000)]:
            filtered_df = filter_data_points(increasing_df, range_type)
            
            # Plot candlesticks for filtered data
            for _, row in filtered_df.iterrows():
                conn = row['connections']
                
                # Candlestick components
                low = row['min_ms']
                q1 = row['q1_ms']
                median = row['median_ms']
                q3 = row['q3_ms']
                high = row['max_ms']
                
                # Adjust width based on range
                if range_type == '0-10':
                    box_width = 0.3
                elif range_type == '10-100':
                    box_width = 3
                else:  # 100-1000
                    box_width = 30
                
                # Offset for multiple versions
                offset = (idx - n_versions/2 + 0.5) * box_width * 0.8 / n_versions
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
            
            # Plot regression line only on the 100-1000 panel
            x_reg = np.array([100, 1000])
            y_reg = slope * x_reg + intercept
            ax_100_1000.plot(x_reg, y_reg, color=color, linewidth=2, alpha=0.5, linestyle='--')
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
    
    # Customize 0-10 plot
    ax_0_10.set_xlabel('Number of Connections', fontsize=12)
    ax_0_10.set_ylabel('Latency (ms)', fontsize=12)
    ax_0_10.set_title('0-10 Connections', fontsize=13, fontweight='bold', pad=10)
    ax_0_10.grid(True, alpha=0.3, linestyle='--', zorder=1)
    ax_0_10.set_xlim(-0.5, 10.5)
    ax_0_10.set_xticks(range(0, 11))
    
    # Customize 10-100 plot
    ax_10_100.set_xlabel('Number of Connections', fontsize=12)
    ax_10_100.set_ylabel('Latency (ms)', fontsize=12)
    ax_10_100.set_title('10-100 Connections', fontsize=13, fontweight='bold', pad=10)
    ax_10_100.grid(True, alpha=0.3, linestyle='--', zorder=1)
    ax_10_100.set_xlim(5, 105)
    ax_10_100.set_xticks(range(10, 101, 10))
    
    # Customize 100-1000 plot
    ax_100_1000.set_xlabel('Number of Connections', fontsize=12)
    ax_100_1000.set_ylabel('Latency (ms)', fontsize=12)
    ax_100_1000.set_title('100-1000 Connections', fontsize=13, fontweight='bold', pad=10)
    ax_100_1000.grid(True, alpha=0.3, linestyle='--', zorder=1)
    ax_100_1000.set_xlim(50, 1050)
    ax_100_1000.set_xticks(range(100, 1001, 100))
    
    # Add explanation text to first panel
    ax_0_10.text(0.02, 0.98, 'All data\npoints shown',
                transform=ax_0_10.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                fontsize=8)
    
    # Add explanation text to middle panel
    ax_10_100.text(0.02, 0.98, 'Every 10th\nconnection',
                transform=ax_10_100.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                fontsize=8)
    
    # Add regression note to right panel
    ax_100_1000.text(0.02, 0.98, 'Every 100th\nconnection\n+ regression',
                transform=ax_100_1000.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5),
                fontsize=8)
    
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

if __name__ == "__main__":
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'candlestick_comparison.png'
        plot_candlestick_comparison(csv_file, output_file)
    else:
        plot_candlestick_comparison()
        
    # Also generate version pair plots
    df = pd.read_csv('benchmark_results.csv')
    versions = []
    for version in df['version']:
        if version not in versions:
            versions.append(version)
    
    print("\nGenerating consecutive version pair plots...")
    for i in range(len(versions) - 1):
        version1 = versions[i]
        version2 = versions[i + 1]
        pair_output_file = f"candlestick_comparison-{i+1}.png"
        
        print(f"Plotting {version1} vs {version2}...")
        plot_version_pair(df, version1, version2, pair_output_file)
        print(f"  Saved to {pair_output_file}")