#!/usr/bin/env python3
"""
Parse pgbench result files and convert them to CSV format.
"""

import os
import re
import csv
import glob
from pathlib import Path

def parse_pgbench_file(filepath):
    """Parse a single pgbench result file and extract metrics."""
    data = {}

    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Extract filename components
        filename = Path(filepath).stem
        parts = filename.split('-')

        if len(parts) >= 6:
            # Find where the test type ends (before 'c')
            c_index = None
            for i, part in enumerate(parts):
                if part == 'c' and i + 1 < len(parts) and parts[i + 1].isdigit():
                    c_index = i
                    break

            if c_index is not None:
                data['test_type'] = '_'.join(parts[:c_index])
                data['clients'] = int(parts[c_index + 1])
                data['jobs'] = int(parts[c_index + 3])  # Skip 'j' at c_index + 2

                # Check if there's a threshold parameter (starts with 't' followed by digits)
                t_index = c_index + 4  # Position after j-{jobs}
                if t_index < len(parts) and parts[t_index] == 't' and t_index + 1 < len(parts) and parts[t_index + 1].isdigit():
                    # New format with threshold
                    data['threshold'] = int(parts[t_index + 1])
                    data['version'] = '-'.join(parts[t_index + 2:-1])
                else:
                    # Old format without threshold
                    data['threshold'] = None  # or 'default' if you prefer
                    data['version'] = '-'.join(parts[c_index + 4:-1])

                data['run_number'] = int(parts[-1])
            else:
                # Fallback if c_index not found
                data['test_type'] = filename
                data['clients'] = None
                data['jobs'] = None
                data['threshold'] = None
                data['version'] = 'unknown'
                data['run_number'] = None
        else:
            # Handle files with fewer parts
            data['test_type'] = filename
            data['clients'] = None
            data['jobs'] = None
            data['threshold'] = None
            data['version'] = 'unknown'
            data['run_number'] = None

        # Parse pgbench output using regex
        patterns = {
            'scaling_factor': r'scaling factor: (\d+)',
            'num_clients': r'number of clients: (\d+)',
            'num_threads': r'number of threads: (\d+)',
            'duration': r'duration: (\d+) s',
            'transactions_processed': r'number of transactions actually processed: (\d+)',
            'failed_transactions': r'number of failed transactions: (\d+)',
            'latency_avg': r'latency average = ([\d.]+) ms',
            'initial_connection_time': r'initial connection time = ([\d.]+) ms',
            'tps': r'tps = ([\d.]+) \(without initial connection time\)'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                if key in ['scaling_factor', 'num_clients', 'num_threads', 'duration', 'transactions_processed', 'failed_transactions']:
                    data[key] = int(match.group(1))
                else:
                    data[key] = float(match.group(1))
            else:
                data[key] = None

        # Extract transaction type
        tx_type_match = re.search(r'transaction type: (.+)', content)
        if tx_type_match:
            data['transaction_type'] = tx_type_match.group(1)

        return data

    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None

def main():
    """Main function to process all pgbench result files."""
    results_dir = './results'

    if not os.path.exists(results_dir):
        print(f"Results directory {results_dir} not found!")
        return

    # Get all .txt files in results directory
    txt_files = glob.glob(os.path.join(results_dir, '*.txt'))

    if not txt_files:
        print("No .txt files found in results directory!")
        return

    print(f"Found {len(txt_files)} result files to process...")

    # Process each file
    all_data = []
    for txt_file in txt_files:
        print(f"Processing {txt_file}...")
        data = parse_pgbench_file(txt_file)
        if data:
            all_data.append(data)

    if not all_data:
        print("No data extracted from files!")
        return

    # Create CSV for each individual file
    for txt_file in txt_files:
        data = parse_pgbench_file(txt_file)
        if data:
            csv_filename = txt_file.replace('.txt', '.csv')
            with open(csv_filename, 'w', newline='') as csvfile:
                fieldnames = list(data.keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(data)
            print(f"Created {csv_filename}")

    # Create a combined CSV file
    combined_csv = 'pgbench_results_combined.csv'
    if all_data:
        fieldnames = set()
        for data in all_data:
            fieldnames.update(data.keys())
        fieldnames = sorted(list(fieldnames))

        with open(combined_csv, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_data)
        print(f"Created combined CSV file: {combined_csv}")

    print(f"Successfully processed {len(all_data)} files")

if __name__ == '__main__':
    main() 