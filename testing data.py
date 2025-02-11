import pandas as pd
import requests
from flask import Flask, request, render_template
from datetime import datetime

app = Flask(__name__)

# Define shift time ranges (relative to the selected date)
SHIFT_TIMES = {
    "day_shift": {"start": "00:00:01", "end": "15:00:00"},
    "night_shift": {"start": "15:00:01", "end": "22:29:59"},
    "full_day": {"start": "00:00:01", "end": "23:59:59"}  # Default
}

def fetch_test_data(selected_date):
    """Fetch full-day test data from API for the given date."""
    url = 'http://10.16.137.77:9900/tst/nvda/fct/getrecords/'
    
    # Construct full-day range for the selected date
    full_day_start = f"{selected_date} 00:00:01"
    full_day_end = f"{selected_date} 23:59:59"
    respond_time = {"start": full_day_start, "end": full_day_end}

    try:
        response = requests.post(url, json=respond_time)
        if response.status_code == 200:
            print(f"✅ API Request Successful for date: {selected_date}")  # Debugging
            return pd.DataFrame(response.json().get('fct_sfc_records', []))
    except Exception as e:
        print("❌ API Error:", e)
    return pd.DataFrame()

# def fetch_avi_data()

@app.route("/", methods=["GET", "POST"])
def index():
    table_html = ""
    product_name = ""
    selected_date = datetime.today().strftime('%Y-%m-%d')  # Default to today
    shift = "full_day"  # Default to full-day

    if request.method == "POST":
        product_name = request.form.get("product_name", "")
        shift = request.form.get("shift", "full_day")
        selected_date = request.form.get("date", selected_date)  # Default to today's date if not selected
        
        print(f"🔍 User Entered Product: {product_name}, Date: {selected_date}, Shift: {shift}")  # ✅ Debugging

        df = fetch_test_data(selected_date)
        print("📊 Fetched Data (First 5 Rows):\n", df.head())  # ✅ Debugging

        if not df.empty:
            # Convert START_TIME to datetime
            df['START_TIME'] = pd.to_datetime(df['START_TIME'], errors='coerce')

            # Get shift time range
            shift_time = SHIFT_TIMES[shift]
            start_time = pd.to_datetime(f"{selected_date} {shift_time['start']}")
            end_time = pd.to_datetime(f"{selected_date} {shift_time['end']}")

            # Filter data by date and shift time
            df_filtered = df[(df['START_TIME'] >= start_time) & (df['START_TIME'] <= end_time)]
            print("🎯 Filtered Data (First 5 Rows):\n", df_filtered.head())  # ✅ Debugging

            # Filter data by product name
            df_filtered = df_filtered[df_filtered['NVPN'].str.contains(product_name, na=False, case=False)]

            # Process the original output
            df_pbr = df_filtered.groupby('NVPBR')['NVSN'].nunique().reset_index()
            df_pbr = df_pbr.rename(columns={'NVPBR': 'PB Number', 'NVSN': 'Test Actual'})
            print("📊 Processed Data (First 5 Rows):\n", df_pbr.head())  # ✅ Debugging

            # Compute unique failure count
            df_failures = df_filtered[df_filtered['RESULT'] == 'FAIL']
            df_failures = df_failures.drop_duplicates(subset=['NVSN']).groupby('NVPBR')['NVSN'].nunique().reset_index()
            df_failures = df_failures.rename(columns={'NVPBR': 'PB Number', 'NVSN': 'Failures'})

            # Merge with left join
            df_merged = df_pbr.merge(df_failures, on='PB Number', how='left')
            df_merged['Failures'] = df_merged['Failures'].fillna(0).astype(int)  # Replace NaN with 0

            print("✅ Final Merged Data:\n", df_merged.head())  # ✅ Debugging

            table_html = df_merged.to_html(classes="table", index=False)

    return render_template(
        "index.html", 
        table_html=table_html, 
        product_name=product_name, 
        selected_date=selected_date, 
        shift=shift
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

