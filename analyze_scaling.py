#!/usr/bin/env python3
"""
Analyze PostgreSQL LISTEN/NOTIFY scaling behavior - linear regression analysis
"""

import pandas as pd
import numpy as np
from scipy import stats
import sys

def analyze_scaling(csv_file='benchmark_results.csv'):
    """Analyze scaling behavior for each PostgreSQL version"""

    # Read the CSV file
    df = pd.read_csv(csv_file)

    # Get unique versions in order they appear
    versions = []
    for version in df['version']:
        if version not in versions:
            versions.append(version)

    print("PostgreSQL LISTEN/NOTIFY Scaling Analysis (all connections)")
    print("=" * 80)
    print()

    results = []

    for version in versions:
        # Filter for this version
        version_df = df[df['version'] == version].copy()

        if len(version_df) < 3:
            print(f"Insufficient data for {version}")
            continue

        # Perform linear regression on median latency
        x = version_df['connections'].values
        y = version_df['median_ms'].values

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        r_squared = r_value ** 2

        # Calculate mean and standard deviation
        mean_latency = np.mean(y)
        stddev = np.std(y)

        # Convert slope to microseconds
        slope_us = slope * 1000  # Convert to microseconds
        cv = stddev / mean_latency  # Coefficient of variation

        # Format the linear formula
        formula = f"{intercept:.3f} + {slope_us:.3f}×10⁻³ × N ms"

        # Store results
        result = {
            'version': version,
            'slope_us': slope_us,
            'intercept': intercept,
            'mean_latency': mean_latency,
            'r_squared': r_squared,
            'cv': cv,
            'formula': formula,
            'stddev': stddev
        }
        results.append(result)

        # Print detailed analysis
        print(f"Version: {version}")
        print(f"  Linear regression: {formula}")
        print(f"  Mean latency: {mean_latency:.3f} ms ± {stddev:.3f} ms")
        print(f"  Coefficient of variation: {cv:.1%}")
        print(f"  R² value: {r_squared:.4f}")
        print(f"  Slope: {slope_us:.3f} μs/connection")
        print(f"  Intercept: {intercept:.3f} ms")
        print(f"  Data points: {len(version_df)}")
        print()

    # Summary table
    print("\nSummary Table")
    print("-" * 100)
    print(f"{'Version':<35} {'Slope (μs/conn)':<18} {'Intercept (ms)':<15} {'R²':<10} {'Formula'}")
    print("-" * 100)

    for result in results:
        version_short = result['version'].split('(')[0].strip()
        if len(version_short) > 35:
            version_short = version_short[:32] + "..."
        print(f"{version_short:<35} {result['slope_us']:>14.3f}     {result['intercept']:>11.3f}     {result['r_squared']:>6.4f}     {result['formula']}")

    print("-" * 100)

if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'benchmark_results.csv'
    analyze_scaling(csv_file)