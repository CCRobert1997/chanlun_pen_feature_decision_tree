import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
from datetime import time as datetime_time
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from trigger_and_feature_library import *
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
# STOCK_NAME_AND_MARKETS = ["TSLA_NASDAQ"]
STOCK_NAME_AND_MARKETS = ["NVDA_NASDAQ", "AMZN_NASDAQ", "META_NASDAQ", "MSFT_NASDAQ", "SNOW_NYSE", "TIGR_NASDAQ", "TSLA_NASDAQ", "U_NYSE", "AVGO_NASDAQ", "AAPL_NASDAQ", "LLY_NYSE", "NVO_NYSE", "ADBE_NASDAQ", "TSM_NYSE", "PFE_NYSE", "JPM_NYSE", "BAC_NYSE", "COST_NASDAQ", "NFLX_NASDAQ"]
# STOCK_NAME_AND_MARKETS = ["NVDA_NASDAQ", "MSFT_NASDAQ", "AAPL_NASDAQ", "AMZN_NASDAQ", "META_NASDAQ"]
# STOCK_NAME_AND_MARKETS = ["NVDA_NASDAQ"]
STOCK_NAME_AND_MARKETS = ["NFLX_NASDAQ"]


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




# strategy = QuantStrategy0001()
# strategy = QuantStrategy0002()
strategy = STOCK_QuantStrategy[STOCK_NAME_AND_MARKETS[0]]()

for STOCK_NAME_AND_MARKET in STOCK_NAME_AND_MARKETS:

    folder_path = strategy.feature_eng_folder_path
    file_name = f"{STOCK_NAME_AND_MARKET}_pen_zhongshu_feature.csv"
    full_path = os.path.join(folder_path, file_name)

    # 确保文件夹存在
    os.makedirs(folder_path, exist_ok=True)



    pen_zhongshus = []

    pen_zhongshus = load_saved_zhongshus(STOCK_NAME_AND_MARKET)
    print(pen_zhongshus[0])


    X_all, Y_all, Z_all = [], [], []

    for i in range(len(pen_zhongshus) - 30):  # 预留至少10个lookahead空间
        x, y, z = strategy.generate_training_sample(pen_zhongshus, start_index=i, max_lookahead=10)
        if x is not None:
            X_all.append(x)
            Y_all.append(y)
            Z_all.append(z)


    # 整合 X_all, Y_all, Z_all 为一个 DataFrame 并保存
    X_df_final = pd.DataFrame(X_all)
    X_df_final['label'] = Y_all
    # X_df_final['segment_length_num_pen_zhongshu'] = Z_all

    Z_all_df = pd.DataFrame(Z_all)
    X_df_final = pd.concat([X_df_final, Z_all_df], axis=1)
    print(X_df_final.columns.tolist())


    X_df_final = strategy.filter_valid_samples(X_df_final)

    # 保存为 CSV
    X_df_final.to_csv(full_path, index=False)


    print(len(X_all), len(Y_all), len(Z_all))






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

