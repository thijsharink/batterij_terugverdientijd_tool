import subprocess
import re
import statistics
import sys
from pathlib import Path

def run_main_and_get_payback_months():
    """
    Runs main.py as a subprocess and extracts the 'Total months' for payback.
    """
    command = [sys.executable, str(Path("main.py")), "--no-visualize"]
    process = subprocess.run(command, capture_output=True, text=True, check=False)

    if process.returncode != 0:
        print(f"Error running main.py: {process.stderr}", file=sys.stderr)
        return None

    # Search for the payback months in the output
    match = re.search(r"Total months: (\d+)", process.stdout)
    if match:
        return int(match.group(1))
    else:
        # If payback not achieved, we might get a different output.
        # Let's check for the 'Payback not achieved' message.
        if "Payback not achieved" in process.stdout:
            print("Warning: Payback not achieved in one of the runs. Returning None for this run.", file=sys.stderr)
            return None
        print(f"Could not find 'Total months' in output: {process.stdout}", file=sys.stderr)
        return None

def main():
    num_runs = 20
    payback_months_list = []

    print(f"Running main.py {num_runs} times to test consistency...")
    for i in range(num_runs):
        print(f"--- Run {i+1}/{num_runs} ---")
        payback_months = run_main_and_get_payback_months()
        if payback_months is not None:
            payback_months_list.append(payback_months)
        print("-" * 20)

    if not payback_months_list:
        print("\nNo successful payback periods recorded to analyze.")
        sys.exit(1)

    print("\n" + "=" * 30)
    print("CONSISTENCY TEST RESULTS")
    print("=" * 30)
    print(f"Successful runs: {len(payback_months_list)}/{num_runs}")
    print(f"All payback months: {payback_months_list}")

    mean_payback = statistics.mean(payback_months_list)
    stdev_payback = statistics.stdev(payback_months_list) if len(payback_months_list) > 1 else 0.0

    print(f"\nMean Payback Time: {mean_payback:.2f} months")
    print(f"Standard Deviation: {stdev_payback:.2f} months")
    print("=" * 30)

if __name__ == "__main__":
    main()
