# Reconciliation Execution & Test Plan

## Overview
This document outlines the architecture, execution plan, and testing criteria for the Reconciliation Assessment.

## 1. Data Ingestion & Parsing
**Task:** Read streams from either direct CSV file paths or bytes streams (via Streamlit uploads).
**Test Focus:**
- Application successfully loads out-of-order date strings and correctly maps types (using `Decimal` for precision).
- Handles grouping overlapping transactions that occur on the exact same date.

## 2. Core Reconciliation Logic & "Noise Reduction"
**Task:** Identify whether the expected running total matches the bank statement.
**Critical Decision:** A standard engine will flag `Expected - Actual != 0`. However, if an error happens on Monday, the variance will carry over to Tuesday, Wednesday, etc. This creates extreme alert fatigue. 
Instead, our engine calculates the `New Discrepancy Amount` (the change in variance between two days). This isolates the exact calendar day where the math drift originated.
**Test Focus:**
- Verify days that carry existing variance but introduce no *new* mathematical drift return `new_discrepancy = 0`.
- Only the "Originating Discrepancy" day should log a non-zero alert.

## 3. Edge Case Handling
**Task:** Accommodate irregular financial edge cases.
**Test Focus:**
- **Missing Dates (Weekends):** Transactions occur on Sat/Sun, but bank only reports on Friday and Monday. The script must explicitly iterate through blind spots, carrying balances over cleanly.
- **Precision:** $0.10 + $0.20 must strictly equal $0.30 (no standard default float behavior like `0.30000004`).
- **Out of Order Data:** System is agnostic to row ordering inside the CSV.

## 4. Reporting & Visualization (Web Dashboard)
**Task:** Provide accountants with an easy-to-read, zero-code interface.
**Execution:** We implemented a Python `Streamlit` application. 
- It isolates the underlying Core Engine from the UX. 
- It allows accountants to drag-and-drop CSVs.
- Uses `Plotly` to display an interactive line-chart rendering Expected vs Actual timelines, placing a giant Red 'X' solely on days where a _new_ mismatch is generated.

## 5. Documentation & Packaging
**Task:** Provide peer-review quality commentary and strict execution commands.
**Execution:** 
- A standard Unix `Makefile` abstracts setup processes (`make install`, `make run`, `make test`).
- A `package_submission.sh` script to properly compile the required ZIP file automatically.
