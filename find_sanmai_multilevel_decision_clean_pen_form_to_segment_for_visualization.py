import pandas as pd
import glob
import os
import pytz
import holidays
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
import time
from copy import deepcopy
import argparse
from chanlun_utils import generate_kline_data, generate_kline_data_group_points, handle_kline_inclusion_with_trend, find_pens_from_kline, find_pens_from_kline_need_fixed, pens_fix, generate_feature_sequence, merge_pens_to_segments, merge_pens_to_segments_based_on_pen_zhongshu, find_zhongshu, find_zhongshu_and_cijibie_qushi, find_zhongshu_csy_steps, find_zhongshu_csy_inverse_look_steps, find_zhongshu_new, find_zhongshu_based_on_looking_for_next_zhongshu, find_zhongshu_one_pen_can_be_a_zhongshu, find_zhongshu_one_pen_brute, find_zhongshu_one_pen_form, clean_zhongshu_detailed, calculate_macd







# 计算均线
def add_moving_average(kline_df, window=10):
    kline_df[f'SMA_{window}'] = kline_df['close'].rolling(window=window).mean()
    return kline_df




def draw_zhongshu(fig, zhongshus, row, col, level):
    """
    在 K 线图上绘制中枢的方框
    参数:
        fig: Plotly 图表对象
        zhongshus: 中枢列表，每个中枢是一个字典，包含 'ZG', 'ZD', 'start_time', 'end_time'
        row: 绘制在的图表行
        col: 绘制在的图表列
    """
    if (level=="pen"):
        for zhongshu in zhongshus:
            # 添加中枢的矩形框
            fig.add_shape(
                type="rect",
                x0=zhongshu["start_time"],
                x1=zhongshu["end_time"],
                y0=zhongshu["ZD"],
                y1=zhongshu["ZG"],
                line=dict(color="blue", width=2),
                fillcolor="rgba(0, 0, 255, 0.2)",  # 半透明蓝色
                xref=f'x{col}',
                yref=f'y{row}',
            )
    if (level=="segment"):
        for zhongshu in zhongshus:
            # 添加中枢的矩形框
            fig.add_shape(
                type="rect",
                x0=zhongshu["start_time"],
                x1=zhongshu["end_time"],
                y0=zhongshu["ZD"],
                y1=zhongshu["ZG"],
                line=dict(color="orange", width=3),
                fillcolor="rgba(0, 0, 255, 0.2)",  # 半透明蓝色
                xref=f'x{col}',
                yref=f'y{row}',
            )
    if (level=="segment_of_segment"):
        for zhongshu in zhongshus:
            # 添加中枢的矩形框
            fig.add_shape(
                type="rect",
                x0=zhongshu["start_time"],
                x1=zhongshu["end_time"],
                y0=zhongshu["ZD"],
                y1=zhongshu["ZG"],
                line=dict(color="red", width=3),
                fillcolor="rgba(0, 0, 255, 0.2)",  # 半透明蓝色
                xref=f'x{col}',
                yref=f'y{row}',
            )


          
            





def read_all_csv_of_one_stock(stock_name_and_market="NVDA_NASDAQ"):
    # 文件夹路径
    data_folder = "data"
    # 匹配所有相关文件（按命名规则匹配）
    file_pattern = os.path.join(data_folder, f"{stock_name_and_market}_prices_*.csv")
    file_list = sorted(glob.glob(file_pattern))  # 自动按文件名排序
    # 主数据框
    df = pd.DataFrame()
    # 从第 n 行开始读取
    start_row = 0
    # 逐文件读取并拼接
    for file_path in file_list:
        # 读取文件，跳过指定行，保留表头
        single_df = pd.read_csv(file_path, skiprows=range(1, start_row))
        # 确保时间列为 datetime 类型
        single_df['timestamp'] = pd.to_datetime(single_df['timestamp'])
        # 按时间顺序拼接
        df = pd.concat([df, single_df], ignore_index=True)

    # 最终按时间排序
    df = df.sort_values(by='timestamp').reset_index(drop=True)
    return df


def read_all_csv_of_one_stock_some_days(stock_name_and_market="NVDA_NASDAQ", days_n = 50):
    # 文件夹路径
    data_folder = "data"
    # 匹配所有相关文件（按命名规则匹配）
    file_pattern = os.path.join(data_folder, f"{stock_name_and_market}_prices_*.csv")
    file_list = sorted(glob.glob(file_pattern))  # 自动按文件名排序
    # 主数据框
    df = pd.DataFrame()
    # 从第 n 行开始读取
    start_row = 0

    read_days = days_n
    if len(file_list) < read_days:
        read_days = len(file_list)
    # 逐文件读取并拼接
    for file_path in file_list[-read_days:]:
        # 读取文件，跳过指定行，保留表头
        single_df = pd.read_csv(file_path, skiprows=range(1, start_row))
        # 确保时间列为 datetime 类型
        single_df['timestamp'] = pd.to_datetime(single_df['timestamp'])
        # 按时间顺序拼接
        df = pd.concat([df, single_df], ignore_index=True)

    # 最终按时间排序
    df = df.sort_values(by='timestamp').reset_index(drop=True)
    return df


def read_all_csv_of_one_stock_some_days_after_date(stock_name_and_market="NVDA_NASDAQ",
                                                    start_date="2024-12-01",
                                                    days_n=50):
    # 文件夹路径
    data_folder = "data"
    # 匹配所有相关文件（按命名规则匹配）
    file_pattern = os.path.join(data_folder, f"{stock_name_and_market}_prices_*.csv")
    file_list = sorted(glob.glob(file_pattern))  # 自动按文件名排序
    # 提取文件中的日期并筛选
    filtered_files = []
    for file_path in file_list:
        # 提取日期字符串
        base_name = os.path.basename(file_path)
        try:
            date_str = base_name.replace(f"{stock_name_and_market}_prices_", "").replace(".csv", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date > datetime.strptime(start_date, "%Y-%m-%d"):
                filtered_files.append((file_date, file_path))
        except ValueError:
            continue  # 跳过无法解析日期的文件名
    # 按日期排序
    filtered_files = sorted(filtered_files, key=lambda x: x[0])
    # 取最近的 days_n 个文件
    selected_files = [f[1] for f in filtered_files[:days_n]]
    # 主数据框
    df = pd.DataFrame()
    for file_path in selected_files:
        single_df = pd.read_csv(file_path)
        single_df['timestamp'] = pd.to_datetime(single_df['timestamp'])
        df = pd.concat([df, single_df], ignore_index=True)
    # 最终按时间排序
    df = df.sort_values(by='timestamp').reset_index(drop=True)
    return df


def read_all_csv_of_one_stock_some_days_before_date(stock_name_and_market="NVDA_NASDAQ",
                                                    end_date="2024-12-01",
                                                    days_n=150):
    # 文件夹路径
    data_folder = "data"
    # 匹配所有相关文件（按命名规则匹配）
    file_pattern = os.path.join(data_folder, f"{stock_name_and_market}_prices_*.csv")
    file_list = sorted(glob.glob(file_pattern))  # 自动按文件名排序
    # 提取文件中的日期并筛选
    filtered_files = []
    for file_path in file_list:
        # 提取日期字符串
        base_name = os.path.basename(file_path)
        try:
            date_str = base_name.replace(f"{stock_name_and_market}_prices_", "").replace(".csv", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date < datetime.strptime(end_date, "%Y-%m-%d"):
                filtered_files.append((file_date, file_path))
        except ValueError:
            continue  # 跳过无法解析日期的文件名
    # 按日期排序
    filtered_files = sorted(filtered_files, key=lambda x: x[0])
    # 取最近的 days_n 个文件
    selected_files = [f[1] for f in filtered_files[-days_n:]]
    # 主数据框
    df = pd.DataFrame()
    for file_path in selected_files:
        single_df = pd.read_csv(file_path)
        single_df['timestamp'] = pd.to_datetime(single_df['timestamp'])
        df = pd.concat([df, single_df], ignore_index=True)
    # 最终按时间排序
    df = df.sort_values(by='timestamp').reset_index(drop=True)
    return df







def read_all_csv_of_one_stock_ten_days(stock_name_and_market="NVDA_NASDAQ"):
    # 文件夹路径
    data_folder = "data"
    # 匹配所有相关文件（按命名规则匹配）
    file_pattern = os.path.join(data_folder, f"{stock_name_and_market}_prices_*.csv")
    file_list = sorted(glob.glob(file_pattern))  # 自动按文件名排序
    # 主数据框
    df = pd.DataFrame()
    # 从第 n 行开始读取
    start_row = 0

    read_days = 10
    if len(file_list) < read_days:
        read_days = len(file_list)
    # 逐文件读取并拼接
    for file_path in file_list[-read_days:]:
        # 读取文件，跳过指定行，保留表头
        single_df = pd.read_csv(file_path, skiprows=range(1, start_row))
        # 确保时间列为 datetime 类型
        single_df['timestamp'] = pd.to_datetime(single_df['timestamp'])
        # 按时间顺序拼接
        df = pd.concat([df, single_df], ignore_index=True)

    # 最终按时间排序
    df = df.sort_values(by='timestamp').reset_index(drop=True)
    return df



def read_all_csv_of_one_stock_fifty_days(stock_name_and_market="NVDA_NASDAQ"):
    # 文件夹路径
    data_folder = "data"
    # 匹配所有相关文件（按命名规则匹配）
    file_pattern = os.path.join(data_folder, f"{stock_name_and_market}_prices_*.csv")
    file_list = sorted(glob.glob(file_pattern))  # 自动按文件名排序
    # 主数据框
    df = pd.DataFrame()
    # 从第 n 行开始读取
    start_row = 0

    read_days = 50
    if len(file_list) < read_days:
        read_days = len(file_list)
    # 逐文件读取并拼接
    for file_path in file_list[-read_days:]:
        # 读取文件，跳过指定行，保留表头
        single_df = pd.read_csv(file_path, skiprows=range(1, start_row))
        # 确保时间列为 datetime 类型
        single_df['timestamp'] = pd.to_datetime(single_df['timestamp'])
        # 按时间顺序拼接
        df = pd.concat([df, single_df], ignore_index=True)

    # 最终按时间排序
    df = df.sort_values(by='timestamp').reset_index(drop=True)
    return df
    
    
def read_single_csv_of_one_stock(file_path='data/NVDA_NASDAQ_prices_2024-12-10.csv'):
    # 读取数据文件
    # 'data/AAPL_NASDAQ_prices_2024-12-09.csv'
    # 'data/AVGO_NASDAQ_prices_2024-12-09.csv'
    # 设置从第 n 行开始读取，例如从第 10 行开始
    start_row = 0
    # 使用 skiprows 跳过数据行，保留表头
    df = pd.read_csv(file_path, skiprows=range(1, start_row))
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df












def is_market_open():
    """
    Check if the US market is open based on Eastern Time, excluding weekends, holidays, and early closing days.
    Returns True if the market is open, otherwise False.
    """
    # Time zone setup
    melbourne_tz = pytz.timezone('Australia/Melbourne')
    us_eastern_tz = pytz.timezone('US/Eastern')


    # Get current US Eastern Time
    melbourne_time = datetime.now(melbourne_tz)
    us_eastern_time = melbourne_time.astimezone(us_eastern_tz)
    current_date = us_eastern_time.date()

    # Define US market hours
    market_open = us_eastern_time.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = us_eastern_time.replace(hour=16, minute=0, second=0, microsecond=0)
    market_half_close = us_eastern_time.replace(hour=13, minute=0, second=0, microsecond=0)  # Half-day close

    # US holidays
    us_holidays = holidays.US(years=current_date.year, observed=True)

    # Special half-day trading dates (e.g., Christmas Eve, Thanksgiving Friday)
    half_day_trading_dates = {
        datetime(current_date.year, 12, 24).date(),  # Christmas Eve
        datetime(current_date.year, 11, 24).date(),  # Day after Thanksgiving (example for 2024)
    }

    # Check conditions
    is_weekday = us_eastern_time.weekday() < 5  # Monday-Friday are 0-4
    is_not_holiday = current_date not in us_holidays
    if current_date in half_day_trading_dates:
        is_within_hours = market_open <= us_eastern_time <= market_half_close
    else:
        is_within_hours = market_open <= us_eastern_time <= market_close

    # Return True if all conditions are met
    return is_weekday and is_not_holiday and is_within_hours


















if __name__ == "__main__":


    parser = argparse.ArgumentParser(description="K线与走势分析参数设置")

    # 添加超参数
    parser.add_argument("--zgzd_type", type=str, choices=["classical", "practical"], default="classical",
                        help="中枢类型 ('classical' 或 'practical')")
    parser.add_argument("--dingdi_start_from", type=int, default=2,
                        help="从哪个顶或底开始计算，影响走势多义性, 这便建议选择2，因为我会在选在数据起点在一个局部极点，实际上会错过第一个很有意义的顶底点，而第二个顶底点又必然与第一个反向，所以从第三个算起。这个逻辑可以优化一下，想办法找到第一个顶底点")
    
    parser.add_argument("--group_size_for_MACD", type=int, default=10,
                    help="MACD的K线基于的时间级别，一般要设的比group_size的时间级别大，建议为group_size的5倍, 而且最好不要低于20")
    parser.add_argument("--stock_name_and_market", type=str, default="AMZN_NASDAQ",
                        help="股票名称及市场，例如 'NVDA_NASDAQ','AAPL_NASDAQ', 'AMZN_NASDAQ', 'META_NASDAQ', 'MSFT_NASDAQ', 'SNOW_NYSE', 'TIGR_NASDAQ', 'TSLA_NASDAQ', 'U_NYSE' ")
    parser.add_argument("--not_all_data_but_single_day", action="store_true",
                        help="设置为 True 时处理仅一天数据，未添加该选项时为 False")
    parser.add_argument("--if_single_day_date", type=str, default="2024-12-11",
                        help="单日数据的日期，格式为 'YYYY-MM-DD'")
    parser.add_argument("--print_process_info", action="store_true",
                        help="设置为 True 时, 打印出运行到哪一步的信息, 并绘制当前状态的走势中枢图")
    parser.add_argument("--print_huice_return_info", action="store_true",
                        help="回测时用，设置为 True 时, 打印出回测的信息")
    parser.add_argument("--info_save_to_file_mode", action="store_true",
                        help="设置为 True 时, 将买卖信息和图片存储到文件中")
    parser.add_argument("--show_fig_when_sell_buy_action", action="store_true",
                        help="设置为 True 时, 出现三买三买平仓信号时会把图片在本地某个端口画出来")

    parser.add_argument("--group_size_for_high_level", type=int, default=10,
                        help="大级别的group size，也就是一个K线几个六秒，比如选5，10，20，对应30秒，60秒，120秒")
    parser.add_argument("--group_size_for_low_level", type=int, default=1,
                        help="小级别的group size，至少是大级别的五分之一")

    # 解析参数
    args = parser.parse_args()

    ZGZD_TYPE = args.zgzd_type #"classical" "practical"
    DINGDI_START_FROM = args.dingdi_start_from #从哪个顶或底开始看影响很大，关系到走势的多义性，一般可以dingdi_start_from=1
    STOCK_NAME_AND_MARKET = args.stock_name_and_market  # "NVDA_NASDAQ" "AAPL_NASDAQ" "AMZN_NASDAQ" "META_NASDAQ" "MSFT_NASDAQ" "SNOW_NYSE" "TIGR_NASDAQ" "TSLA_NASDAQ" "U_NYSE" "AVGO_NASDAQ"
    ALL_DATA_NOT_SINGLE_DAY = not args.not_all_data_but_single_day
    IF_SINGLE_DAY_DATE = args.if_single_day_date
    PRINT_PROCESS_INFO = args.print_process_info
    PRINT_HUICE_RETURN_INFO = args.print_huice_return_info
    GROUP_SIZE_FOR_MACD = args.group_size_for_MACD
    INFO_SAVE_TO_FILE_MODE = args.info_save_to_file_mode
    SHOW_FIG_WHEN_SELL_BUY_ACTION = args.show_fig_when_sell_buy_action

    GROUP_SIZE_FOE_HIGH_LEVEL = args.group_size_for_high_level  # 10
    GROUP_SIZE_FOE_LOW_LEVEL = args.group_size_for_low_level # 1

    # GROUP_SIZEs = [10]
    # GROUP_SIZEs = [5]
    # GROUP_SIZEs = [1]
    GROUP_SIZEs = [GROUP_SIZE_FOE_HIGH_LEVEL, GROUP_SIZE_FOE_LOW_LEVEL]
    # GROUP_SIZEs = [10, 10]
    # GROUP_SIZEs = [30, 1]
    # GROUP_SIZEs = [20, 20]
    # GROUP_SIZEs = [10]

    folder_path = "sanmai_caozuo"
    file_name = f"{STOCK_NAME_AND_MARKET}_{GROUP_SIZEs[0]*6}_second_sanmai_caozuo.csv"
    file_path = os.path.join(folder_path, file_name)




    def write_to_sanmai_info_file(data_sanmai_argue):
        # 确保文件夹存在
        os.makedirs(folder_path, exist_ok=True)
        # 判断文件是否已存在
        file_exists = os.path.isfile(file_path)
        df_data_sanmai = pd.DataFrame([data_sanmai_argue])
        df_data_sanmai.to_csv(file_path, mode='a', header=not file_exists, index=False, encoding='utf-8-sig')



    san_buy_appeared = False
    qian_top_before_san_buy = 0.0
    chengben_sanbuy = 0.0
    huilajianyan_time_for_san_buy = pd.to_datetime("2000-12-17 15:19:07")

    san_sell_appeared = False
    qian_bottom_before_san_sell = 0.0
    chengben_sansell = 0.0
    huilajianyan_time_for_san_sell = pd.to_datetime("2000-12-17 15:19:07")


    current_status = "empty" #"check_sanlong", "check_sanshort", "sanlong_in_position", "sanshort_in_position"
    jiancang_time = pd.to_datetime("2000-12-17 15:19:07")
    jiancang_price = 0
    check_sanmaisanmai_zhicheng = 0.0
    da_jibie_xianduanjieshu_time = None  # 大级别线段结束的时间


    ############################### 全时间回测用 ###############################
    def return_test_generate_timestamps(start_timestamp: str, end_timestamp: str, interval_minutes: int):
        return_test_initial_timestamp = datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M:%S")
        return_test_final_timestamp = datetime.strptime(end_timestamp, "%Y-%m-%d %H:%M:%S")
        return_test_allowed_start_hour = 14
        return_test_allowed_start_minute = 30
        return_test_allowed_start_second = 2
        return_test_allowed_end_hour = 21
        return_test_allowed_end_minute = 0
        return_test_allowed_end_second = 0
        return_test_timeframe_collection = []
        return_test_current_iteration_date = return_test_initial_timestamp.date()
        while return_test_current_iteration_date <= return_test_final_timestamp.date():
            if return_test_current_iteration_date.weekday() != 6:  # 0=Monday, ..., 6=Sunday
                return_test_daily_start_time = datetime.combine(return_test_current_iteration_date,
                                                                datetime.min.time()).replace(
                    hour=return_test_allowed_start_hour, minute=return_test_allowed_start_minute,
                    second=return_test_allowed_start_second)
                return_test_daily_end_time = datetime.combine(return_test_current_iteration_date,
                                                              datetime.min.time()).replace(
                    hour=return_test_allowed_end_hour, minute=return_test_allowed_end_minute,
                    second=return_test_allowed_end_second)
                return_test_incremental_time = return_test_daily_start_time
                while return_test_incremental_time <= return_test_daily_end_time:
                    return_test_timeframe_collection.append(return_test_incremental_time.strftime("%Y-%m-%d %H:%M:%S"))
                    return_test_incremental_time += timedelta(minutes=interval_minutes)
            return_test_current_iteration_date += timedelta(days=1)
        return return_test_timeframe_collection
    # return_test_timestamps = return_test_generate_timestamps("2025-01-15 17:19:07", "2025-03-11 15:10:07", 30)
    # return_test_timestamps = return_test_generate_timestamps("2025-02-26 20:19:07", "2025-03-11 15:10:07", 30)
    # time_until_list = return_test_timestamps[398:2000]
    # time_until_list = return_test_timestamps[499:2000]
    # time_until_list = [return_test_timestamps[i] for i in [553, 554, 564, 565, 607, 608, 623]]
    return_test_timestamps = return_test_generate_timestamps("2024-12-15 17:19:07", "2025-03-11 15:10:07", 30)
    # time_until_list = return_test_timestamps[500:2000] #for 120 second
    # time_until_list = return_test_timestamps[50:2000]  # for 30 second
    time_until_list = return_test_timestamps[312:2000]  # for 30 second
    time_until_list = [return_test_timestamps[i] for i in [317, 325, 326, 327, 332]] # for META test

    return_test_timestamps = return_test_generate_timestamps("2024-12-15 17:19:07", "2025-03-11 15:10:07", 10)
    # time_until_list = return_test_timestamps[900:3000]  # for 30 second
    # time_until_list = return_test_timestamps[880:3000]  # for 30 second
    # time_until_list = [return_test_timestamps[i] for i in range(951, 999)]  # for META test

    # 针对U_NYSE，1分钟对6秒的卖点错失
    # return_test_timestamps = return_test_generate_timestamps("2024-12-15 17:19:07", "2025-03-11 15:10:07", 10)
    # time_until_list = [return_test_timestamps[i] for i in [857, 858, 860, 927, 1210, 2000]] #857其实已经三卖确立, 927已经可以平仓

    # return_test_timestamps = return_test_generate_timestamps("2024-12-15 17:19:07", "2025-03-11 15:10:07", 10)
    # time_until_list = [return_test_timestamps[i] for i in [1900]]


    # 看一下全时长总体，如果是6秒级的话跑得会很慢
    return_test_timestamps = return_test_generate_timestamps("2024-12-15 17:19:07", "2025-05-24 15:10:07", 10)
    return_test_timestamps = return_test_generate_timestamps("2025-01-15 17:19:07", "2025-05-16 18:10:07", 10)
    time_until_list = [return_test_timestamps[i] for i in [-1]]
    # time_until_list = return_test_timestamps[312:2000]



    # # 大时间间隔观察一下
    # return_test_timestamps = return_test_generate_timestamps("2024-12-15 17:19:07", "2025-03-11 15:10:07", 180)
    # time_until_list = return_test_timestamps[17:]

    # time_until_list = [return_test_timestamps[i] for i in [500, 505, 506, 507, 508]]
    # time_until_list = return_test_timestamps[-2:]
    # time_until_list = [return_test_timestamps[i] for i in [900, 901]]
    if PRINT_PROCESS_INFO and (not PRINT_HUICE_RETURN_INFO) and (not INFO_SAVE_TO_FILE_MODE):
        # time_until_list = [return_test_timestamps[i] for i in [901]]
        # time_until_list = [return_test_timestamps[i] for i in [650]]
        time_until_list = [return_test_timestamps[i] for i in [-1]]
        # print(time_until_list)

    time_until_index = -1
    while time_until_index < len(time_until_list)-1:
        time_until_index += 1
        time_until = time_until_list[time_until_index]
        if PRINT_HUICE_RETURN_INFO:
            print(f"当前回测截止时间{time_until} {time_until_index}")
    ############################### 全时间回测用 ###############################


    ############################### 线上实盘用 ###############################
    # while True:
    ############################### 线上实盘用 ###############################


    ############################### 单次测试用 ###############################
    # if True:
    ############################### 单次测试用 ###############################


        if True: # 单次测试用 或者 全时间回测用
        # if is_market_open(): # 线上实盘用

            # 开始计时
            start_time = time.time()

            DAYS_LOOK_BASED_ON_GROUP_SIZE = {45: 150, 1: 15}



            # # df = read_all_csv_of_one_stock_some_days(stock_name_and_market=STOCK_NAME_AND_MARKET, days_n=50)
            # #GROUP_SIZE_FOE_HIGH_LEVEL*2
            # # 20->40天 10->20天 5->10天
            # # df = read_all_csv_of_one_stock_some_days(stock_name_and_market=STOCK_NAME_AND_MARKET, days_n=GROUP_SIZE_FOE_HIGH_LEVEL*2)
            # if PRINT_HUICE_RETURN_INFO:
            #     df = read_all_csv_of_one_stock_some_days(stock_name_and_market=STOCK_NAME_AND_MARKET, days_n=70)
            # elif PRINT_PROCESS_INFO and (not PRINT_HUICE_RETURN_INFO) and (not INFO_SAVE_TO_FILE_MODE):
            #     df = read_all_csv_of_one_stock_some_days(stock_name_and_market=STOCK_NAME_AND_MARKET, days_n=70)
            # else:
            #     df = read_all_csv_of_one_stock_some_days(stock_name_and_market=STOCK_NAME_AND_MARKET,
            #                                              days_n=GROUP_SIZE_FOE_HIGH_LEVEL * 2)

            ############################### 全时间回测用 ###############################
            # df = read_all_csv_of_one_stock_some_days_after_date(
            #     stock_name_and_market=STOCK_NAME_AND_MARKET, days_n=GROUP_SIZE_FOE_HIGH_LEVEL * 2,
            #     start_date="2024-12-15"
            # )
            ######## 从最小级别向上递归 ######
            # df = read_all_csv_of_one_stock_some_days_after_date(
            #     stock_name_and_market=STOCK_NAME_AND_MARKET, days_n=20,
            #     start_date="2024-12-15"
            # )
            df = read_all_csv_of_one_stock_some_days_after_date(
                stock_name_and_market=STOCK_NAME_AND_MARKET, days_n=200,
                start_date="2024-12-15"
            )
            df = read_all_csv_of_one_stock_some_days_after_date(
                stock_name_and_market=STOCK_NAME_AND_MARKET, days_n=200,
                start_date="2024-12-15"
            )
            df = read_all_csv_of_one_stock_some_days_before_date(
                stock_name_and_market=STOCK_NAME_AND_MARKET, days_n=DAYS_LOOK_BASED_ON_GROUP_SIZE[GROUP_SIZE_FOE_HIGH_LEVEL],
                end_date="2025-05-16"
            )
            ######## 从最小级别向上递归 ######
            ############################### 全时间回测用 ###############################



            ############################### 线上实盘用 ###############################
            # # GROUP_SIZE_FOE_HIGH_LEVEL*2
            # # 20->40天 10->20天 5->10天
            # df = read_all_csv_of_one_stock_some_days(stock_name_and_market=STOCK_NAME_AND_MARKET,
            #                                          days_n=GROUP_SIZE_FOE_HIGH_LEVEL * 2)
            ############################### 线上实盘用 ###############################




            # 找到他的最高点和最低点，第二高点和第二低点，选出这四个点中不是整个数据集最早的时间点，但是四个点中最早的点，截取数据集这个时间点之后的df
            # 这样在一个比较方便的点开始分析
            # 排序找到最高点、最低点、第二高点、第二低点
            sorted_df = df.sort_values(by='price', ascending=False).reset_index()
            highest = sorted_df.iloc[0]
            second_highest = sorted_df.iloc[1]
            lowest = sorted_df.iloc[-1]
            second_lowest = sorted_df.iloc[-2]
            # 将这四个点整理为一个 DataFrame
            extreme_points = pd.DataFrame([highest, second_highest, lowest, second_lowest])
            # 从这四个点中找最早时间点（但不是全局最早的时间点）
            global_earliest_time = df['timestamp'].min()
            filtered_points = extreme_points[extreme_points['timestamp'] != global_earliest_time]
            selected_time = filtered_points['timestamp'].min()
            """
            # 从这四个点中找最晚时间点（但不是全局最晚的时间点）
            global_latest_time = df['timestamp'].max()
            filtered_points = extreme_points[extreme_points['timestamp'] != global_latest_time]
            selected_time = filtered_points['timestamp'].max()
            """
            # 截取数据集从该时间点开始的数据
            # print(selected_time)
            # df = df[df['timestamp'] >= selected_time]
            # df = df[df['timestamp'] >= "2024-12-17 15:19:07"] #英伟达的一个局部低点
            # df = df[df['timestamp'] <= "2024-12-18 15:19:07"]
            # df = df[df['timestamp'] >= "2024-12-16 20:59:50"]
            # df = df[df['timestamp'] <= "2024-12-11 20:23:50"]
            # df = df[df['timestamp'] <= "2024-12-25 20:59:50"]
            # df = df[df['timestamp'] >= "2025-01-03 20:59:50"]
            # df = df[df['timestamp'] <= "2024-12-19 20:59:50"]
            # df = df[df['timestamp'] <= "2024-12-23 20:59:50"]
            # df = df[df['timestamp'] <= "2024-12-28 20:59:50"]
            # df = df[df['timestamp'] <= "2024-12-27 16:59:50"]
            # df = df[df['timestamp'] >= "2024-12-31 15:59:50"]
            # df = df[df['timestamp'] >= "2025-01-14 20:30:50"]
            # df = df[df['timestamp'] <= "2025-01-03 19:30:50"] #英伟达的一分钟线3买 在画线段时产生
            # df = df[df['timestamp'] <= "2025-01-21 19:42:50"]  # 英伟达的一分钟线3买 在画线段时产生
            # df = df[df['timestamp'] <= "2025-01-21 20:42:50"] #英伟达的一分钟线3买 在画线段时产生
            # df = df[df['timestamp'] <= "2025-01-22 15:45:50"] #英伟达的一分钟线3买 在画线段时产生
            # df = df[df['timestamp'] >= "2025-01-21 19:42:50"]
            # df = df[df['timestamp'] <= "2025-01-22 19:42:50"]
            # df = df[df['timestamp'] <= "2024-12-20 17:35:07"] #英伟达的30秒三买 v1版本
            # df = df[df['timestamp'] <= "2025-01-07 17:45:07"]
            # df = df[df['timestamp'] <= "2025-01-07 19:20:07"]
            # df = df[df['timestamp'] <= "2025-01-08 14:53:07"]
            # df = df[df['timestamp'] <= "2025-01-06 16:29:07"]
            # df = df[df['timestamp'] <= "2025-01-31 15:48:07"]
            # df = df[df['timestamp'] <= "2025-01-31 15:40:07"]
            # df = df[df['timestamp'] <= "2025-01-15 19:00:07"]
            # df = df[df['timestamp'] <= "2024-12-27 20:59:07"]
            # df = df[df['timestamp'] <= "2025-01-30 18:57:07"]

            # df = df[df['timestamp'] <= "2024-12-23 16:06:50"] #达子长线买卖点
            # df = df[df['timestamp'] <= "2024-12-24 16:06:50"]  # 达子长线买卖点
            # df = df[df['timestamp'] <= "2025-01-07 19:45:07"] #达子长线买卖点
            # df = df[df['timestamp'] <= "2025-01-15 19:00:07"] #达子长线买卖点
            # df = df[df['timestamp'] <= "2025-01-15 19:30:07"]  # 达子长线买卖点
            # df = df[df['timestamp'] <= "2025-01-29 15:50:07"] #达子长线买卖点
            # df = df[df['timestamp'] <= "2025-02-04 15:50:07"] #达子长线买卖点
            # df = df[df['timestamp'] <= "2025-01-10 19:10:07"]

            # df = df[df['timestamp'] <= "2025-01-28 15:50:07"] #亚马逊测试案例
            # df = df[df['timestamp'] <= "2025-01-28 18:50:07"] #亚马逊测试案例
            # df = df[df['timestamp'] <= "2025-01-30 15:16:07"] #亚马逊测试案例
            # df = df[df['timestamp'] <= "2025-01-30 17:22:07"] #亚马逊测试案例
            # df = df[df['timestamp'] <= "2025-01-30 19:22:07"] #亚马逊测试案例
            # df = df[df['timestamp'] <= "2025-01-30 19:30:07"] #亚马逊测试案例
            # df = df[df['timestamp'] <= "2025-01-31 20:01:07"] #亚马逊测试案例



            # df = df[df['timestamp'] <= "2025-01-30 17:20:07"] #这一段是英伟达的典型假突破
            # df = df[df['timestamp'] <= "2025-01-30 17:50:07"] #这一段是英伟达的典型假突破
            # df = df[df['timestamp'] <= "2025-01-30 18:04:07"] #这一段是英伟达的典型假突破
            # df = df[df['timestamp'] <= "2025-01-31 13:04:07"]
            # df = df[df['timestamp'] <= "2025-01-31 14:42:07"]
            # df = df[df['timestamp'] <= "2025-01-31 18:44:07"]

            # df = df[df['timestamp'] <= "2025-02-06 18:14:07"]  # 特斯拉三买

            # df = df[df['timestamp'] <= "2025-01-22 16:35:07"]  # 苹果三买

            # df = df[df['timestamp'] <= "2025-01-21 16:14:07"]  # Netflix，三买

            # df = df[df['timestamp'] <= "2025-01-31 15:50:07"]

            # df = df[df['timestamp'] <= "2025-02-20 20:28:07"]
            # df = df[df['timestamp'] <= "2025-02-18 14:36:07"]
            # df = df[df['timestamp'] <= "2025-02-24 17:32:07"]
            # df = df[df['timestamp'] <= "2025-02-24 17:50:07"]
            # df = df[df['timestamp'] <= "2025-02-24 18:50:07"]
            # df = df[df['timestamp'] <= "2025-02-26 20:50:07"]
            # df = df[df['timestamp'] <= "2025-01-29 15:10:07"]
            ############################### 全时间回测用 ###############################
            df = df[df['timestamp'] <= time_until] #全时间回测用

            ############################### 全时间回测用 ###############################

            # 创建子图布局
            fig = make_subplots(rows=len(GROUP_SIZEs)*3, cols=1, shared_xaxes=False, vertical_spacing=0.05,
                                subplot_titles=['GROUP_SIZE' + str(GROUP_SIZEs[int(group_size_in_GROUP_SIZEs_index/3)]) if (group_size_in_GROUP_SIZEs_index%3==0 or group_size_in_GROUP_SIZEs_index%3==1) else 'MACD' for group_size_in_GROUP_SIZEs_index in range(3*len(GROUP_SIZEs))], row_heights=[0.8 for group_i in range(3*len(GROUP_SIZEs))])


            # 先画一个全数据图以确保后面几幅图所有时间戳包含，也就是GROUP_SIZEs等于1
            kline_df = generate_kline_data_group_points(df, group_size=1)
            # print("6 second data processed")







            for GROUP_SIZE_index, GROUP_SIZE in enumerate(GROUP_SIZEs):
                # 调用函数生成 K 线数据
                # kline_df = generate_kline_data(df)
                # group_size=10就是分钟K线
                kline_df = generate_kline_data_group_points(df, group_size=GROUP_SIZE)


                # 调用处理包含关系的函数
                kline_df_no_inclusion = handle_kline_inclusion_with_trend(kline_df)
                # if PRINT_PROCESS_INFO:
                #     print("包含K线组合完毕，开始找笔")


                # 调用处理笔的函数
                #从哪个顶或底开始看影响很大，关系到走势的多义性，一般可以dingdi_start_from=1
                pens =  find_pens_from_kline(kline_df_no_inclusion, dingdi_start_from=DINGDI_START_FROM)
                # pens =  find_pens_from_kline_need_fixed(kline_df_no_inclusion, dingdi_start_from=DINGDI_START_FROM)
                # if PRINT_PROCESS_INFO:
                #     print("笔处理完毕，开始修复不合理的连续笔")
                # pens_fix 函数，它会合并 find_pens_from_kline 的结果中连续同向的笔，并重新计算合并后的每笔的最高点、最低点、起始时间和结束时间
                # fixed_pens = pens_fix(pens)
                fixed_pens = pens
                # if PRINT_PROCESS_INFO:
                #     print("笔修复处理完毕，开始找线段")
                    # if GROUP_SIZE_index==1:
                    #     print([(pen['direction'], pen['top_time']) for pen in fixed_pens])
                # 调用寻找中枢的函数
                pen_zhongshus = []
                # zgzd_type="classical"
                # zgzd_type="practical"
                # pen_zhongshus = find_zhongshu(fixed_pens, zgzd_type=ZGZD_TYPE)
                # pen_zhongshus, pen_cijibie_qushis = find_zhongshu_and_cijibie_qushi(fixed_pens, zgzd_type=ZGZD_TYPE)
                # pen_zhongshus = find_zhongshu_csy_steps(fixed_pens)
                # pen_zhongshus = find_zhongshu_csy_inverse_look_steps(fixed_pens)
                # pen_zhongshus = find_zhongshu_new(fixed_pens)
                # pen_zhongshus = find_zhongshu_one_pen_can_be_a_zhongshu(fixed_pens)
                # if PRINT_PROCESS_INFO:
                #     print("************************笔中枢***********************")
                # pen_zhongshus, pen_zhuanzhes = find_zhongshu_based_on_looking_for_next_zhongshu(fixed_pens)
                pen_zhongshus, pen_zhuanzhes = find_zhongshu_one_pen_form(fixed_pens)
                pen_zhongshus_clean, pen_zhuanzhes_clean, sanmai_info_pen = clean_zhongshu_detailed(
                    pen_zhongshus, fixed_pens)
                if GROUP_SIZE_index == 0:
                    print(
                        ["+" if clean_zhongshu["direction"] == "Up" else "-" for clean_zhongshu in pen_zhongshus_clean])




                # 用笔组合成线段
                # segments, standard_feature_sequence_lists = merge_pens_to_segments(fixed_pens)
                segments = []
                segments_fix = []
                segments, type_three_buy_sell = merge_pens_to_segments_based_on_pen_zhongshu(fixed_pens, pen_zhongshus_clean)
                # segments, type_three_buy_sell = merge_pens_to_segments(fixed_pens)
                if segments:
                    #segments_fix = pens_fix(segments)
                    segments_fix = segments

                # 把线段当作笔，画线段的线段
                segments_of_segments_fix = []
                # if segments_fix:
                #     segments_of_segments_fix = merge_pens_to_segments(segments_fix)
                #     if segments_of_segments_fix:
                #         fixed_segments_of_segments_fix = pens_fix(segments_of_segments_fix)


                # segments = merge_pens_to_segments(pens)
                # if PRINT_PROCESS_INFO:
                #     print("线段处理完毕，开始找中枢")



                segment_zhongshus = []
                segment_zhuanzhes = []
                segment_zhongshus_clean = []


                if segments:
                    if segments_fix:
                        # segment_zhongshus = find_zhongshu_new(segments_fix)
                        #segment_zhongshus = find_zhongshu_one_pen_can_be_a_zhongshu(segments_fix)
                        # if PRINT_PROCESS_INFO:
                        #     print("************************线段中枢***********************")
                        #segment_zhongshus, segment_zhuanzhes = find_zhongshu_based_on_looking_for_next_zhongshu(segments_fix)
                        # segment_zhongshus, segment_zhuanzhes = find_zhongshu_one_pen_brute(segments_fix)
                        segment_zhongshus, segment_zhuanzhes = find_zhongshu_one_pen_form(segments_fix)

                        segment_zhongshus_clean, segment_zhuanzhes_clean, sanmai_info = clean_zhongshu_detailed(segment_zhongshus, segments_fix)




                segment_of_segment_zhongshus = []
                # if segments_fix:
                #    if segments_of_segments_fix:
                #        segment_of_segment_zhongshus = find_zhongshu_new(segments_of_segments_fix)



                # if PRINT_PROCESS_INFO:
                #     print("中枢处理完毕，开始画图")

                # if PRINT_PROCESS_INFO:
                #     print("数据处理完毕，开始画图")

                GROUP_SIZE_FOR_MACD = GROUP_SIZE * 25
                MACD_kline_df = generate_kline_data_group_points(df, group_size=GROUP_SIZE_FOR_MACD)


                # 计算 MACD 值
                MACD_kline_df = calculate_macd(MACD_kline_df)



                # 将均线加入kline_df数据中
                # 短期均线 duanjunxian, 长均线 changjunxian
                duanjunxian_window = 125#625#125
                changjunxian_window = 250#1250#250
                kline_df = add_moving_average(kline_df, window=duanjunxian_window)  # 计算短周期均线
                kline_df = add_moving_average(kline_df, window=changjunxian_window)  # 计算长周期均线

                def plot_if_sanmai(sanmaitype="long", zhichengwei=0):
                    # 画6秒级，也就是最低级别数据的空线，给后面的图参考对齐x轴
                    fig.add_trace(go.Scatter(
                        x=kline_df['timestamp'],  # 使用 kline_df 的时间戳
                        y=[None] * len(kline_df),  # 不绘制 y 值
                        mode='lines',  # 设置为线模式（但不会显示）
                        showlegend=False  # 隐藏图例
                    ), row=GROUP_SIZE_index * 3 + 1, col=1)
                    fig.add_trace(go.Scatter(
                        x=kline_df['timestamp'],  # 使用 kline_df 的时间戳
                        y=[None] * len(kline_df),  # 不绘制 y 值
                        mode='lines',  # 设置为线模式（但不会显示）
                        showlegend=False  # 隐藏图例
                    ), row=GROUP_SIZE_index * 3 + 2, col=1)
                    fig.add_trace(go.Scatter(
                        x=kline_df['timestamp'],  # 使用 kline_df 的时间戳
                        y=[None] * len(kline_df),  # 不绘制 y 值
                        mode='lines',  # 设置为线模式（但不会显示）
                        showlegend=False  # 隐藏图例
                    ), row=GROUP_SIZE_index * 3 + 3, col=1)


                    # 处理后的 K 线图
                    for i in range(len(kline_df_no_inclusion)):
                        color = 'green' if kline_df_no_inclusion.iloc[i]['close'] > kline_df_no_inclusion.iloc[i][
                            'open'] else 'red'
                        fig.add_trace(
                            go.Candlestick(
                                x=[kline_df_no_inclusion.iloc[i]['timestamp']],
                                open=[kline_df_no_inclusion.iloc[i]['open']],
                                close=[kline_df_no_inclusion.iloc[i]['close']],
                                high=[kline_df_no_inclusion.iloc[i]['high']],
                                low=[kline_df_no_inclusion.iloc[i]['low']],
                                increasing_line_color=color,
                                decreasing_line_color=color,
                                showlegend=False
                            ),
                            row=GROUP_SIZE_index * 3 + 1, col=1
                        )



                    # Add fixed Pens to the chart
                    for pen_index, pen in enumerate(fixed_pens):
                        fig.add_trace(
                            go.Scatter(
                                x=[pen['top_time'], pen['bottom_time']],
                                y=[pen['top_price'], pen['bottom_price']],
                                mode='lines',
                                line=dict(color='white', width=2),
                                name='Penfix',
                                showlegend=False
                            ),
                            row=GROUP_SIZE_index * 3 + 1, col=1
                        )
                    draw_zhongshu(fig, pen_zhongshus, row=GROUP_SIZE_index * 3 + 1, col=GROUP_SIZE_index * 3 + 1,
                                  level="pen")

                    if segments_fix:
                        if segment_zhuanzhes:
                            for zhuanzhedian in segment_zhuanzhes:
                                fig.add_trace(
                                    go.Scatter(
                                        x=[zhuanzhedian['time']],
                                        y=[zhuanzhedian['price']],
                                        mode='markers',
                                        marker=dict(
                                            size=9,
                                            color="rgb(0, 255, 0)"
                                        )
                                    ),
                                    row=GROUP_SIZE_index * 3 + 1, col=1
                                )

                    if segments_fix:
                        # Add Zhongshu Rectangles to the chart
                        draw_zhongshu(fig, segment_zhongshus, row=GROUP_SIZE_index * 3 + 1,
                                      col=GROUP_SIZE_index * 3 + 1, level="segment")
                        # draw_zhongshu(fig, segment_of_segment_zhongshus, row=GROUP_SIZE_index*2 + 2, col=1, level="segment_of_segment")

                        for segment_index, segment in enumerate(segments_fix):
                            fig.add_trace(
                                go.Scatter(
                                    x=[segment['top_time'], segment['bottom_time']],
                                    y=[segment['top_price'], segment['bottom_price']],
                                    mode='lines',
                                    line=dict(color='yellow', width=2.5),
                                    name='segment',
                                    showlegend=False
                                ),
                                row=GROUP_SIZE_index * 3 + 1, col=1
                            )

                            # 计算线段的中点位置
                            middle_time = max(segment['top_time'], segment['bottom_time'])
                            middle_price = segment['bottom_price'] * 0.95

                            # 添加文本
                            fig.add_trace(
                                go.Scatter(
                                    x=[middle_time],
                                    y=[middle_price - 2],  # 位置在线段下方，调整 -5 为适当的偏移值
                                    mode='text',
                                    text=[str(segment_index) + ","],
                                    textfont=dict(color='yellow', size=12),
                                    showlegend=False
                                ),
                                row=GROUP_SIZE_index * 3 + 1, col=1
                            )

                            # 添加线段明确完成点
                            # print(segment["timestamp_segment_complete"], segment["price_segment_complete"])
                            # fig.add_trace(
                            #     go.Scatter(
                            #         x=[segment["timestamp_segment_complete"]],
                            #         y=[segment["price_segment_complete"]],  # 位置在线段下方，调整 -5 为适当的偏移值
                            #         mode='markers',
                            #         marker=dict(
                            #             size=20,
                            #             color="rgb(0, 200, 0)" if segment['direction'] == "Up" else "rgb(200, 0, 0)"
                            #         ),
                            #         name='segment_complete_point',
                            #         showlegend=False
                            #     ),
                            #     row=GROUP_SIZE_index * 3 + 1, col=1
                            # )


                            line_based_on_segment_range = (segment['top_price'] - segment['bottom_price'])/2
                            fig.add_trace(
                                go.Scatter(
                                    x=[segment["timestamp_segment_complete"], segment["timestamp_segment_complete"]],
                                    y=[segment["price_segment_complete"]-line_based_on_segment_range, segment["price_segment_complete"]+line_based_on_segment_range],  # 位置在线段下方，调整 -5 为适当的偏移值
                                    mode='lines',
                                    line=dict(
                                        color="rgb(0, 200, 0)" if segment['direction'] == "Up" else "rgb(200, 0, 0)",
                                        width=1
                                    ),
                                    name='segment_complete_point',
                                    showlegend=False
                                ),
                                row=GROUP_SIZE_index * 3 + 1, col=1
                            )



                    # DIF 线 (MACD 线) 和 DEA 线 (Signal 线)
                    fig.add_trace(go.Scatter(
                        x=MACD_kline_df['timestamp'], y=MACD_kline_df['DIF'], mode='lines', name="DIF (MACD Line)",
                        line=dict(color='blue')
                    ), row=GROUP_SIZE_index * 3 + 3, col=1)
        
                    fig.add_trace(go.Scatter(
                        x=MACD_kline_df['timestamp'], y=MACD_kline_df['DEA'], mode='lines', name="DEA (Signal Line)",
                        line=dict(color='red')
                    ), row=GROUP_SIZE_index * 3 + 3, col=1)
        
                    # MACD 柱状图（增加宽度）
                    fig.add_trace(go.Bar(
                        x=MACD_kline_df['timestamp'],
                        y=MACD_kline_df['MACD'],
                        name="MACD Histogram",
                        width=GROUP_SIZE_FOR_MACD,
                        marker_color=['green' if m >= 0 else 'red' for m in MACD_kline_df['MACD']]
                    ), row=GROUP_SIZE_index * 3 + 3, col=1)
                    # width=50,  # 增加柱状图宽度（时间戳单位为纳秒，具体数值根据数据调整）

                    # 处理后的 K 线图
                    for i in range(len(kline_df_no_inclusion)):
                        color = 'green' if kline_df_no_inclusion.iloc[i]['close'] > kline_df_no_inclusion.iloc[i][
                            'open'] else 'red'
                        fig.add_trace(
                            go.Candlestick(
                                x=[kline_df_no_inclusion.iloc[i]['timestamp']],
                                open=[kline_df_no_inclusion.iloc[i]['open']],
                                close=[kline_df_no_inclusion.iloc[i]['close']],
                                high=[kline_df_no_inclusion.iloc[i]['high']],
                                low=[kline_df_no_inclusion.iloc[i]['low']],
                                increasing_line_color=color,
                                decreasing_line_color=color,
                                showlegend=False
                            ),
                            row=GROUP_SIZE_index * 3 + 2, col=1
                        )

                    # Add fixed Pens to the chart
                    for pen_index, pen in enumerate(fixed_pens):
                        fig.add_trace(
                            go.Scatter(
                                x=[pen['top_time'], pen['bottom_time']],
                                y=[pen['top_price'], pen['bottom_price']],
                                mode='lines',
                                line=dict(color='white', width=2),
                                name='Penfix',
                                showlegend=False
                            ),
                            row=GROUP_SIZE_index * 3 + 2, col=1
                        )
                    draw_zhongshu(fig, pen_zhongshus_clean, row=GROUP_SIZE_index * 3 + 2,
                                  col=GROUP_SIZE_index * 3 + 2, level="pen")

                    # if segments_fix:
                    #     if segment_zhuanzhes:
                    #         for zhuanzhedian in segment_zhuanzhes:
                    #             fig.add_trace(
                    #                 go.Scatter(
                    #                     x=[zhuanzhedian['time']],
                    #                     y=[zhuanzhedian['price']],
                    #                     mode='markers',
                    #                     marker=dict(
                    #                         size=9,
                    #                         color="rgb(0, 255, 0)"
                    #                     )
                    #                 ),
                    #                 row=GROUP_SIZE_index * 3 + 2, col=1
                    #             )

                    if segments_fix:
                        # Add Zhongshu Rectangles to the chart
                        draw_zhongshu(fig, segment_zhongshus_clean, row=GROUP_SIZE_index * 3 + 2,
                                      col=GROUP_SIZE_index * 3 + 2, level="segment")
                        # draw_zhongshu(fig, segment_of_segment_zhongshus, row=GROUP_SIZE_index*2 + 2, col=1, level="segment_of_segment")

                        for segment_index, segment in enumerate(segments_fix):
                            fig.add_trace(
                                go.Scatter(
                                    x=[segment['top_time'], segment['bottom_time']],
                                    y=[segment['top_price'], segment['bottom_price']],
                                    mode='lines',
                                    line=dict(color='yellow', width=2.5),
                                    name='segment',
                                    showlegend=False
                                ),
                                row=GROUP_SIZE_index * 3 + 2, col=1
                            )

                            # 计算线段的中点位置
                            middle_time = max(segment['top_time'], segment['bottom_time'])
                            middle_price = segment['bottom_price'] * 0.95

                            # 添加文本
                            fig.add_trace(
                                go.Scatter(
                                    x=[middle_time],
                                    y=[middle_price - 2],  # 位置在线段下方，调整 -5 为适当的偏移值
                                    mode='text',
                                    text=[str(segment_index) + ","],
                                    textfont=dict(color='yellow', size=12),
                                    showlegend=False
                                ),
                                row=GROUP_SIZE_index * 3 + 2, col=1
                            )

                    # 添加均线
                    fig.add_trace(
                        go.Scatter(
                            x=kline_df['timestamp'],
                            y=kline_df[f'SMA_{duanjunxian_window}'],
                            mode='lines',
                            name=f'{duanjunxian_window}-period SMA',
                            line=dict(color='pink', width=2)
                        ),
                        row=GROUP_SIZE_index * 3 + 2, col=1
                    )

                    # 添加均线
                    fig.add_trace(
                        go.Scatter(
                            x=kline_df['timestamp'],
                            y=kline_df[f'SMA_{changjunxian_window}'],
                            mode='lines',
                            name=f'{changjunxian_window}-period SMA',
                            line=dict(color='purple', width=2)
                        ),
                        row=GROUP_SIZE_index * 3 + 2, col=1
                    )

                def plot_complete(sanmaitype="long", zhichengwei=0):
                    # 更新布局
                    fig.update_layout(
                        title=f'{STOCK_NAME_AND_MARKET} Price Trend and K-Line Chart multi time level',
                        yaxis=dict(
                            title="Price"
                        ),
                        template='plotly_dark',
                        height=500 * (3 * len(GROUP_SIZEs)),
                    )

                    for i in range(len(GROUP_SIZEs) * 3):
                        fig.update_layout({f"xaxis{i+1}": dict(type='category')})
                        fig.update_layout({f"xaxis{i+1}_rangeslider_visible": False})
                        # fig.update_layout({f"xaxis{i + 1}": dict(domain=[0, 1], categoryorder="category ascending")})
                        # fig['layout'][f'xaxis{i + 1}'] = fig['layout'][f'xaxis{int(i/3)+1}']

                    # 显示图表
                    # fig.show()
                    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

                    # 生成文件名
                    file_name_record_if_sanmai = f"sanmaiplot/{current_time}_{STOCK_NAME_AND_MARKET}_{GROUP_SIZEs[0]*6}_second_{sanmaitype}_zhichengwei_{zhichengwei}.png"

                    fig.write_image(file_name_record_if_sanmai, width=3000, height=2500)



                need_qujiantao = False #判断是否要用区间套分析当前未完成笔

                if segment_zhongshus_clean and len(segment_zhongshus_clean) >= 2 and GROUP_SIZE_index == 0 and current_status == "empty":
                    # 三买
                    # 两种情况，
                    # 一种是三买形成前的一笔上拉已经完成，但三买前的一笔回拉还没有完成
                    # 另一种, 三买形成前的一笔上拉完成得比较晚，三买前的一笔回拉也已经完成
                    #趋势后
                    if segment_zhongshus_clean[-1]['ZG'] <= segment_zhongshus_clean[-2]['ZD']: # 这里用清理过的中枢, 但后面都用粗糙中枢
                            if segments_fix[-1]['direction'] == "Up":
                                if segments_fix[-1]['top_price'] > segment_zhongshus[-1]['ZG']: #价格突破中枢了
                                    if (df.iloc[-1]['price'] > segment_zhongshus[-1]['ZG']): #暂时还没拉回中枢
                                        need_qujiantao = True
                                        if PRINT_HUICE_RETURN_INFO:
                                            print("去确认三买")
                                        da_jibie_xianduanjieshu_time = segments_fix[-1]['top_time']
                                        fangxiang_before_beichi = "Down"
                                        current_status = "check_sanlong"  # "empty", "check_sanlong", "check_sanshort", "sanlong_in_position", "sanshort_in_position"
                                        check_sanmaisanmai_zhicheng = segment_zhongshus[-1]['ZG']
                                        if SHOW_FIG_WHEN_SELL_BUY_ACTION:
                                            plot_if_sanmai('long', "visualize_for_test")
                    elif sanmai_info == "long" and len(segment_zhongshus_clean) >= 3 and segment_zhongshus_clean[-2]['ZG'] <= segment_zhongshus_clean[-3]['ZD']: #三买前的一笔回拉已经出现的话，segment_zhongshus_clean已经帮助判断了是否是三买
                        if (df.iloc[-1]['price'] > segment_zhongshus[-1]['ZG']):  #暂时还没拉回中枢
                            need_qujiantao = True
                            if PRINT_HUICE_RETURN_INFO:
                                print(f"三买已确认, 建仓价格{df.iloc[-1]['price']},建仓时间{df.iloc[-1]['timestamp']}")
                            da_jibie_xianduanjieshu_time = segments_fix[-1]['bottom_time']
                            fangxiang_before_beichi = "Up"
                            current_status = "sanlong_in_position"  # "empty", "check_sanlong", "check_sanshort", "sanlong_in_position", "sanshort_in_position"
                            check_sanmaisanmai_zhicheng = segment_zhongshus[-1]['ZG']
                            jiancang_time = df.iloc[-1]['timestamp']
                            jiancang_price = df.iloc[-1]['price']
                            if INFO_SAVE_TO_FILE_MODE:
                                data_sanmai = {
                                    "sanmai_state": "三买确认",
                                    "price": f"{df.iloc[-1]['price']}",
                                    "time": f"{df.iloc[-1]['timestamp']}"
                                }
                                write_to_sanmai_info_file(data_sanmai)
                            if SHOW_FIG_WHEN_SELL_BUY_ACTION:
                                plot_if_sanmai('long', "visualize_for_test")
                                plot_complete('long', "visualize_for_test")
                                fig.show()

                    # 三卖
                    # 两种情况，
                    # 一种是三卖形成前的一笔下拉已经完成，但三卖前的一笔回拉还没有完成
                    # 另一种, 三卖形成前的一笔下拉完成得比较晚，三卖前的一笔回拉也已经完成
                    # 趋势后
                    if segment_zhongshus_clean[-1]['ZD'] >= segment_zhongshus_clean[-2][
                        'ZG']:  # 这里用清理过的中枢, 但后面都用粗糙中枢
                        if segments_fix[-1]['direction'] == "Down":
                            if segments_fix[-1]['bottom_price'] < segment_zhongshus[-1]['ZD']:  # 价格突破中枢了
                                if (df.iloc[-1]['price'] < segment_zhongshus[-1]['ZD']):  # 暂时还没拉回中枢
                                    need_qujiantao = True
                                    if PRINT_HUICE_RETURN_INFO:
                                        print("去确认三卖")
                                    da_jibie_xianduanjieshu_time = segments_fix[-1]['bottom_time']
                                    fangxiang_before_beichi = "Up"
                                    current_status = "check_sanshort"  # "empty", "check_sanlong", "check_sanshort", "sanlong_in_position", "sanshort_in_position"
                                    check_sanmaisanmai_zhicheng = segment_zhongshus[-1]['ZD']
                                    if SHOW_FIG_WHEN_SELL_BUY_ACTION:
                                        plot_if_sanmai('short', "visualize_for_test")
                    elif sanmai_info == "short" and len(segment_zhongshus_clean) >= 3 and segment_zhongshus_clean[-2]['ZD'] >= segment_zhongshus_clean[-3]['ZG']:  # 三卖前的一笔回拉已经出现的话，segment_zhongshus_clean已经帮助判断了是否是三卖
                        if (df.iloc[-1]['price'] < segment_zhongshus[-1]['ZD']):  # 暂时还没拉回中枢
                            need_qujiantao = True
                            if PRINT_HUICE_RETURN_INFO:
                                print(f"三卖已确认, 建仓价格{df.iloc[-1]['price']},建仓时间{df.iloc[-1]['timestamp']}")
                            da_jibie_xianduanjieshu_time = segments_fix[-1]['top_time']
                            fangxiang_before_beichi = "Down"
                            current_status = "sanshort_in_position"  # "empty", "check_sanlong", "check_sanshort", "sanlong_in_position", "sanshort_in_position"
                            check_sanmaisanmai_zhicheng = segment_zhongshus[-1]['ZD']
                            jiancang_time = df.iloc[-1]['timestamp']
                            jiancang_price = df.iloc[-1]['price']
                            if INFO_SAVE_TO_FILE_MODE:
                                data_sanmai = {
                                    "sanmai_state": "三卖确认",
                                    "price": f"{df.iloc[-1]['price']}",
                                    "time": f"{df.iloc[-1]['timestamp']}"
                                }
                                write_to_sanmai_info_file(data_sanmai)
                            if SHOW_FIG_WHEN_SELL_BUY_ACTION:
                                plot_if_sanmai('short', "visualize_for_test")
                                plot_complete('short', "visualize_for_test")
                                fig.show()
                            # if 三卖点后没有出现次级别中枢背驰就建仓，首先判断这个中枢方向，需要是向下，但如果这个中枢跨过三卖，那么它是一个盘整，单独考虑

                # 持仓中，如果出现小级别背驰就平仓, 所以要确保会进入小级别分析
                elif GROUP_SIZE_index == 0 and (current_status in ["sanlong_in_position", "sanshort_in_position"]):

                    if max(segments_fix[-1]['bottom_time'], segments_fix[-1]['top_time']) >= jiancang_time \
                        and ((current_status == "sanshort_in_position" and segments_fix[-1]["direction"] == "Down") or (current_status == "sanlong_in_position" and segments_fix[-1]["direction"] == "Up")):
                        #当前三买三卖后次级别已经结束
                        current_status = "empty"  # "empty", "check_sanlong", "check_sanshort", "sanlong_in_position", "sanshort_in_position"
                        jiancang_time = pd.to_datetime("2000-12-17 15:19:07")
                        jiancang_price = 0
                        need_qujiantao = False
                        if PRINT_HUICE_RETURN_INFO:
                            print(f"平仓头寸止盈止损, 平仓价格{df.iloc[-1]['price']},平仓时间{df.iloc[-1]['timestamp']}")
                        if INFO_SAVE_TO_FILE_MODE:
                            data_sanmai = {
                                "sanmai_state": "平仓",
                                "price": f"{df.iloc[-1]['price']}",
                                "time": f"{df.iloc[-1]['timestamp']}"
                            }
                            write_to_sanmai_info_file(data_sanmai)
                        if SHOW_FIG_WHEN_SELL_BUY_ACTION:
                            plot_if_sanmai('stop', "visualize_for_test")
                            plot_complete('stop', "visualize_for_test")
                            fig.show()
                        if not (PRINT_PROCESS_INFO and (not SHOW_FIG_WHEN_SELL_BUY_ACTION)):
                            break
                    if current_status == "sanlong_in_position":
                        if df.iloc[-1]['price'] < check_sanmaisanmai_zhicheng:
                            current_status = "empty"  # "empty", "check_sanlong", "check_sanshort", "sanlong_in_position", "sanshort_in_position"
                            jiancang_time = pd.to_datetime("2000-12-17 15:19:07")
                            jiancang_price = 0
                            need_qujiantao = False
                            if PRINT_HUICE_RETURN_INFO:
                                print(f"出现盘整平仓多头头寸止盈止损, 平仓价格{df.iloc[-1]['price']},平仓时间{df.iloc[-1]['timestamp']}")
                            if INFO_SAVE_TO_FILE_MODE:
                                data_sanmai = {
                                    "sanmai_state": "平仓",
                                    "price": f"{df.iloc[-1]['price']}",
                                    "time": f"{df.iloc[-1]['timestamp']}"
                                }
                                write_to_sanmai_info_file(data_sanmai)
                            if SHOW_FIG_WHEN_SELL_BUY_ACTION:
                                plot_if_sanmai('stop', "visualize_for_test")
                                plot_complete('stop', "visualize_for_test")
                                fig.show()
                            if not (PRINT_PROCESS_INFO and (not SHOW_FIG_WHEN_SELL_BUY_ACTION)):
                                break
                        need_qujiantao = True
                        fangxiang_before_beichi = "Up"
                        plot_if_sanmai('long_stop', "visualize_for_test")
                    elif current_status == "sanshort_in_position":
                        if df.iloc[-1]['price'] > check_sanmaisanmai_zhicheng:
                            current_status = "empty"  # "empty", "check_sanlong", "check_sanshort", "sanlong_in_position", "sanshort_in_position"
                            jiancang_time = pd.to_datetime("2000-12-17 15:19:07")
                            jiancang_price = 0
                            need_qujiantao = False
                            if PRINT_HUICE_RETURN_INFO:
                                print(f"出现盘整平仓空头头寸止盈止损, 平仓价格{df.iloc[-1]['price']},平仓时间{df.iloc[-1]['timestamp']}")
                            if INFO_SAVE_TO_FILE_MODE:
                                data_sanmai = {
                                    "sanmai_state": "平仓",
                                    "price": f"{df.iloc[-1]['price']}",
                                    "time": f"{df.iloc[-1]['timestamp']}"
                                }
                                write_to_sanmai_info_file(data_sanmai)
                            if SHOW_FIG_WHEN_SELL_BUY_ACTION:
                                plot_if_sanmai('stop', "visualize_for_test")
                                plot_complete('stop', "visualize_for_test")
                                fig.show()
                            if not (PRINT_PROCESS_INFO and (not SHOW_FIG_WHEN_SELL_BUY_ACTION)):
                                break
                        need_qujiantao = True
                        fangxiang_before_beichi = "Down"
                        plot_if_sanmai('short_stop', "visualize_for_test")

                elif GROUP_SIZE_index == 0 and (current_status in ["check_sanlong", "check_sanshort"]):
                    if current_status == "check_sanlong":
                        # confirm_sanmai_segment_i, confirm_sanmai_segment = next(((i, segment) for i, segment in enumerate(segments_fix) if
                        #       max(segment['bottom_time'], segment['top_time']) > da_jibie_xianduanjieshu_time and
                        #       segment['direction'] == "Down"), None)

                        if not isinstance(segments_fix, list):
                            confirm_sanmai_segment_i, confirm_sanmai_segment = None, None
                        else:
                            result = next(((i, segment) for i, segment in enumerate(segments_fix) if
                                           min(segment['bottom_time'],
                                               segment['top_time']) > da_jibie_xianduanjieshu_time and
                                           segment['direction'] == "Down"), None)

                            if result is not None:
                                confirm_sanmai_segment_i, confirm_sanmai_segment = result
                            else:
                                confirm_sanmai_segment_i, confirm_sanmai_segment = None, None
                        if confirm_sanmai_segment_i is None:
                            if PRINT_PROCESS_INFO and (not SHOW_FIG_WHEN_SELL_BUY_ACTION):
                                plot_if_sanmai('test', "visualize_for_test")
                            break

                        if confirm_sanmai_segment_i == len(segments_fix)-1 and (check_sanmaisanmai_zhicheng < df.iloc[-1]['price']):
                            #三买刚刚出现, 可以介入
                            need_qujiantao = True
                            if PRINT_HUICE_RETURN_INFO:
                                print(f"三买已确认, 建仓价格{df.iloc[-1]['price']},建仓时间{df.iloc[-1]['timestamp']}")
                            da_jibie_xianduanjieshu_time = segments_fix[-1]['bottom_time']
                            fangxiang_before_beichi = "Up"
                            current_status = "sanlong_in_position"  # "empty", "check_sanlong", "check_sanshort", "sanlong_in_position", "sanshort_in_position"
                            check_sanmaisanmai_zhicheng = segment_zhongshus[-1]['ZG']
                            jiancang_time = df.iloc[-1]['timestamp']
                            jiancang_price = df.iloc[-1]['price']
                            if INFO_SAVE_TO_FILE_MODE:
                                data_sanmai = {
                                    "sanmai_state": "三买确认",
                                    "price": f"{df.iloc[-1]['price']}",
                                    "time": f"{df.iloc[-1]['timestamp']}"
                                }
                                write_to_sanmai_info_file(data_sanmai)
                            if SHOW_FIG_WHEN_SELL_BUY_ACTION:
                                plot_if_sanmai('long', "visualize_for_test")
                                plot_complete('long', "visualize_for_test")
                                fig.show()
                        else:
                            # 三买出现后已经出现下一段，放弃这个交易机会
                            if PRINT_HUICE_RETURN_INFO:
                                print(f"三买出现后已经出现下一段，不值得交易, 价格{df.iloc[-1]['price']},时间{df.iloc[-1]['timestamp']}")
                            current_status = "empty"  # "empty", "check_sanlong", "check_sanshort", "sanlong_in_position", "sanshort_in_position"
                            jiancang_time = pd.to_datetime("2000-12-17 15:19:07")
                            jiancang_price = 0
                            need_qujiantao = False
                            if INFO_SAVE_TO_FILE_MODE:
                                data_sanmai = {
                                    "sanmai_state": "三买确认但不建仓",
                                    "price": f"{df.iloc[-1]['price']}",
                                    "time": f"{df.iloc[-1]['timestamp']}"
                                }
                                write_to_sanmai_info_file(data_sanmai)
                            if SHOW_FIG_WHEN_SELL_BUY_ACTION:
                                plot_if_sanmai('long_stop', "visualize_for_test")
                                plot_complete('long_stop', "visualize_for_test")
                                fig.show()
                    elif current_status == "check_sanshort":
                        # confirm_sanmai_segment_i, confirm_sanmai_segment = next(((i, segment) for i, segment in enumerate(segments_fix) if
                        #       max(segment['bottom_time'], segment['top_time']) > da_jibie_xianduanjieshu_time and
                        #       segment['direction'] == "Up"), None)

                        if not isinstance(segments_fix, list):
                            confirm_sanmai_segment_i, confirm_sanmai_segment = None, None
                        else:
                            result = next(((i, segment) for i, segment in enumerate(segments_fix) if
                                           min(segment['bottom_time'],
                                               segment['top_time']) > da_jibie_xianduanjieshu_time and
                                           segment['direction'] == "Up"), None)

                            if result is not None:
                                confirm_sanmai_segment_i, confirm_sanmai_segment = result
                            else:
                                confirm_sanmai_segment_i, confirm_sanmai_segment = None, None
                        if confirm_sanmai_segment_i is None:
                            if PRINT_PROCESS_INFO and (not SHOW_FIG_WHEN_SELL_BUY_ACTION):
                                plot_if_sanmai('test', "visualize_for_test")
                            break


                        if confirm_sanmai_segment_i == len(segments_fix)-1 and (check_sanmaisanmai_zhicheng > df.iloc[-1]['price']):
                            #三卖刚刚出现, 可以介入
                            need_qujiantao = True
                            if PRINT_HUICE_RETURN_INFO:
                                print(f"三卖已确认, 建仓价格{df.iloc[-1]['price']},建仓时间{df.iloc[-1]['timestamp']}")
                            da_jibie_xianduanjieshu_time = segments_fix[-1]['top_time']
                            fangxiang_before_beichi = "Down"
                            current_status = "sanshort_in_position"  # "empty", "check_sanlong", "check_sanshort", "sanlong_in_position", "sanshort_in_position"
                            check_sanmaisanmai_zhicheng = segment_zhongshus[-1]['ZD']
                            jiancang_time = df.iloc[-1]['timestamp']
                            jiancang_price = df.iloc[-1]['price']
                            if INFO_SAVE_TO_FILE_MODE:
                                data_sanmai = {
                                    "sanmai_state": "三卖确认",
                                    "price": f"{df.iloc[-1]['price']}",
                                    "time": f"{df.iloc[-1]['timestamp']}"
                                }
                                write_to_sanmai_info_file(data_sanmai)
                            if SHOW_FIG_WHEN_SELL_BUY_ACTION:
                                plot_if_sanmai('short', "visualize_for_test")
                                plot_complete('short', "visualize_for_test")
                                fig.show()
                        else:
                            # 三卖出现后已经出现下一段，放弃这个交易机会
                            if PRINT_HUICE_RETURN_INFO:
                                print(f"三卖出现后已经出现下一段，不值得交易, 价格{df.iloc[-1]['price']},时间{df.iloc[-1]['timestamp']}")
                            current_status = "empty"  # "empty", "check_sanlong", "check_sanshort", "sanlong_in_position", "sanshort_in_position"
                            jiancang_time = pd.to_datetime("2000-12-17 15:19:07")
                            jiancang_price = 0
                            need_qujiantao = False
                            if INFO_SAVE_TO_FILE_MODE:
                                data_sanmai = {
                                    "sanmai_state": "三卖确认但不建仓",
                                    "price": f"{df.iloc[-1]['price']}",
                                    "time": f"{df.iloc[-1]['timestamp']}"
                                }
                                write_to_sanmai_info_file(data_sanmai)
                            if SHOW_FIG_WHEN_SELL_BUY_ACTION:
                                plot_if_sanmai('short_stop', "visualize_for_test")
                                plot_complete('short_stop', "visualize_for_test")
                                fig.show()



                if GROUP_SIZE_index == 1:
                    # if (segment_zhongshus[-1]['end_time'] > da_jibie_xianduanjieshu_time and current_status in ["check_sanlong", "check_sanshort"]) or (True): #有中枢用来判断背驰
                    if len(segment_zhongshus) == 0:
                        if PRINT_PROCESS_INFO and (not SHOW_FIG_WHEN_SELL_BUY_ACTION):
                            plot_if_sanmai('test', "visualize_for_test")
                        break
                    # 有中枢用来判断背驰, 如果是在确认三买三卖中枢就要在前面的线段后，如果在三买三卖建仓后找背离，就要在建仓时间后
                    if ((current_status in ["check_sanlong", "check_sanshort"]) and (segment_zhongshus[-1]['end_time'] > da_jibie_xianduanjieshu_time)) or ((current_status in [
                        "sanlong_in_position", "sanshort_in_position"]) and segment_zhongshus[-1]['end_time'] > jiancang_time):

                        if fangxiang_before_beichi == "Down":

                            # 找到最后一个满足条件的 segment
                            filtered_zhongshus_clean_no_last_item = segment_zhongshus_clean[:-1] if segment_zhongshus_clean and segment_zhongshus_clean[-1]['core_pens_index'][-1] == len(segments_fix) - 1 else segment_zhongshus_clean
                            zhongshu_to_check_beichi = next(
                                (zhongshu for zhongshu in reversed(filtered_zhongshus_clean_no_last_item) if
                                 zhongshu["direction"] == "Down" and zhongshu['start_time'] > da_jibie_xianduanjieshu_time),
                                None
                            )
                            if zhongshu_to_check_beichi is not None:
                                last_index = zhongshu_to_check_beichi['core_pens_index'][-1]
                                into_seg = segments_fix[last_index - 1]  # 进入段
                                leave_seg = segments_fix[last_index + 1]  # 离开段


                                # if segments_fix[segment_zhongshus[-1]['core_pens_index'][-1]]['direction'] == "Down":
                                #     into_seg = segments_fix[segment_zhongshus[-1]['core_pens_index'][-1]-2]  # 进入段
                                #     leave_seg = segments_fix[segment_zhongshus[-1]['core_pens_index'][-1]]  #离开段
                                # else:
                                #     into_seg = segments_fix[segment_zhongshus[-1]['core_pens_index'][-1] - 1]  # 进入段
                                #     leave_seg = segments_fix[segment_zhongshus[-1]['core_pens_index'][-1] + 1]  # 离开段

                                beichi = (leave_seg['top_price'] / leave_seg['bottom_price'] < into_seg['top_price'] /
                                          into_seg['bottom_price'])
                                if beichi:  # 这里要完善的，还没定义方向是不是我要找的方向
                                    if current_status == "check_sanlong":
                                        # if (len(segment_zhongshus_clean) > 0) and segment_zhongshus_clean[-1][
                                        #     'direction'] == "Down" and \
                                        #         any(item['start_time'] > da_jibie_xianduanjieshu_time and item[
                                        #             'direction'] == "Up" for item in segment_zhongshus_clean):
                                        if (len(segment_zhongshus_clean) > 0) and \
                                                any(item['start_time'] > da_jibie_xianduanjieshu_time and item[
                                                    'direction'] == "Up" for item in segment_zhongshus_clean):

                                            # if into_seg['top_time'] >= da_jibie_xianduanjieshu_time and (df.iloc[-1]['price'] > check_sanmaisanmai_zhicheng):
                                            if df.iloc[-1]['price'] > check_sanmaisanmai_zhicheng:
                                                if PRINT_HUICE_RETURN_INFO:
                                                    print(f"背驰了，三买可以介入了, 建仓价格{df.iloc[-1]['price']},建仓时间{df.iloc[-1]['timestamp']}")
                                                current_status = "sanlong_in_position"  # "empty", "check_sanlong", "check_sanshort", "sanlong_in_position", "sanshort_in_position"
                                                check_sanmaisanmai_zhicheng = segment_zhongshus[-1]['ZG']
                                                jiancang_time = df.iloc[-1]['timestamp']
                                                jiancang_price = df.iloc[-1]['price']
                                                if INFO_SAVE_TO_FILE_MODE:
                                                    data_sanmai = {
                                                        "sanmai_state": "三买确认",
                                                        "price": f"{df.iloc[-1]['price']}",
                                                        "time": f"{df.iloc[-1]['timestamp']}"
                                                    }
                                                    write_to_sanmai_info_file(data_sanmai)
                                                if SHOW_FIG_WHEN_SELL_BUY_ACTION:
                                                    plot_if_sanmai('long_or_short', "visualize_for_test")
                                                    plot_complete('long_or_short', "visualize_for_test")
                                                    fig.show()
                                    if current_status == "sanshort_in_position":
                                        if (len(segment_zhongshus_clean) > 0) and segment_zhongshus_clean[-1][
                                            'direction'] == "Down" and \
                                                any(item['start_time'] > da_jibie_xianduanjieshu_time and item[
                                                    'direction'] == "Up" for item in segment_zhongshus_clean):
                                            if into_seg['top_time'] >= da_jibie_xianduanjieshu_time:
                                                if PRINT_HUICE_RETURN_INFO:
                                                    print(f"背驰了，将空头头寸平仓，平仓价格{df.iloc[-1]['price']},平仓时间{df.iloc[-1]['timestamp']}")
                                                current_status = "empty"  # "empty", "check_sanlong", "check_sanshort", "sanlong_in_position", "sanshort_in_position"
                                                jiancang_time = pd.to_datetime("2000-12-17 15:19:07")
                                                jiancang_price = 0
                                                need_qujiantao = False
                                                if INFO_SAVE_TO_FILE_MODE:
                                                    data_sanmai = {
                                                        "sanmai_state": "平仓",
                                                        "price": f"{df.iloc[-1]['price']}",
                                                        "time": f"{df.iloc[-1]['timestamp']}"
                                                    }
                                                    write_to_sanmai_info_file(data_sanmai)
                                                if SHOW_FIG_WHEN_SELL_BUY_ACTION:
                                                    plot_if_sanmai('short_stop', "visualize_for_test")
                                                    plot_complete('short_stop', "visualize_for_test")
                                                    fig.show()

                        elif fangxiang_before_beichi == "Up":
                            # 找到最后一个满足条件的 segment
                            filtered_zhongshus_clean_no_last_item = segment_zhongshus_clean[:-1] if segment_zhongshus_clean and segment_zhongshus_clean[-1]['core_pens_index'][-1] == len(segments_fix) - 1 else segment_zhongshus_clean
                            zhongshu_to_check_beichi = next(
                                (zhongshu for zhongshu in reversed(filtered_zhongshus_clean_no_last_item) if
                                 zhongshu["direction"] == "Up" and zhongshu[
                                     'start_time'] > da_jibie_xianduanjieshu_time),
                                None
                            )
                            if zhongshu_to_check_beichi is not None:
                                last_index = zhongshu_to_check_beichi['core_pens_index'][-1]
                                into_seg = segments_fix[last_index - 1]  # 进入段
                                leave_seg = segments_fix[last_index + 1]  # 离开段


                                # if segments_fix[segment_zhongshus[-1]['core_pens_index'][-1]]['direction'] == "Up":
                                #     into_seg = segments_fix[segment_zhongshus[-1]['core_pens_index'][-1]-2]  # 进入段
                                #     leave_seg = segments_fix[segment_zhongshus[-1]['core_pens_index'][-1]]  #离开段
                                # else:
                                #     into_seg = segments_fix[segment_zhongshus[-1]['core_pens_index'][-1] - 1]  # 进入段
                                #     leave_seg = segments_fix[segment_zhongshus[-1]['core_pens_index'][-1] + 1]  # 离开段

                                beichi = (leave_seg['top_price'] / leave_seg['bottom_price'] < into_seg['top_price'] /
                                          into_seg['bottom_price'])
                                if beichi:  # 这里要完善的，还没定义方向是不是我要找的方向
                                    if current_status == "check_sanshort":
                                        # if (len(segment_zhongshus_clean) > 0) and segment_zhongshus_clean[-1][
                                        #     'direction'] == "Up" and \
                                        #         any(item['start_time'] > da_jibie_xianduanjieshu_time and item[
                                        #             'direction'] == "Down" for item in segment_zhongshus_clean):
                                        if (len(segment_zhongshus_clean) > 0) and \
                                                any(item['start_time'] > da_jibie_xianduanjieshu_time and item[
                                                    'direction'] == "Down" for item in segment_zhongshus_clean):
                                            #if into_seg['bottom_time'] >= da_jibie_xianduanjieshu_time and (df.iloc[-1]['price'] < check_sanmaisanmai_zhicheng):
                                            if df.iloc[-1]['price'] < check_sanmaisanmai_zhicheng:
                                                if PRINT_HUICE_RETURN_INFO:
                                                    print(f"背驰了，三卖可以介入了, 建仓价格{df.iloc[-1]['price']},建仓时间{df.iloc[-1]['timestamp']}")
                                                current_status = "sanshort_in_position"  # "empty", "check_sanlong", "check_sanshort", "sanlong_in_position", "sanshort_in_position"
                                                check_sanmaisanmai_zhicheng = segment_zhongshus[-1]['ZD']
                                                jiancang_time = df.iloc[-1]['timestamp']
                                                jiancang_price = df.iloc[-1]['price']
                                                if INFO_SAVE_TO_FILE_MODE:
                                                    data_sanmai = {
                                                        "sanmai_state": "三卖确认",
                                                        "price": f"{df.iloc[-1]['price']}",
                                                        "time": f"{df.iloc[-1]['timestamp']}"
                                                    }
                                                    write_to_sanmai_info_file(data_sanmai)
                                                if SHOW_FIG_WHEN_SELL_BUY_ACTION:
                                                    plot_if_sanmai('long_or_short', "visualize_for_test")
                                                    plot_complete('long_or_short', "visualize_for_test")
                                                    fig.show()
                                    if current_status == "sanlong_in_position":
                                        if (len(segment_zhongshus_clean) > 0) and segment_zhongshus_clean[-1][
                                            'direction'] == "Up" and \
                                                any(item['start_time'] > da_jibie_xianduanjieshu_time and item[
                                                    'direction'] == "Down" for item in segment_zhongshus_clean):
                                            if into_seg['bottom_time'] >= da_jibie_xianduanjieshu_time:
                                                if PRINT_HUICE_RETURN_INFO:
                                                    print(f"背驰了，将多头头寸平仓，平仓价格{df.iloc[-1]['price']},平仓时间{df.iloc[-1]['timestamp']}")
                                                current_status = "empty"  # "empty", "check_sanlong", "check_sanshort", "sanlong_in_position", "sanshort_in_position"
                                                jiancang_time = pd.to_datetime("2000-12-17 15:19:07")
                                                jiancang_price = 0
                                                need_qujiantao = False
                                                if INFO_SAVE_TO_FILE_MODE:
                                                    data_sanmai = {
                                                        "sanmai_state": "平仓",
                                                        "price": f"{df.iloc[-1]['price']}",
                                                        "time": f"{df.iloc[-1]['timestamp']}"
                                                    }
                                                    write_to_sanmai_info_file(data_sanmai)
                                                if SHOW_FIG_WHEN_SELL_BUY_ACTION:
                                                    plot_if_sanmai('long_stop', "visualize_for_test")
                                                    plot_complete('long_stop', "visualize_for_test")
                                                    fig.show()








                if PRINT_PROCESS_INFO and (not SHOW_FIG_WHEN_SELL_BUY_ACTION):
                    plot_if_sanmai('test', "visualize_for_test")
                if (not need_qujiantao) and (not (PRINT_PROCESS_INFO and (not SHOW_FIG_WHEN_SELL_BUY_ACTION))):
                    break
                if GROUP_SIZE_index == 0:
                    # df = df[df['timestamp'] >= segment_zhongshus_clean[-1]['start_time']]
                    # df = df[df['timestamp'] >= min(segments_fix[-1]['top_time'], segments_fix[-1]['bottom_time'])]
                    df = df[df['timestamp'] >= min(segments_fix[-2]['top_time'], segments_fix[-2]['bottom_time'])]
            if PRINT_PROCESS_INFO and (not SHOW_FIG_WHEN_SELL_BUY_ACTION):
                plot_complete('test', "visualize_for_test")
                fig.show()
            # 结束计时


            end_time = time.time()

            # 计算运行时间
            elapsed_time = end_time - start_time
            if PRINT_PROCESS_INFO:
                # 打印运行时间（秒）
                print(f"运行时间：{elapsed_time:.2f} 秒***********************************************************")

        # time.sleep(300)  # Wait for 300 seconds (5 minutes) before the next attempt
        # time.sleep(600)  # Wait for 600 seconds (10 minutes) before the next attempt




        



