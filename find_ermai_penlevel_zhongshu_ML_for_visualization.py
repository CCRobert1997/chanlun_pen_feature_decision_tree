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
from trigger_and_feature_library import *




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


# def read_all_csv_of_one_stock_some_days_after_date(stock_name_and_market="NVDA_NASDAQ",
#                                                     start_date="2024-12-01",
#                                                     days_n=50):
#     # 文件夹路径
#     data_folder = "data"
#     # 匹配所有相关文件（按命名规则匹配）
#     file_pattern = os.path.join(data_folder, f"{stock_name_and_market}_prices_*.csv")
#     file_list = sorted(glob.glob(file_pattern))  # 自动按文件名排序
#     # 提取文件中的日期并筛选
#     filtered_files = []
#     for file_path in file_list:
#         # 提取日期字符串
#         base_name = os.path.basename(file_path)
#         try:
#             date_str = base_name.replace(f"{stock_name_and_market}_prices_", "").replace(".csv", "")
#             file_date = datetime.strptime(date_str, "%Y-%m-%d")
#             if file_date > datetime.strptime(start_date, "%Y-%m-%d"):
#                 filtered_files.append((file_date, file_path))
#         except ValueError:
#             continue  # 跳过无法解析日期的文件名
#     # 按日期排序
#     filtered_files = sorted(filtered_files, key=lambda x: x[0])
#     # 取最近的 days_n 个文件
#     selected_files = [f[1] for f in filtered_files[:days_n]]
#     # 主数据框
#     df = pd.DataFrame()
#     for file_path in selected_files:
#         single_df = pd.read_csv(file_path)
#         single_df['timestamp'] = pd.to_datetime(single_df['timestamp'])
#         df = pd.concat([df, single_df], ignore_index=True)
#     # 最终按时间排序
#     df = df.sort_values(by='timestamp').reset_index(drop=True)
#     return df



def read_all_csv_of_one_stock_some_days_after_date(stock_name_and_market="NVDA_NASDAQ",
                                                    start_date="2024-12-01",
                                                    days_n=50):
    # 文件夹路径
    data_folder = "data"
    file_pattern = os.path.join(data_folder, f"{stock_name_and_market}_prices_*.csv")
    file_list = sorted(glob.glob(file_pattern))

    # 提取所有可用的日期和文件路径
    dated_files = []
    for file_path in file_list:
        base_name = os.path.basename(file_path)
        try:
            date_str = base_name.replace(f"{stock_name_and_market}_prices_", "").replace(".csv", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            dated_files.append((file_date, file_path))
        except ValueError:
            continue

    # 检查是否存在文件日期 ≤ start_date
    start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
    has_earlier_or_equal = any(file_date <= start_date_dt for file_date, _ in dated_files)

    if not has_earlier_or_equal and dated_files:
        # 替换 start_date 为最早的 available 日期
        start_date_dt = min(file_date for file_date, _ in dated_files)

    # 筛选 start_date 之后的文件
    filtered_files = [f for f in dated_files if f[0] > start_date_dt]
    filtered_files = sorted(filtered_files, key=lambda x: x[0])

    # 选取最近 days_n 个文件
    selected_files = [f[1] for f in filtered_files[:days_n]]

    # 合并读取数据
    df = pd.DataFrame()
    for file_path in selected_files:
        single_df = pd.read_csv(file_path)
        single_df['timestamp'] = pd.to_datetime(single_df['timestamp'])
        df = pd.concat([df, single_df], ignore_index=True)

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
    # current_play = CurrentPlay()

    STOCK_QuantStrategy = {"NVDA_NASDAQ": QuantStrategyNVDA_NASDAQ,
                           "AMZN_NASDAQ": QuantStrategyAMZN_NASDAQ,
                           "META_NASDAQ": QuantStrategyMETA_NASDAQ,
                           "MSFT_NASDAQ": QuantStrategyMSFT_NASDAQ,
                           "SNOW_NYSE": QuantStrategySNOW_NYSE,
                           "TIGR_NASDAQ": QuantStrategyTIGR_NASDAQ,
                           "TSLA_NASDAQ": QuantStrategyTSLA_NASDAQ,
                           "U_NYSE": QuantStrategyU_NYSE,
                           "AVGO_NASDAQ": QuantStrategyAVGO_NASDAQ,
                           "AAPL_NASDAQ": QuantStrategyAAPL_NASDAQ,
                           "LLY_NYSE": QuantStrategyLLY_NYSE,
                           "NVO_NYSE": QuantStrategyNVO_NYSE,
                           "ADBE_NASDAQ": QuantStrategyADBE_NASDAQ,
                           "TSM_NYSE": QuantStrategyTSM_NYSE,
                           "PFE_NYSE": QuantStrategyPFE_NYSE,
                           "JPM_NYSE": QuantStrategyJPM_NYSE,
                           "BAC_NYSE": QuantStrategyBAC_NYSE,
                           "COST_NASDAQ": QuantStrategyCOST_NASDAQ,
                           "NFLX_NASDAQ": QuantStrategyNFLX_NASDAQ}

    # strategy = QuantStrategy0001(STOCK_NAME_AND_MARKET, GROUP_SIZEs[0] * 6)
    strategy = strategy = STOCK_QuantStrategy[STOCK_NAME_AND_MARKET](STOCK_NAME_AND_MARKET, GROUP_SIZEs[0] * 6)


    # ############################### 全时间回测用 ###############################
    # ########################线上实盘到全时间回测记得切换#########################
    # def return_test_generate_timestamps(start_timestamp: str, end_timestamp: str, interval_minutes: int):
    #     return_test_initial_timestamp = datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M:%S")
    #     return_test_final_timestamp = datetime.strptime(end_timestamp, "%Y-%m-%d %H:%M:%S")
    #     return_test_allowed_start_hour = 14
    #     return_test_allowed_start_minute = 30
    #     return_test_allowed_start_second = 2
    #     return_test_allowed_end_hour = 21
    #     return_test_allowed_end_minute = 0
    #     return_test_allowed_end_second = 0
    #     return_test_timeframe_collection = []
    #     return_test_current_iteration_date = return_test_initial_timestamp.date()
    #     while return_test_current_iteration_date <= return_test_final_timestamp.date():
    #         if return_test_current_iteration_date.weekday() != 6:  # 0=Monday, ..., 6=Sunday
    #             return_test_daily_start_time = datetime.combine(return_test_current_iteration_date,
    #                                                             datetime.min.time()).replace(
    #                 hour=return_test_allowed_start_hour, minute=return_test_allowed_start_minute,
    #                 second=return_test_allowed_start_second)
    #             return_test_daily_end_time = datetime.combine(return_test_current_iteration_date,
    #                                                           datetime.min.time()).replace(
    #                 hour=return_test_allowed_end_hour, minute=return_test_allowed_end_minute,
    #                 second=return_test_allowed_end_second)
    #             return_test_incremental_time = return_test_daily_start_time
    #             while return_test_incremental_time <= return_test_daily_end_time:
    #                 return_test_timeframe_collection.append(return_test_incremental_time.strftime("%Y-%m-%d %H:%M:%S"))
    #                 return_test_incremental_time += timedelta(minutes=interval_minutes)
    #         return_test_current_iteration_date += timedelta(days=1)
    #     return return_test_timeframe_collection
    #
    #
    # # return_test_timestamps = return_test_generate_timestamps("2024-12-16 17:19:07", "2025-06-03 18:10:07", 200)
    # # return_test_timestamps = return_test_generate_timestamps("2024-12-16 17:19:07", "2025-06-21 18:10:07", 200)
    # # print(f"**************************************{len(return_test_timestamps)}********************************************")
    # # time_until_list = return_test_timestamps[25:-1]
    # # time_from_list = return_test_timestamps[0:-25]
    # # # time_until_list = return_test_timestamps[25+266:-1]
    # # # time_from_list = return_test_timestamps[0+266:-25]
    # # # time_until_list = return_test_timestamps[316:-1]
    # # # time_from_list = return_test_timestamps[291:-25]
    #
    # return_test_timestamps = return_test_generate_timestamps("2024-12-16 17:19:07", "2025-06-21 18:10:07", 20)
    # print(
    #     f"**************************************{len(return_test_timestamps)}********************************************")
    # time_until_list = return_test_timestamps[250:-1]
    # time_from_list = return_test_timestamps[0:-250]
    #
    #
    #
    #
    # time_until_index = -1
    #
    # print(time_until_list)
    # while time_until_index < len(time_until_list)-1:
    #     time_until_index += 1
    #     time_until = time_until_list[time_until_index]
    #     time_from = time_from_list[time_until_index]
    #     if PRINT_HUICE_RETURN_INFO:
    #         print(f"当前回测起始时间{time_from} {time_until_index}")
    #         print(f"当前回测截止时间{time_until} {time_until_index}")
    #     print(f"当前回测起始时间{time_from} {time_until_index}")
    #     print(f"当前回测截止时间{time_until} {time_until_index}")
    # ############################### 全时间回测用 ###############################


    ############################### 线上实盘用 ###############################
    ########################线上实盘到全时间回测记得切换#########################
    while True:
    ############################### 线上实盘用 ###############################



        # ############################### 全时间回测用 ###############################
        # ########################线上实盘到全时间回测记得切换#########################
        # if True: # 单次测试用 或者 全时间回测用
        # ############################### 全时间回测用 ###############################



        ############################### 线上实盘用 ###############################
        ########################线上实盘到全时间回测记得切换#########################
        if is_market_open(): # 线上实盘用
        ############################### 线上实盘用 ###############################

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

            # ############################### 全时间回测用 ###############################
            # ########################线上实盘到全时间回测记得切换#########################
            # # df = read_all_csv_of_one_stock_some_days_after_date(
            # #     stock_name_and_market=STOCK_NAME_AND_MARKET, days_n=GROUP_SIZE_FOE_HIGH_LEVEL * 2,
            # #     start_date="2024-12-15"
            # # )
            # ######## 从最小级别向上递归 ######
            # # df = read_all_csv_of_one_stock_some_days_after_date(
            # #     stock_name_and_market=STOCK_NAME_AND_MARKET, days_n=20,
            # #     start_date="2024-12-15"
            # # )
            # # df = read_all_csv_of_one_stock_some_days_before_date(
            # #     stock_name_and_market=STOCK_NAME_AND_MARKET, days_n=DAYS_LOOK_BASED_ON_GROUP_SIZE[GROUP_SIZE_FOE_HIGH_LEVEL],
            # #     end_date="2025-05-16"
            # # )
            #
            # df = read_all_csv_of_one_stock_some_days_after_date(
            #     stock_name_and_market=STOCK_NAME_AND_MARKET, days_n=DAYS_LOOK_BASED_ON_GROUP_SIZE[GROUP_SIZE_FOE_HIGH_LEVEL],
            #     start_date=datetime.strptime(time_from, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
            # )
            #
            # ######## 从最小级别向上递归 ######
            # ############################### 全时间回测用 ###############################



            ############################### 线上实盘用 ###############################
            ########################线上实盘到全时间回测记得切换#########################
            # # GROUP_SIZE_FOE_HIGH_LEVEL*2
            # # 20->40天 10->20天 5->10天
            # df = read_all_csv_of_one_stock_some_days(stock_name_and_market=STOCK_NAME_AND_MARKET,
            #                                          days_n=GROUP_SIZE_FOE_HIGH_LEVEL * 2)
            df = read_all_csv_of_one_stock_some_days(stock_name_and_market=STOCK_NAME_AND_MARKET,
                                                     days_n=DAYS_LOOK_BASED_ON_GROUP_SIZE[GROUP_SIZE_FOE_HIGH_LEVEL])
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
            # ############################### 全时间回测用 ###############################
            # ########################线上实盘到全时间回测记得切换#########################
            # if df['timestamp'].empty or df['timestamp'].min() > pd.to_datetime(time_until):
            #     # 当前时间段内没有数据，推进索引直到找到匹配的时间段
            #     while time_until_index < len(time_until_list) - 1 and \
            #             df['timestamp'].min() > pd.to_datetime(time_from_list[time_until_index]):
            #         time_until_index += 1
            #     continue  # 跳过本轮，进入下一个时间段
            # df = df[df['timestamp'] <= time_until] #全时间回测用
            #
            # ############################### 全时间回测用 ###############################

            # 创建子图布局
            plot_number_each_jibie = 3
            #
            # fig = make_subplots(rows=len(GROUP_SIZEs) * plot_number_each_jibie, cols=1, shared_xaxes=False,
            #                     vertical_spacing=0.05,
            #                     subplot_titles=['GROUP_SIZE' + str(
            #                         GROUP_SIZEs[int(group_size_in_GROUP_SIZEs_index / plot_number_each_jibie)]) for group_size_in_GROUP_SIZEs_index in range(plot_number_each_jibie * len(GROUP_SIZEs))],
            #                     row_heights=[0.8 for group_i in range(plot_number_each_jibie * len(GROUP_SIZEs))])


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
                # save_new_segments_fix_to_checkpoint_pen(fixed_pens, pen_zhongshus, STOCK_NAME_AND_MARKET, seconds_level=GROUP_SIZEs[0]*6)

                history_long_time_pens = []
                history_long_time_pen_zhongshus = []

                history_long_time_pens = merge_segments_fix_with_checkpoint(fixed_pens, STOCK_NAME_AND_MARKET,
                                                                                seconds_level=GROUP_SIZEs[0] * 6, for_segment=False)
                history_long_time_pen_zhongshus = merge_zhongshu_with_checkpoint(pen_zhongshus, STOCK_NAME_AND_MARKET, seconds_level=GROUP_SIZEs[0] * 6)

                # save_new_pen_zhongshu_to_checkpoint(pen_zhongshus, STOCK_NAME_AND_MARKET, seconds_level=6)


                if len(history_long_time_pen_zhongshus) > 60:
                    history_long_time_pen_zhongshus = history_long_time_pen_zhongshus[-60:]
                    history_long_time_pens = history_long_time_pens[
                                                 history_long_time_pen_zhongshus[0]["core_pens_index"][0] - 1:]
                    history_long_time_pens_index_fix = \
                    history_long_time_pen_zhongshus[0]["core_pens_index"][-1] - 1
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


                def plot_test():
                    plot_number_each_jibie = 3
                    fig = make_subplots(rows=len(GROUP_SIZEs) * plot_number_each_jibie, cols=1, shared_xaxes=False,
                                        vertical_spacing=0.05,
                                        subplot_titles=['GROUP_SIZE' + str(
                                            GROUP_SIZEs[
                                                int(group_size_in_GROUP_SIZEs_index / plot_number_each_jibie)]) for
                                                        group_size_in_GROUP_SIZEs_index in
                                                        range(plot_number_each_jibie * len(GROUP_SIZEs))],
                                        row_heights=[0.8 for group_i in
                                                     range(plot_number_each_jibie * len(GROUP_SIZEs))])
                    category_x = {zs['start_time'] for zs in pen_zhongshus} | {zs['end_time'] for zs in
                                                                               pen_zhongshus}
                    category_x |= {pen['top_time'] for pen in fixed_pens} | {pen['bottom_time'] for pen in
                                                                             fixed_pens}
                    category_x = sorted(category_x)
                    fig.add_trace(
                        go.Scatter(
                            x=category_x,  # 所有中枢涉及的时间点作为 category
                            y=[None] * len(category_x),  # 没有数据
                            mode='lines',
                            line=dict(color='rgba(0,0,0,0)'),  # 完全透明
                            showlegend=False
                        ),
                        row=1, col=1
                    )
                    for pen_index, pen in enumerate(fixed_pens):
                        fig.add_trace(
                            go.Scatter(
                                x=[pen['top_time'], pen['bottom_time']],
                                # x=[ensure_datetime(pen['top_time']), ensure_datetime(pen['bottom_time'])],
                                y=[pen['top_price'], pen['bottom_price']],
                                mode='lines',
                                line=dict(color='white', width=2),
                                name='Penfix',
                                showlegend=False
                            ),
                            row=1, col=1
                        )

                    draw_zhongshu(fig, pen_zhongshus, row=1,
                                  col=1,
                                  level="pen")
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
                        fig.update_layout({f"xaxis{i + 1}": dict(type='category')})
                        fig.update_layout({f"xaxis{i + 1}_rangeslider_visible": False})
                        fig.update_layout(
                            {f"xaxis{i + 1}": dict(type='category', categoryorder='category ascending')})
                    # ############################### 全时间回测用 ###############################
                    # ########################线上实盘到全时间回测记得切换#########################
                    # fig.show()
                    # ############################### 全时间回测用 ###############################
                    # 显示图表
                    # fig.show()
                    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                    # 生成文件名
                    fig_save_dir = "machine_learning_plot"
                    file_name_record_if_sanmai = f"{fig_save_dir}/{current_time}_{STOCK_NAME_AND_MARKET}_{GROUP_SIZEs[0] * 6}_second_{strategy.strategy_name}.png"
                    # 确保文件夹存在
                    os.makedirs(fig_save_dir, exist_ok=True)
                    fig.write_image(file_name_record_if_sanmai, width=3000, height=2500)



                if len(history_long_time_pen_zhongshus) > 30:

                    X = strategy.construct_X_features(history_long_time_pen_zhongshus, 0)
                    if strategy.trigger_signals_detect(X, len(history_long_time_pen_zhongshus[-1]["core_pens"]), history_long_time_pen_zhongshus):
                        if not strategy.operation_direction:
                            plot_test()
                        strategy.join_market_operation(history_long_time_pen_zhongshus[-1]['end_time'],
                                              history_long_time_pen_zhongshus[-1]["ZG"],
                                              history_long_time_pen_zhongshus[-2]["ZD"], df.iloc[-1]['price'],
                                              df.iloc[-1]['timestamp'])


                    elif strategy.operation_direction: # 出现新中枢，止损或者止盈，或者更新信息
                        strategy.detect_during_operation(history_long_time_pen_zhongshus[-1]['end_time'],
                                                history_long_time_pen_zhongshus[-1]['start_time'],
                                                history_long_time_pen_zhongshus[-1]["ZG"],
                                                history_long_time_pen_zhongshus[-1]["ZD"],
                                                history_long_time_pen_zhongshus[-2]["ZG"],
                                                history_long_time_pen_zhongshus[-2]["ZD"],
                                                         df.iloc[-1]['timestamp'],
                                                         df.iloc[-1]['price']) #建仓后的盯盘，止盈止损
                        if not strategy.operation_direction:
                            plot_test()





                if GROUP_SIZE_index == 0:
                    print(f"{df.iloc[-1]['timestamp']}:当前价{df.iloc[-1]['price']}")
                    # print(
                    #     ["+" if clean_zhongshu["direction"] == "Up" else "-" for clean_zhongshu in pen_zhongshus_clean])




            end_time = time.time()

            # 计算运行时间
            elapsed_time = end_time - start_time
            if PRINT_PROCESS_INFO:
                # 打印运行时间（秒）
                print(f"运行时间：{elapsed_time:.2f} 秒***********************************************************")

        ############################### 线上实盘用 ###############################
        ########################线上实盘到全时间回测记得切换#########################
        time.sleep(300)  # Wait for 300 seconds (5 minutes) before the next attempt
        ####### time.sleep(600)  # Wait for 600 seconds (10 minutes) before the next attempt
        ############################### 线上实盘用 ###############################





        



