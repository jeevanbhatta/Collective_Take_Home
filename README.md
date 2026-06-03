# Automated Reconciliation Dashboard

This repository provides a tool to reconcile expected daily running balances (from a transactions ledger) against externally reported daily bank balances.

## Approach
When a balance discrepancy occurs on a given day, subsequent days will also show a mismatch if the error is not corrected. A standard comparison script would flag all subsequent days as errors, creating noise.

This engine calculates the **New Discrepancy Amount**. It isolates the specific day a mathematical divergence is introduced, ignoring days where a previous error simply carried over. This helps accountants pinpoint the exact date an error occurred without having to filter through carry-over variances.

---

## Setup & Execution

### Prerequisites
* Python 3.10+
* Unix-based OS (macOS/Linux) or WSL

### Commands (via Makefile)

**1. Install Dependencies**
Sets up the virtual environment and installs required packages (pandas, matplotlib, streamlit, plotly).
```bash
make install
```

**2. Launch the Web Application**
Starts the local Streamlit dashboard. You can upload custom CSV files through the web interface.
```bash
make run
```

**3. Run Tests**
Executes the test suite for the core reconciliation logic, including edge cases like missing days and floating point precision.
```bash
make test
```

**4. Package for Submission**
Cleans up temporary files and builds the final zip file.
```bash
make package
```
