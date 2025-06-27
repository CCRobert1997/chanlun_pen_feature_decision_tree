# """
import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
from datetime import time as datetime_time
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from chanlun_utils import draw_zhongshu, merge_segments_fix_with_checkpoint, load_segments_from_ndjson, ensure_datetime, find_zhongshu_one_pen_form

def load_saved_pen(stock_name_and_market, seconds_level=6):
    folder_path = f"checkpoint_pen_{seconds_level}_seconds"

    file_path = os.path.join(folder_path, f"{stock_name_and_market}_segments.ndjson")

    existing_segments = load_segments_from_ndjson(file_path)


    return existing_segments


def load_saved_zhongshus(stock_name_and_market, seconds_level=6):
    folder_path = f"checkpoint_pen_zhongshus_{seconds_level}_seconds"

    file_path = os.path.join(folder_path, f"{stock_name_and_market}_pen_zhongshus.ndjson")

    existing_zhongshus = load_segments_from_ndjson(file_path)


    return existing_zhongshus





GROUP_SIZEs = [1]
STOCK_NAME_AND_MARKET = "AAPL_NASDAQ"

fixed_pens = load_saved_pen(STOCK_NAME_AND_MARKET)
pen_zhongshus = []
# pen_new_zhongshu_clean = None
# pen_zhongshus, pen_zhuanzhes = find_zhongshu_one_pen_form(fixed_pens)
pen_zhongshus = load_saved_zhongshus(STOCK_NAME_AND_MARKET)
# pen_zhongshus = pen_zhongshus[5:200]
#
# fixed_pens = fixed_pens[pen_zhongshus[0]["core_pens_index"][0]:pen_zhongshus[-1]["core_pens_index"][-1]+1]

print(len(pen_zhongshus), len(fixed_pens))




plot_number_each_jibie = 3
fig = make_subplots(rows=len(GROUP_SIZEs) * plot_number_each_jibie, cols=1, shared_xaxes=False,
                                vertical_spacing=0.05,
                                subplot_titles=['GROUP_SIZE' + str(
                                    GROUP_SIZEs[int(group_size_in_GROUP_SIZEs_index / plot_number_each_jibie)]) for group_size_in_GROUP_SIZEs_index in range(plot_number_each_jibie * len(GROUP_SIZEs))],
                                row_heights=[0.8 for group_i in range(plot_number_each_jibie * len(GROUP_SIZEs))])



def plot_if_mai():
    # Add fixed Pens to the chart


    category_x = {zs['start_time'] for zs in pen_zhongshus} | {zs['end_time'] for zs in pen_zhongshus}
    category_x |= {pen['top_time'] for pen in fixed_pens} | {pen['bottom_time'] for pen in fixed_pens}
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

    # # Add fixed Pens to the chart
    # for pen_index, pen in enumerate(fixed_pens):
    #     fig.add_trace(
    #         go.Scatter(
    #             # x=[pen['top_time'], pen['bottom_time']],
    #             x=[ensure_datetime(pen['top_time']), ensure_datetime(pen['bottom_time'])],
    #             y=[pen['top_price'], pen['bottom_price']],
    #             mode='lines',
    #             line=dict(color='white', width=2),
    #             name='Penfix',
    #             showlegend=False
    #         ),
    #         row=2, col=1
    #     )
    # draw_zhongshu(fig, pen_zhongshus, row=2,
    #               col=1,
    #               level="pen")


def plot_complete():
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
        fig.update_layout({f"xaxis{i + 1}": dict(type='category', categoryorder='category ascending')})
        # fig.update_layout({f"xaxis{i + 1}": dict(domain=[0, 1], categoryorder="category ascending")})
        # fig['layout'][f'xaxis{i + 1}'] = fig['layout'][f'xaxis{int(i/plot_number_each_jibie)+1}']

    # 显示图表
    fig.show()
    # current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 生成文件名
    # file_name_record_if_sanmai = f"sanmaiplot/{current_time}_{STOCK_NAME_AND_MARKET}_{GROUP_SIZEs[0] * 6}_second_{sanmaitype}_zhichengwei_{zhichengwei}.png"

    # fig.write_image(file_name_record_if_sanmai, width=3000, height=2500)


plot_if_mai()
plot_complete()
# """



"""
import json
from datetime import datetime

file_path = "checkpoint_pen_zhongshus_6_seconds/TSLA_NASDAQ_pen_zhongshus.ndjson"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

records = []
errors = []

for i, line in enumerate(lines):
    try:
        data = json.loads(line.strip())
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time'])
        records.append((i, start_time, end_time))
    except Exception as e:
        errors.append((i, str(e)))

print("格式错误条数:", len(errors))
if errors:
    for e in errors[:3]:
        print("示例错误:", e)

ordering_issues = []
for i in range(len(records) - 1):
    if records[i][2] >= records[i+1][1]:
        ordering_issues.append((records[i][0], records[i][2], records[i+1][1], "条间错误"))
    if records[i][2] <= records[i][1]:
        ordering_issues.append((records[i][0], records[i][1], records[i][2], "条内错误"))

print("时间顺序错误条数:", len(ordering_issues))
if ordering_issues:
    for issue in ordering_issues[:3]:
        print("示例顺序错误:", issue)
"""

