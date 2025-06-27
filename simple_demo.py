import os
import glob
import joblib
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import matplotlib.pyplot as plt

# 设置数据路径
data_dir = 'data'
pattern = os.path.join(data_dir, 'AAPL_NASDAQ_prices_*.csv')
file_list = glob.glob(pattern)

X_all, y_all = [], []

# 日内处理每个文件
daily_data = {}
for file in file_list:
    df = pd.read_csv(file, parse_dates=['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    prices = df['price'].values

    if len(prices) <= 120:
        continue

    for i in range(len(prices) - 120):
        x = prices[i:i+100]
        base = prices[i+99]
        future = prices[i+120]
        if base == 0:
            continue
        pct_change = (future - base) / base
        label = int(pct_change > 0.01)
        X_all.append(x)
        y_all.append(label)

X_all = np.array(X_all)
y_all = np.array(y_all)

# 模型训练并保存
# model = LogisticRegression(max_iter=1000)
# model.fit(X_all, y_all)
# joblib.dump(model, 'logistic_model.joblib')
from sklearn.ensemble import RandomForestClassifier

model = RandomForestClassifier(
    n_estimators=200,
    max_depth=20,
    min_samples_split=2,
    random_state=42
)
model.fit(X_all, y_all)
joblib.dump(model, 'random_forest_model_daily.joblib')



print("Complete training")

# 回测：日内分文件处理
capital = 1.0
equity_curve = []
daily_returns = []
timestamps_all = []

for file in file_list:
    df = pd.read_csv(file, parse_dates=['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    prices = df['price'].values
    timestamps = df['timestamp'].values

    if len(prices) <= 120:
        continue

    day_capital = capital
    i = 0
    while i < len(prices) - 120:
        x = prices[i:i+100]
        base = prices[i+99]
        if base == 0:
            i += 1
            continue
        x_input = np.array(x).reshape(1, -1)
        pred = model.predict(x_input)[0]

        if pred == 1:
            entry_price = prices[i+99]
            exit_price = prices[i+120]
            ret = (exit_price - entry_price) / entry_price
            day_capital *= (1 + ret)
            daily_returns.append(np.log(1 + ret))
            i += 120  # 持仓期间不重叠
        else:
            i += 1

    equity_curve.append(day_capital)
    capital = day_capital
    timestamps_all.append(timestamps[-1])  # 记录每天最后一个时间戳
    if i == len(prices) - 120:
        daily_returns.append(0.0)

# 回测指标
equity_array = np.array(equity_curve)
peak = np.maximum.accumulate(equity_array)
drawdown = (equity_array - peak) / peak
max_drawdown = drawdown.min()
sharpe_ratio = np.mean(daily_returns) / (np.std(daily_returns) + 1e-8) * np.sqrt(252)

# 生成 DataFrame 供展示
result_df = pd.DataFrame({
    'timestamp': timestamps_all,
    'equity': equity_curve
})

result_df.to_csv('equity_curve_daily.csv', index=False)

# # 只保留日期用于横轴展示
# result_df['date'] = pd.to_datetime(result_df['timestamp']).dt.date

result_df = result_df.sort_values('timestamp')

# 画图（横轴为日期，按时间排序）
plt.figure(figsize=(10, 5))
plt.plot(result_df['timestamp'], result_df['equity'], marker='o')
plt.title("Daily Equity Curve (Flat at EOD)")
plt.xlabel("Date")
plt.ylabel("Capital")
plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()
plt.show()
