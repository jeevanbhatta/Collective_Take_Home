# Automated Reconciliation Dashboard

This tool reconciles expected daily running balances (from a transactions ledger) against externally reported bank balances.

## The Idea
When a balance discrepancy happens on a given day, every day after it will also show a mismatch — even if nothing new went wrong. A basic comparison would flag all of those as errors, which creates a lot of noise.

Instead, this engine calculates the **New Discrepancy Amount**. It isolates the specific day a divergence was introduced, so the accounting team can go straight to the source of the problem without wading through carry-over noise.

## Sample Data
The repo includes two sets of sample data:
- `sample_provided_*` — the original data from the prompt (reconciles cleanly)
- `sample_mismatch_*` — same transactions, but with two deliberate bank errors ($50 gap on 06-03, additional $5 gap on 06-10) to demonstrate discrepancy isolation

The dashboard defaults to the mismatch data so you can see the feature in action.

---

## Setup & Execution

### Prerequisites
* Python 3.10+
* Unix-based OS (macOS/Linux) or WSL

### Commands (via Makefile)

**1. Install Dependencies**
Sets up the virtual environment and installs required packages.
```bash
make install
```

**2. Launch the Web Application**
Starts the local Streamlit dashboard. You can upload custom CSV files through the web interface.
```bash
make run
```

**3. Run Tests**
Runs the test suite, including edge cases like missing days, floating point precision, and discrepancy isolation.
```bash
make test
```

**4. Package for Submission**
Cleans up temp files and builds the final zip.
```bash
make package
```
