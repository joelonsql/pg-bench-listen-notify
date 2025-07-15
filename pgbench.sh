#!/bin/sh

# Function to run benchmarks for all versions in randomized order
run_benchmarks() {
    # Define version parameters
    local versions=("master" "patch-v1" "patch-v2")
    local output_files=("master" "optimize_listen_notify" "optimize_listen_notify_v2")

    # Define benchmark parameters
    local sql_scripts=(
        "listen_notify_common.sql"
        "listen_notify_unique.sql"
        "listen_unlisten_common.sql"
        "listen_unlisten_unique.sql"
        "listen_common.sql"
        "listen_unique.sql"
    )

    local runs=(1 2 3 4 5)
    local job_counts=(1 2 4 8 16 32)

    # Generate all combinations
    local combinations=()
    
    # Copy the exact nested for loops to generate all combinations
    for run in "${runs[@]}"; do
        for i in "${!versions[@]}"; do
            local version="${versions[$i]}"
            local output_file="${output_files[$i]}"
            
            for script in "${sql_scripts[@]}"; do
                for jobs in "${job_counts[@]}"; do
                    # Clients can be either equal to jobs or set to 1000
                    for clients in "$jobs" 1000; do
                        combinations+=("$run|$i|$script|$jobs|$clients")
                    done
                done
            done
        done
    done
    
    # Randomize the combinations array using sort -R (available on macOS)
    local randomized_combinations=($(printf '%s\n' "${combinations[@]}" | sort -R))
    
    echo "Generated ${#combinations[@]} total benchmark combinations"
    echo ""
    echo "Randomized execution order:"
    echo "Format: run|version_index|script|jobs|clients"
    echo "----------------------------------------"
    local counter=1
    for combo in "${randomized_combinations[@]}"; do
        IFS='|' read -r run version_index script jobs clients <<< "$combo"
        local version="${versions[$version_index]}"
        printf "%3d: %s|%s|%s|%s|%s\n" "$counter" "$run" "$version" "$script" "$jobs" "$clients"
        counter=$((counter + 1))
    done
    echo "----------------------------------------"
    echo ""
    echo "Starting benchmark execution..."
    
    # Execute each combination in random order
    local current_version=""
    local current_pgdata=""
    local current_pg_ctl=""
    local port="54321"
    local dbname="bench_listen_notify"
    
    for combination in "${randomized_combinations[@]}"; do
        # Parse the combination
        IFS='|' read -r run version_index script jobs clients <<< "$combination"
        
        local version="${versions[$version_index]}"
        local output_file="${output_files[$version_index]}"
        
        # Set absolute paths for PostgreSQL commands
        local pg_ctl="$HOME/pg-$version/bin/pg_ctl"
        local pgbench="$HOME/pg-$version/bin/pgbench"
        local createdb="$HOME/pg-$version/bin/createdb"
        local dropdb="$HOME/pg-$version/bin/dropdb"
        local psql="$HOME/pg-$version/bin/psql"
        local pg_isready="$HOME/pg-$version/bin/pg_isready"
        local pgdata="$HOME/pg-$version-data"
        
        # Stop previous PostgreSQL if we're switching versions
        if [ "$current_version" != "" ] && [ "$current_version" != "$version" ]; then
            echo "Switching from $current_version to $version, stopping previous PostgreSQL..."
            $current_pg_ctl -D "$current_pgdata" -o "-p $port" stop
            if [ $? -ne 0 ]; then
                echo "Error: pg_ctl stop failed for version $current_version"
                exit 1
            fi
            
            # Wait for the server to completely shut down
            echo "Waiting for PostgreSQL to completely shut down..."
            while lsof -i :$port -sTCP:LISTEN > /dev/null 2>&1; do
                echo "Still waiting for port $port to be free..."
                sleep 1
            done
            echo "PostgreSQL has completely shut down"
            
            current_version=""
        fi
        
        # Start PostgreSQL if not already running for this version
        if [ "$current_version" != "$version" ]; then
            echo "Starting PostgreSQL for version $version"
            echo "Using pg_ctl: $pg_ctl"
            echo "Using pgdata: $pgdata"

            # Wait for the port to be free
            echo "Waiting for port $port to be free..."
            while lsof -i :$port -sTCP:LISTEN > /dev/null 2>&1; do
                sleep 0.1
            done
            echo "Port $port is now free"
            
            # Add a small delay to ensure clean startup
            sleep 1

            echo "Starting PostgreSQL server..."
            $pg_ctl -D "$pgdata" -l /tmp/pg-$version.log -o "-p $port" start
            if [ $? -ne 0 ]; then
                echo "Error: pg_ctl start failed for version $version"
                echo "Log output:"
                tail -20 /tmp/pg-$version.log
                exit 1
            fi

            # Wait for PostgreSQL to start
            echo "Waiting for PostgreSQL to be ready..."
            while ! $pg_isready -p "$port" > /dev/null 2>&1; do
                sleep 0.1
            done
            echo "PostgreSQL is ready to accept connections"

            # Setup database for this version
            $dropdb -p "$port" "$dbname" > /dev/null 2>&1 || true  # Ignore errors if DB doesn't exist
            $createdb -p "$port" "$dbname" > /dev/null 2>&1
            $pgbench -p "$port" -d "$dbname" -i
            
            current_version="$version"
            current_pgdata="$pgdata"
            current_pg_ctl="$pg_ctl"
        fi
        
        # Run the benchmark
        local script_name="${script%.sql}"  # Remove .sql extension
        local output_path="results/${script_name}-c-$(printf "%04d" $clients)-j-$(printf "%04d" $jobs)-${output_file}-${run}.txt"

        echo "Running version $version: $script with $clients clients and $jobs jobs (run $run)"
        caffeinate -dims $pgbench -p "$port" -d "$dbname" -f "$script" -c "$clients" -j "$jobs" -T 3 -n > "$output_path"

        # Check if the command failed
        if [ $? -ne 0 ]; then
            echo "Error running benchmark for $script with $clients clients and $jobs jobs"
            return 1
        fi
    done
    
    # Stop the final PostgreSQL instance
    if [ "$current_version" != "" ]; then
        echo "Stopping final PostgreSQL instance for version $current_version"
        $current_pg_ctl -D "$current_pgdata" -o "-p $port" stop
        if [ $? -ne 0 ]; then
            echo "Error: pg_ctl stop failed for version $current_version"
            exit 1
        fi
    fi
}

# Run benchmarks for all versions
run_benchmarks
