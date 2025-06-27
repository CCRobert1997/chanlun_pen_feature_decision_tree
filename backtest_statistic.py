import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 参数
directory = "ermai_caozuo"  # 交易数据文件夹
initial_capital = 100000  # 初始资金
position_size = 0.3  # 每次建仓使用总资金的20%
start_date = pd.Timestamp("2024-12-09")  # 开始回测时间
trade_log_file = "trade_log.csv"  # 交易日志文件


def process_trades():
    """ 处理所有交易数据，执行回测并记录交易日志 """
    total_capital = initial_capital
    positions = {}  # 当前持仓 {ticker: (direction, entry_price, size)}
    capital_history = [(start_date, total_capital, total_capital)]  # (时间, 现金资金, 估值总资金)
    all_trades = []
    wins, losses = [], []  # 记录盈利和亏损交易

    # 读取所有符合条件的文件
    trade_data = []
    for filename in os.listdir(directory):
        if filename.endswith("_6_second_ermai_caozuo.csv"):
            ticker = filename.split("_6_second")[0]  # 提取股票代码
            file_path = os.path.join(directory, filename)
            df = pd.read_csv(file_path, parse_dates=['time'])
            df = df[df['time'] >= start_date]  # 仅考虑2024年12月9日后的数据
            df['ticker'] = ticker
            trade_data.append(df)

    if not trade_data:
        print("No trade data found.")
        return total_capital, all_trades, capital_history, wins, losses

    all_data = pd.concat(trade_data).sort_values('time')

    # 处理交易
    for _, row in all_data.iterrows():
        ticker, state, price, time = row['ticker'], row['sanmai_state'], row['price'], row['time']

        if state == "二卖确认":  # 建立空头头寸
            # if ticker not in positions and total_capital > 0:
            if ticker not in positions and total_capital > initial_capital * position_size:
                # size = (total_capital * position_size) / price
                size = (initial_capital * position_size) / price
                positions[ticker] = ('short', price, size)
                total_capital -= size * price
                all_trades.append((time, ticker, 'short', price, size, None))

        elif state == "二买确认":  # 建立多头头寸
            # if ticker not in positions and total_capital > 0:
            if ticker not in positions and total_capital > initial_capital * position_size:
                # size = (total_capital * position_size) / price
                size = (initial_capital * position_size) / price
                positions[ticker] = ('long', price, size)
                total_capital -= size * price
                all_trades.append((time, ticker, 'long', price, size, None))

        elif state == "平仓":  # 平仓现有头寸
            if ticker in positions:
                direction, entry_price, size = positions.pop(ticker)

                profit = (entry_price - price) * size if direction == 'short' else (price - entry_price) * size
                total_capital += profit + (size * entry_price)
                all_trades.append((time, ticker, 'close', price, size, profit))

                # 计算收益比例
                profit_ratio = profit / (size * entry_price)
                if profit > 0:
                    wins.append(profit_ratio)
                else:
                    losses.append(profit_ratio)

        # 计算当前总估值，包括未平仓的头寸
        total_value = total_capital
        for _, (direction, entry_price, size) in positions.items():
            total_value += size * entry_price  # 仍按建仓价计算
        capital_history.append((time, total_capital, total_value))

    print(f"最终资金: {total_capital:.2f} USD")
    print(f"最终资产: {total_value:.2f} USD")

    # 保存交易日志
    trade_df = pd.DataFrame(all_trades, columns=['time', 'ticker', 'action', 'price', 'size', 'profit'])
    trade_df.to_csv(trade_log_file, index=False)
    print(f"交易日志已保存至 {trade_log_file}")

    return total_capital, all_trades, capital_history, wins, losses


def compute_strategy_metrics(capital_history, wins, losses):
    """ 计算交易指标 """
    df = pd.DataFrame(capital_history, columns=['date', 'cash_capital', 'total_value'])
    df['returns'] = df['total_value'].pct_change().dropna()

    total_trades = len(wins) + len(losses)
    win_rate = len(wins) / total_trades if total_trades > 0 else 0
    expected_gain = np.mean(wins) if len(wins) > 0 else 0
    expected_loss = np.mean(losses) if len(losses) > 0 else 0

    sharpe_ratio = df['returns'].mean() / df['returns'].std() * np.sqrt(252) if df['returns'].std() > 0 else 0
    peak = df['total_value'].cummax()
    drawdown = (df['total_value'] - peak) / peak
    max_drawdown = drawdown.min()

    kelly_fraction = max(0, min(win_rate / abs(expected_loss) - (1 - win_rate) / expected_gain, 1))

    return win_rate, expected_gain, expected_loss, sharpe_ratio, max_drawdown, kelly_fraction


def plot_capital_curve(capital_history, win_rate, expected_gain, expected_loss, sharpe_ratio, max_drawdown,
                       kelly_fraction):
    """ 绘制资金曲线，并标注交易指标 """
    df = pd.DataFrame(capital_history, columns=['date', 'cash_capital', 'total_value'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax1.plot(df['date'], df['cash_capital'], marker='o', linestyle='-', color='blue', label='Cash Capital (Realized)')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Cash Capital (USD)', color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')

    ax2 = ax1.twinx()
    ax2.plot(df['date'], df['total_value'], marker='o', linestyle='-', color='red',
             label='Total Value (Including Open Positions)')
    ax2.set_ylabel('Total Value (USD)', color='red')
    ax2.tick_params(axis='y', labelcolor='red')

    text = (
        f"Win Rate: {win_rate:.2%}\n"
        f"Expected Gain: {expected_gain:.2%}\n"
        f"Expected Loss: {expected_loss:.2%}\n"
        f"Sharpe Ratio: {sharpe_ratio:.2f}\n"
        f"Max Drawdown: {max_drawdown:.2%}\n"
        f"Kelly Fraction: {kelly_fraction:.2%}"
    )
    ax1.text(0.05, 0.95, text, transform=ax1.transAxes, fontsize=12, verticalalignment='top')

    fig.suptitle('Trading Capital Over Time')
    plt.show()


if __name__ == "__main__":
    final_capital, trade_log, capital_history, wins, losses = process_trades()
    win_rate, expected_gain, expected_loss, sharpe_ratio, max_drawdown, kelly_fraction = compute_strategy_metrics(
        capital_history, wins, losses)
    plot_capital_curve(capital_history, win_rate, expected_gain, expected_loss, sharpe_ratio, max_drawdown,
                       kelly_fraction)
