import pandas as pd
import glob
import os
import pytz
import holidays
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
from datetime import time as datetime_time
import time
from copy import deepcopy
import argparse
from chanlun_utils import generate_kline_data, generate_kline_data_group_points, handle_kline_inclusion_with_trend, find_pens_from_kline, find_pens_from_kline_need_fixed, pens_fix, generate_feature_sequence, merge_pens_to_segments, merge_pens_to_segments_based_on_pen_zhongshu, find_zhongshu, find_zhongshu_and_cijibie_qushi, find_zhongshu_csy_steps, find_zhongshu_csy_inverse_look_steps, find_zhongshu_new, find_zhongshu_based_on_looking_for_next_zhongshu, find_zhongshu_one_pen_can_be_a_zhongshu, find_zhongshu_one_pen_brute, find_zhongshu_one_pen_form, clean_zhongshu_detailed, calculate_macd
from chanlun_utils import draw_zhongshu, CurrentPlay, save_new_segments_fix_to_checkpoint, save_new_segments_fix_to_checkpoint_pen, merge_segments_fix_with_checkpoint, ensure_datetime, same_level_or_higher_level_before, check_zhongshu_kuozhang, zhongshu_kuozhang_merge_same_dir, greater_then_least_samelevel_tolerant, greater_then_least_samelevel_strict, merge_zhongshu_with_checkpoint, save_new_pen_zhongshu_to_checkpoint
import copy




# 计算均线
def add_moving_average(kline_df, window=10):
    kline_df[f'SMA_{window}'] = kline_df['close'].rolling(window=window).mean()
    return kline_df




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
                        help="设置为 True 时, 出现买卖和平仓信号时会把图片在本地某个端口画出来")

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
    # GROUP_SIZEs = [GROUP_SIZE_FOE_HIGH_LEVEL, GROUP_SIZE_FOE_LOW_LEVEL]
    GROUP_SIZEs = [GROUP_SIZE_FOE_HIGH_LEVEL]
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

    def write_to_ermai_info_file(data_ermai_argue):
        ermai_folder_path = "ermai_caozuo"
        ermai_file_name = f"{STOCK_NAME_AND_MARKET}_{GROUP_SIZEs[0] * 6}_second_ermai_caozuo.csv"
        ermai_file_path = os.path.join(ermai_folder_path, ermai_file_name)
        # 确保文件夹存在
        os.makedirs(ermai_folder_path, exist_ok=True)
        # 判断文件是否已存在
        file_exists = os.path.isfile(ermai_file_path)
        df_data_sanmai = pd.DataFrame([data_ermai_argue])
        df_data_sanmai.to_csv(ermai_file_path, mode='a', header=not file_exists, index=False, encoding='utf-8-sig')



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



    last_operation_confirm_time = pd.to_datetime("2000-12-17 15:19:07")
    # last_operation_confirm_time = "2000-12-17 15:19:07"
    current_play = CurrentPlay()


    ############################### 全时间回测用 ###############################
    ########################线上实盘到全时间回测记得切换#########################
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
    # # return_test_timestamps = return_test_generate_timestamps("2025-01-15 17:19:07", "2025-03-11 15:10:07", 30)
    # # return_test_timestamps = return_test_generate_timestamps("2025-02-26 20:19:07", "2025-03-11 15:10:07", 30)
    # # time_until_list = return_test_timestamps[398:2000]
    # # time_until_list = return_test_timestamps[499:2000]
    # # time_until_list = [return_test_timestamps[i] for i in [553, 554, 564, 565, 607, 608, 623]]
    # return_test_timestamps = return_test_generate_timestamps("2024-12-15 17:19:07", "2025-03-11 15:10:07", 30)
    # # time_until_list = return_test_timestamps[500:2000] #for 120 second
    # # time_until_list = return_test_timestamps[50:2000]  # for 30 second
    # time_until_list = return_test_timestamps[312:2000]  # for 30 second
    # time_until_list = [return_test_timestamps[i] for i in [317, 325, 326, 327, 332]] # for META test
    #
    # return_test_timestamps = return_test_generate_timestamps("2024-12-15 17:19:07", "2025-03-11 15:10:07", 10)
    # # time_until_list = return_test_timestamps[900:3000]  # for 30 second
    # # time_until_list = return_test_timestamps[880:3000]  # for 30 second
    # # time_until_list = [return_test_timestamps[i] for i in range(951, 999)]  # for META test
    #
    # # 针对U_NYSE，1分钟对6秒的卖点错失
    # # return_test_timestamps = return_test_generate_timestamps("2024-12-15 17:19:07", "2025-03-11 15:10:07", 10)
    # # time_until_list = [return_test_timestamps[i] for i in [857, 858, 860, 927, 1210, 2000]] #857其实已经三卖确立, 927已经可以平仓
    #
    # # return_test_timestamps = return_test_generate_timestamps("2024-12-15 17:19:07", "2025-03-11 15:10:07", 10)
    # # time_until_list = [return_test_timestamps[i] for i in [1900]]
    #
    #
    # # 看一下全时长总体，如果是6秒级的话跑得会很慢
    # return_test_timestamps = return_test_generate_timestamps("2024-12-15 17:19:07", "2025-05-24 15:10:07", 10)
    # return_test_timestamps = return_test_generate_timestamps("2025-01-01 17:19:07", "2025-05-16 18:10:07", 10)
    # return_test_timestamps = return_test_generate_timestamps("2025-01-01 17:19:07", "2025-06-02 18:10:07", 10)
    #
    # time_until_list = [return_test_timestamps[i] for i in [-19, -1]]
    # # time_until_list = return_test_timestamps[312:2000]
    #
    #
    #
    # # # 大时间间隔观察一下
    # # return_test_timestamps = return_test_generate_timestamps("2024-12-15 17:19:07", "2025-03-11 15:10:07", 180)
    # # time_until_list = return_test_timestamps[17:]
    #
    # # time_until_list = [return_test_timestamps[i] for i in [500, 505, 506, 507, 508]]
    # # time_until_list = return_test_timestamps[-2:]
    # # time_until_list = [return_test_timestamps[i] for i in [900, 901]]
    # print(len(return_test_timestamps))
    # if PRINT_PROCESS_INFO and (not PRINT_HUICE_RETURN_INFO) and (not INFO_SAVE_TO_FILE_MODE):
    #     # time_until_list = [return_test_timestamps[i] for i in [901]]
    #     # time_until_list = [return_test_timestamps[i] for i in [650]]
    #     time_until_list = return_test_timestamps[-len(return_test_timestamps) + 1000:-1]
    #     time_from_list = return_test_timestamps[-len(return_test_timestamps) + 430:-571]
    #     time_until_list = [return_test_timestamps[i] for i in [-80, -60, -40, -30, -1]]
    #     time_from_list = [return_test_timestamps[i] for i in [-650, -630, -610, -600, -571]]
    #
    #
    #     # time_until_list = [return_test_timestamps[i] for i in [-310, -1]]
    #     # time_until_list = [return_test_timestamps[i] for i in [-305, -1]]
    #     # print(time_until_list)
    #
    #
    #
    # # time_until_list = [return_test_timestamps[i] for i in [-80, -60, -40, -30, -1]]
    # # time_from_list = [return_test_timestamps[i] for i in [-650, -630, -610, -600, -571]]
    # time_until_list = return_test_timestamps[-len(return_test_timestamps) + 1000:-1]
    # time_from_list = return_test_timestamps[-len(return_test_timestamps) + 400:-601]
    # # time_until_list = return_test_timestamps[-80:-1]
    # # time_from_list = return_test_timestamps[-680:-601]
    # # time_until_list = [return_test_timestamps[i] for i in [-340, -335, -330, -320, -310, -300, -250, -245, -230, -200, -100]]
    # # time_from_list = [return_test_timestamps[i] for i in [-940, -935, -930, -920, -910, -900, -850, -845, -830, -800, -700]]
    # # time_until_list = return_test_timestamps[-2:-1]
    # # time_from_list = return_test_timestamps[-602:-601]
    # #
    # # time_until_list = [return_test_timestamps[i] for i in [-3100, -3000, -2900, -2880, -2800, -2700]]
    # # time_from_list = [return_test_timestamps[i] for i in [-3700, -3600, -3500, -3480, -3400, -3300]]
    # #
    # # time_until_list = [return_test_timestamps[i] for i in [-2700, -2675, -2630, -2600, -2500]]
    # # time_from_list = [return_test_timestamps[i] for i in [-3300, -3275, -3230, -3200, -3100]]
    # #
    # # time_until_list = return_test_timestamps[-2:-1]
    # # time_from_list = return_test_timestamps[-4300:-4299]
    # #
    # # time_until_list = return_test_timestamps[-2:-1]
    # # time_from_list = return_test_timestamps[-602:-601]
    #
    #
    # # return_test_timestamps = return_test_generate_timestamps("2024-12-16 17:19:07", "2025-06-02 18:10:07", 30)
    # # time_until_list = return_test_timestamps[-len(return_test_timestamps) + 333:-1]
    # # time_from_list = return_test_timestamps[-len(return_test_timestamps) + 133:-201]
    # # return_test_timestamps = return_test_generate_timestamps("2024-12-16 17:19:07", "2025-06-03 18:10:07", 180)
    # # time_until_list = return_test_timestamps[60:-1]
    # # time_from_list = return_test_timestamps[0:-61]
    # # time_until_list = return_test_timestamps[-2:-1]
    # # time_from_list = return_test_timestamps[-62:-61]
    # # time_until_list = return_test_timestamps[-2:-1]
    # # time_from_list = return_test_timestamps[-32:-31]
    # # return_test_timestamps = return_test_generate_timestamps("2024-12-16 17:19:07", "2025-06-03 18:10:07", 540)
    # # time_until_list = return_test_timestamps[10:-1]
    # # time_from_list = return_test_timestamps[0:-11]

    # return_test_timestamps = return_test_generate_timestamps("2024-12-16 17:19:07", "2025-06-03 18:10:07", 10)
    # # time_until_list = return_test_timestamps[1080+280:-1]
    # # time_from_list = return_test_timestamps[0+280:-1081]
    # # time_until_list = return_test_timestamps[1080:-1]
    # # time_from_list = return_test_timestamps[0:-1081]
    # time_until_list = return_test_timestamps[250:-1]
    # time_from_list = return_test_timestamps[0:-250]

    return_test_timestamps = return_test_generate_timestamps("2024-12-16 17:19:07", "2025-06-03 18:10:07", 10)
    time_until_list = return_test_timestamps[500:-1]
    time_from_list = return_test_timestamps[0:-500]
    # time_until_list = return_test_timestamps[5666:5667]
    # time_from_list = return_test_timestamps[5166:5167]
    # return_test_timestamps = return_test_generate_timestamps("2024-12-15 17:19:07", "2025-06-03 18:10:07", 50)
    # # time_until_list = return_test_timestamps[100:-1]
    # # time_from_list = return_test_timestamps[0:-100]
    # time_until_list = return_test_timestamps[100:-1]
    # time_from_list = return_test_timestamps[0:-100]



    time_until_index = -1

    print(time_until_list)
    while time_until_index < len(time_until_list)-1:
        time_until_index += 1
        time_until = time_until_list[time_until_index]
        time_from = time_from_list[time_until_index]
        if PRINT_HUICE_RETURN_INFO:
            print(f"当前回测起始时间{time_from} {time_until_index}")
            print(f"当前回测截止时间{time_until} {time_until_index}")
        print(f"当前回测起始时间{time_from} {time_until_index}")
        print(f"当前回测截止时间{time_until} {time_until_index}")
    ############################### 全时间回测用 ###############################


    # ############################### 线上实盘用 ###############################
    # ########################线上实盘到全时间回测记得切换#########################
    # while True:
    # ############################### 线上实盘用 ###############################


        ########################线上实盘到全时间回测记得切换#########################
        if True: # 单次测试用 或者 全时间回测用



        # ########################线上实盘到全时间回测记得切换#########################
        # if is_market_open(): # 线上实盘用

            # 开始计时
            start_time = time.time()

            # DAYS_LOOK_BASED_ON_GROUP_SIZE = {45: 150, 10: 15, 1: 15}
            # DAYS_LOOK_BASED_ON_GROUP_SIZE = {45: 150, 10: 30, 1: 30}
            DAYS_LOOK_BASED_ON_GROUP_SIZE = {45: 150, 10: 70, 5: 60, 4: 50, 3: 40, 2: 30, 1: 20}



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
            ########################线上实盘到全时间回测记得切换#########################
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
            df = read_all_csv_of_one_stock_some_days_after_date(
                stock_name_and_market=STOCK_NAME_AND_MARKET, days_n=200,
                start_date="2025-04-25"
            )
            df = read_all_csv_of_one_stock_some_days_after_date(
                stock_name_and_market=STOCK_NAME_AND_MARKET, days_n=DAYS_LOOK_BASED_ON_GROUP_SIZE[GROUP_SIZE_FOE_HIGH_LEVEL],
                start_date=datetime.strptime(time_from, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
            )

            ######## 从最小级别向上递归 ######
            ############################### 全时间回测用 ###############################



            # ############################### 线上实盘用 ###############################
            # ########################线上实盘到全时间回测记得切换#########################
            # # # GROUP_SIZE_FOE_HIGH_LEVEL*2
            # # # 20->40天 10->20天 5->10天
            # # df = read_all_csv_of_one_stock_some_days(stock_name_and_market=STOCK_NAME_AND_MARKET,
            # #                                          days_n=GROUP_SIZE_FOE_HIGH_LEVEL * 2)
            # df = read_all_csv_of_one_stock_some_days(stock_name_and_market=STOCK_NAME_AND_MARKET,
            #                                          days_n=DAYS_LOOK_BASED_ON_GROUP_SIZE[GROUP_SIZE_FOE_HIGH_LEVEL])
            # ############################### 线上实盘用 ###############################




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
            ########################线上实盘到全时间回测记得切换#########################
            df = df[df['timestamp'] <= time_until] #全时间回测用

            ############################### 全时间回测用 ###############################

            # 创建子图布局
            plot_number_each_jibie = 3
            # fig = make_subplots(rows=len(GROUP_SIZEs)*plot_number_each_jibie, cols=1, shared_xaxes=False, vertical_spacing=0.05,
            #                     subplot_titles=['GROUP_SIZE' + str(GROUP_SIZEs[int(group_size_in_GROUP_SIZEs_index/plot_number_each_jibie)]) if (group_size_in_GROUP_SIZEs_index%plot_number_each_jibie==0 or group_size_in_GROUP_SIZEs_index%plot_number_each_jibie==1) else 'MACD' for group_size_in_GROUP_SIZEs_index in range(3*len(GROUP_SIZEs))], row_heights=[0.8 for group_i in range(3*len(GROUP_SIZEs))])
            fig = make_subplots(rows=len(GROUP_SIZEs) * plot_number_each_jibie, cols=1, shared_xaxes=False,
                                vertical_spacing=0.05,
                                subplot_titles=['GROUP_SIZE' + str(
                                    GROUP_SIZEs[int(group_size_in_GROUP_SIZEs_index / plot_number_each_jibie)]) for group_size_in_GROUP_SIZEs_index in range(plot_number_each_jibie * len(GROUP_SIZEs))],
                                row_heights=[0.8 for group_i in range(plot_number_each_jibie * len(GROUP_SIZEs))])


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
                pen_new_zhongshu_clean = None
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
                save_new_segments_fix_to_checkpoint_pen(fixed_pens, pen_zhongshus, STOCK_NAME_AND_MARKET, seconds_level=GROUP_SIZEs[0]*6)

                history_long_time_pens = []
                history_long_time_pen_zhongshus = []

                history_long_time_pens = merge_segments_fix_with_checkpoint(fixed_pens, STOCK_NAME_AND_MARKET,
                                                                                seconds_level=GROUP_SIZEs[0] * 6, for_segment=False)
                history_long_time_pen_zhongshus = merge_zhongshu_with_checkpoint(pen_zhongshus, STOCK_NAME_AND_MARKET, seconds_level=GROUP_SIZEs[0] * 6)

                save_new_pen_zhongshu_to_checkpoint(pen_zhongshus, STOCK_NAME_AND_MARKET, seconds_level=6)

                if len(history_long_time_pen_zhongshus) > 80:
                    history_long_time_pen_zhongshus = history_long_time_pen_zhongshus[-80:]
                    history_long_time_pens = history_long_time_pens[
                                             history_long_time_pen_zhongshus[0]["core_pens_index"][-1] - 1:]
                    history_long_time_pens_index_fix = \
                        history_long_time_pen_zhongshus[0]["core_pens_index"][0] - 1
                    for index, seg in enumerate(history_long_time_pen_zhongshus):
                        history_long_time_pen_zhongshus[index]["core_pens_index"] = [
                            i - history_long_time_pens_index_fix for i in
                            history_long_time_pen_zhongshus[index]["core_pens_index"]
                        ]

                if sanmai_info_pen != "":
                    pen_new_zhongshu_clean = pen_zhongshus_clean[-1]
                    pen_zhongshus_clean = pen_zhongshus_clean[:-1]
                    # if (pen_zhongshus_clean[-1]["direction"] !=
                    #         pen_zhongshus_clean[-2]["direction"]):
                    #     pen_new_zhongshu_clean = pen_zhongshus_clean[-1]
                    #     pen_zhongshus_clean = pen_zhongshus_clean[:-1]
                    #     # print(len(segment_zhongshus_clean))
                    # else:
                    #     sanmai_info_pen = ""

                if GROUP_SIZE_index == 0:
                    print(f"{df.iloc[-1]['timestamp']}:当前价{df.iloc[-1]['price']}")
                    # print(
                    #     ["+" if clean_zhongshu["direction"] == "Up" else "-" for clean_zhongshu in pen_zhongshus_clean])




                # 用笔组合成线段
                # segments, standard_feature_sequence_lists = merge_pens_to_segments(fixed_pens)
                segments = []
                segments_fix = []
                # segments_late_complete_version, type_three_buy_sell_late_complete_version = merge_pens_to_segments_based_on_pen_zhongshu(fixed_pens, pen_zhongshus_clean)
                # segments, type_three_buy_sell = merge_pens_to_segments(fixed_pens)
                segments, type_three_buy_sell = merge_pens_to_segments_based_on_pen_zhongshu(fixed_pens, pen_zhongshus_clean)
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

                new_zhongshu_clean = None
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

                        # print(f"""sanmai_info is {sanmai_info}, bool gives {sanmai_info != ""}""")
                        if sanmai_info != "":
                            new_zhongshu_clean = segment_zhongshus_clean[-1]
                            # print(len(segment_zhongshus_clean))
                            # new_zhongshu_clean = segment_zhongshus_clean.pop()
                            # segment_zhongshus_clean = copy.deepcopy(segment_zhongshus_clean)
                            segment_zhongshus_clean = segment_zhongshus_clean[:-1]
                            # print(len(segment_zhongshus_clean))

                        save_new_segments_fix_to_checkpoint(segments_fix, segment_zhongshus, STOCK_NAME_AND_MARKET, seconds_level=GROUP_SIZEs[0]*6)

                history_long_time_segments = []
                high_level_segments_zhongshus = []
                high_level_segments_zhongshus_clean = []
                history_long_time_new_zhongshu_clean = None
                if segments_fix:
                    history_long_time_segments = merge_segments_fix_with_checkpoint(segments_fix, STOCK_NAME_AND_MARKET, seconds_level=GROUP_SIZEs[0]*6)
                    # high_level_segments, high_level_type_three_buy_sell = merge_pens_to_segments(history_long_time_segments, merge_segments_to_segments=True)
                    history_long_time_segment_zhongshus, history_long_time_segment_zhuanzhes = find_zhongshu_one_pen_form(history_long_time_segments)


                    if len(history_long_time_segment_zhongshus) > 80:
                        history_long_time_segment_zhongshus = history_long_time_segment_zhongshus[-80:]
                        history_long_time_segments = history_long_time_segments[history_long_time_segment_zhongshus[0]["core_pens_index"][-1]-1:]
                        history_long_time_segments_index_fix = history_long_time_segment_zhongshus[0]["core_pens_index"][0] - 1
                        for index, seg in enumerate(history_long_time_segment_zhongshus):
                            history_long_time_segment_zhongshus[index]["core_pens_index"] = [
                                i - history_long_time_segments_index_fix for i in
                                history_long_time_segment_zhongshus[index]["core_pens_index"]
                            ]


                    history_long_time_segment_zhongshus_clean, history_long_time_segment_zhuanzhes_clean, history_long_time_sanmai_info = clean_zhongshu_detailed(
                        history_long_time_segment_zhongshus, history_long_time_segments)
                #     if history_long_time_sanmai_info != "":
                #         history_long_time_new_zhongshu_clean = history_long_time_segment_zhongshus_clean[-1]
                #         history_long_time_segment_zhongshus_clean = history_long_time_segment_zhongshus_clean[:-1]
                #         # if (history_long_time_segment_zhongshus_clean[-1]["direction"] != history_long_time_segment_zhongshus_clean[-2]["direction"]):
                #         #     history_long_time_new_zhongshu_clean = history_long_time_segment_zhongshus_clean[-1]
                #         #     history_long_time_segment_zhongshus_clean = history_long_time_segment_zhongshus_clean[:-1]
                #         #     # print(len(segment_zhongshus_clean))
                #         # else:
                #         #     history_long_time_sanmai_info = ""
                #
                #
                #
                #
                    #画更大级别线
                    # high_level_segments, high_level_type_three_buy_sell = merge_pens_to_segments(history_long_time_segments, merge_segments_to_segments=True)
                    high_level_segments, high_level_type_three_buy_sell = merge_pens_to_segments_based_on_pen_zhongshu(history_long_time_segments, history_long_time_segment_zhongshus_clean, merge_segments_to_segments=True)
                    high_level_segments_zhongshus, high_level_segment_zhuanzhes = find_zhongshu_one_pen_form(high_level_segments)
                    # high_level_segments_zhongshus_clean, high_level_segments_zhuanzhes_clean, high_level_sanmai_info = clean_zhongshu_detailed(
                    #     high_level_segments_zhongshus, high_level_segments)



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

                def plot_if_mai(sanmaitype="long", zhichengwei=0):
                    # # 画6秒级，也就是最低级别数据的空线，给后面的图参考对齐x轴
                    # fig.add_trace(go.Scatter(
                    #     x=kline_df['timestamp'],  # 使用 kline_df 的时间戳
                    #     y=[None] * len(kline_df),  # 不绘制 y 值
                    #     mode='lines',  # 设置为线模式（但不会显示）
                    #     showlegend=False  # 隐藏图例
                    # ), row=GROUP_SIZE_index * plot_number_each_jibie + 1, col=1)
                    # fig.add_trace(go.Scatter(
                    #     x=kline_df['timestamp'],  # 使用 kline_df 的时间戳
                    #     y=[None] * len(kline_df),  # 不绘制 y 值
                    #     mode='lines',  # 设置为线模式（但不会显示）
                    #     showlegend=False  # 隐藏图例
                    # ), row=GROUP_SIZE_index * plot_number_each_jibie + 2, col=1)
                    #
                    # # 处理后的 K 线图
                    # for i in range(len(kline_df_no_inclusion)):
                    #     color = 'green' if kline_df_no_inclusion.iloc[i]['close'] > kline_df_no_inclusion.iloc[i][
                    #         'open'] else 'red'
                    #     fig.add_trace(
                    #         go.Candlestick(
                    #             x=[kline_df_no_inclusion.iloc[i]['timestamp']],
                    #             open=[kline_df_no_inclusion.iloc[i]['open']],
                    #             close=[kline_df_no_inclusion.iloc[i]['close']],
                    #             high=[kline_df_no_inclusion.iloc[i]['high']],
                    #             low=[kline_df_no_inclusion.iloc[i]['low']],
                    #             increasing_line_color=color,
                    #             decreasing_line_color=color,
                    #             showlegend=False
                    #         ),
                    #         row=GROUP_SIZE_index * plot_number_each_jibie + 1, col=1
                    #     )



                    # Add fixed Pens to the chart
                    # for pen_index, pen in enumerate(fixed_pens):
                    for pen_index, pen in enumerate(history_long_time_pens):
                        fig.add_trace(
                            go.Scatter(
                                # x=[pen['top_time'], pen['bottom_time']],
                                x=[ensure_datetime(pen['top_time']), ensure_datetime(pen['bottom_time'])],
                                y=[pen['top_price'], pen['bottom_price']],
                                mode='lines',
                                line=dict(color='white', width=2),
                                name='Penfix',
                                showlegend=False
                            ),
                            row=GROUP_SIZE_index * plot_number_each_jibie + 1, col=1
                        )
                    # draw_zhongshu(fig, pen_zhongshus, row=GROUP_SIZE_index * plot_number_each_jibie + 1, col=GROUP_SIZE_index * plot_number_each_jibie + 1,
                    #               level="pen")
                    draw_zhongshu(fig, history_long_time_pen_zhongshus, row=GROUP_SIZE_index * plot_number_each_jibie + 1,
                                  col=GROUP_SIZE_index * plot_number_each_jibie + 1,
                                  level="pen")

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
                    #                 row=GROUP_SIZE_index * plot_number_each_jibie + 1, col=1
                    #             )

                    if segments_fix:
                        # Add Zhongshu Rectangles to the chart
                        # draw_zhongshu(fig, segment_zhongshus, row=GROUP_SIZE_index * plot_number_each_jibie + 1,
                        #               col=GROUP_SIZE_index * plot_number_each_jibie + 1, level="segment")
                        # draw_zhongshu(fig, segment_of_segment_zhongshus, row=GROUP_SIZE_index*2 + 2, col=1, level="segment_of_segment")

                        for segment_index, segment in enumerate(segments_fix):
                            fig.add_trace(
                                go.Scatter(
                                    # x=[segment['top_time'], segment['bottom_time']],
                                    x=[ensure_datetime(segment['top_time']), ensure_datetime(segment['bottom_time'])],
                                    y=[segment['top_price'], segment['bottom_price']],
                                    mode='lines',
                                    line=dict(color='yellow', width=2.5),
                                    name='segment',
                                    showlegend=False
                                ),
                                row=GROUP_SIZE_index * plot_number_each_jibie + 1, col=1
                            )

                            # # 计算线段的中点位置
                            # middle_time = max(segment['top_time'], segment['bottom_time'])
                            # middle_price = segment['bottom_price'] * 0.95
                            #
                            # # 添加文本
                            # fig.add_trace(
                            #     go.Scatter(
                            #         x=[middle_time],
                            #         y=[middle_price - 2],  # 位置在线段下方，调整 -5 为适当的偏移值
                            #         mode='text',
                            #         text=[str(segment_index) + ","],
                            #         textfont=dict(color='yellow', size=12),
                            #         showlegend=False
                            #     ),
                            #     row=GROUP_SIZE_index * plot_number_each_jibie + 1, col=1
                            # )

                            # line_based_on_segment_range = (segment['top_price'] - segment['bottom_price'])/2
                            # fig.add_trace(
                            #     go.Scatter(
                            #         x=[segment["timestamp_segment_complete"], segment["timestamp_segment_complete"]],
                            #         y=[segment["price_segment_complete"]-line_based_on_segment_range, segment["price_segment_complete"]+line_based_on_segment_range],  # 位置在线段下方，调整 -5 为适当的偏移值
                            #         mode='lines',
                            #         line=dict(
                            #             color="rgb(0, 200, 0)" if segment['direction'] == "Up" else "rgb(200, 0, 0)",
                            #             width=1
                            #         ),
                            #         name='segment_complete_point',
                            #         showlegend=False
                            #     ),
                            #     row=GROUP_SIZE_index * plot_number_each_jibie + 1, col=1
                            # )

                    # 更高级别segments
                    # history_long_time_segments
                    # high_level_segments
                    # high_level_segments_zhongshus_clean
                    if history_long_time_segments:
                        draw_zhongshu(fig, history_long_time_segment_zhongshus, row=GROUP_SIZE_index * plot_number_each_jibie + 1,
                                      col=1, level="segment")
                        # Add Zhongshu Rectangles to the chart
                        # draw_zhongshu(fig, segment_zhongshus, row=GROUP_SIZE_index * plot_number_each_jibie + 1,
                        #               col=GROUP_SIZE_index * plot_number_each_jibie + 1, level="segment")
                        # draw_zhongshu(fig, segment_of_segment_zhongshus, row=GROUP_SIZE_index*2 + 2, col=1, level="segment_of_segment")
                        for segment_index, segment in enumerate(history_long_time_segments):
                            fig.add_trace(
                                go.Scatter(
                                    # x=[segment['top_time'], segment['bottom_time']],
                                    x=[ensure_datetime(segment['top_time']), ensure_datetime(segment['bottom_time'])],
                                    y=[segment['top_price'], segment['bottom_price']],
                                    mode='lines',
                                    line=dict(color='brown', width=1.0),
                                    name='segment_long_history',
                                    showlegend=False
                                ),
                                row=GROUP_SIZE_index * plot_number_each_jibie + 1, col=1
                            )
                    # if high_level_segments:
                    #     draw_zhongshu(fig, high_level_segments_zhongshus, row=GROUP_SIZE_index * plot_number_each_jibie + 1,
                    #                   col=1, level="segment_of_segment")
                    #     for segment_index, segment in enumerate(high_level_segments):
                    #         fig.add_trace(
                    #             go.Scatter(
                    #                 # x=[segment['top_time'], segment['bottom_time']],
                    #                 x=[ensure_datetime(segment['top_time']), ensure_datetime(segment['bottom_time'])],
                    #                 y=[segment['top_price'], segment['bottom_price']],
                    #                 mode='lines',
                    #                 line=dict(color='blue', width=2.5),
                    #                 name='segment_high_level',
                    #                 showlegend=False
                    #             ),
                    #             row=GROUP_SIZE_index * plot_number_each_jibie + 1, col=1
                    #         )




                    # # 处理后的 K 线图
                    # for i in range(len(kline_df_no_inclusion)):
                    #     color = 'green' if kline_df_no_inclusion.iloc[i]['close'] > kline_df_no_inclusion.iloc[i][
                    #         'open'] else 'red'
                    #     fig.add_trace(
                    #         go.Candlestick(
                    #             x=[kline_df_no_inclusion.iloc[i]['timestamp']],
                    #             open=[kline_df_no_inclusion.iloc[i]['open']],
                    #             close=[kline_df_no_inclusion.iloc[i]['close']],
                    #             high=[kline_df_no_inclusion.iloc[i]['high']],
                    #             low=[kline_df_no_inclusion.iloc[i]['low']],
                    #             increasing_line_color=color,
                    #             decreasing_line_color=color,
                    #             showlegend=False
                    #         ),
                    #         row=GROUP_SIZE_index * plot_number_each_jibie + 2, col=1
                    #     )



                    # Add fixed Pens to the chart
                    # for pen_index, pen in enumerate(fixed_pens):
                    for pen_index, pen in enumerate(history_long_time_pens):
                        fig.add_trace(
                            go.Scatter(
                                # x=[pen['top_time'], pen['bottom_time']],
                                x=[ensure_datetime(pen['top_time']), ensure_datetime(pen['bottom_time'])],
                                y=[pen['top_price'], pen['bottom_price']],
                                mode='lines',
                                line=dict(color='white', width=2),
                                name='Penfix',
                                showlegend=False
                            ),
                            row=GROUP_SIZE_index * plot_number_each_jibie + 2, col=1
                        )
                    draw_zhongshu(fig, pen_zhongshus_clean, row=GROUP_SIZE_index * plot_number_each_jibie + 2,
                                  col=GROUP_SIZE_index * plot_number_each_jibie + 2, level="pen")


                    if segments_fix:
                        # Add Zhongshu Rectangles to the chart
                        # draw_zhongshu(fig, segment_zhongshus_clean, row=GROUP_SIZE_index * plot_number_each_jibie + 2,
                        #               col=GROUP_SIZE_index * plot_number_each_jibie + 2, level="segment")
                        # draw_zhongshu(fig, segment_of_segment_zhongshus, row=GROUP_SIZE_index*2 + 2, col=1, level="segment_of_segment")

                        for segment_index, segment in enumerate(segments_fix):
                            fig.add_trace(
                                go.Scatter(
                                    # x=[segment['top_time'], segment['bottom_time']],
                                    x=[ensure_datetime(segment['top_time']), ensure_datetime(segment['bottom_time'])],
                                    y=[segment['top_price'], segment['bottom_price']],
                                    mode='lines',
                                    line=dict(color='yellow', width=2.5),
                                    name='segment',
                                    showlegend=False
                                ),
                                row=GROUP_SIZE_index * plot_number_each_jibie + 2, col=1
                            )

                            # # 计算线段的中点位置
                            # middle_time = max(segment['top_time'], segment['bottom_time'])
                            # middle_price = segment['bottom_price'] * 0.95
                            #
                            # # 添加文本
                            # fig.add_trace(
                            #     go.Scatter(
                            #         x=[middle_time],
                            #         y=[middle_price - 2],  # 位置在线段下方，调整 -5 为适当的偏移值
                            #         mode='text',
                            #         text=[str(segment_index) + ","],
                            #         textfont=dict(color='yellow', size=12),
                            #         showlegend=False
                            #     ),
                            #     row=GROUP_SIZE_index * plot_number_each_jibie + 2, col=1
                            # )
                            # line_based_on_segment_range = (segment['top_price'] - segment['bottom_price']) / 2
                            # fig.add_trace(
                            #     go.Scatter(
                            #         x=[segment["timestamp_segment_complete"], segment["timestamp_segment_complete"]],
                            #         y=[segment["price_segment_complete"] - line_based_on_segment_range,
                            #            segment["price_segment_complete"] + line_based_on_segment_range],
                            #         # 位置在线段下方，调整 -5 为适当的偏移值
                            #         mode='lines',
                            #         line=dict(
                            #             color="rgb(0, 200, 0)" if segment['direction'] == "Up" else "rgb(200, 0, 0)",
                            #             width=1
                            #         ),
                            #         name='segment_complete_point',
                            #         showlegend=False
                            #     ),
                            #     row=GROUP_SIZE_index * plot_number_each_jibie + 2, col=1
                            # )

                    # # 更高级别segments
                    # # history_long_time_segments
                    # # high_level_segments
                    if history_long_time_segments:
                        draw_zhongshu(fig, history_long_time_segment_zhongshus_clean, row=GROUP_SIZE_index * plot_number_each_jibie + 2,
                                      col=GROUP_SIZE_index * plot_number_each_jibie + 1, level="segment")
                        # Add Zhongshu Rectangles to the chart
                        # draw_zhongshu(fig, segment_zhongshus, row=GROUP_SIZE_index * plot_number_each_jibie + 1,
                        #               col=GROUP_SIZE_index * plot_number_each_jibie + 1, level="segment")
                        # draw_zhongshu(fig, segment_of_segment_zhongshus, row=GROUP_SIZE_index*2 + 2, col=1, level="segment_of_segment")
                        for segment_index, segment in enumerate(history_long_time_segments):
                            fig.add_trace(
                                go.Scatter(
                                    # x=[segment['top_time'], segment['bottom_time']],
                                    x=[ensure_datetime(segment['top_time']), ensure_datetime(segment['bottom_time'])],
                                    y=[segment['top_price'], segment['bottom_price']],
                                    mode='lines',
                                    line=dict(color='brown', width=1.0),
                                    name='segment_long_history',
                                    showlegend=False
                                ),
                                row=GROUP_SIZE_index * plot_number_each_jibie + 2, col=1
                            )
                    if high_level_segments:
                        draw_zhongshu(fig, high_level_segments_zhongshus_clean,
                                      row=GROUP_SIZE_index * plot_number_each_jibie + 2,
                                      col=1, level="segment_of_segment")
                        for segment_index, segment in enumerate(high_level_segments):
                            fig.add_trace(
                                go.Scatter(
                                    # x=[segment['top_time'], segment['bottom_time']],
                                    x=[ensure_datetime(segment['top_time']), ensure_datetime(segment['bottom_time'])],
                                    y=[segment['top_price'], segment['bottom_price']],
                                    mode='lines',
                                    line=dict(color='blue', width=2.5),
                                    name='segment_high_level',
                                    showlegend=False
                                ),
                                row=GROUP_SIZE_index * plot_number_each_jibie + 2, col=1
                            )

                    # # 添加均线
                    # fig.add_trace(
                    #     go.Scatter(
                    #         x=kline_df['timestamp'],
                    #         y=kline_df[f'SMA_{duanjunxian_window}'],
                    #         mode='lines',
                    #         name=f'{duanjunxian_window}-period SMA',
                    #         line=dict(color='pink', width=2)
                    #     ),
                    #     row=GROUP_SIZE_index * plot_number_each_jibie + 2, col=1
                    # )
                    #
                    # # 添加均线
                    # fig.add_trace(
                    #     go.Scatter(
                    #         x=kline_df['timestamp'],
                    #         y=kline_df[f'SMA_{changjunxian_window}'],
                    #         mode='lines',
                    #         name=f'{changjunxian_window}-period SMA',
                    #         line=dict(color='purple', width=2)
                    #     ),
                    #     row=GROUP_SIZE_index * plot_number_each_jibie + 2, col=1
                    # )

                def plot_complete(sanmaitype="long", zhichengwei=0):
                    # 更新布局
                    fig.update_layout(
                        title=f'{STOCK_NAME_AND_MARKET} Price Trend and K-Line Chart multi time level',
                        yaxis=dict(
                            title="Price"
                        ),
                        template='plotly_dark',
                        height=500 * (plot_number_each_jibie * len(GROUP_SIZEs)),
                    )

                    for i in range(len(GROUP_SIZEs) * plot_number_each_jibie):
                        fig.update_layout({f"xaxis{i+1}": dict(type='category')})
                        fig.update_layout({f"xaxis{i+1}_rangeslider_visible": False})
                        fig.update_layout({f"xaxis{i+1}":dict(type='category', categoryorder='category ascending')})
                        # fig.update_layout({f"xaxis{i + 1}": dict(domain=[0, 1], categoryorder="category ascending")})
                        # fig['layout'][f'xaxis{i + 1}'] = fig['layout'][f'xaxis{int(i/plot_number_each_jibie)+1}']


                    # 显示图表
                    # fig.show()
                    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

                    # 生成文件名
                    file_name_record_if_sanmai = f"sanmaiplot/{current_time}_{STOCK_NAME_AND_MARKET}_{GROUP_SIZEs[0]*6}_second_{sanmaitype}_zhichengwei_{zhichengwei}.png"

                    fig.write_image(file_name_record_if_sanmai, width=3000, height=2500)






                # yimai = ""
                # ermai = ""
                # sanmai = ""
                # join_time = ""
                # if ermai == "buy" or ermai == "sell": #now try to decide when to stop make money or lose money
                #     if "price back and broke the yimai point":
                #         "stop lose money"
                #     if "new zhongshu":
                #         if "ermai and yimai in a zhongshu" and "new zhongshu is sanmai":
                #             sanmai = "buy"
                #             "or"
                #             sanmai = "sell"
                #         else "yimai not in same zhongshu with ermai":
                #             "check beichi"
                #             if "bechi":
                #                 "stop make money"
                #             else:
                #                 "wait for beichi"

                # 啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊
                # zhongshu_last_temp_new = {
                #     "ZG": segments[-1]["top_price"],
                #     "ZD": segments[-1]["bottom_price"],
                #     "start_time": segments[-1]["top_time"],
                #     "end_time": segments[-1]["bottom_time"],
                #     "core_pens": [segments[-1]],
                #     "core_pens_index": [len(segments) - 1],
                #     "GG": segments[-1]["top_price"],
                #     "DD": segments[-1]["bottom_price"],
                #     "direction": "Up",
                #     "zhongshu_jieshu": False,  # zhongshu_stop,
                #     "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
                # }
                # segment_last_complete = {
                #     "top_price": pens[last_pen_index]["top_price"] if direction_before == "Up" else
                #     pens[first_pen_this_qushi_index]["top_price"],
                #     "bottom_price": pens[first_pen_this_qushi_index]["bottom_price"] if direction_before == "Up" else
                #     pens[last_pen_index]["bottom_price"],
                #     "top_time": pens[last_pen_index]["top_time"] if direction_before == "Up" else
                #     pens[first_pen_this_qushi_index]["top_time"],
                #     "bottom_time": pens[first_pen_this_qushi_index]["bottom_time"] if direction_before == "Up" else
                #     pens[last_pen_index]["bottom_time"],
                #     "top_index": last_pen_index if direction_before == "Up" else first_pen_this_qushi_index,
                #     "bottom_index": first_pen_this_qushi_index if direction_before == "Up" else last_pen_index,
                #     "direction": direction_before,
                #     "timestamp_segment_complete": pens[last_pen_index]["top_time"] if direction_before == "Up" else
                #     pens[last_pen_index]["bottom_time"],
                #     "price_segment_complete": pens[last_pen_index]["top_price"] if direction_before == "Up" else
                #     pens[last_pen_index]["bottom_price"],
                #     "complex_fix": "complete"
                # }
                # pens = [{"top_index": 0,
                #          "bottom_index": current_dingdi["index"],
                #          "top_time": kline_df_no_inclusion.iloc[0]['timestamp'],
                #          "bottom_time": current_dingdi["timestamp"],
                #          "top_price": kline_df_no_inclusion.iloc[0]['high'],
                #          "bottom_price": current_dingdi["price"],
                #          "direction": "Up",
                #          "timestamp_pen_complete": current_dingdi["timestamp_fenxing_complete"],
                #          "price_pen_complete": current_dingdi["price_fenxing_complete"]}]
                # 啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊

                # ############################### 线上实盘用 ###############################
                # ########################线上实盘到全时间回测记得切换#########################
                # show_func = None
                # ############################### 线上实盘用 ###############################

                ############################### 全时间回测用 ###############################
                ########################线上实盘到全时间回测记得切换#########################
                show_func = fig.show
                ############################### 全时间回测用 ###############################






                # # 处理最后一个方向上的中枢扩张
                # # 处理最后一个方向上的中枢扩张
                # # 处理最后一个方向上的中枢扩张
                # current_dir_for_check_zhongshu_kuozhang = pen_zhongshus_clean[-1][
                #     "direction"]
                # cut_index = -1
                # for i in range(len(pen_zhongshus_clean) - 1):
                #     if pen_zhongshus_clean[-i - 2][
                #         "direction"] == current_dir_for_check_zhongshu_kuozhang:
                #         cut_index = -i - 2
                #     else:
                #         break
                # pen_zhongshus_clean_SEC_1 = pen_zhongshus_clean[
                #                                                   :cut_index]
                # pen_zhongshus_clean_SEC_2 = pen_zhongshus_clean[
                #                                                   cut_index:]
                # pen_zhongshus_clean_SEC_2_rebuild = [
                #     pen_zhongshus_clean_SEC_2[0]]
                # for i in range(len(pen_zhongshus_clean_SEC_2) - 1):
                #     if check_zhongshu_kuozhang(pen_zhongshus_clean_SEC_2_rebuild[-1],
                #                                pen_zhongshus_clean_SEC_2[i + 1]):
                #         rebuild_zhongshu = zhongshu_kuozhang_merge_same_dir(
                #             pen_zhongshus_clean_SEC_2_rebuild[-1],
                #             pen_zhongshus_clean_SEC_2[i + 1], fixed_pens)
                #         if rebuild_zhongshu["core_pens_index"][-1] == len(fixed_pens) - 1:
                #             #这里最后一段可能被算入扩张的中枢，要再截出来
                #             print("处理了同向三mai，有扩张的情况")
                #             rebuild_zhongshu["core_pens_index"] = rebuild_zhongshu["core_pens_index"][:-1]
                #         pen_zhongshus_clean_SEC_2_rebuild[-1] = rebuild_zhongshu
                #     else:
                #         pen_zhongshus_clean_SEC_2_rebuild.append(
                #             pen_zhongshus_clean_SEC_2[i + 1])
                # pen_zhongshus_clean = pen_zhongshus_clean_SEC_1 + pen_zhongshus_clean_SEC_2_rebuild
                # if pen_zhongshus_clean[-1]["core_pens_index"][-1] == len(fixed_pens) - 1:
                #     #再处理一下同向三mai，没有扩张的情况
                #     print("处理了同向三mai，没有扩张的情况")
                #     pen_zhongshus_clean = pen_zhongshus_clean[:-1]
                #     pen_zhongshus_clean[-1]["core_pens_index"].append(pen_zhongshus_clean[-1]["core_pens_index"][-1]+1)

                beichi_hyperparameter = 0.618
                # beichi_hyperparameter = 0.72
                #做空检查
                if current_play.yimai_status == "inactivate" and len(history_long_time_segments) >= 5 and len(history_long_time_segment_zhongshus) >= 2:# and (df.iloc[-1]['timestamp'].time() < datetime_time(18, 30)):
                    if history_long_time_segments[-2]["direction"] == "Up" and (current_play.last_operation_seg_complete_time_zuokong != max(history_long_time_segments[-1]["top_time"], history_long_time_segments[-1]["bottom_time"])):
                        # 以找卖点为目标,并且上次止损后有新的线段形成
                        if history_long_time_segments[-2]["top_price"] > history_long_time_segments[-4][
                            "top_price"]:  # 至少是新高才去考虑是不是一卖
                            if (history_long_time_segments[-2]["top_price"] - history_long_time_segments[-2]["bottom_price"] < beichi_hyperparameter*(history_long_time_segments[-4][
                                "top_price"] - history_long_time_segments[-4]["bottom_price"])) and (df.iloc[-1]['price'] - history_long_time_segments[-2]["bottom_price"] < beichi_hyperparameter*(history_long_time_segments[-4][
                                "top_price"] - history_long_time_segments[-4]["bottom_price"])):  # history_long_time_segments[-2]相比history_long_time_segments[-4]背驰, 且当前价格不破坏背驰
                                if history_long_time_segments[-4]["bottom_price"] < history_long_time_segments[-2][
                                    "bottom_price"]:  # history_long_time_segments[-4,-3,-2]是趋势

                                    panzheng_then_qushi = False
                                    base_zhongshu = history_long_time_segment_zhongshus[-1]
                                    support_price_old_big_zhongshu = None
                                    for zhongshu_before in history_long_time_segment_zhongshus[-2:]:
                                        if zhongshu_before["GG"] < base_zhongshu["ZD"]: #当前是上涨趋势
                                            base_zhongshu = zhongshu_before
                                            if len(zhongshu_before["core_pens_index"])>=3: #前面是盘整
                                                panzheng_then_qushi = True
                                                support_price_old_big_zhongshu = zhongshu_before["GG"]
                                        else:
                                            break

                                    if history_long_time_segment_zhongshus[-2]["end_time"] == history_long_time_segments[-4]["bottom_time"]:# and (len(history_long_time_segment_zhongshus[-2]["core_pens_index"])>=3): #前面一个中枢级别大
                                        # if history_long_time_segment_zhongshus[-2]["GG"] < history_long_time_segment_zhongshus[-1]["ZD"]: #否则可能是 下跌+上涨，而我们要盘整+上涨
                                        if panzheng_then_qushi:
                                            if history_long_time_segments[-1]["bottom_price"] > history_long_time_segment_zhongshus[-2]["ZG"] and df.iloc[-1]['price'] > history_long_time_segment_zhongshus[-2]["ZG"]:
                                                print("一卖一卖，一卖一卖，一卖一卖，标了二卖但实际上是一卖，回头再修改")
                                                last_direction = history_long_time_segments[-2]["direction"]
                                                current_play.update_yimai_by_direction(history_long_time_segments[-2], last_direction)
                                                current_play.handle_ermai_confirmation(
                                                    segment=history_long_time_segments[-2],
                                                    df_row=df.iloc[-1],
                                                    info_save_mode=INFO_SAVE_TO_FILE_MODE,
                                                    print_return_info=PRINT_HUICE_RETURN_INFO,
                                                    show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                                                    write_func=write_to_ermai_info_file,
                                                    plot_if_func=plot_if_mai,
                                                    plot_complete_func=plot_complete,
                                                    show_func=show_func
                                                )
                                                current_play.join_price = df.iloc[-1]['price']
                                                # current_play.support_price = min(history_long_time_segments[-2]["top_price"],
                                                #                                  history_long_time_segments[-2]["bottom_price"] + (
                                                #                                              history_long_time_segments[-4]["top_price"] -
                                                #                                              history_long_time_segments[-4][
                                                #                                                  "bottom_price"]))
                                                current_play.support_price = max(history_long_time_segments[-2]["top_price"],
                                                                                 history_long_time_segments[-2]["bottom_price"] + beichi_hyperparameter*(
                                                                                         history_long_time_segments[-4]["top_price"] -
                                                                                         history_long_time_segments[-4][
                                                                                             "bottom_price"]))
                                                current_play.support_price_old_big_zhongshu = support_price_old_big_zhongshu
                                                current_play.last_operation_seg_complete_time_zuokong = max(history_long_time_segments[-1]["top_time"], history_long_time_segments[-1]["bottom_time"])
                                                # current_play.compare_pen_min_or_max = max(current_play.yimai_price, df.iloc[-1]['price'], fixed_pens[-1]["top_price"])  # 做空介入后，线段后笔的极大值，或做多后，线段后笔的极小值，以避免重复介入
                    elif history_long_time_segments[-1]["direction"] == "Up" and (current_play.last_operation_seg_complete_time_zuokong != max(history_long_time_segments[-1]["top_time"], history_long_time_segments[-1]["bottom_time"])):
                        # 以找卖点为目标,并且上次止损后有新的线段形成
                        if history_long_time_segments[-1]["top_price"] > history_long_time_segments[-3][
                            "top_price"]:  # 至少是新高才去考虑是不是一卖
                            if (history_long_time_segments[-1]["top_price"] - history_long_time_segments[-1]["bottom_price"] < beichi_hyperparameter*(history_long_time_segments[-3][
                                "top_price"] - history_long_time_segments[-3]["bottom_price"])) and (df.iloc[-1]['price'] - history_long_time_segments[-1]["bottom_price"] < beichi_hyperparameter*(history_long_time_segments[-3][
                                "top_price"] - history_long_time_segments[-3]["bottom_price"])):  # history_long_time_segments[-1]相比history_long_time_segments[-3]背驰, 且当前价格不破坏背驰
                                if history_long_time_segments[-3]["bottom_price"] < history_long_time_segments[-1][
                                    "bottom_price"]:  # history_long_time_segments[-3,-2,-1]是趋势

                                    panzheng_then_qushi = False
                                    base_zhongshu = history_long_time_segment_zhongshus[-1]
                                    support_price_old_big_zhongshu = None
                                    for zhongshu_before in history_long_time_segment_zhongshus[-2:]:
                                        if zhongshu_before["GG"] < base_zhongshu["ZD"]:  # 当前是上涨趋势
                                            base_zhongshu = zhongshu_before
                                            if len(zhongshu_before["core_pens_index"]) >= 3:  # 前面是盘整
                                                panzheng_then_qushi = True
                                                support_price_old_big_zhongshu = zhongshu_before["GG"]
                                        else:
                                            break
                                    if history_long_time_segment_zhongshus[-2]["end_time"] == history_long_time_segments[-3]["bottom_time"]:# and (len(history_long_time_segment_zhongshus[-2]["core_pens_index"])>=3): #前面一个中枢级别大
                                        # if history_long_time_segment_zhongshus[-2]["GG"] < history_long_time_segment_zhongshus[-1][
                                        #     "ZD"]:  # 否则可能是 下跌+上涨，而我们要盘整+上涨
                                        if panzheng_then_qushi:
                                            if df.iloc[-1]['price'] > history_long_time_segment_zhongshus[-2]["ZG"]:
                                                print("一卖一卖，一卖一卖，一卖一卖，标了二卖但实际上是一卖，回头再修改")
                                                last_direction = history_long_time_segments[-1]["direction"]
                                                current_play.update_yimai_by_direction(history_long_time_segments[-1], last_direction)
                                                current_play.handle_ermai_confirmation(
                                                    segment=history_long_time_segments[-1],
                                                    df_row=df.iloc[-1],
                                                    info_save_mode=INFO_SAVE_TO_FILE_MODE,
                                                    print_return_info=PRINT_HUICE_RETURN_INFO,
                                                    show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                                                    write_func=write_to_ermai_info_file,
                                                    plot_if_func=plot_if_mai,
                                                    plot_complete_func=plot_complete,
                                                    show_func=show_func
                                                )
                                                current_play.join_price = df.iloc[-1]['price']
                                                # current_play.support_price = min(history_long_time_segments[-1]["top_price"],
                                                #                                  history_long_time_segments[-1]["bottom_price"] + (
                                                #                                              history_long_time_segments[-3]["top_price"] -
                                                #                                              history_long_time_segments[-3][
                                                #                                                  "bottom_price"]))
                                                current_play.support_price = max(history_long_time_segments[-1]["top_price"],
                                                                                 history_long_time_segments[-1]["bottom_price"] + beichi_hyperparameter*(
                                                                                         history_long_time_segments[-3]["top_price"] -
                                                                                         history_long_time_segments[-3][
                                                                                             "bottom_price"]))
                                                current_play.support_price_old_big_zhongshu = support_price_old_big_zhongshu

                                                current_play.last_operation_seg_complete_time_zuokong = max(history_long_time_segments[-1]["top_time"], history_long_time_segments[-1]["bottom_time"])
                                                # current_play.compare_pen_min_or_max = max(current_play.yimai_price,
                                                #                                           df.iloc[-1]['price'],
                                                #                                           fixed_pens[-1][
                                                #                                               "top_price"])  # 做空介入后，线段后笔的极大值，或做多后，线段后笔的极小值，以避免重复介入
                elif current_play.yimai_status == "short":
                    if df.iloc[-1]['price'] >= current_play.join_price * 1.005:
                        print("止损了止损了止损了止损了止损了止损了")
                        current_play.handle_pingcang(
                            df_row=df.iloc[-1],
                            info_save_mode=INFO_SAVE_TO_FILE_MODE,
                            print_return_info=PRINT_HUICE_RETURN_INFO,
                            show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                            write_func=write_to_ermai_info_file,
                            plot_if_func=plot_if_mai,
                            plot_complete_func=plot_complete,
                            show_func=show_func
                        )
                        current_play.last_operation_seg_complete_time_zuokong = max(
                            history_long_time_segments[-1]["top_time"],
                            history_long_time_segments[-1]["bottom_time"])
                    elif df.iloc[-1]['price'] >= current_play.support_price:
                        print("止损了止损了止损了止损了止损了止损了")
                        #击穿一卖就止损
                        current_play.handle_pingcang(
                            df_row=df.iloc[-1],
                            info_save_mode=INFO_SAVE_TO_FILE_MODE,
                            print_return_info=PRINT_HUICE_RETURN_INFO,
                            show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                            write_func=write_to_ermai_info_file,
                            plot_if_func=plot_if_mai,
                            plot_complete_func=plot_complete,
                            show_func=show_func
                        )
                        current_play.last_operation_seg_complete_time_zuokong = max(history_long_time_segments[-1]["top_time"],
                                                                            history_long_time_segments[-1]["bottom_time"])
                        # current_play.compare_pen_min_or_max = max(current_play.yimai_price,
                        #                                           df.iloc[-1]['price'],
                        #                                           fixed_pens[-1][
                        #                                               "top_price"])  # 做空介入后，线段后笔的极大值，或做多后，线段后笔的极小值，以避免重复介入
                    elif min(history_long_time_segments[-1]["top_time"], history_long_time_segments[-1]["bottom_time"]) < current_play.yimai_time and max(history_long_time_segments[-1]["top_time"], history_long_time_segments[-1]["bottom_time"]) > current_play.yimai_time:
                        if history_long_time_segments[-1]["direction"] == "Up" and (history_long_time_segments[-1]["top_price"] - history_long_time_segments[-1]["bottom_price"] >= beichi_hyperparameter*(history_long_time_segments[-3]["top_price"] - history_long_time_segments[-3]["bottom_price"])):
                            print("背驰被破坏 止损了止损了止损了止损了止损了止损了")
                            current_play.handle_pingcang(
                                df_row=df.iloc[-1],
                                info_save_mode=INFO_SAVE_TO_FILE_MODE,
                                print_return_info=PRINT_HUICE_RETURN_INFO,
                                show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                                write_func=write_to_ermai_info_file,
                                plot_if_func=plot_if_mai,
                                plot_complete_func=plot_complete,
                                show_func=show_func
                            )
                            current_play.last_operation_seg_complete_time_zuokong = max(history_long_time_segments[-1]["top_time"],
                                                                                history_long_time_segments[-1]["bottom_time"])
                            # current_play.compare_pen_min_or_max = max(current_play.yimai_price,
                            #                                           df.iloc[-1]['price'],
                            #                                           fixed_pens[-1][
                            #                                               "top_price"])  # 做空介入后，线段后笔的极大值，或做多后，线段后笔的极小值，以避免重复介入
                        else:
                            print("一卖位置被更新")
                            current_play.yimai_time = history_long_time_segments[-1]["top_time"]
                            current_play.yimai_price = history_long_time_segments[-1]["top_price"]
                            current_play.ermai_time = history_long_time_segments[-1]["top_time"]
                            current_play.ermai_price = history_long_time_segments[-1]["top_price"]
                            # current_play.support_price = history_long_time_segments[-1]["top_price"]
                            if history_long_time_segments[-1]["direction"] == "Up":
                                current_play.support_price= max(history_long_time_segments[-1]["top_price"],
                                                                history_long_time_segments[-1]["bottom_price"] + beichi_hyperparameter * (
                                                                        history_long_time_segments[-3]["top_price"] -
                                                                        history_long_time_segments[-3][
                                                                            "bottom_price"]))
                                current_play.last_operation_seg_complete_time_zuokong = max(history_long_time_segments[-1]["top_time"], history_long_time_segments[-1]["bottom_time"])
                                # current_play.compare_pen_min_or_max = max(current_play.yimai_price,
                                #                                           df.iloc[-1]['price'],
                                #                                           fixed_pens[-1][
                                #                                               "top_price"])  # 做空介入后，线段后笔的极大值，或做多后，线段后笔的极小值，以避免重复介入

                            else:
                                current_play.support_price = max(history_long_time_segments[-2]["top_price"],
                                                                 history_long_time_segments[-2]["bottom_price"] + beichi_hyperparameter * (
                                                                         history_long_time_segments[-4]["top_price"] -
                                                                         history_long_time_segments[-4][
                                                                             "bottom_price"]))
                                current_play.last_operation_seg_complete_time_zuokong = max(history_long_time_segments[-1]["top_time"], history_long_time_segments[-1]["bottom_time"])
                                # current_play.compare_pen_min_or_max = max(current_play.yimai_price,
                                #                                           df.iloc[-1]['price'],
                                #                                           fixed_pens[-1][
                                #                                               "top_price"])  # 做空介入后，线段后笔的极大值，或做多后，线段后笔的极小值，以避免重复介入
                    #elif (min(history_long_time_segments[-1]["top_time"], history_long_time_segments[-1]["bottom_time"]) >= current_play.yimai_time):
                        # if history_long_time_segments[-1]["direction"] == "Down":
                        #     if history_long_time_segments[-1]["top_price"] < current_play.ermai_price and history_long_time_segments[-1]["bottom_price"] < current_play.join_price: #已经在明确下跌，创出新低
                        #         if (history_long_time_segments[-1]["top_price"] - history_long_time_segments[-1]["bottom_price"]) < (history_long_time_segments[-3]["top_price"] - history_long_time_segments[-3]["bottom_price"]): #背驰
                        #             current_play.handle_pingcang(
                        #                 df_row=df.iloc[-1],
                        #                 info_save_mode=INFO_SAVE_TO_FILE_MODE,
                        #                 print_return_info=PRINT_HUICE_RETURN_INFO,
                        #                 show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                        #                 write_func=write_to_ermai_info_file,
                        #                 plot_if_func=plot_if_mai,
                        #                 plot_complete_func=plot_complete,
                        #                 show_func=show_func
                        #             )
                    elif df.iloc[-1]['price'] <= current_play.support_price_old_big_zhongshu:
                        print("赚了减点仓，赚了减点仓，赚了减点仓，赚了减点仓，赚了减点仓")
                        current_play.handle_jiancang(
                            df_row=df.iloc[-1],
                            info_save_mode=INFO_SAVE_TO_FILE_MODE,
                            print_return_info=PRINT_HUICE_RETURN_INFO,
                            show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                            write_func=write_to_ermai_info_file,
                            plot_if_func=plot_if_mai,
                            plot_complete_func=plot_complete,
                            show_func=show_func,
                            jiancang_percent=0.5
                        )
                        current_play.support_price_old_big_zhongshu = -100  # 只减仓一次，将减仓支撑弄很小
                    elif min(history_long_time_segments[-3]["top_time"], history_long_time_segments[-3]["bottom_time"]) >= current_play.yimai_time:  # 右侧交易，右侧止盈
                        current_play.support_price = current_play.yimai_price #一买过去很久，将止损变严格
                        if history_long_time_segments[-1]["bottom_time"] < history_long_time_segments[-3]["bottom_time"]: #赚一波就跑，猥琐
                            print("止赢了止赢了止赢了止赢了")
                            current_play.handle_pingcang(
                                df_row=df.iloc[-1],
                                info_save_mode=INFO_SAVE_TO_FILE_MODE,
                                print_return_info=PRINT_HUICE_RETURN_INFO,
                                show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                                write_func=write_to_ermai_info_file,
                                plot_if_func=plot_if_mai,
                                plot_complete_func=plot_complete,
                                show_func=show_func
                            )
                        elif history_long_time_segments[-1]["direction"] == "Up": #右侧交易，右侧止盈
                            # if history_long_time_segments[-2]["top_price"] < current_play.yimai_price and history_long_time_segments[-2][
                            #     "bottom_price"] < current_play.join_price:  # 已经在明确下跌，创出新低
                                if (history_long_time_segments[-2]["top_price"] - history_long_time_segments[-2]["bottom_price"]) < (
                                        history_long_time_segments[-4]["top_price"] - history_long_time_segments[-4]["bottom_price"]):  # 背驰
                                    current_play.handle_pingcang(
                                        df_row=df.iloc[-1],
                                        info_save_mode=INFO_SAVE_TO_FILE_MODE,
                                        print_return_info=PRINT_HUICE_RETURN_INFO,
                                        show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                                        write_func=write_to_ermai_info_file,
                                        plot_if_func=plot_if_mai,
                                        plot_complete_func=plot_complete,
                                        show_func=show_func
                                    )
                        elif history_long_time_segments[-1]["direction"] == "Down": #右侧交易，右侧止盈
                            # if history_long_time_segments[-1]["top_price"] < current_play.yimai_price and history_long_time_segments[-1][
                            #     "bottom_price"] < current_play.join_price:  # 已经在明确下跌，创出新低
                                if (history_long_time_segments[-1]["top_price"] - history_long_time_segments[-1]["bottom_price"]) < (
                                        history_long_time_segments[-3]["top_price"] - history_long_time_segments[-3]["bottom_price"]):  # 背驰
                                    current_play.handle_pingcang(
                                        df_row=df.iloc[-1],
                                        info_save_mode=INFO_SAVE_TO_FILE_MODE,
                                        print_return_info=PRINT_HUICE_RETURN_INFO,
                                        show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                                        write_func=write_to_ermai_info_file,
                                        plot_if_func=plot_if_mai,
                                        plot_complete_func=plot_complete,
                                        show_func=show_func
                                    )
                        # elif (min(history_long_time_segments[-3]["top_time"], history_long_time_segments[-3]["bottom_time"]) >= current_play.ermai_time): #二卖介入后走出三段段，看看有没有盘整
                        #     if df.iloc[-1]['price'] >= current_play.join_price: #如果还不盈利，就没必要等了，要么机会结束，要么是盘整
                        #         current_play.handle_pingcang(
                        #             df_row=df.iloc[-1],
                        #             info_save_mode=INFO_SAVE_TO_FILE_MODE,
                        #             print_return_info=PRINT_HUICE_RETURN_INFO,
                        #             show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                        #             write_func=write_to_ermai_info_file,
                        #             plot_if_func=plot_if_mai,
                        #             plot_complete_func=plot_complete,
                        #             show_func=show_func
                        #         )



                #做多检查
                if current_play.yimai_status == "inactivate" and len(history_long_time_segments) >= 5 and len(history_long_time_segment_zhongshus) >= 2:# and (df.iloc[-1]['timestamp'].time() < datetime_time(18, 30)):
                    if history_long_time_segments[-2]["direction"] == "Down" and (current_play.last_operation_seg_complete_time_zuoduo != max(history_long_time_segments[-1]["top_time"], history_long_time_segments[-1]["bottom_time"])):
                        # 以找买点为目标,并且上次止损后有新的线段形成
                        if history_long_time_segments[-2]["bottom_price"] < history_long_time_segments[-4][
                            "bottom_price"]:  # 至少是新低才去考虑是不是一买
                            if (history_long_time_segments[-2]["top_price"] - history_long_time_segments[-2]["bottom_price"] < beichi_hyperparameter*(history_long_time_segments[-4][
                                "top_price"] - history_long_time_segments[-4]["bottom_price"])) and (history_long_time_segments[-2]["top_price"] - df.iloc[-1]['price'] < beichi_hyperparameter*(history_long_time_segments[-4][
                                "top_price"] - history_long_time_segments[-4]["bottom_price"])):  # history_long_time_segments[-2]相比history_long_time_segments[-4]背驰, 且当前价格不破坏背驰
                                if history_long_time_segments[-4]["top_price"] > history_long_time_segments[-2][
                                    "top_price"]:  # history_long_time_segments[-4,-3,-2]是趋势

                                    panzheng_then_qushi = False
                                    base_zhongshu = history_long_time_segment_zhongshus[-1]
                                    support_price_old_big_zhongshu = None
                                    for zhongshu_before in history_long_time_segment_zhongshus[-2:]:
                                        if zhongshu_before["DD"] > base_zhongshu["ZG"]: #当前是上涨趋势
                                            base_zhongshu = zhongshu_before
                                            if len(zhongshu_before["core_pens_index"])>=3: #前面是盘整
                                                panzheng_then_qushi = True
                                                support_price_old_big_zhongshu = zhongshu_before["DD"]
                                        else:
                                            break

                                    if history_long_time_segment_zhongshus[-2]["end_time"] == history_long_time_segments[-4]["top_time"]:# and (len(history_long_time_segment_zhongshus[-2]["core_pens_index"])>=3): #前面一个中枢级别大
                                        # if history_long_time_segment_zhongshus[-2]["DD"] < history_long_time_segment_zhongshus[-1]["ZG"]: #否则可能是 上涨+下跌，而我们要盘整+下跌
                                        if panzheng_then_qushi:
                                            if history_long_time_segments[-1]["top_price"] < history_long_time_segment_zhongshus[-2]["ZD"] and df.iloc[-1]['price'] < history_long_time_segment_zhongshus[-2]["ZD"]:
                                                print("一买一买，一买一买，一买一买，标了二买但实际上是一买，回头再修改")
                                                last_direction = history_long_time_segments[-2]["direction"]
                                                current_play.update_yimai_by_direction(history_long_time_segments[-2], last_direction)
                                                current_play.handle_ermai_confirmation(
                                                    segment=history_long_time_segments[-2],
                                                    df_row=df.iloc[-1],
                                                    info_save_mode=INFO_SAVE_TO_FILE_MODE,
                                                    print_return_info=PRINT_HUICE_RETURN_INFO,
                                                    show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                                                    write_func=write_to_ermai_info_file,
                                                    plot_if_func=plot_if_mai,
                                                    plot_complete_func=plot_complete,
                                                    show_func=show_func
                                                )
                                                current_play.join_price = df.iloc[-1]['price']

                                                current_play.support_price = min(history_long_time_segments[-2]["bottom_price"],
                                                                                 history_long_time_segments[-2]["top_price"] - beichi_hyperparameter*(
                                                                                         history_long_time_segments[-4]["top_price"] -
                                                                                         history_long_time_segments[-4][
                                                                                             "bottom_price"]))
                                                current_play.support_price_old_big_zhongshu = support_price_old_big_zhongshu

                                                current_play.last_operation_seg_complete_time_zuoduo = max(history_long_time_segments[-1]["top_time"], history_long_time_segments[-1]["bottom_time"])
                                                # current_play.compare_pen_min_or_max = min(current_play.yimai_price,
                                                #                                           df.iloc[-1]['price'],
                                                #                                           fixed_pens[-1][
                                                #                                               "bottom_price"])  # 做空介入后，线段后笔的极大值，或做多后，线段后笔的极小值，以避免重复介入
                    elif history_long_time_segments[-1]["direction"] == "Down" and (current_play.last_operation_seg_complete_time_zuoduo != max(history_long_time_segments[-1]["top_time"], history_long_time_segments[-1]["bottom_time"])):
                        # 以找买点为目标,并且上次止损后有新的线段形成
                        if history_long_time_segments[-1]["bottom_price"] < history_long_time_segments[-3][
                            "bottom_price"]:  # 至少是新低才去考虑是不是一买
                            if (history_long_time_segments[-1]["top_price"] - history_long_time_segments[-1]["bottom_price"] < beichi_hyperparameter*(history_long_time_segments[-3][
                                "top_price"] - history_long_time_segments[-3]["bottom_price"])) and (history_long_time_segments[-1]["top_price"] - df.iloc[-1]['price'] < beichi_hyperparameter*(history_long_time_segments[-3][
                                "top_price"] - history_long_time_segments[-3]["bottom_price"])):  # history_long_time_segments[-1]相比history_long_time_segments[-3]背驰, 且当前价格不破坏背驰
                                if history_long_time_segments[-3]["top_price"] > history_long_time_segments[-1][
                                    "top_price"]:  # history_long_time_segments[-3,-2,-1]是趋势

                                    panzheng_then_qushi = False
                                    base_zhongshu = history_long_time_segment_zhongshus[-1]
                                    support_price_old_big_zhongshu = None
                                    for zhongshu_before in history_long_time_segment_zhongshus[-2:]:
                                        if zhongshu_before["DD"] > base_zhongshu["ZG"]:  # 当前是下跌趋势
                                            base_zhongshu = zhongshu_before
                                            print(f"""数出来中枢的段数{len(zhongshu_before["core_pens_index"])}""")
                                            if len(zhongshu_before["core_pens_index"]) >= 3:  # 前面是盘整
                                                panzheng_then_qushi = True
                                                support_price_old_big_zhongshu = zhongshu_before["DD"]
                                        else:
                                            break
                                    if history_long_time_segment_zhongshus[-2]["end_time"] == history_long_time_segments[-3]["top_time"]:# and (len(history_long_time_segment_zhongshus[-2]["core_pens_index"])>=3): #前面一个中枢级别大
                                        # if history_long_time_segment_zhongshus[-2]["DD"] < history_long_time_segment_zhongshus[-1][
                                        #     "ZG"]:  # 否则可能是 上涨+下跌，而我们要盘整+下跌
                                        if panzheng_then_qushi:
                                            if df.iloc[-1]['price'] < history_long_time_segment_zhongshus[-2]["ZD"]:
                                                print("一买一买，一买一买，一买一买，标了二买但实际上是一买，回头再修改")
                                                last_direction = history_long_time_segments[-1]["direction"]
                                                current_play.update_yimai_by_direction(history_long_time_segments[-1], last_direction)
                                                current_play.handle_ermai_confirmation(
                                                    segment=history_long_time_segments[-1],
                                                    df_row=df.iloc[-1],
                                                    info_save_mode=INFO_SAVE_TO_FILE_MODE,
                                                    print_return_info=PRINT_HUICE_RETURN_INFO,
                                                    show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                                                    write_func=write_to_ermai_info_file,
                                                    plot_if_func=plot_if_mai,
                                                    plot_complete_func=plot_complete,
                                                    show_func=show_func
                                                )
                                                current_play.join_price = df.iloc[-1]['price']

                                                current_play.support_price = min(history_long_time_segments[-1]["bottom_price"],
                                                                                 history_long_time_segments[-1]["top_price"] - beichi_hyperparameter*(
                                                                                         history_long_time_segments[-3]["top_price"] -
                                                                                         history_long_time_segments[-3][
                                                                                             "bottom_price"]))
                                                current_play.support_price_old_big_zhongshu = support_price_old_big_zhongshu

                                                current_play.last_operation_seg_complete_time_zuoduo = max(history_long_time_segments[-1]["top_time"], history_long_time_segments[-1]["bottom_time"])
                                                # current_play.compare_pen_min_or_max = min(current_play.yimai_price,
                                                #                                           df.iloc[-1]['price'],
                                                #                                           fixed_pens[-1][
                                                #                                               "bottom_price"])  # 做空介入后，线段后笔的极大值，或做多后，线段后笔的极小值，以避免重复介入
                elif current_play.yimai_status == "long":
                    if df.iloc[-1]['price'] <= current_play.join_price * 0.995:
                        print("止损了止损了止损了止损了止损了止损了")
                        current_play.handle_pingcang(
                            df_row=df.iloc[-1],
                            info_save_mode=INFO_SAVE_TO_FILE_MODE,
                            print_return_info=PRINT_HUICE_RETURN_INFO,
                            show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                            write_func=write_to_ermai_info_file,
                            plot_if_func=plot_if_mai,
                            plot_complete_func=plot_complete,
                            show_func=show_func
                        )
                        current_play.last_operation_seg_complete_time_zuokong = max(
                            history_long_time_segments[-1]["top_time"],
                            history_long_time_segments[-1]["bottom_time"])
                    elif df.iloc[-1]['price'] <= current_play.support_price:
                        print("止损了止损了止损了止损了止损了止损了")
                        #击穿一卖就止损
                        current_play.handle_pingcang(
                            df_row=df.iloc[-1],
                            info_save_mode=INFO_SAVE_TO_FILE_MODE,
                            print_return_info=PRINT_HUICE_RETURN_INFO,
                            show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                            write_func=write_to_ermai_info_file,
                            plot_if_func=plot_if_mai,
                            plot_complete_func=plot_complete,
                            show_func=show_func
                        )
                        current_play.last_operation_seg_complete_time_zuoduo = max(history_long_time_segments[-1]["top_time"],
                                                                            history_long_time_segments[-1]["bottom_time"])
                        # current_play.compare_pen_min_or_max = min(current_play.yimai_price,
                        #                                           df.iloc[-1]['price'],
                        #                                           fixed_pens[-1][
                        #                                               "bottom_price"])  # 做空介入后，线段后笔的极大值，或做多后，线段后笔的极小值，以避免重复介入
                    elif min(history_long_time_segments[-1]["top_time"], history_long_time_segments[-1]["bottom_time"]) < current_play.yimai_time and max(history_long_time_segments[-1]["top_time"], history_long_time_segments[-1]["bottom_time"]) > current_play.yimai_time:
                        if history_long_time_segments[-1]["direction"] == "Down" and (history_long_time_segments[-1]["top_price"] - history_long_time_segments[-1]["bottom_price"] >= beichi_hyperparameter*(history_long_time_segments[-3]["top_price"] - history_long_time_segments[-3]["bottom_price"])):
                            print("背驰被破坏 止损了止损了止损了止损了止损了止损了")
                            current_play.handle_pingcang(
                                df_row=df.iloc[-1],
                                info_save_mode=INFO_SAVE_TO_FILE_MODE,
                                print_return_info=PRINT_HUICE_RETURN_INFO,
                                show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                                write_func=write_to_ermai_info_file,
                                plot_if_func=plot_if_mai,
                                plot_complete_func=plot_complete,
                                show_func=show_func
                            )
                            current_play.last_operation_seg_complete_time_zuoduo = max(history_long_time_segments[-1]["top_time"],
                                                                                history_long_time_segments[-1]["bottom_time"])
                            # current_play.compare_pen_min_or_max = min(current_play.yimai_price,
                            #                                           df.iloc[-1]['price'],
                            #                                           fixed_pens[-1][
                            #                                               "bottom_price"])  # 做空介入后，线段后笔的极大值，或做多后，线段后笔的极小值，以避免重复介入
                        else:
                            print("一买位置被更新")
                            current_play.yimai_time = history_long_time_segments[-1]["bottom_time"]
                            current_play.yimai_price = history_long_time_segments[-1]["bottom_price"]
                            current_play.ermai_time = history_long_time_segments[-1]["bottom_time"]
                            current_play.ermai_price = history_long_time_segments[-1]["bottom_price"]
                            # current_play.support_price = history_long_time_segments[-1]["bottom_price"]
                            if history_long_time_segments[-1]["direction"] == "Down":
                                current_play.support_price = min(history_long_time_segments[-1]["bottom_price"],
                                                                 history_long_time_segments[-1][
                                                                     "top_price"] - beichi_hyperparameter * (
                                                                         history_long_time_segments[-3]["top_price"] -
                                                                         history_long_time_segments[-3][
                                                                             "bottom_price"]))
                                current_play.last_operation_seg_complete_time_zuoduo = max(history_long_time_segments[-1]["top_time"], history_long_time_segments[-1]["bottom_time"])
                                # current_play.compare_pen_min_or_max = min(current_play.yimai_price,
                                #                                           df.iloc[-1]['price'],
                                #                                           fixed_pens[-1][
                                #                                               "bottom_price"])  # 做空介入后，线段后笔的极大值，或做多后，线段后笔的极小值，以避免重复介入

                            else:
                                current_play.support_price = min(history_long_time_segments[-2]["bottom_price"],
                                                                 history_long_time_segments[-2][
                                                                     "top_price"] - beichi_hyperparameter * (
                                                                         history_long_time_segments[-4]["top_price"] -
                                                                         history_long_time_segments[-4][
                                                                             "bottom_price"]))
                                current_play.last_operation_seg_complete_time_zuoduo = max(history_long_time_segments[-1]["top_time"], history_long_time_segments[-1]["bottom_time"])
                                # current_play.compare_pen_min_or_max = min(current_play.yimai_price,
                                #                                           df.iloc[-1]['price'],
                                #                                           fixed_pens[-1][
                                #                                               "bottom_price"])  # 做空介入后，线段后笔的极大值，或做多后，线段后笔的极小值，以避免重复介入
                    elif df.iloc[-1]['price'] >= current_play.support_price_old_big_zhongshu:
                        print("赚了减点仓，赚了减点仓，赚了减点仓，赚了减点仓，赚了减点仓")
                        current_play.handle_jiancang(
                            df_row=df.iloc[-1],
                            info_save_mode=INFO_SAVE_TO_FILE_MODE,
                            print_return_info=PRINT_HUICE_RETURN_INFO,
                            show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                            write_func=write_to_ermai_info_file,
                            plot_if_func=plot_if_mai,
                            plot_complete_func=plot_complete,
                            show_func=show_func,
                            jiancang_percent=0.5
                        )
                        current_play.support_price_old_big_zhongshu = 1000000000 #只减仓一次，将减仓支撑放大
                    elif min(history_long_time_segments[-3]["top_time"], history_long_time_segments[-3]["bottom_time"]) >= current_play.yimai_time:  # 右侧交易，右侧止盈
                        current_play.support_price = current_play.yimai_price #一买过去很久，将止损变严格
                        if history_long_time_segments[-1]["top_time"] > history_long_time_segments[-3]["top_time"]: #赚一波就跑，猥琐
                            print("止赢了止赢了止赢了止赢了")
                            current_play.handle_pingcang(
                                df_row=df.iloc[-1],
                                info_save_mode=INFO_SAVE_TO_FILE_MODE,
                                print_return_info=PRINT_HUICE_RETURN_INFO,
                                show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                                write_func=write_to_ermai_info_file,
                                plot_if_func=plot_if_mai,
                                plot_complete_func=plot_complete,
                                show_func=show_func
                            )
                        elif history_long_time_segments[-1]["direction"] == "Down": #右侧交易，右侧止盈
                            # if history_long_time_segments[-2]["top_price"] < current_play.yimai_price and history_long_time_segments[-2][
                            #     "bottom_price"] < current_play.join_price:  # 已经在明确下跌，创出新低
                                if (history_long_time_segments[-2]["top_price"] - history_long_time_segments[-2]["bottom_price"]) < (
                                        history_long_time_segments[-4]["top_price"] - history_long_time_segments[-4]["bottom_price"]):  # 背驰
                                    current_play.handle_pingcang(
                                        df_row=df.iloc[-1],
                                        info_save_mode=INFO_SAVE_TO_FILE_MODE,
                                        print_return_info=PRINT_HUICE_RETURN_INFO,
                                        show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                                        write_func=write_to_ermai_info_file,
                                        plot_if_func=plot_if_mai,
                                        plot_complete_func=plot_complete,
                                        show_func=show_func
                                    )
                        elif history_long_time_segments[-1]["direction"] == "Up": #右侧交易，右侧止盈
                            # if history_long_time_segments[-1]["top_price"] < current_play.yimai_price and history_long_time_segments[-1][
                            #     "bottom_price"] < current_play.join_price:  # 已经在明确下跌，创出新低
                                if (history_long_time_segments[-1]["top_price"] - history_long_time_segments[-1]["bottom_price"]) < (
                                        history_long_time_segments[-3]["top_price"] - history_long_time_segments[-3]["bottom_price"]):  # 背驰
                                    current_play.handle_pingcang(
                                        df_row=df.iloc[-1],
                                        info_save_mode=INFO_SAVE_TO_FILE_MODE,
                                        print_return_info=PRINT_HUICE_RETURN_INFO,
                                        show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                                        write_func=write_to_ermai_info_file,
                                        plot_if_func=plot_if_mai,
                                        plot_complete_func=plot_complete,
                                        show_func=show_func
                                    )
                        # elif (min(history_long_time_segments[-3]["top_time"], history_long_time_segments[-3]["bottom_time"]) >= current_play.ermai_time): #二卖介入后走出三段段，看看有没有盘整
                        #     if df.iloc[-1]['price'] >= current_play.join_price: #如果还不盈利，就没必要等了，要么机会结束，要么是盘整
                        #         current_play.handle_pingcang(
                        #             df_row=df.iloc[-1],
                        #             info_save_mode=INFO_SAVE_TO_FILE_MODE,
                        #             print_return_info=PRINT_HUICE_RETURN_INFO,
                        #             show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                        #             write_func=write_to_ermai_info_file,
                        #             plot_if_func=plot_if_mai,
                        #             plot_complete_func=plot_complete,
                        #             show_func=show_func
                        #         )









                # if current_play.yimai_status == "inactivate" and (df.iloc[-1]['timestamp'].time() < datetime_time(18, 30)):
                #     if segments_fix[-2]["direction"] == "Up": #以找卖点为目标
                #         if segments_fix[-2]["top_price"] < segments_fix[-4]["top_price"]: #可以是二卖, segments_fix[-3]["top_price"]可以是一卖
                #             if segments_fix[-4]["top_price"] > segments_fix[-6]["top_price"]: #segments_fix[-3]["top_price"]是新高
                #                 if segments_fix[-4]["top_price"] - segments_fix[-4]["bottom_price"] < segments_fix[-6]["top_price"] - segments_fix[-6]["bottom_price"]: #segments_fix[-4]相比segments_fix[-6]背驰
                #                     if segments_fix[-6]["bottom_price"] < segments_fix[-4]["bottom_price"]: #segments_fix[-6,-5,-4]是趋势
                #                         if (segments_fix[-2]["bottom_price"] > segments_fix[-6]["bottom_price"]) and (segments_fix[-2]["top_price"] > segments_fix[-4]["bottom_price"]): #给下跌留点空间,并且不操作三卖
                #                             if segments_fix[-1]["bottom_price"] > segments_fix[-2]["bottom_price"] and segments_fix[-2]["bottom_price"] < df.iloc[-1]['price'] < segments_fix[-2]["top_price"]: #下拉段不破二卖形成段的低位， 当前价也还在二卖区间内
                #                                 print("二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖")
                #                                 last_direction = segments_fix[-2]["direction"]
                #                                 current_play.update_yimai_by_direction(segments_fix[-4], last_direction)
                #                                 current_play.handle_ermai_confirmation(
                #                                     segment=segments_fix[-2],
                #                                     df_row=df.iloc[-1],
                #                                     info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #                                     print_return_info=PRINT_HUICE_RETURN_INFO,
                #                                     show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #                                     write_func=write_to_ermai_info_file,
                #                                     plot_if_func=plot_if_mai,
                #                                     plot_complete_func=plot_complete,
                #                                     show_func=show_func
                #                                 )
                #                                 current_play.join_price = df.iloc[-1]['price']
                #                                 current_play.support_price = min(segments_fix[-4]["top_price"], segments_fix[-4]["bottom_price"] + (segments_fix[-6]["top_price"] - segments_fix[-6]["bottom_price"]))
                #     elif segments_fix[-1]["direction"] == "Up": #以找卖点为目标
                #         if segments_fix[-1]["top_price"] < segments_fix[-3]["top_price"]: #可以是二卖, segments_fix[-4]["top_price"]可以是一卖
                #             if segments_fix[-3]["top_price"] > segments_fix[-5]["top_price"]: #segments_fix[-4]["top_price"]是新高
                #                 if segments_fix[-3]["top_price"] - segments_fix[-3]["bottom_price"] < segments_fix[-5]["top_price"] - segments_fix[-5]["bottom_price"]: #segments_fix[-3]相比segments_fix[-5]背驰
                #                     if segments_fix[-5]["bottom_price"] < segments_fix[-3]["bottom_price"]: #segments_fix[-5,-4,-3]是趋势
                #                         if (segments_fix[-1]["bottom_price"] > segments_fix[-5]["bottom_price"]) and (segments_fix[-1]["top_price"] > segments_fix[-3]["bottom_price"]): #给下跌留点空间,并且不操作三卖
                #                             if segments_fix[-1]["bottom_price"] < df.iloc[-1]['price'] < segments_fix[-1]["top_price"]: #下拉段不破二卖形成段的低位， 当前价也还在二卖区间内
                #                                 print("二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖二卖")
                #                                 last_direction = segments_fix[-2]["direction"]
                #                                 current_play.update_yimai_by_direction(segments_fix[-4], last_direction)
                #                                 current_play.handle_ermai_confirmation(
                #                                     segment=segments_fix[-1],
                #                                     df_row=df.iloc[-1],
                #                                     info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #                                     print_return_info=PRINT_HUICE_RETURN_INFO,
                #                                     show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #                                     write_func=write_to_ermai_info_file,
                #                                     plot_if_func=plot_if_mai,
                #                                     plot_complete_func=plot_complete,
                #                                     show_func=show_func
                #                                 )
                #                                 current_play.join_price = df.iloc[-1]['price']
                #                                 current_play.support_price = min(segments_fix[-4]["top_price"], segments_fix[-4]["bottom_price"] + (segments_fix[-6]["top_price"] - segments_fix[-6]["bottom_price"]))
                # elif current_play.yimai_status == "short":
                #     if df.iloc[-1]['price'] >= current_play.support_price:
                #         #击穿一卖就止损
                #         current_play.handle_pingcang(
                #             df_row=df.iloc[-1],
                #             info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #             print_return_info=PRINT_HUICE_RETURN_INFO,
                #             show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #             write_func=write_to_ermai_info_file,
                #             plot_if_func=plot_if_mai,
                #             plot_complete_func=plot_complete,
                #             show_func=show_func
                #         )
                #     elif (min(segments_fix[-1]["top_time"], segments_fix[-1]["bottom_time"]) >= current_play.ermai_time):
                #         # if segments_fix[-1]["direction"] == "Down":
                #         #     if segments_fix[-1]["top_price"] < current_play.ermai_price and segments_fix[-1]["bottom_price"] < current_play.join_price: #已经在明确下跌，创出新低
                #         #         if (segments_fix[-1]["top_price"] - segments_fix[-1]["bottom_price"]) < (segments_fix[-3]["top_price"] - segments_fix[-3]["bottom_price"]): #背驰
                #         #             current_play.handle_pingcang(
                #         #                 df_row=df.iloc[-1],
                #         #                 info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #         #                 print_return_info=PRINT_HUICE_RETURN_INFO,
                #         #                 show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #         #                 write_func=write_to_ermai_info_file,
                #         #                 plot_if_func=plot_if_mai,
                #         #                 plot_complete_func=plot_complete,
                #         #                 show_func=show_func
                #         #             )
                #         if segments_fix[-1]["direction"] == "Up": #右侧交易，右侧止盈
                #             if segments_fix[-2]["top_price"] < current_play.ermai_price and segments_fix[-2][
                #                 "bottom_price"] < current_play.join_price:  # 已经在明确下跌，创出新低
                #                 if (segments_fix[-2]["top_price"] - segments_fix[-2]["bottom_price"]) < (
                #                         segments_fix[-4]["top_price"] - segments_fix[-4]["bottom_price"]):  # 背驰
                #                     current_play.handle_pingcang(
                #                         df_row=df.iloc[-1],
                #                         info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #                         print_return_info=PRINT_HUICE_RETURN_INFO,
                #                         show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #                         write_func=write_to_ermai_info_file,
                #                         plot_if_func=plot_if_mai,
                #                         plot_complete_func=plot_complete,
                #                         show_func=show_func
                #                     )
                #         elif (min(segments_fix[-3]["top_time"], segments_fix[-3]["bottom_time"]) >= current_play.ermai_time): #二卖介入后走出三段段，看看有没有盘整
                #             if df.iloc[-1]['price'] >= current_play.join_price: #如果还不盈利，就没必要等了，要么机会结束，要么是盘整
                #                 current_play.handle_pingcang(
                #                     df_row=df.iloc[-1],
                #                     info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #                     print_return_info=PRINT_HUICE_RETURN_INFO,
                #                     show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #                     write_func=write_to_ermai_info_file,
                #                     plot_if_func=plot_if_mai,
                #                     plot_complete_func=plot_complete,
                #                     show_func=show_func
                #                 )











                # if current_play.join_price:
                #     print(current_play.join_price, current_play.join_price * 0.999, current_play.yimai_status, df.iloc[-1]['price'])
                # if current_play.yimai_status == "inactivate" and (df.iloc[-1]['timestamp'].time() < datetime_time(19, 30)):
                #     last_direction = fixed_pens[-1]["direction"]
                #     current_play.update_yimai_by_direction(fixed_pens[-1], last_direction)
                #     if (last_direction=="Up" and (fixed_pens[-1]["top_price"] - df.iloc[-1]['price'] < 0.2*(fixed_pens[-1]["top_price"]-fixed_pens[-1]["bottom_price"]))) or (last_direction=="Down" and (df.iloc[-1]['price'] - fixed_pens[-1]["bottom_price"] < 0.2 * (fixed_pens[-1]["top_price"] - fixed_pens[-1]["bottom_price"]))):
                #         current_play.handle_ermai_confirmation(
                #             segment=fixed_pens[-1],
                #             df_row=df.iloc[-1],
                #             info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #             print_return_info=PRINT_HUICE_RETURN_INFO,
                #             show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #             write_func=write_to_ermai_info_file,
                #             plot_if_func=plot_if_mai,
                #             plot_complete_func=plot_complete,
                #             show_func=show_func,
                #             ersan_lianmai=True,
                #             zhongshu_before_ersanlianmai=pen_zhongshus_clean[-1]
                #         )
                #         current_play.join_price = df.iloc[-1]['price']
                #     else:
                #         current_play.reset()
                # elif (current_play.yimai_status == "long" and fixed_pens[-1]["direction"] == "Up" and (fixed_pens[-1]["top_price"] - df.iloc[-1]['price'] > 0.2*(fixed_pens[-1]["top_price"]-current_play.join_price))) or (current_play.yimai_status == "short" and fixed_pens[-1]["direction"] == "Down" and (df.iloc[-1]['price'] - fixed_pens[-1]["bottom_price"] > 0.2 * (current_play.join_price - fixed_pens[-1]["bottom_price"]))):
                #         current_play.handle_pingcang(
                #             df_row=df.iloc[-1],
                #             info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #             print_return_info=PRINT_HUICE_RETURN_INFO,
                #             show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #             write_func=write_to_ermai_info_file,
                #             plot_if_func=plot_if_mai,
                #             plot_complete_func=plot_complete,
                #             show_func=show_func
                #         )
                # elif current_play.yimai_status == "long":
                #     if df.iloc[-1]['price'] < current_play.join_price * 0.999:
                #         current_play.handle_pingcang(
                #             df_row=df.iloc[-1],
                #             info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #             print_return_info=PRINT_HUICE_RETURN_INFO,
                #             show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #             write_func=write_to_ermai_info_file,
                #             plot_if_func=plot_if_mai,
                #             plot_complete_func=plot_complete,
                #             show_func=show_func
                #         )
                # elif current_play.yimai_status == "short":
                #     if df.iloc[-1]['price'] > current_play.join_price * 1.001:
                #         current_play.handle_pingcang(
                #             df_row=df.iloc[-1],
                #             info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #             print_return_info=PRINT_HUICE_RETURN_INFO,
                #             show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #             write_func=write_to_ermai_info_file,
                #             plot_if_func=plot_if_mai,
                #             plot_complete_func=plot_complete,
                #             show_func=show_func
                #         )






                # #pen的逻辑给segment用
                # if current_play.join_price:
                #     print(current_play.join_price, current_play.join_price * 0.999, current_play.yimai_status, df.iloc[-1]['price'])
                # if current_play.yimai_status == "inactivate" and (df.iloc[-1]['timestamp'].time() < datetime_time(19, 30)):
                #     last_direction = segments_fix[-1]["direction"]
                #     current_play.update_yimai_by_direction(segments_fix[-1], last_direction)
                #     if (last_direction=="Up" and (segments_fix[-1]["top_price"] - df.iloc[-1]['price'] < 0.5*(segments_fix[-1]["top_price"]-segments_fix[-1]["bottom_price"]))) or (last_direction=="Down" and (df.iloc[-1]['price'] - segments_fix[-1]["bottom_price"] < 0.5 * (segments_fix[-1]["top_price"] - segments_fix[-1]["bottom_price"]))):
                #         current_play.handle_ermai_confirmation(
                #             segment=segments_fix[-1],
                #             df_row=df.iloc[-1],
                #             info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #             print_return_info=PRINT_HUICE_RETURN_INFO,
                #             show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #             write_func=write_to_ermai_info_file,
                #             plot_if_func=plot_if_mai,
                #             plot_complete_func=plot_complete,
                #             show_func=show_func,
                #             ersan_lianmai=True,
                #             zhongshu_before_ersanlianmai=history_long_time_segment_zhongshus_clean[-1]
                #         )
                #         current_play.join_price = df.iloc[-1]['price']
                #     else:
                #         current_play.reset()
                # elif (current_play.yimai_status == "long" and segments_fix[-1]["direction"] == "Up") or (current_play.yimai_status == "short" and segments_fix[-1]["direction"] == "Down"):
                #         current_play.handle_pingcang(
                #             df_row=df.iloc[-1],
                #             info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #             print_return_info=PRINT_HUICE_RETURN_INFO,
                #             show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #             write_func=write_to_ermai_info_file,
                #             plot_if_func=plot_if_mai,
                #             plot_complete_func=plot_complete,
                #             show_func=show_func
                #         )
                # elif current_play.yimai_status == "long":
                #     if df.iloc[-1]['price'] < pen_zhongshus[-2]["ZG"]:#current_play.join_price * 0.995:
                #         current_play.handle_pingcang(
                #             df_row=df.iloc[-1],
                #             info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #             print_return_info=PRINT_HUICE_RETURN_INFO,
                #             show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #             write_func=write_to_ermai_info_file,
                #             plot_if_func=plot_if_mai,
                #             plot_complete_func=plot_complete,
                #             show_func=show_func
                #         )
                # elif current_play.yimai_status == "short":
                #     if df.iloc[-1]['price'] > pen_zhongshus[-2]["ZD"]:#current_play.join_price * 1.005:
                #         current_play.handle_pingcang(
                #             df_row=df.iloc[-1],
                #             info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #             print_return_info=PRINT_HUICE_RETURN_INFO,
                #             show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #             write_func=write_to_ermai_info_file,
                #             plot_if_func=plot_if_mai,
                #             plot_complete_func=plot_complete,
                #             show_func=show_func
                #         )




                # if current_play.yimai_status in {"long", "short"}:
                #     print(current_play.support_price)
                #     #####<........止损.......>#######
                #     #####<........止损.......>#######
                #     #####<........止损.......>#######
                #     #####<........止损.......>#######
                #     # if current_play.check_zhisun(df.iloc[-1]['price']):
                #     #     print("触发止损")
                #     #     current_play.handle_pingcang(
                #     #         df_row=df.iloc[-1],
                #     #         info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #     #         print_return_info=PRINT_HUICE_RETURN_INFO,
                #     #         show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #     #         write_func=write_to_ermai_info_file,
                #     #         plot_if_func=plot_if_mai,
                #     #         plot_complete_func=plot_complete,
                #     #         show_func=show_func
                #     #     )
                #     #####<........止盈.......>#######
                #     #####<........止盈.......>#######
                #     #####<........止盈.......>#######
                #     #####<........止盈.......>#######
                #     #####<........止盈.......>#######
                #     # current_play.zhiying_or_keep_operation(
                #     #     zhongshus=pen_zhongshus_clean,
                #     #     segments_fix=fixed_pens,
                #     #     df_row=df.iloc[-1],
                #     #     info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #     #     print_return_info=PRINT_HUICE_RETURN_INFO,
                #     #     show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #     #     write_func=write_to_ermai_info_file,
                #     #     plot_if_func=plot_if_mai,
                #     #     plot_complete_func=plot_complete,
                #     #     show_func=show_func,
                #     #     sanmai_info=sanmai_info_pen,
                #     #     new_zhongshu_clean=pen_new_zhongshu_clean,
                #     #     golden_magic_number=0.618
                #     # )
                #     current_play.zhiying_or_keep_operation_for_pen(
                #         zhongshus=pen_zhongshus_clean,
                #         segments_fix=fixed_pens,
                #         df_row=df.iloc[-1],
                #         info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #         print_return_info=PRINT_HUICE_RETURN_INFO,
                #         show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #         write_func=write_to_ermai_info_file,
                #         plot_if_func=plot_if_mai,
                #         plot_complete_func=plot_complete,
                #         show_func=show_func,
                #         sanmai_info=sanmai_info_pen,
                #         new_zhongshu_clean=pen_new_zhongshu_clean,
                #         golden_magic_number=0.618
                #     )
                #
                # # plot_if_mai('test', "visualize_for_test")
                # # plot_complete('test', "visualize_for_test")
                # # fig.show()
                # # print(pen_zhongshus_clean[-1]["direction"])
                # # print(fixed_pens[pen_zhongshus_clean[-1]["core_pens_index"][0] - 1]["direction"])
                # # print(list(fixed_pens[penindex]["direction"] for penindex in pen_zhongshus_clean[-1]["core_pens_index"]))
                # # print(list(penindex for penindex in pen_zhongshus_clean[-1]["core_pens_index"]))
                # # print(list(penindex for penindex in pen_zhongshus_clean[-2]["core_pens_index"]))
                #
                #
                #
                #
                # #####<........交易介入的判定，就是寻找一mai后的二mai.......>#######
                # #####<........交易介入的判定，就是寻找一mai后的二mai.......>#######
                # #####<........交易介入的判定，就是寻找一mai后的二mai.......>#######
                # #####<........交易介入的判定，就是寻找一mai后的二mai.......>#######
                # #####<........交易介入的判定，就是寻找一mai后的二mai.......>#######
                # if current_play.yimai_status in {"candidate_long", "candidate_short"} and (
                #         not bool(pen_new_zhongshu_clean) and (not same_level_or_higher_level_before(pen_zhongshus_clean, fixed_pens, greater_then_least_samelevel_strict))):
                #     #中枢升级的判定，如果有一mai，清掉，不该再找二mai
                #     print("中枢延伸，升级")
                #     current_play.reset()
                # #if pen_zhongshus_clean """ now we have two same direction zhongshu""" and """ I am 空仓 current_play.operation_direction == "" """:
                # #因为构成三买的中枢被拿掉了，所以用len(pen_zhongshus_clean) + bool(sanmai_info_pen)补回
                # # if (not (current_play.yimai_status in {"long", "short"})) and (len(pen_zhongshus_clean) + bool(sanmai_info_pen)) >= 3 and ((pen_zhongshus_clean[-1]["direction"] == pen_zhongshus_clean[-2]["direction"]) or (pen_new_zhongshu_clean and (pen_zhongshus_clean[-1]["direction"] == pen_new_zhongshu_clean["direction"]))):
                # elif (not (current_play.yimai_status in {"long", "short"})) and ((len(pen_zhongshus_clean) + bool(sanmai_info_pen)) >= 3) and ((not bool(pen_new_zhongshu_clean)) or (pen_new_zhongshu_clean and (pen_zhongshus_clean[-1]["direction"] != pen_new_zhongshu_clean["direction"]))):
                # # elif (not (current_play.yimai_status in {"long", "short"}))  and ((not bool(pen_new_zhongshu_clean)) or (pen_new_zhongshu_clean and (pen_zhongshus_clean[-1]["direction"] != pen_new_zhongshu_clean["direction"]))):
                #     last_direction = pen_zhongshus_clean[-1]["direction"]
                #
                #     beichi_check_segment_new = fixed_pens[pen_zhongshus_clean[-1]["core_pens_index"][-1] + 1]
                #     beichi_check_segment_old = fixed_pens[pen_zhongshus_clean[-1]["core_pens_index"][0] - 1]
                #     if beichi_check_segment_new["direction"] != beichi_check_segment_old["direction"]:
                #         beichi_check_segment_new = fixed_pens[pen_zhongshus_clean[-1]["core_pens_index"][-1]]
                #
                #     if current_play.yimai_status == "inactivate":
                #         if last_direction == fixed_pens[-1]["direction"]:
                #             current_play.check_beichi_and_update_yimai(pen_zhongshus_clean[-1], beichi_check_segment_new, beichi_check_segment_old, last_direction)
                #             if current_play.yimai_status in {"candidate_long", "candidate_short"}:
                #                 print("背驰已触发，已标记一买候选")
                #         else:
                #             # print("不是进入的方向，看下一条线段完成再说")
                #             # print("当然，如果已经建仓，那要再想想止盈止损")
                #             pass
                #     elif current_play.yimai_status in {"candidate_long", "candidate_short"}:
                #         print(f"一买后找二买的尝试 {df.iloc[-1]['timestamp']}")
                #         if last_direction == fixed_pens[-1]["direction"]:
                #             # if beichi:
                #             detect_zhongshu_kuozhang = current_play.detect_zhongshu_expansion(beichi_check_segment_new, pen_zhongshus_clean[-2])
                #             if detect_zhongshu_kuozhang:
                #                 #如果扩展，除了二三连买，别的都要放弃交易
                #                 current_play.kuozhang = True
                #                 if sanmai_info_pen == "":
                #                     current_play.reset()
                #                 else: #二三连买
                #                     if max(fixed_pens[-1]["top_time"],
                #                            fixed_pens[-1]["bottom_time"]) > last_operation_confirm_time:
                #                         print("二三连mai确认mai点")
                #                         current_play.handle_ermai_confirmation(
                #                             segment=fixed_pens[-1],
                #                             df_row=df.iloc[-1],
                #                             info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #                             print_return_info=PRINT_HUICE_RETURN_INFO,
                #                             show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #                             write_func=write_to_ermai_info_file,
                #                             plot_if_func=plot_if_mai,
                #                             plot_complete_func=plot_complete,
                #                             show_func=show_func,
                #                             ersan_lianmai=True,
                #                             zhongshu_before_ersanlianmai=pen_zhongshus_clean[-1]
                #                         )
                #                         last_operation_confirm_time = max(fixed_pens[-1]["top_time"], fixed_pens[-1]["bottom_time"])
                #             else: # 如果不扩展
                #                 #
                #                 print(f"一买后确认没有扩展，找二买最后一步 {df.iloc[-1]['timestamp']}")
                #                 if current_play.check_ermai_by_compare_to_yimai(fixed_pens[-1]):
                #                     if max(fixed_pens[-1]["top_time"], fixed_pens[-1]["bottom_time"]) > last_operation_confirm_time:
                #                         print(f"一买后确认二买 {df.iloc[-1]['timestamp']}")
                #                         #如果二mai成立，那就介入二买
                #                         current_play.handle_ermai_confirmation(
                #                             segment=fixed_pens[-1],
                #                             df_row=df.iloc[-1],
                #                             info_save_mode=INFO_SAVE_TO_FILE_MODE,
                #                             print_return_info=PRINT_HUICE_RETURN_INFO,
                #                             show_fig=SHOW_FIG_WHEN_SELL_BUY_ACTION,
                #                             write_func=write_to_ermai_info_file,
                #                             plot_if_func=plot_if_mai,
                #                             plot_complete_func=plot_complete,
                #                             show_func=show_func
                #                         )
                #                         last_operation_confirm_time = max(fixed_pens[-1]["top_time"], fixed_pens[-1]["bottom_time"])
                #                 else:
                #                     # 如果二mai不成立，那可能是是个新一mai
                #                     print("不是二mai，把一mai突破了，可能是新一mai")
                #                     current_play.check_beichi_and_update_yimai(pen_zhongshus_clean[-1],
                #                                                                beichi_check_segment_new,
                #                                                                beichi_check_segment_old, last_direction)
                #                     # current_play.update_yimai_by_direction(beichi_check_segment_new, last_direction)
                #
                #         else:
                #             print("不是进入的方向，看下一条线段完成再说")
                #             pass
                #     ## elif current_play.yimai_status in {"long", "short"}:
                #     ##     print("止损咋搞咋搞")
                #     ##     print("止盈咋搞咋搞")
                #     ##     pass


                #if PRINT_PROCESS_INFO and (not SHOW_FIG_WHEN_SELL_BUY_ACTION):
                #     plot_if_mai('test', "visualize_for_test")
                plot_if_mai('test', "visualize_for_test")
            # if PRINT_PROCESS_INFO and (not SHOW_FIG_WHEN_SELL_BUY_ACTION):
            #     plot_complete('test', "visualize_for_test")
            #     fig.show()
            plot_complete('test', "visualize_for_test")
            fig.show()
            # 结束计时



            end_time = time.time()

            # 计算运行时间
            elapsed_time = end_time - start_time
            if PRINT_PROCESS_INFO:
                # 打印运行时间（秒）
                print(f"运行时间：{elapsed_time:.2f} 秒***********************************************************")

        # ############################### 线上实盘用 ###############################
        # ########################线上实盘到全时间回测记得切换#########################
        # time.sleep(300)  # Wait for 300 seconds (5 minutes) before the next attempt
        # ####### time.sleep(600)  # Wait for 600 seconds (10 minutes) before the next attempt
        # ############################### 线上实盘用 ###############################





        



