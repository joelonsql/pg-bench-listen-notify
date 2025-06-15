#!/usr/bin/env python3
"""
Analyze PostgreSQL LISTEN/NOTIFY scaling behavior to determine if it's O(N) or O(1)
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

    print("PostgreSQL LISTEN/NOTIFY Scaling Analysis (connections >= 100)")
    print("=" * 80)
    print()

    results = []

    for version in versions:
        # Filter for this version and connections >= 100
        version_df = df[(df['version'] == version) & (df['connections'] >= 100)].copy()

        if len(version_df) < 3:
            print(f"Insufficient data for {version}")
            continue

        # Perform linear regression on median latency
        x = version_df['connections'].values
        y = version_df['median_ms'].values

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        r_squared = r_value ** 2

        # Calculate mean for O(1) comparison
        mean_latency = np.mean(y)

        # Determine if it's O(N) or O(1) based on slope
        slope_us = slope * 1000  # Convert to microseconds
        stddev = np.std(y)
        cv = stddev / mean_latency  # Coefficient of variation

        # Simple criteria: if slope < 0.1 μs per connection, it's O(1)
        # This means latency increases by less than 0.1 ms per 1000 connections
        is_o1 = abs(slope_us) < 0.1

        if is_o1:
            complexity = "O(1)"
            formula = f"≈ {mean_latency:.3f} ms (constant)"
        else:
            complexity = "O(N)"
            formula = f"{intercept:.3f} + {slope_us:.3f}×10⁻³ × N ms"

        # Store results
        result = {
            'version': version,
            'complexity': complexity,
            'slope_us': slope_us,
            'intercept': intercept,
            'mean_latency': mean_latency,
            'r_squared': r_squared,
            'cv': cv,
            'formula': formula
        }
        results.append(result)

        # Print detailed analysis
        print(f"Version: {version}")
        print(f"  Complexity: {complexity}")
        print(f"  Latency formula: {formula}")
        print(f"  Mean latency: {mean_latency:.3f} ms ± {stddev:.3f} ms")
        print(f"  Coefficient of variation: {cv:.1%}")
        print(f"  R² value: {r_squared:.4f}")
        print(f"  Slope: {slope_us:.3f} μs/connection")
        print(f"  Data points: {len(version_df)}")
        print()

    # Summary table
    print("\nSummary Table")
    print("-" * 80)
    print(f"{'Version':<35} {'Complexity':<10} {'Formula':<40}")
    print("-" * 80)

    for result in results:
        version_short = result['version'].split('(')[0].strip()
        if len(version_short) > 35:
            version_short = version_short[:32] + "..."
        print(f"{version_short:<35} {result['complexity']:<10} {result['formula']:<40}")

    print("-" * 80)

    # Group by complexity
    o1_versions = [r for r in results if r['complexity'] == 'O(1)']
    on_versions = [r for r in results if r['complexity'] == 'O(N)']

    print(f"\nO(1) scaling (constant time): {len(o1_versions)} versions")
    print(f"O(N) scaling (linear with connections): {len(on_versions)} versions")

    if o1_versions:
        print("\nO(1) versions (excellent scaling):")
        for r in o1_versions:
            print(f"  - {r['version'].split('(')[0].strip()}: {r['mean_latency']:.3f} ms average")

    if on_versions:
        print("\nO(N) versions (latency increases with connections):")
        for r in on_versions:
            print(f"  - {r['version'].split('(')[0].strip()}: {r['slope_us']:.1f} μs per connection")

if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'benchmark_results.csv'
    analyze_scaling(csv_file)