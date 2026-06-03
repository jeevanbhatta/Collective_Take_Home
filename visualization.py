import os
import pandas as pd
import matplotlib.pyplot as plt

def generate_visualization(transactions_csv, bank_balances_csv, output_folder="visualizations"):
    """
    Generates visualizations of expected vs actual balances and an HTML report.
    """
    os.makedirs(output_folder, exist_ok=True)
    
    # 1. Load data
    df_tx = pd.read_csv(transactions_csv, parse_dates=['date'])
    df_bb = pd.read_csv(bank_balances_csv, parse_dates=['date'])

    # 2. Daily aggregate and running cumulative sum
    df_tx_daily = df_tx.groupby('date')['amount'].sum().reset_index()
    df_tx_daily['expected_balance'] = df_tx_daily['amount'].cumsum()

    # 3. Merge data streams on date
    df_merged = pd.merge(df_bb, df_tx_daily[['date', 'expected_balance']], on='date', how='outer').sort_values('date')

    # 4. Forward fill expected balances
    df_merged['expected_balance'] = df_merged['expected_balance'].ffill()
    
    # 5. Calculate discrepancies
    df_merged['discrepancy'] = df_merged['expected_balance'] - df_merged['balance']
    
    anomalies = df_merged[df_merged['discrepancy'] != 0].dropna()
    
    # 6. Plot 1: The Trend Line Graph
    plt.figure(figsize=(10, 6))
    plt.plot(df_merged['date'], df_merged['expected_balance'], label='Expected Balance', marker='o')
    plt.plot(df_merged['date'], df_merged['balance'], label='Actual Bank Balance', marker='x', linestyle='--')
    if not anomalies.empty:
        plt.scatter(anomalies['date'], anomalies['expected_balance'], color='red', s=100, label='Discrepancy', zorder=5)
    plt.title('Daily Bank Balance Reconciliation: Expected vs Actual')
    plt.xlabel('Date')
    plt.ylabel('Balance Amount ($)')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    trend_path = os.path.join(output_folder, "reconciliation_trend_chart.png")
    plt.savefig(trend_path)
    plt.close()

    # 7. Plot 2: Discrepancy Bar Chart
    plt.figure(figsize=(10, 4))
    colors = ['red' if abs(x) > 0.01 else 'green' for x in df_merged['discrepancy']]
    plt.bar(df_merged['date'], df_merged['discrepancy'], color=colors)
    plt.title('Daily Mismatch Amount (Expected - Actual)')
    plt.xlabel('Date')
    plt.ylabel('Discrepancy ($)')
    plt.axhline(0, color='black', linewidth=0.8)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    bar_path = os.path.join(output_folder, "discrepancy_bar_chart.png")
    plt.savefig(bar_path)
    plt.close()

    # 8. HTML Report Generation
    # We create a simple HTML string to make an easy-to-read report
    html_report_path = os.path.join(output_folder, "reconciliation_report.html")
    
    # Format dates nicely for the table
    if not anomalies.empty:
        anomalies_display = anomalies.copy()
        anomalies_display['date'] = anomalies_display['date'].dt.strftime('%Y-%m-%d')
        table_html = anomalies_display[['date', 'expected_balance', 'balance', 'discrepancy']].to_html(index=False, classes='discrepancy-table', border=0)
    else:
        table_html = "<p style='color: green; font-weight: bold;'>All balances reconcile perfectly! No discrepancies found.</p>"

    html_content = f"""
    <html>
    <head>
        <title>Reconciliation Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f9f9f9; }}
            .container {{ background-color: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 1000px; margin: 0 auto; }}
            h1, h2 {{ color: #333; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .img-container {{ margin-bottom: 40px; text-align: center; }}
            img {{ max-width: 100%; height: auto; border: 1px solid #ddd; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Automated Reconciliation Report</h1>
            <p>Generated to highlight discrepancies between the internal transaction ledger and reported bank statements.</p>
            
            <h2>Identified Discrepancies Details</h2>
            {table_html}
            
            <div class="img-container">
                <h2>Reconciliation Trend</h2>
                <img src="reconciliation_trend_chart.png" alt="Trend Chart">
            </div>
            
            <div class="img-container">
                <h2>Daily Variance Amounts</h2>
                <img src="discrepancy_bar_chart.png" alt="Bar Chart">
            </div>
        </div>
    </body>
    </html>
    """
    with open(html_report_path, 'w') as f:
        f.write(html_content)

    print(f"Generated Visualizations and an HTML Report in '{output_folder}/'")

if __name__ == "__main__":
    generate_visualization("transactions.csv", "bank_balances.csv")
