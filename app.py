"""
Reconciliation Dashboard (Streamlit)

I went with Streamlit here because it lets me wrap the Python reconciliation
logic in a reactive web UI without writing any frontend code. Accountants
can drag-and-drop their CSVs and immediately see where things went wrong.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from reconciler import reconcile

st.set_page_config(page_title="Recon Engine", layout="wide")

# ---- HEADER ----
st.title("Recon Engine")
st.markdown("""
Welcome to the reconciliation dashboard. 
This tool compares internal transaction ledgers against bank statements. 

**How it works:** Instead of flagging every day after an error (which just creates noise), 
this engine computes the **New Discrepancy Amount** — isolating the specific day a 
mismatch first appeared.
""")

# ---- SIDEBAR: FILE UPLOADS ----
st.sidebar.header("Upload Files")
st.sidebar.markdown("Upload your CSVs here. If nothing is uploaded, we'll use the mismatch sample data to demo the discrepancy detection.")

tx_file = st.sidebar.file_uploader("Transactions CSV", type=['csv'])
bb_file = st.sidebar.file_uploader("Bank Balances CSV", type=['csv'])

# Default to the mismatch sample so the demo actually shows something interesting
tx_source = tx_file if tx_file is not None else "data/sample_mismatch_tx.csv"
bb_source = bb_file if bb_file is not None else "data/sample_mismatch_bb.csv"

# ---- RUN THE ENGINE ----
try:
    results_list = reconcile(tx_source, bb_source)
    df = pd.DataFrame(results_list)
    df['date'] = pd.to_datetime(df['date'])
except Exception as e:
    st.error(f"Error parsing files: {e}")
    st.stop()

if df.empty:
    st.warning("No data found in the files.")
    st.stop()

# ---- SUMMARY METRICS ----
# Only count days where a genuinely new discrepancy appeared (not carry-over noise).
# Using 0.001 as threshold to avoid floating point dust after Decimal->float conversion.
origin_discrepancies = df[df['new_discrepancy'].abs() > 0.001].copy()

total_days_checked = len(df)
number_of_bad_days = len(origin_discrepancies)
final_gap = df['cumulative_discrepancy'].fillna(0).iloc[-1]

st.markdown("---")
col1, col2, col3 = st.columns(3)
col1.metric("Total Days Reconciled", total_days_checked)
col2.metric("Originating Discrepancies", number_of_bad_days, help="Days where a brand new math discrepancy appeared (not carry-over).")

delta_text = "Urgent Action Required" if abs(final_gap) > 0.01 else "All Good"
delta_color_option = "inverse" if abs(final_gap) > 0.01 else "normal"

col3.metric("Final Outstanding Gap", f"${final_gap:,.2f}", 
            delta=delta_text, 
            delta_color=delta_color_option)

# ---- CHART ----
st.markdown("### Expected vs Actual Balance Trend")
st.markdown("A single discrepancy causes the two lines to diverge permanently unless corrected. Hover over points for details.")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df['date'], y=df['expected_balance'],
    mode='lines+markers',
    name='Expected (Internal Ledger)',
    line=dict(color='blue')
))

fig.add_trace(go.Scatter(
    x=df['date'], y=df['actual_balance'],
    mode='lines+markers',
    name='Actual (Bank Report)',
    line=dict(color='orange', dash='dot')
))

# Big red X markers on the days where things actually went wrong
if not origin_discrepancies.empty:
    fig.add_trace(go.Scatter(
        x=origin_discrepancies['date'], 
        y=origin_discrepancies['expected_balance'],
        mode='markers',
        name='Mismatch Origin',
        marker=dict(color='red', size=12, symbol='x')
    ))

fig.update_layout(hovermode='x unified', xaxis_title="Date", yaxis_title="Balance Amount ($)", height=500)
st.plotly_chart(fig, use_container_width=True)

# ---- ACTION TABLE ----
st.markdown("### Required Accounting Interventions")
if origin_discrepancies.empty:
    st.success("All balances line up perfectly. No new discrepancies found.")
else:
    st.error(f"Action required on {number_of_bad_days} specific days. Investigate your logs for these dates.")
    
    display_df = origin_discrepancies[['date', 'transaction_total', 'expected_balance', 'actual_balance', 'new_discrepancy']].copy()
    
    # Format for display only
    display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
    for col in ['transaction_total', 'expected_balance', 'actual_balance', 'new_discrepancy']:
        display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "N/A")
    
    display_df.columns = ['Date', 'Internal Daily Sum', 'Expected Bank Bal', 'Actual Bank Bal', 'New Variance Amount']
    st.table(display_df)

st.markdown("---")
st.caption("Powered by Python and Streamlit. Developed by Jeevan Bhatta for Collective's Take-Home Assignment.")
