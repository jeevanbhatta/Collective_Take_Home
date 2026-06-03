"""
Reconciliation Web Dashboard (Streamlit UI)

The prompt requests: "...whatever you think would be useful for accountants... 
or a lightweight web app." 

Streamlit was selected to accomplish this because it allows us to deploy a reactive 
dashboard with zero front-end boilerplate, directly wrapping our core Python calculations.
It enables accountants to upload CSVs directly, and visualize the findings via interactive Plotly charts.
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

**Approach:** Rather than alerting on every day a rolling balance is mismatched, this engine computes the **New Discrepancy Amount**. This isolates the specific day a mismatch originated, reducing noise from carry-over errors.
""")

# ---- SIDEBAR: FILE UPLOADS ----
st.sidebar.header("Upload Files")
st.sidebar.markdown("Upload your CSVs here. If nothing is uploaded, we'll use the sample data.")

tx_file = st.sidebar.file_uploader("Transactions CSV", type=['csv'])
bb_file = st.sidebar.file_uploader("Bank Balances CSV", type=['csv'])

# Use uploaded files or fallback to the local sample files
tx_source = tx_file if tx_file is not None else "data/sample_provided_tx.csv"
bb_source = bb_file if bb_file is not None else "data/sample_provided_bb.csv"

# ---- RUN LOGIC (De-coupled from UI) ----
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

# ---- METRICS ----
# Filter exclusively for the originating days to reduce noise
origin_discrepancies = df[df['new_discrepancy'].abs() > 0.001].copy()

total_days_checked = len(df)
number_of_bad_days = len(origin_discrepancies)
final_gap = df['cumulative_discrepancy'].iloc[-1] if 'cumulative_discrepancy' in df.columns else 0

st.markdown("---")
col1, col2, col3 = st.columns(3)
col1.metric("Total Days Reconciled", total_days_checked)
col2.metric("Originating Discrepancies", number_of_bad_days, help="Days where a BRAND NEW math discrepancy occurred.")

delta_text = "Urgent Action Required" if abs(final_gap) > 0.01 else "All Good"
delta_color_option = "inverse" if abs(final_gap) > 0.01 else "normal"

col3.metric("Final Outstanding Gap", f"${final_gap:,.2f}", 
            delta=delta_text, 
            delta_color=delta_color_option)

# ---- VISUALIZATION ----
st.markdown("### Expected vs Actual Balance Trend")
st.markdown("Notice how a single discrepancy causes the two lines to diverge permanently unless corrected. (Hover over points for details).")

# Interactive graph showing the continuous trend against the reported milestones
fig = go.Figure()

# Expected Line (Internal Ledger calculations)
fig.add_trace(go.Scatter(
    x=df['date'], y=df['expected_balance'],
    mode='lines+markers',
    name='Expected (Internal Ledger)',
    line=dict(color='blue')
))

# Actual Line (Bank Report)
fig.add_trace(go.Scatter(
    x=df['date'], y=df['actual_balance'],
    mode='lines+markers',
    name='Actual (Bank Report)',
    line=dict(color='orange', dash='dot')
))

# Specifically highlight the exact coordinates where the math broke down
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
    st.error(f"Action required on {number_of_bad_days} specific days. Please investigate your logs for these dates.")
    
    display_df = origin_discrepancies[['date', 'transaction_total', 'expected_balance', 'actual_balance', 'new_discrepancy']].copy()
    
    # Format currency logic strictly for front-end presentation 
    display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
    for col in ['transaction_total', 'expected_balance', 'actual_balance', 'new_discrepancy']:
        display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "N/A")
    
    display_df.columns = ['Date', 'Internal Daily Sum', 'Expected Bank Bal', 'Actual Bank Bal', 'New Variance Amount']
    st.table(display_df)

st.markdown("---")
st.caption("Powered by Python and Streamlit. Developed by Jeevan Bhatta for Collective's Take-Home Assignment.")
