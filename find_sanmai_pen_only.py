import pandas as pd
import glob
import os
import pytz
import holidays
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date
import time
from copy import deepcopy
import argparse
from chanlun_utils import generate_kline_data, generate_kline_data_group_points, handle_kline_inclusion_with_trend, find_pens_from_kline, find_pens_from_kline_need_fixed, pens_fix, generate_feature_sequence, merge_pens_to_segments, find_zhongshu, find_zhongshu_and_cijibie_qushi, find_zhongshu_csy_steps, find_zhongshu_csy_inverse_look_steps, find_zhongshu_new, find_zhongshu_based_on_looking_for_next_zhongshu, find_zhongshu_one_pen_can_be_a_zhongshu, find_zhongshu_one_pen_brute, find_zhongshu_one_pen_form, calculate_macd

    
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



def read_all_csv_of_one_stock_five_days(stock_name_and_market="NVDA_NASDAQ"):
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
    for file_path in file_list[-5:]:
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
                        help="设置为 True 时, 打印出运行到哪一步的信息")

    # 解析参数
    args = parser.parse_args()

    ZGZD_TYPE = args.zgzd_type #"classical" "practical"
    DINGDI_START_FROM = args.dingdi_start_from #从哪个顶或底开始看影响很大，关系到走势的多义性，一般可以dingdi_start_from=1
    STOCK_NAME_AND_MARKET = args.stock_name_and_market  # "NVDA_NASDAQ" "AAPL_NASDAQ" "AMZN_NASDAQ" "META_NASDAQ" "MSFT_NASDAQ" "SNOW_NYSE" "TIGR_NASDAQ" "TSLA_NASDAQ" "U_NYSE" "AVGO_NASDAQ"
    ALL_DATA_NOT_SINGLE_DAY = not args.not_all_data_but_single_day
    IF_SINGLE_DAY_DATE = args.if_single_day_date
    PRINT_PROCESS_INFO = args.print_process_info
    GROUP_SIZE_FOR_MACD = args.group_size_for_MACD





    folder_path = "sanmai_caozuo"
    file_name = f"{STOCK_NAME_AND_MARKET}_30_second_sanmai_caozuo.csv"
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





    while True:

        # if True:
        if is_market_open():

            # 开始计时
            start_time = time.time()

            # if ALL_DATA_NOT_SINGLE_DAY:
            #     #####################读取某个股的全部数据###########################
            #     df = read_all_csv_of_one_stock(stock_name_and_market=STOCK_NAME_AND_MARKET)
            # else:
            #     #####################读取某个股的单天数据###########################
            #     df = read_single_csv_of_one_stock(file_path=f'data/{STOCK_NAME_AND_MARKET}_prices_{IF_SINGLE_DAY_DATE}.csv')

            #####################读取某个股的最近5天数据###########################
            df = read_all_csv_of_one_stock_five_days(stock_name_and_market=STOCK_NAME_AND_MARKET)
            """
            50min: 500
            37p5min: 375
            25min: 250
            12p5min: 125
                
            10min: 100
            7p5min: 75
            5min: 50
            2p5min: 25
            
            2min: 20
            1p5min: 15
            1min: 10
            30s: 5
            
            24s: 4
            18s:  3
            12s: 2
            6s:1
            """

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
            # df = df[df['timestamp'] <= "2025-01-06 16:29:07"]
            # df = df[df['timestamp'] <= "2025-01-31 15:48:07"]
            # df = df[df['timestamp'] <= "2025-01-31 15:40:07"]
            # df = df[df['timestamp'] <= "2025-01-15 19:00:07"]
            # df = df[df['timestamp'] <= "2024-12-27 20:59:07"]
            # df = df[df['timestamp'] <= "2025-01-30 18:57:07"]

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

            # GROUP_SIZEs = [10]
            GROUP_SIZEs = [5]
            # GROUP_SIZEs = [1]


            # 创建子图布局
            fig = make_subplots(rows=len(GROUP_SIZEs)*2+1, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                                subplot_titles=['basetime']+['GROUP_SIZE' + str(GROUP_SIZEs[int(group_size_in_GROUP_SIZEs_index/2)]) if (group_size_in_GROUP_SIZEs_index%2==0) else 'MACD' for group_size_in_GROUP_SIZEs_index in range(2*len(GROUP_SIZEs))], row_heights=[0.7 for group_i in range(2*len(GROUP_SIZEs) + 1)])


            # 先画一个圈数据图以确保后面几幅图所有时间戳包含，也就是GROUP_SIZEs等于1
            kline_df = generate_kline_data_group_points(df, group_size=1)
            # print("6 second data processed")

            # 画6秒级，也就是最低级别数据的空线，给后面的图参考对齐x轴
            fig.add_trace(go.Scatter(
                x=kline_df['timestamp'],  # 使用 kline_df 的时间戳
                y=[None] * len(kline_df),                     # 不绘制 y 值
                mode='lines',             # 设置为线模式（但不会显示）
                showlegend=False          # 隐藏图例
            ), row=1, col=1)




            for GROUP_SIZE_index, GROUP_SIZE in enumerate(GROUP_SIZEs):
                # 调用函数生成 K 线数据
                # kline_df = generate_kline_data(df)
                # group_size=10就是分钟K线
                kline_df = generate_kline_data_group_points(df, group_size=GROUP_SIZE)


                # 调用处理包含关系的函数
                kline_df_no_inclusion = handle_kline_inclusion_with_trend(kline_df)
                if PRINT_PROCESS_INFO:
                    print("包含K线组合完毕，开始找笔")


                # 调用处理笔的函数
                #从哪个顶或底开始看影响很大，关系到走势的多义性，一般可以dingdi_start_from=1
                pens =  find_pens_from_kline(kline_df_no_inclusion, dingdi_start_from=DINGDI_START_FROM)
                # pens =  find_pens_from_kline_need_fixed(kline_df_no_inclusion, dingdi_start_from=DINGDI_START_FROM)
                if PRINT_PROCESS_INFO:
                    print("笔处理完毕，开始修复不合理的连续笔")
                # pens_fix 函数，它会合并 find_pens_from_kline 的结果中连续同向的笔，并重新计算合并后的每笔的最高点、最低点、起始时间和结束时间
                # fixed_pens = pens_fix(pens)
                fixed_pens = pens
                if PRINT_PROCESS_INFO:
                    print("笔修复处理完毕，开始找线段")

                # 用笔组合成线段
                #segments, standard_feature_sequence_lists = merge_pens_to_segments(fixed_pens)
                segments = []
                # segments, type_three_buy_sell = merge_pens_to_segments(fixed_pens)
                segments_fix = []
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
                if PRINT_PROCESS_INFO:
                    print("线段处理完毕，开始找中枢")

                # 调用寻找中枢的函数
                pen_zhongshus = []
                #zgzd_type="classical"
                #zgzd_type="practical"
                # pen_zhongshus = find_zhongshu(fixed_pens, zgzd_type=ZGZD_TYPE)
                # pen_zhongshus, pen_cijibie_qushis = find_zhongshu_and_cijibie_qushi(fixed_pens, zgzd_type=ZGZD_TYPE)
                # pen_zhongshus = find_zhongshu_csy_steps(fixed_pens)
                # pen_zhongshus = find_zhongshu_csy_inverse_look_steps(fixed_pens)
                #pen_zhongshus = find_zhongshu_new(fixed_pens)
                # pen_zhongshus = find_zhongshu_one_pen_can_be_a_zhongshu(fixed_pens)
                if PRINT_PROCESS_INFO:
                    print("************************笔中枢***********************")
                #pen_zhongshus, pen_zhuanzhes = find_zhongshu_based_on_looking_for_next_zhongshu(fixed_pens)
                pen_zhongshus, pen_zhuanzhes = find_zhongshu_one_pen_form(fixed_pens)

                segment_zhongshus = []
                segment_zhuanzhes = []


                if segments:
                    if segments_fix:
                        # segment_zhongshus = find_zhongshu_new(segments_fix)
                        #segment_zhongshus = find_zhongshu_one_pen_can_be_a_zhongshu(segments_fix)
                        if PRINT_PROCESS_INFO:
                            print("************************线段中枢***********************")
                        #segment_zhongshus, segment_zhuanzhes = find_zhongshu_based_on_looking_for_next_zhongshu(segments_fix)
                        # segment_zhongshus, segment_zhuanzhes = find_zhongshu_one_pen_brute(segments_fix)
                        segment_zhongshus, segment_zhuanzhes = find_zhongshu_one_pen_form(segments_fix)



                segment_of_segment_zhongshus = []
                # if segments_fix:
                #    if segments_of_segments_fix:
                #        segment_of_segment_zhongshus = find_zhongshu_new(segments_of_segments_fix)



                if PRINT_PROCESS_INFO:
                    print("中枢处理完毕，开始画图")

                if PRINT_PROCESS_INFO:
                    print("数据处理完毕，开始画图")

                GROUP_SIZE_FOR_MACD = GROUP_SIZE * 25
                MACD_kline_df = generate_kline_data_group_points(df, group_size=GROUP_SIZE_FOR_MACD)


                # 计算 MACD 值
                MACD_kline_df = calculate_macd(MACD_kline_df)


                def plot_if_sanmai(sanmaitype="long", zhichengwei=0):
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
                            row=GROUP_SIZE_index * 2 + 2, col=1
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
                            row=GROUP_SIZE_index * 2 + 2, col=1
                        )
                    # Add Zhongshu Rectangles to the chart
                    draw_zhongshu(fig, pen_zhongshus, row=GROUP_SIZE_index * 2 + 2, col=1, level="pen")
                    draw_zhongshu(fig, segment_zhongshus, row=GROUP_SIZE_index * 2 + 2, col=1, level="segment")
                    # draw_zhongshu(fig, segment_of_segment_zhongshus, row=GROUP_SIZE_index*2 + 2, col=1, level="segment_of_segment")

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
                                    row=GROUP_SIZE_index * 2 + 2, col=1
                                )

                    if segments_fix:
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
                                row=GROUP_SIZE_index * 2 + 2, col=1
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
                                row=GROUP_SIZE_index * 2 + 2, col=1
                            )

                    """
                    # DIF 线 (MACD 线) 和 DEA 线 (Signal 线)
                    fig.add_trace(go.Scatter(
                        x=MACD_kline_df['timestamp'], y=MACD_kline_df['DIF'], mode='lines', name="DIF (MACD Line)",
                        line=dict(color='blue')
                    ), row=GROUP_SIZE_index * 2 + 3, col=1)
        
                    fig.add_trace(go.Scatter(
                        x=MACD_kline_df['timestamp'], y=MACD_kline_df['DEA'], mode='lines', name="DEA (Signal Line)",
                        line=dict(color='red')
                    ), row=GROUP_SIZE_index * 2 + 3, col=1)
        
                    # MACD 柱状图（增加宽度）
                    fig.add_trace(go.Bar(
                        x=MACD_kline_df['timestamp'],
                        y=MACD_kline_df['MACD'],
                        name="MACD Histogram",
                        width=GROUP_SIZE_FOR_MACD,
                        marker_color=['green' if m >= 0 else 'red' for m in MACD_kline_df['MACD']]
                    ), row=GROUP_SIZE_index * 2 + 3, col=1)
                    # width=50,  # 增加柱状图宽度（时间戳单位为纳秒，具体数值根据数据调整）
                    """



                    # 更新布局


                    fig.update_layout(
                        title=f'{STOCK_NAME_AND_MARKET} Price Trend and K-Line Chart multi time level',
                        yaxis=dict(
                            title="Price"
                        ),
                        template='plotly_dark',
                        height=500 * (2 * len(GROUP_SIZEs) + 1),
                    )

                    for i in range(len(GROUP_SIZEs) * 2 + 1):
                        fig.update_layout({f"xaxis{i + 1}": dict(type='category')})
                        fig.update_layout({f"xaxis{i + 1}_rangeslider_visible": False})

                    # 显示图表
                    # fig.show()
                    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

                    # 生成文件名
                    file_name_record_if_sanmai = f"sanmaiplot/{current_time}_{STOCK_NAME_AND_MARKET}_{sanmaitype}_zhichengwei_{zhichengwei}.png"

                    fig.write_image(file_name_record_if_sanmai, width=3000, height=1500)





                #处理最近几个线段，中枢，笔，做决策：
                # 最后一个中枢被突破后找三买三卖：

                # 缠论原文49：利润率最大的操作模式 第三种情况的第2类，
                # 如果离该买点的形成与位置不远，可以介入，但最好就是刚形成时介入，
                # 若一旦从该买点开始已出现次级别走势的完成并形成盘整顶背驰，后面就必须等待

                # 我采用的具体逻辑，首先要看到中枢后出现了两个线段，以三买为例，就是要出现一个向上线段和向下线段，如果当前还没有抵达向上线段的高点，就可以介入

                #止损点还没想好，止盈点也还没想好
                #止损可以考虑出现新的次级别中枢并回到前线段中枢
                #止盈先考虑出现一个和前中枢同级别的线段中枢，但最好还是去考虑同级别背驰后的一买一卖
                #总之止损止盈都很关键且要优化



                # 止损情况1，假突破回到中枢
                # 条件1是突破出现过，条件2是回拉回前中枢，条件三是最后一个中枢依旧是突破前的前中枢
                if san_buy_appeared and (df.iloc[-1]['price'] < qian_top_before_san_buy) and (pen_zhongshus[-1]['start_time'] < huilajianyan_time_for_san_buy):
                    san_buy_appeared = False
                    san_sell_appeared = True

                    data_sanmai = {
                        "sanmai_state": "三买是假",
                        "info": f"但有可能是二买，回拉小的话可以持有看看，当前{df.iloc[-1]['price']}, 跌破支撑{qian_top_before_san_buy}，距交易点下跌{(chengben_sanbuy - df.iloc[-1]['price'])/chengben_sanbuy}"
                    }
                    write_to_sanmai_info_file(data_sanmai)

                    plot_if_sanmai('stop_long_jiatupo', "")

                if san_sell_appeared and (df.iloc[-1]['price'] > qian_bottom_before_san_sell) and (pen_zhongshus[-1]['start_time'] < huilajianyan_time_for_san_sell):
                    san_sell_appeared = False
                    san_buy_appeared = True

                    data_sanmai = {
                        "sanmai_state": "三卖是假",
                        "info": f"但有可能是二卖，回拉小的话可以持有看看，当前{df.iloc[-1]['price']}, 涨破支撑{qian_bottom_before_san_sell}，距交易点上涨{(df.iloc[-1]['price'] - chengben_sansell)/chengben_sansell}"
                    }
                    write_to_sanmai_info_file(data_sanmai)

                    plot_if_sanmai('stop_short_jiatupo', "")


                # 止损情况2，出现盘整，也就是说，出现了新的中枢，相比前一个中枢方向不对
                if san_buy_appeared and (pen_zhongshus[-1]['end_time'] > huilajianyan_time_for_san_buy) and (pen_zhongshus[-1]['ZG'] < pen_zhongshus[-2]['ZG']):
                    # 条件1 是三买后，条件2是三买后已经出现中枢，条件三是新中枢说明3买后的涨势已经结束
                    if huilajianyan_time_for_san_buy >= pen_zhongshus[-2]['start_time']:
                        #这个条件如果不满足，就不是盘整了，是趋势了
                        san_buy_appeared = False
                        san_sell_appeared = True

                        data_sanmai = {
                            "sanmai_state": "三买后明确盘整",
                            "info": f"新中枢高点{pen_zhongshus[-1]['ZG']}低于原中枢{pen_zhongshus[-2]['ZG']}"
                        }
                        write_to_sanmai_info_file(data_sanmai)
                        plot_if_sanmai('stop_long_panzheng', "")

                if san_sell_appeared and (pen_zhongshus[-1]['end_time'] > huilajianyan_time_for_san_sell) and (pen_zhongshus[-1]['ZD'] > pen_zhongshus[-2]['ZD']):
                    if huilajianyan_time_for_san_sell >= pen_zhongshus[-2]['start_time']:
                        san_sell_appeared = False
                        san_buy_appeared = True
                        data_sanmai = {
                            "sanmai_state": "三卖后明确盘整",
                            "info": f"新中枢低点{pen_zhongshus[-1]['ZD']}高于原中枢{pen_zhongshus[-2]['ZD']}"
                        }
                        write_to_sanmai_info_file(data_sanmai)
                        plot_if_sanmai('stop_short_panzheng', "")



                # 寻找三买，无缺口的情况
                if fixed_pens[-1]['direction'] == 'Down': #即离开中枢后的拉回段
                    # 给线段0开始编号，最后一个线段的编号就是 len(fixed_pens)-1
                    # 最后一个线段作为最后一个中枢的离开段 pen_zhongshus[-1]['core_pens_index'][-1] + 2 或 pen_zhongshus[-1]['core_pens_index'][-1] + 1
                    # 因为离开段可能被画进中枢
                    if len(fixed_pens) - 1 >= pen_zhongshus[-1]['core_pens_index'][-1] + 1:
                        # 检查中枢突破，最后一个线段最低价要高于中枢最高价，当前价也要高于中枢最高价
                        if (fixed_pens[-1]['bottom_price'] > pen_zhongshus[-1]['ZG']) and (
                                df.iloc[-1]['price'] > pen_zhongshus[-1]['ZG']):
                            # 做趋势背驰后的买点，当然我这里趋势和背驰的假设都还不严谨
                            if len(pen_zhongshus) >= 3:
                                if not san_buy_appeared:
                                    # 当前价格不能高于前一个线段的高点,也就是三买形成后不要走太远
                                    maidian_juli = "买点出现不远，价值高" if (df.iloc[-1]['price'] < fixed_pens[-2]['top_price']) else "买点已经有点距离，价值略降低"
                                    if (pen_zhongshus[-1]['ZG'] < pen_zhongshus[-2]['ZD']) and (
                                            pen_zhongshus[-2]['ZG'] < pen_zhongshus[-3]['ZD']):
                                            # 标记三类买点，并将三类卖点结束，保留前面的三买相关数据
                                            # 如果三买已经出现，就不重复标记了
                                            san_buy_appeared = True
                                            qian_top_before_san_buy = pen_zhongshus[-1]['ZG']
                                            chengben_sanbuy = df.iloc[-1]['price']
                                            huilajianyan_time_for_san_buy = fixed_pens[-1]["bottom_time"]
                                            san_sell_appeared = False
                                            # print("三买出现", f"在{chengben_sanbuy}做多", f"支撑在{qian_top_before_san_buy}", f"在{huilajianyan_time_for_san_buy}时操作")
                                            if (len(pen_zhongshus) >= 4) and (pen_zhongshus[-3]['ZG'] < pen_zhongshus[-4]['ZD']):
                                                data_sanmai = {
                                                    "sanmai_state": "高价值三买出现",
                                                    "info": f"{maidian_juli}, 前方四段中枢，趋势转折概率极大，在{chengben_sanbuy}做多, 支撑在{qian_top_before_san_buy}, 在{huilajianyan_time_for_san_buy}时操作"
                                                }
                                                write_to_sanmai_info_file(data_sanmai)
                                                if PRINT_PROCESS_INFO:
                                                    print("三买！！！！！！三买！！！！！！！！三买！！！！！！！！！！！！！")
                                            else:
                                                data_sanmai = {
                                                    "sanmai_state": "低价值三买出现",
                                                    "info": f"{maidian_juli}, 前方三段中枢，有可能只是盘整后的转折，只观察不要介入，在{chengben_sanbuy}做多, 支撑在{qian_top_before_san_buy}, 在{huilajianyan_time_for_san_buy}时操作"
                                                }
                                                write_to_sanmai_info_file(data_sanmai)
                                            # print("疑似三买！！！！！！三买！！！！！！！！三买！！！！！！！！！！！！！")
                                            # print("评估一下前面有没有一买！是否前面是低点！")
                                            # print("注意要非常小心止损，回到三买前的中枢要止损，回跌过大，比如1%要止损")
                                            plot_if_sanmai('long', str(pen_zhongshus[-1]['ZG']) + "_buyprice_" + str(df.iloc[-1]['price']))
                                    elif (pen_zhongshus[-1]['ZG'] < pen_zhongshus[-2]['ZD']):
                                        san_buy_appeared = True
                                        san_sell_appeared = False
                                        data_sanmai = {
                                            "sanmai_state": "类似三买，疑似线段三卖后盘整或趋势结束",
                                            "info": f"有仓平仓，无仓不建仓，{maidian_juli}, 新中枢低点{pen_zhongshus[-1]['ZD']}高于原中枢{pen_zhongshus[-2]['ZD']}"
                                        }
                                        write_to_sanmai_info_file(data_sanmai)
                                        if PRINT_PROCESS_INFO:
                                            print("不值得交易的三买！")
                                        plot_if_sanmai('long_no_trade', str(pen_zhongshus[-1]['ZG']) + "_buyprice_" + str(
                                            df.iloc[-1]['price']))

                # 寻找三卖
                if fixed_pens[-1]['direction'] == 'Up': #即离开中枢后的拉回段
                    # 给线段0开始编号，最后一个线段的编号就是 len(fixed_pens)-1
                    # 最后一个线段作为最后一个中枢的离开段 pen_zhongshus[-1]['core_pens_index'][-1] + 2 或 pen_zhongshus[-1]['core_pens_index'][-1] + 1
                    # 因为离开段可能被画进中枢
                    if len(fixed_pens) - 1 >= pen_zhongshus[-1]['core_pens_index'][-1] + 1:
                        # 检查中枢突破，最后一个线段最低价要低于中枢最低价，当前价也要低于中枢最低价
                        if (fixed_pens[-1]['top_price'] < pen_zhongshus[-1]['ZD']) and (
                                df.iloc[-1]['price'] < pen_zhongshus[-1]['ZD']):
                            # 做趋势背驰后的卖点，当然我这里趋势和背驰的假设都还不严谨
                            if len(pen_zhongshus) >= 3:
                                if not san_sell_appeared:
                                    # 当前价格不能低于前一个线段的低点,也就是三卖形成后不要走太远
                                    maidian_juli = "卖点出现不远，价值高" if (df.iloc[-1]['price'] > fixed_pens[-2]['bottom_price']) else "卖点已经有点距离，价值略降低"
                                    if (pen_zhongshus[-1]['ZD'] > pen_zhongshus[-2]['ZG']) and (
                                            pen_zhongshus[-2]['ZD'] > pen_zhongshus[-3]['ZG']):
                                        # 标记三类卖点，并将三类买点结束，保留前面的三卖相关数据
                                        # 如果三卖已经出现，就不重复标记了
                                        san_sell_appeared = True
                                        qian_bottom_before_san_sell = pen_zhongshus[-1]['ZD']
                                        chengben_sansell = df.iloc[-1]['price']
                                        huilajianyan_time_for_san_sell = fixed_pens[-1]["top_time"]
                                        san_buy_appeared = False
                                        # print("三卖出现", f"在{chengben_sansell}做空", f"支撑在{qian_bottom_before_san_sell}", f"在{huilajianyan_time_for_san_sell}时操作")
                                        if (len(pen_zhongshus) >= 4) and (pen_zhongshus[-3]['ZD'] > pen_zhongshus[-4]['ZG']):
                                            data_sanmai = {
                                                "sanmai_state": "高价值三卖出现",
                                                "info": f"{maidian_juli}, 前方四段中枢，趋势转折概率极大，在{chengben_sansell}做空, 支撑在{qian_bottom_before_san_sell}, 在{huilajianyan_time_for_san_sell}时操作"
                                            }
                                            if PRINT_PROCESS_INFO:
                                                print("三卖！！！！！！三卖！！！！！！！！三卖！！！！！！！！！！！！！")
                                            write_to_sanmai_info_file(data_sanmai)
                                        else:
                                            data_sanmai = {
                                                "sanmai_state": "低价值三卖出现",
                                                "info": f"{maidian_juli}, 前方三段中枢，有可能只是盘整后的转折，只观察不要介入，在{chengben_sansell}做空, 支撑在{qian_bottom_before_san_sell}, 在{huilajianyan_time_for_san_sell}时操作"
                                            }
                                            write_to_sanmai_info_file(data_sanmai)
                                        # print("疑似三卖！！！！！！三卖！！！！！！！！三卖！！！！！！！！！！！！！")
                                        # print("评估一下前面有没有一卖！是否前面是高点！")
                                        # print("注意要非常小心止损，回到三卖前的中枢要止损，回涨过大，比如1%要止损")
                                        plot_if_sanmai('short', str(pen_zhongshus[-1]['ZD']) + "_shortprice_" + str(df.iloc[-1]['price']))
                                    elif (pen_zhongshus[-1]['ZD'] > pen_zhongshus[-2]['ZG']):
                                        san_buy_appeared = False
                                        san_sell_appeared = True
                                        data_sanmai = {
                                            "sanmai_state": "类似三卖，疑似线段三买后盘整或趋势结束",
                                            "info": f"有仓平仓，无仓不建仓，{maidian_juli}, 新中枢高点{pen_zhongshus[-1]['ZG']}低于原中枢{pen_zhongshus[-2]['ZG']}"
                                        }
                                        write_to_sanmai_info_file(data_sanmai)
                                        if PRINT_PROCESS_INFO:
                                            print("不值得交易的三卖！")
                                        plot_if_sanmai('short_no_trade', str(pen_zhongshus[-1]['ZD']) + "_shortprice_" + str(
                                            df.iloc[-1]['price']))

            # if PRINT_PROCESS_INFO:
            #     plot_if_sanmai('short', "visualize_for_test")
            #     fig.show()
            # 结束计时


            end_time = time.time()

            # 计算运行时间
            elapsed_time = end_time - start_time
            if PRINT_PROCESS_INFO:
                # 打印运行时间（秒）
                print(f"运行时间：{elapsed_time:.2f} 秒")

        time.sleep(60)  # Wait for 60 seconds (1 minutes) before the next attempt




        



