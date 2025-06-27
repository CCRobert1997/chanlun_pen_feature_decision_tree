from flask import Flask, render_template, request, jsonify, send_from_directory, make_response
import pandas as pd
import os
import time
import re

data_folder = "ermai_caozuo"
plot_folder = "sanmaiplot"
valid_prefixes = [
    "NVDA_NASDAQ", "AMZN_NASDAQ", "META_NASDAQ", "MSFT_NASDAQ",
    "SNOW_NYSE", "TIGR_NASDAQ", "TSLA_NASDAQ", "U_NYSE",
    "AVGO_NASDAQ", "AAPL_NASDAQ", "LLY_NYSE", "NVO_NYSE",
    "ADBE_NASDAQ", "TSM_NYSE", "PFE_NYSE", "JPM_NYSE",
    "BAC_NYSE", "COST_NASDAQ", "NFLX_NASDAQ"
]
time_intervals = ["6_second", "24_second", "60_second"]

app = Flask(__name__, static_folder="sanmaiplot")
latest_entry_timestamps = {}

def load_data():
    stock_data = {}
    global latest_entry_timestamps
    current_time = time.time()

    for prefix in valid_prefixes:
        stock_data[prefix] = {}
        for interval in time_intervals:
            file_name = f"{prefix}_{interval}_ermai_caozuo.csv"
            file_path = os.path.join(data_folder, file_name)
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)

                stock_data[prefix][interval] = df.values.tolist()[-4:]  # 只保留最近四条记录
                for row in stock_data[prefix][interval]:
                    entry_key = (prefix, interval, row[2])
                    if entry_key not in latest_entry_timestamps:
                        latest_entry_timestamps[entry_key] = current_time  # 记录每条数据的时间戳
            else:
                stock_data[prefix][interval] = []

    return stock_data

def get_latest_plot(stock, interval):
    """ 获取某个股票和时间级别的所有可用图片 """
    pattern = re.compile(rf"^\d+_\d+_{stock}_{interval}_.+\.png$")
    images = sorted(
        [f for f in os.listdir(plot_folder) if pattern.match(f)],
        key=lambda x: int(re.search(r"^\d+_\d+", x).group()),
        reverse=True
    )
    return images

@app.route('/')
def index():
    data = load_data()
    return render_template('index.html', data=data, time_intervals=time_intervals,
                           latest_entry_timestamps=latest_entry_timestamps, current_time=time.time())

@app.route('/get_latest_plot', methods=['GET'])
def get_plot():
    stock = request.args.get('stock')
    interval = request.args.get('interval')
    images = get_latest_plot(stock, interval)
    return jsonify({'images': images})

@app.route('/sanmaiplot/<path:filename>')
def serve_plot(filename):
    response = make_response(send_from_directory(plot_folder, filename))
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7010)
