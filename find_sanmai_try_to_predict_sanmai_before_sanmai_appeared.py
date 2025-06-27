import pandas as pd
import glob
import os
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

    # 开始计时
    start_time = time.time()

    if ALL_DATA_NOT_SINGLE_DAY:
        #####################读取某个股的全部数据###########################
        df = read_all_csv_of_one_stock(stock_name_and_market=STOCK_NAME_AND_MARKET)
    else:
        #####################读取某个股的单天数据###########################
        df = read_single_csv_of_one_stock(file_path=f'data/{STOCK_NAME_AND_MARKET}_prices_{IF_SINGLE_DAY_DATE}.csv')
    
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
    df = df[df['timestamp'] <= "2025-01-15 16:53:07"]


    find_candidate_sanmai = False
    di_jibie_analysis_from = None





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
        segments, type_three_buy_sell = merge_pens_to_segments(fixed_pens)
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
        #止损点还没想好，止盈点也还没想好
        #止损可以考虑出现新的次级别中枢并回到前线段中枢
        #止盈先考虑出现一个和前中枢同级别的线段中枢，但最好还是去考虑同级别背驰后的一买一卖
        #总之止损止盈都很关键且要优化

        # 寻找三买，无缺口的情况
        if segments_fix[-1]['direction'] == 'Up':
            # 给线段0开始编号，最后一个线段的编号就是 len(segments_fix)-1
            # 最后一个线段作为最后一个中枢的离开段 其编号等于segment_zhongshus[-1]['core_pens_index'][-1] + 1
            if len(segments_fix) - 1 == segment_zhongshus[-1]['core_pens_index'][-1] + 1:
                # 检查中枢突破，最后一个线段最高价要高于中枢最高价，当前价也要高于中枢最高价
                if (fixed_pens[-1]['top_price'] > segment_zhongshus[-1]['ZG']) and (
                        df.iloc[-1]['price'] > segment_zhongshus[-1]['ZG']):
                    # 做趋势背驰后的买点，当然我这里趋势和背驰的假设都还不严谨
                    if len(segment_zhongshus) >= 3:
                        if (segment_zhongshus[-1]['ZG'] < segment_zhongshus[-2]['ZD']) and (
                                segment_zhongshus[-2]['ZG'] < segment_zhongshus[-3]['ZD']):
                            # 寻找次级别中枢
                            for pen_zhongshu_index in range(len(pen_zhongshus)):
                                if pen_zhongshus[-1 - pen_zhongshu_index]['end_time'] > max(
                                        segments_fix[-1]['top_time'], segments_fix[-1]['bottom_time']):
                                    if pen_zhongshus[-1 - pen_zhongshu_index]['DD'] > segment_zhongshus[-1]['ZG']:
                                        # 次级别回调不回中枢
                                        print(segments_fix[-1]['top_time'])
                                        find_candidate_sanmai = True
                                        di_jibie_analysis_from = segments_fix[-1]['top_time']
                                        print("疑似三买！！！！！！三买！！！！！！！！三买！！！！！！！！！！！！！")
                                        print("评估一下前面有没有一买！是否前面是低点！")
                                        plot_if_sanmai('short', segment_zhongshus[-1]['ZG'])
                                        break
                                elif pen_zhongshus[-1 - pen_zhongshu_index]['end_time'] <= max(
                                        segments_fix[-1]['top_time'], segments_fix[-1]['bottom_time']):
                                    # 不用往前找了
                                    break

        # 寻找三卖
        if segments_fix[-1]['direction'] == 'Down':
            # 给线段0开始编号，最后一个线段的编号就是 len(segments_fix)-1
            # 最后一个线段作为最后一个中枢的离开段 其编号等于segment_zhongshus[-1]['core_pens_index'][-1] + 1
            if len(segments_fix) - 1 == segment_zhongshus[-1]['core_pens_index'][-1] + 1:
                # 检查中枢突破
                if (fixed_pens[-1]['bottom_price'] < segment_zhongshus[-1]['ZD']) and (
                        df.iloc[-1]['price'] < segment_zhongshus[-1]['ZD']):
                    # 做趋势背驰后的卖点，当然我这里趋势和背驰的假设都还不严谨
                    if len(segment_zhongshus) >= 3:
                        if (segment_zhongshus[-1]['ZD'] > segment_zhongshus[-2]['ZG']) and (
                                segment_zhongshus[-2]['ZD'] > segment_zhongshus[-3]['ZG']):
                            # 寻找次级别中枢
                            for pen_zhongshu_index in range(len(pen_zhongshus)):
                                if pen_zhongshus[-1 - pen_zhongshu_index]['end_time'] > max(
                                        segments_fix[-1]['top_time'], segments_fix[-1]['bottom_time']):
                                    if pen_zhongshus[-1 - pen_zhongshu_index]['GG'] < segment_zhongshus[-1]['ZD']:
                                        # 次级别回调不回中枢
                                        print(segments_fix[-1]['bottom_time'])
                                        find_candidate_sanmai = True
                                        di_jibie_analysis_from = segments_fix[-1]['bottom_time']
                                        print("疑似三卖！！！！！！三卖！！！！！！！！三卖！！！！！！！！！！！！！")
                                        print("评估一下前面有没有一卖！是否前面是高点！")
                                        plot_if_sanmai('short', segment_zhongshus[-1]['ZD'])
                                        break
                                elif pen_zhongshus[-1 - pen_zhongshu_index]['end_time'] <= max(
                                        segments_fix[-1]['top_time'], segments_fix[-1]['bottom_time']):
                                    # 不用往前找了
                                    break
        if PRINT_PROCESS_INFO:
            plot_if_sanmai('short', "visualize_for_test")

    # 结束计时





    ####################中枢突破后，根据次级别走势判断是否有三买三卖#####################
    ####################中枢突破后，根据次级别走势判断是否有三买三卖#####################
    ####################中枢突破后，根据次级别走势判断是否有三买三卖#####################
    ####################中枢突破后，根据次级别走势判断是否有三买三卖#####################
    ####################中枢突破后，根据次级别走势判断是否有三买三卖#####################

    if find_candidate_sanmai and di_jibie_analysis_from:
        GROUP_SIZEs = [1]
        df = df[df['timestamp'] >= di_jibie_analysis_from]

        # 创建子图布局
        fig = make_subplots(rows=len(GROUP_SIZEs) * 2 + 1, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                            subplot_titles=['basetime'] + [
                                'GROUP_SIZE' + str(GROUP_SIZEs[int(group_size_in_GROUP_SIZEs_index / 2)]) if (
                                            group_size_in_GROUP_SIZEs_index % 2 == 0) else 'MACD' for
                                group_size_in_GROUP_SIZEs_index in range(2 * len(GROUP_SIZEs))],
                            row_heights=[0.7 for group_i in range(2 * len(GROUP_SIZEs) + 1)])

        # 先画一个圈数据图以确保后面几幅图所有时间戳包含，也就是GROUP_SIZEs等于1
        kline_df = generate_kline_data_group_points(df, group_size=1)
        # print("6 second data processed")

        # 画6秒级，也就是最低级别数据的空线，给后面的图参考对齐x轴
        fig.add_trace(go.Scatter(
            x=kline_df['timestamp'],  # 使用 kline_df 的时间戳
            y=[None] * len(kline_df),  # 不绘制 y 值
            mode='lines',  # 设置为线模式（但不会显示）
            showlegend=False  # 隐藏图例
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
            # 从哪个顶或底开始看影响很大，关系到走势的多义性，一般可以dingdi_start_from=1
            pens = find_pens_from_kline(kline_df_no_inclusion, dingdi_start_from=DINGDI_START_FROM)
            # pens =  find_pens_from_kline_need_fixed(kline_df_no_inclusion, dingdi_start_from=DINGDI_START_FROM)
            if PRINT_PROCESS_INFO:
                print("笔处理完毕，开始修复不合理的连续笔")
            # pens_fix 函数，它会合并 find_pens_from_kline 的结果中连续同向的笔，并重新计算合并后的每笔的最高点、最低点、起始时间和结束时间
            # fixed_pens = pens_fix(pens)
            fixed_pens = pens
            if PRINT_PROCESS_INFO:
                print("笔修复处理完毕，开始找线段")

            # 用笔组合成线段
            # segments, standard_feature_sequence_lists = merge_pens_to_segments(fixed_pens)
            segments = []
            segments, type_three_buy_sell = merge_pens_to_segments(fixed_pens)
            segments_fix = []
            if segments:
                # segments_fix = pens_fix(segments)
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
            # zgzd_type="classical"
            # zgzd_type="practical"
            # pen_zhongshus = find_zhongshu(fixed_pens, zgzd_type=ZGZD_TYPE)
            # pen_zhongshus, pen_cijibie_qushis = find_zhongshu_and_cijibie_qushi(fixed_pens, zgzd_type=ZGZD_TYPE)
            # pen_zhongshus = find_zhongshu_csy_steps(fixed_pens)
            # pen_zhongshus = find_zhongshu_csy_inverse_look_steps(fixed_pens)
            # pen_zhongshus = find_zhongshu_new(fixed_pens)
            # pen_zhongshus = find_zhongshu_one_pen_can_be_a_zhongshu(fixed_pens)
            if PRINT_PROCESS_INFO:
                print("************************笔中枢***********************")
            # pen_zhongshus, pen_zhuanzhes = find_zhongshu_based_on_looking_for_next_zhongshu(fixed_pens)
            pen_zhongshus, pen_zhuanzhes = find_zhongshu_one_pen_form(fixed_pens)

            segment_zhongshus = []
            segment_zhuanzhes = []

            if segments:
                if segments_fix:
                    # segment_zhongshus = find_zhongshu_new(segments_fix)
                    # segment_zhongshus = find_zhongshu_one_pen_can_be_a_zhongshu(segments_fix)
                    if PRINT_PROCESS_INFO:
                        print("************************线段中枢***********************")
                    # segment_zhongshus, segment_zhuanzhes = find_zhongshu_based_on_looking_for_next_zhongshu(segments_fix)
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
            file_name_record_if_sanmai = f"sanmaiplot/{current_time}_{STOCK_NAME_AND_MARKET}_qujiantao_after_{di_jibie_analysis_from}.png"

            fig.write_image(file_name_record_if_sanmai, width=3000, height=1500)


    end_time = time.time()

    # 计算运行时间
    elapsed_time = end_time - start_time
    if PRINT_PROCESS_INFO:
        # 打印运行时间（秒）
        print(f"运行时间：{elapsed_time:.2f} 秒")






        



