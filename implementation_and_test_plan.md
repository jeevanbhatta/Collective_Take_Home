# Reconciliation — How I Approached It

This doc walks through my thinking on the architecture, the key decisions, and what I tested.

**Data Ingestion & Parsing** — Reads CSVs from either file paths or in-memory streams (Streamlit gives us byte streams on upload, not file paths). I tested that out-of-order dates get handled correctly, multiple transactions on the same day get summed together, and all money values go through `Decimal` to avoid float precision issues.

**The "New Discrepancy" Idea** — A naive comparison flags `Expected - Actual != 0` for every day. But if an error happens on Monday, Tuesday through Friday will all show mismatches too — even though nothing new went wrong. That's a lot of noise for an accounting team. So I track the *change* in discrepancy between consecutive days. If today's gap is the same as yesterday's, the `new_discrepancy` is 0 — meaning the error is just carrying forward. Only the day where the gap actually *grew* gets flagged. I tested that carry-over days return `new_discrepancy = 0`, only the originating day gets a non-zero alert, and the mismatch sample data correctly identifies two separate error origins.

**Edge Cases** — Missing dates (weekends/holidays): bank doesn't report on Sat/Sun, but transactions still happen. I iterate through every calendar day and carry balances forward so the timeline stays continuous. Float precision: `$0.10 + $0.20` must equal `$0.30`, not `$0.30000000000000004`. Using `Decimal` handles this. Out-of-order data: CSVs aren't always sorted. The engine doesn't assume they are.

**Dashboard** — I went with Streamlit because it lets me wrap the Python engine in a web UI without writing frontend code. Accountants can upload their own CSVs and see results immediately. It shows summary metrics (how many days checked, how many originating errors, final outstanding gap), an interactive line chart (expected vs actual, with red X markers on error-origin days), and an action table listing only the days that need investigation.

**Packaging** — `Makefile` handles setup (`make install`), running (`make run`), and testing (`make test`). `package_submission.sh` builds the submission zip. Dependencies are pinned in `requirements.txt`.
