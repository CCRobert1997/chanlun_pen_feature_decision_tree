import pandas as pd
import glob
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from copy import deepcopy
import argparse
import json
from datetime import datetime
import numpy as np




# 生成 K 线数据的函数
def generate_kline_data(df):
    """
    根据价格数据生成 K 线数据
    参数:
        df: 包含 'timestamp' 和 'price' 列的 DataFrame
    返回:
        kline_df: 包含 'timestamp', 'high', 'low', 'open', 'close' 列的 K 线 DataFrame
    """
    kline_data = []
    for i in range(len(df) - 1):
        kline_data.append({
            "timestamp": df.iloc[i]['timestamp'],  # 开始时间
            "high": max(df.iloc[i]['price'], df.iloc[i + 1]['price']),  # 最高价
            "low": min(df.iloc[i]['price'], df.iloc[i + 1]['price']),   # 最低价
            "open": df.iloc[i]['price'],  # 开盘价
            "close": df.iloc[i + 1]['price']  # 收盘价
        })
    return pd.DataFrame(kline_data)
    
    
# 生成 K 线数据的函数,不是一个数据一个K线了，一般我的数据6秒一个，比如group_size=10的话那就是分钟K线
def generate_kline_data_group_points(df, group_size=2):
    """
    根据价格数据生成 K 线数据
    参数:
        df: 包含 'timestamp' 和 'price' 列的 DataFrame
        group_size: 每根 K 线包含的数据点数量，默认为 2
    返回:
        kline_df: 包含 'timestamp', 'high', 'low', 'open', 'close' 列的 K 线 DataFrame
    """
    kline_data = []

    # 确保数据按时间排序
    df_sort = df.sort_values(by="timestamp").reset_index(drop=True)

    # 按 group_size 分组生成 K 线
    for i in range(0, len(df_sort), group_size):
        group = df_sort.iloc[i:i + group_size]  # 当前分组
        if group.empty:
            continue

        kline_data.append({
            "timestamp": group.iloc[0]['timestamp'],  # K 线起始时间
            "high": group['price'].max(),            # 分组内最高价
            "low": group['price'].min(),             # 分组内最低价
            "open": group.iloc[0]['price'],          # 开盘价
            "close": group.iloc[-1]['price']         # 收盘价
        })

    return pd.DataFrame(kline_data)

    
# 合并K线包含关系函数
def handle_kline_inclusion_with_trend(kline_df):
    """
    处理 K 线的包含关系，考虑前两根 K 线的趋势方向
    参数:
        kline_df: 包含 'timestamp', 'open', 'close', 'high', 'low' 的 K 线数据 DataFrame
    返回:
        new_kline_df: 无包含的 K 线序列
    """
    result = []
    
    time_index_from = 0
    for j in range(len(kline_df)-1):
        #处理一开始就有包含关系，从没有包含关系的k线开始
        prev1 = kline_df.iloc[j].to_dict()
        prev2 = kline_df.iloc[j+1].to_dict()
        if ((prev1['low'] <= prev2['low']) and (prev1['high'] >= prev2['high'])) or ((prev1['low'] >= prev2['low']) and (prev1['high'] <= prev2['high'])):
            continue
        else:
            time_index_from = j
            break
            
    
    
    for i in range(time_index_from, len(kline_df)):
        if len(result) < 2:  # 如果不足两根，直接添加
            result.append(kline_df.iloc[i].to_dict())  # 转换为字典存储
            result[-1]['index'] = i

            continue

        prev1 = result[-2]  # 前两根 K 线
        prev2 = result[-1]  # 前一根 K 线
        curr = kline_df.iloc[i].to_dict()  # 当前 K 线

        # 判断前两根 K 线的趋势方向
        # 不需要判断 (prev2['high'] > prev1['high']) and (prev2['low'] > prev1['low'])
        # 因为前面的包含关系已经被处理掉了
        prev_trend = "up" if (prev2['high'] > prev1['high']) else "down"

        # 判断当前 K 线与上一根 K 线是否存在包含关系
        if ((curr['low'] <= prev2['low']) and (curr['high'] >= prev2['high'])) or ((curr['low'] >= prev2['low']) and (curr['high'] <= prev2['high'])):
            # 存在包含关系，根据前两根的趋势方向处理
            if prev_trend == "up":
                # 上升趋势，保留高点更高，低点更高的范围
                # 确定合并后的最高价与其对应的时间戳
                if prev2['high'] > curr['high']:
                    high_price = prev2['high']
                    high_timestamp = prev2['timestamp']
                    high_index = prev2['index']
                else:
                    high_price = curr['high']
                    high_timestamp = curr['timestamp']
                    high_index = i

                # 生成合并后的特征序列
                merged = {
                    "timestamp": high_timestamp,  # 最高价对应的时间
                    "open": prev2['open'],       # 保留上一根的开盘价
                    "close": curr['close'],      # 当前的收盘价
                    "high": high_price,          # 合并后的最高价
                    "low": max(prev2['low'], curr['low']),  # 合并后的最低价
                    "index": high_index
                }

            else:
                # 下降趋势，保留低点更低，高点更低的范围
                # 确定合并后的最低价与其对应的时间戳
                if prev2['low'] < curr['low']:
                    low_price = prev2['low']
                    low_timestamp = prev2['timestamp']
                    low_index = prev2['index']
                else:
                    low_price = curr['low']
                    low_timestamp = curr['timestamp']
                    low_index = i

                # 合并逻辑
                merged = {
                    "timestamp": low_timestamp,  # 最低价对应的时间
                    "open": prev2['open'],       # 保留上一根的开盘价
                    "close": curr['close'],      # 当前的收盘价
                    "high": min(prev2['high'], curr['high']),  # 合并后的最高价
                    "low": low_price,             # 合并后的最低价
                    "index": low_index
                }
            result[-1] = merged  # 更新最后一根 K 线
        else:
            # 如果没有包含关系，直接添加当前 K 线
            result.append(curr)
            result[-1]['index'] = i
    return pd.DataFrame(result)  # 确保转换为 DataFrame


# 合并K线包含关系函数
def handle_kline_inclusion_with_trend_for_feature_sequence(kline_df, prev_trend, partition_pens_start_index, merge_segments_to_segments=False):
    """
    处理 K 线的包含关系，考虑前两根 K 线的趋势方向
    参数:
        kline_df: 包含 'timestamp', 'open', 'close', 'high', 'low' 的 K 线数据 DataFrame
    返回:
        new_kline_df: 无包含的 K 线序列
    """
    result = []

    time_index_from = 0
    # for j in range(len(kline_df) - 1):
    #     # 处理一开始就有包含关系，从没有包含关系的k线开始
    #     prev1 = kline_df.iloc[j].to_dict()
    #     prev2 = kline_df.iloc[j + 1].to_dict()
    #     if ((prev1['low'] <= prev2['low']) and (prev1['high'] >= prev2['high'])) or (
    #             (prev1['low'] >= prev2['low']) and (prev1['high'] <= prev2['high'])):
    #         continue
    #     else:
    #         time_index_from = j
    #         break

    for i in range(time_index_from, len(kline_df)):
        if len(result) < 1:  # 如果不足一根，直接添加
            result.append(kline_df.iloc[i].to_dict())  # 转换为字典存储
            result[-1]['index'] = 2 * i + partition_pens_start_index + 1

            continue

        prev2 = result[-1]  # 前一根 K 线
        curr = kline_df.iloc[i].to_dict()  # 当前 K 线

        # print(f" 这一笔{2 * i + partition_pens_start_index + 1}")
        # print(f"找到你了 前high{prev2['high']}, 后high{curr['high']}，，， 前low{prev2['low']}, 后low{curr['low']}!!!!!!!!!!!!!")
        # print(((curr['low'] <= prev2['low']) and (curr['high'] >= prev2['high'])))
        # 判断当前 K 线与上一根 K 线是否存在包含关系
        if ((curr['low'] <= prev2['low']) and (curr['high'] >= prev2['high'])) or (
                (curr['low'] >= prev2['low']) and (curr['high'] <= prev2['high'])):
            # 存在包含关系，根据前两根的趋势方向处理
            if prev_trend == "Up":
                # if (2 * i + partition_pens_start_index + 1 == 20):
                # 上升趋势，保留高点更高，低点更高的范围
                # 确定合并后的最高价与其对应的时间戳
                if prev2['high'] > curr['high']:
                    high_price = prev2['high']
                    high_timestamp = prev2['timestamp']
                    high_index = prev2['index']
                else:
                    high_price = curr['high']
                    high_timestamp = curr['timestamp']
                    #high_index = i
                    high_index = 2 * i + partition_pens_start_index + 1

                # 生成合并后的特征序列
                if not merge_segments_to_segments:
                    merged = {
                        "timestamp": high_timestamp,  # 最高价对应的时间
                        "open": prev2['open'],  # 保留上一根的开盘价
                        "close": curr['close'],  # 当前的收盘价
                        "high": high_price,  # 合并后的最高价
                        "low": max(prev2['low'], curr['low']),  # 合并后的最低价
                        "index": high_index,
                        "timestamp_feature_complete": curr["timestamp_feature_complete"],
                        "price_feature_complete": curr["price_feature_complete"]
                    }
                else:
                    merged = {
                        "timestamp": high_timestamp,  # 最高价对应的时间
                        "open": prev2['open'],  # 保留上一根的开盘价
                        "close": curr['close'],  # 当前的收盘价
                        "high": high_price,  # 合并后的最高价
                        "low": max(prev2['low'], curr['low']),  # 合并后的最低价
                        "index": high_index
                    }


            else:
                # 下降趋势，保留低点更低，高点更低的范围
                # 确定合并后的最低价与其对应的时间戳
                if prev2['low'] < curr['low']:
                    low_price = prev2['low']
                    low_timestamp = prev2['timestamp']
                    low_index = prev2['index']
                else:
                    low_price = curr['low']
                    low_timestamp = curr['timestamp']
                    # low_index = i
                    low_index = 2 * i + partition_pens_start_index + 1


                # 合并逻辑
                if not merge_segments_to_segments:
                    merged = {
                        "timestamp": low_timestamp,  # 最低价对应的时间
                        "open": prev2['open'],  # 保留上一根的开盘价
                        "close": curr['close'],  # 当前的收盘价
                        "high": min(prev2['high'], curr['high']),  # 合并后的最高价
                        "low": low_price,  # 合并后的最低价
                        "index": low_index,
                        "timestamp_feature_complete": curr["timestamp_feature_complete"],
                        "price_feature_complete": curr["price_feature_complete"]
                    }
                else:
                    merged = {
                        "timestamp": low_timestamp,  # 最低价对应的时间
                        "open": prev2['open'],  # 保留上一根的开盘价
                        "close": curr['close'],  # 当前的收盘价
                        "high": min(prev2['high'], curr['high']),  # 合并后的最高价
                        "low": low_price,  # 合并后的最低价
                        "index": low_index
                    }
            result[-1] = merged  # 更新最后一根 K 线
        else:
            # 如果没有包含关系，直接添加当前 K 线
            result.append(curr)
            result[-1]['index'] = 2 * i + partition_pens_start_index + 1

    return pd.DataFrame(result)  # 确保转换为 DataFrame


# 合并后的K线画笔的函数
# 从哪个顶或底开始看影响很大，关系到走势的多义性
def find_pens_from_kline_need_fixed(kline_df_no_inclusion, dingdi_start_from=1):
    """
    从 K 线数据中直接找出缠论的笔（起点和终点）
    参数:
        kline_df_no_inclusion: 无包含的 K 线数据 DataFrame，包含 'timestamp', 'high', 'low'
    返回:
        pens: 包含 (start_index, end_index, start_time, end_time, top_price, bottom_price) 的笔列表
    """
    pens = []
    fenxings = []

    def fill_pen(fenxing, pen):
        if fenxing["type"] == "di":
            pen.update({
                "bottom_price": fenxing["price"],
                "bottom_index": fenxing["index"],
                "bottom_time": fenxing["timestamp"]
            })
        elif fenxing["type"] == "ding":
            pen.update({
                "top_price": fenxing["price"],
                "top_index": fenxing["index"],
                "top_time": fenxing["timestamp"]
            })
    i = 1
    while i < len(kline_df_no_inclusion) - 1:
        # 判断顶分型
        if (kline_df_no_inclusion.iloc[i]['high'] > kline_df_no_inclusion.iloc[i - 1]['high'] and
            kline_df_no_inclusion.iloc[i]['high'] > kline_df_no_inclusion.iloc[i + 1]['high'] and
            kline_df_no_inclusion.iloc[i]['low'] > kline_df_no_inclusion.iloc[i - 1]['low'] and
            kline_df_no_inclusion.iloc[i]['low'] > kline_df_no_inclusion.iloc[i + 1]['low']):
                fenxing = {
                    "timestamp": kline_df_no_inclusion.iloc[i]['timestamp'],
                    "index": i,
                    "type": "ding",
                    "price": kline_df_no_inclusion.iloc[i]['high']
                }
                fenxings.append(fenxing)
        # 判断底分型
        elif (kline_df_no_inclusion.iloc[i]['low'] < kline_df_no_inclusion.iloc[i - 1]['low'] and
              kline_df_no_inclusion.iloc[i]['low'] < kline_df_no_inclusion.iloc[i + 1]['low'] and
              kline_df_no_inclusion.iloc[i]['high'] < kline_df_no_inclusion.iloc[i - 1]['high'] and
              kline_df_no_inclusion.iloc[i]['high'] < kline_df_no_inclusion.iloc[i + 1]['high']):
            fenxing = {
                "timestamp": kline_df_no_inclusion.iloc[i]['timestamp'],
                "index": i,
                "type": "di",
                "price": kline_df_no_inclusion.iloc[i]['low']
            }
            fenxings.append(fenxing)
        i+=1


    #从哪个顶或底开始看影响很大，关系到走势的多义性
    i = dingdi_start_from
    last_dingdi = fenxings[i]


    #初始化第一笔的顶底
    if last_dingdi["type"] == "ding":
        pens = [{"top_index": last_dingdi["index"], "bottom_index": 0, "top_time": last_dingdi["timestamp"], "bottom_time": kline_df_no_inclusion.iloc[0]['timestamp'], "top_price": last_dingdi["price"], "bottom_price": kline_df_no_inclusion.iloc[0]['low'], "direction": "Up" if last_dingdi["type"] == "ding" else "Down"}]
    elif last_dingdi["type"] == "di":
        pens = [{"top_index": 0, "bottom_index": last_dingdi["index"], "top_time": kline_df_no_inclusion.iloc[0]['timestamp'], "bottom_time": last_dingdi["timestamp"], "top_price": kline_df_no_inclusion.iloc[0]['high'], "bottom_price": last_dingdi["price"], "direction": "Up"}]


    while i < len(fenxings):
        current_dingdi = fenxings[i]
        # print(current_dingdi["type"], current_dingdi["index"], current_dingdi["timestamp"], kline_df_no_inclusion.iloc[current_dingdi["index"]]['high'], kline_df_no_inclusion.iloc[current_dingdi["index"]]['low'])
        if current_dingdi["type"] == last_dingdi["type"]:
            last_dingdi = current_dingdi
            if current_dingdi["type"] == "ding":
                pens[-1].update({
                    "top_price": current_dingdi["price"],
                    "top_index": current_dingdi["index"],
                    "top_time": current_dingdi["timestamp"]
                })
            elif current_dingdi["type"] == "di":
                pens[-1].update({
                    "bottom_price": current_dingdi["price"],
                    "bottom_index": current_dingdi["index"],
                    "bottom_time": current_dingdi["timestamp"]
                })

            i+=1
        else:
            if current_dingdi["index"] - 4 >= last_dingdi["index"]:
                pen = {}
                fill_pen(last_dingdi, pen)
                fill_pen(current_dingdi, pen)
                if current_dingdi["type"] == "ding":
                    pen.update({
                        "direction": "Up"
                    })
                else:
                    pen.update({
                        "direction": "Down"
                    })
                # 添加新笔
                pens.append(pen)
                i+=1
                last_dingdi = current_dingdi
            else:
                i+=1
    return pens




    
    
# 合并后的K线画笔的函数
#从哪个顶或底开始看影响很大，关系到走势的多义性
def find_pens_from_kline(kline_df_no_inclusion, dingdi_start_from=2):
    """
    从 K 线数据中直接找出缠论的笔（起点和终点）
    参数:
        kline_df_no_inclusion: 无包含的 K 线数据 DataFrame，包含 'timestamp', 'high', 'low'
    返回:
        pens: 包含 (start_index, end_index, start_time, end_time, top_price, bottom_price) 的笔列表
    """
    pens = []
    fenxings = []
    
    def fill_pen(fenxing, pen):
        if fenxing["type"] == "di":
            pen.update({
                "bottom_price": fenxing["price"],
                "bottom_index": fenxing["index"],
                "bottom_time": fenxing["timestamp"]
            })
        elif fenxing["type"] == "ding":
            pen.update({
                "top_price": fenxing["price"],
                "top_index": fenxing["index"],
                "top_time": fenxing["timestamp"]
            })
    i = 1
    while i < len(kline_df_no_inclusion) - 1:
        # 判断顶分型
        if (kline_df_no_inclusion.iloc[i]['high'] > kline_df_no_inclusion.iloc[i - 1]['high'] and
            kline_df_no_inclusion.iloc[i]['high'] > kline_df_no_inclusion.iloc[i + 1]['high'] and
            kline_df_no_inclusion.iloc[i]['low'] > kline_df_no_inclusion.iloc[i - 1]['low'] and
            kline_df_no_inclusion.iloc[i]['low'] > kline_df_no_inclusion.iloc[i + 1]['low']):
                fenxing = {
                    "timestamp": kline_df_no_inclusion.iloc[i]['timestamp'],
                    "index": i,
                    "type": "ding",
                    "price": kline_df_no_inclusion.iloc[i]['high'],
                    "timestamp_fenxing_complete": kline_df_no_inclusion.iloc[i + 1]['timestamp'],
                    "price_fenxing_complete": kline_df_no_inclusion.iloc[i + 1]['close']
                }
                fenxings.append(fenxing)
        # 判断底分型
        elif (kline_df_no_inclusion.iloc[i]['low'] < kline_df_no_inclusion.iloc[i - 1]['low'] and
              kline_df_no_inclusion.iloc[i]['low'] < kline_df_no_inclusion.iloc[i + 1]['low'] and
              kline_df_no_inclusion.iloc[i]['high'] < kline_df_no_inclusion.iloc[i - 1]['high'] and
              kline_df_no_inclusion.iloc[i]['high'] < kline_df_no_inclusion.iloc[i + 1]['high']):
            fenxing = {
                "timestamp": kline_df_no_inclusion.iloc[i]['timestamp'],
                "index": i,
                "type": "di",
                "price": kline_df_no_inclusion.iloc[i]['low'],
                "timestamp_fenxing_complete": kline_df_no_inclusion.iloc[i + 1]['timestamp'],
                "price_fenxing_complete": kline_df_no_inclusion.iloc[i + 1]['close']
            }
            fenxings.append(fenxing)
        i+=1
    
    
    #从哪个顶或底开始看影响很大，关系到走势的多义性
    # i = dingdi_start_from
    i = 0
    last_dingdi = fenxings[i]
    dingdi_start_next_pen =  fenxings[i]
    
    
    #初始化第一笔的顶底
    if last_dingdi["type"] == "ding":
        pens = [{"top_index": last_dingdi["index"], "bottom_index": 0, "top_time": last_dingdi["timestamp"], "bottom_time": kline_df_no_inclusion.iloc[0]['timestamp'], "top_price": last_dingdi["price"], "bottom_price": kline_df_no_inclusion.iloc[0]['low'], "direction": "Up" if last_dingdi["type"] == "ding" else "Down", "timestamp_pen_complete": last_dingdi["timestamp_fenxing_complete"], "price_pen_complete": last_dingdi["price_fenxing_complete"]}]
    elif last_dingdi["type"] == "di":
        pens = [{"top_index": 0, "bottom_index": last_dingdi["index"], "top_time": kline_df_no_inclusion.iloc[0]['timestamp'], "bottom_time": last_dingdi["timestamp"], "top_price": kline_df_no_inclusion.iloc[0]['high'], "bottom_price": last_dingdi["price"], "direction": "Up" if last_dingdi["type"] == "ding" else "Down", "timestamp_pen_complete": last_dingdi["timestamp_fenxing_complete"], "price_pen_complete": last_dingdi["price_fenxing_complete"]}]

    while i < len(fenxings):
        current_dingdi = fenxings[i]
        # print(current_dingdi["type"], current_dingdi["index"], current_dingdi["timestamp"], kline_df_no_inclusion.iloc[current_dingdi["index"]]['high'], kline_df_no_inclusion.iloc[current_dingdi["index"]]['low'])
        #if current_dingdi["type"] == last_dingdi["type"]:
        if current_dingdi["type"] == dingdi_start_next_pen["type"]:
            last_dingdi = current_dingdi
            if current_dingdi["type"] == "ding":
                if current_dingdi["price"] > pens[-1]["top_price"]: #new rule #笔延长
                    pens[-1].update({
                        "top_price": current_dingdi["price"],
                        "top_index": current_dingdi["index"],
                        "top_time": current_dingdi["timestamp"],
                        "timestamp_pen_complete": current_dingdi["timestamp_fenxing_complete"],
                        "price_pen_complete": current_dingdi["price_fenxing_complete"]
                    })
                    dingdi_start_next_pen = current_dingdi
            elif current_dingdi["type"] == "di":
                if current_dingdi["price"] < pens[-1]["bottom_price"]: #new rule #笔延长
                    pens[-1].update({
                        "bottom_price": current_dingdi["price"],
                        "bottom_index": current_dingdi["index"],
                        "bottom_time": current_dingdi["timestamp"],
                        "timestamp_pen_complete": current_dingdi["timestamp_fenxing_complete"],
                        "price_pen_complete": current_dingdi["price_fenxing_complete"]
                    })
                    dingdi_start_next_pen = current_dingdi
            
            i+=1
        else:
            # if current_dingdi["index"] - 4 >= dingdi_start_next_pen["index"]:  # 这个条件的话偏向于高频画笔
            if current_dingdi["index"] - 4 >= last_dingdi["index"]: #新笔
                pen = {}
                fill_pen(dingdi_start_next_pen, pen)
                fill_pen(current_dingdi, pen)
                pen.update({
                    "timestamp_pen_complete": current_dingdi["timestamp_fenxing_complete"],
                    "price_pen_complete": current_dingdi["price_fenxing_complete"]
                })
                if current_dingdi["type"] == "ding":
                    pen.update({
                        "direction": "Up"
                    })
                else:
                    pen.update({
                        "direction": "Down"
                    })
                # 添加新笔
                pens.append(pen)
                i+=1
                last_dingdi = current_dingdi
                dingdi_start_next_pen = current_dingdi
            elif pens and ((current_dingdi["type"] == "ding" and current_dingdi["price"] > pens[-1]["top_price"]) or (
                    current_dingdi["type"] == "di" and current_dingdi["price"] < pens[-1]["bottom_price"])):
                # 笔重整
                if len(pens) == 1:
                    # 初始化第一笔的顶底
                    if current_dingdi["type"] == "ding":
                        pens = [
                            {"top_index": current_dingdi["index"], "bottom_index": 0, "top_time": current_dingdi["timestamp"],
                             "bottom_time": kline_df_no_inclusion.iloc[0]['timestamp'],
                             "top_price": current_dingdi["price"], "bottom_price": kline_df_no_inclusion.iloc[0]['low'],
                             "direction": "Up" if current_dingdi["type"] == "ding" else "Down",
                             "timestamp_pen_complete": current_dingdi["timestamp_fenxing_complete"],
                             "price_pen_complete": current_dingdi["price_fenxing_complete"]}]
                    elif current_dingdi["type"] == "di":
                        pens = [{"top_index": 0, "bottom_index": current_dingdi["index"],
                                 "top_time": kline_df_no_inclusion.iloc[0]['timestamp'],
                                 "bottom_time": current_dingdi["timestamp"],
                                 "top_price": kline_df_no_inclusion.iloc[0]['high'],
                                 "bottom_price": current_dingdi["price"], "direction": "Up",
                                 "timestamp_pen_complete": current_dingdi["timestamp_fenxing_complete"],
                                 "price_pen_complete": current_dingdi["price_fenxing_complete"]}]
                    dingdi_start_next_pen = current_dingdi
                else:
                    pens = pens[:-1]
                    if pens:
                        if current_dingdi["type"] == "ding":
                            pens[-1].update({
                                "top_price": current_dingdi["price"],
                                "top_index": current_dingdi["index"],
                                "top_time": current_dingdi["timestamp"],
                                "timestamp_pen_complete": current_dingdi["timestamp_fenxing_complete"],
                                "price_pen_complete": current_dingdi["price_fenxing_complete"]
                            })
                        elif current_dingdi["type"] == "di":
                            pens[-1].update({
                                "bottom_price": current_dingdi["price"],
                                "bottom_index": current_dingdi["index"],
                                "bottom_time": current_dingdi["timestamp"],
                                "timestamp_pen_complete": current_dingdi["timestamp_fenxing_complete"],
                                "price_pen_complete": current_dingdi["price_fenxing_complete"]
                            })
                    dingdi_start_next_pen = current_dingdi
                i += 1
            else:
                i+=1
    # print([pen['direction'] for pen in pens])
    return pens
        

#def find_pens_from_kline_incomplete(kline_df_no_inclusion):
#    """
#    从 K 线数据中直接找出缠论的笔（起点和终点）
#    参数:
#        kline_df_no_inclusion: 无包含的 K 线数据 DataFrame，包含 'timestamp', 'high', 'low'
#    返回:
#        pens: 包含 (start_index, end_index, start_time, end_time, top_price, bottom_price) 的笔列表
#    """
#    pens = []  # 存储笔的信息
#    i = 1  # 从第二根 K 线开始
#
#    while i < len(kline_df_no_inclusion) - 1:
#        # 判断顶分型
#        if (kline_df_no_inclusion.iloc[i]['high'] > kline_df_no_inclusion.iloc[i - 1]['high'] and
#            kline_df_no_inclusion.iloc[i]['high'] > kline_df_no_inclusion.iloc[i + 1]['high'] and
#            kline_df_no_inclusion.iloc[i]['low'] > kline_df_no_inclusion.iloc[i - 1]['low'] and
#            kline_df_no_inclusion.iloc[i]['low'] > kline_df_no_inclusion.iloc[i + 1]['low']):
#
#            # 找到顶分型，继续寻找底分型
#            top_idx = i
#            top_time = kline_df_no_inclusion.iloc[i]['timestamp']
#            top_price = kline_df_no_inclusion.iloc[i]['high']
#
#            i += 4  # 至少间隔一个 K 线
#            while i < len(kline_df_no_inclusion) - 1:
#                # 判断底分型
#                # 必须五段呈现连续方向的命令是必要的，数据不够多时comment掉，用pens_fix将就一下
#                if (kline_df_no_inclusion.iloc[i]['low'] < kline_df_no_inclusion.iloc[i - 1]['low'] and
#                    kline_df_no_inclusion.iloc[i]['low'] < kline_df_no_inclusion.iloc[i + 1]['low'] and
#                    kline_df_no_inclusion.iloc[i]['high'] < kline_df_no_inclusion.iloc[i - 1]['high'] and
#                    kline_df_no_inclusion.iloc[i]['high'] < kline_df_no_inclusion.iloc[i + 1]['high']):
#                    """and (kline_df_no_inclusion.iloc[i-4]['high'] > kline_df_no_inclusion.iloc[i-3]['high'] and kline_df_no_inclusion.iloc[i-3]['high'] > kline_df_no_inclusion.iloc[i-2]['high'] and kline_df_no_inclusion.iloc[i-2]['high'] > kline_df_no_inclusion.iloc[i-1]['high']):"""
#
#                    # 找到底分型，形成一笔,但这一笔还没有确认
#                    bottom_idx = i
#                    bottom_time = kline_df_no_inclusion.iloc[i]['timestamp']
#                    bottom_price = kline_df_no_inclusion.iloc[i]['low']
#
#                    # 找到底分型，确认上一向上笔的结束时间
#
#                    if (len(pens)>0):
#                        pens[-1]["top_index"] = top_idx
#                        pens[-1]["top_time"] = top_time
#                        pens[-1]["top_price"] = top_price
#
#                    # 添加新笔
#                    pens.append({
#                        "top_index": top_idx,
#                        "bottom_index": bottom_idx,
#                        "top_time": top_time,
#                        "bottom_time": bottom_time,
#                        "top_price": top_price,
#                        "bottom_price": bottom_price,
#                        "direction": "Down"
#                    })
#                    break
#                i += 1
#
#        # 判断底分型
#        elif (kline_df_no_inclusion.iloc[i]['low'] < kline_df_no_inclusion.iloc[i - 1]['low'] and
#              kline_df_no_inclusion.iloc[i]['low'] < kline_df_no_inclusion.iloc[i + 1]['low'] and
#              kline_df_no_inclusion.iloc[i]['high'] < kline_df_no_inclusion.iloc[i - 1]['high'] and
#              kline_df_no_inclusion.iloc[i]['high'] < kline_df_no_inclusion.iloc[i + 1]['high']):
#
#            # 找到底分型，继续寻找顶分型
#            bottom_idx = i
#            bottom_time = kline_df_no_inclusion.iloc[i]['timestamp']
#            bottom_price = kline_df_no_inclusion.iloc[i]['low']
#            i += 4  # 至少间隔一个 K 线
#            while i < len(kline_df_no_inclusion) - 1:
#                # 判断顶分型
#                # 必须五段呈现连续方向的命令是必要的，数据不够多时comment掉，用pens_fix将就一下
#                if (kline_df_no_inclusion.iloc[i]['high'] > kline_df_no_inclusion.iloc[i - 1]['high'] and
#                    kline_df_no_inclusion.iloc[i]['high'] > kline_df_no_inclusion.iloc[i + 1]['high'] and
#                    kline_df_no_inclusion.iloc[i]['low'] > kline_df_no_inclusion.iloc[i - 1]['low'] and
#                    kline_df_no_inclusion.iloc[i]['low'] > kline_df_no_inclusion.iloc[i + 1]['low']):
#                    """and (kline_df_no_inclusion.iloc[i-4]['low'] < kline_df_no_inclusion.iloc[i-3]['low'] and
#                        kline_df_no_inclusion.iloc[i-3]['low'] < kline_df_no_inclusion.iloc[i-2]['low'] and
#                        kline_df_no_inclusion.iloc[i-2]['low'] < kline_df_no_inclusion.iloc[i-1]['low']):"""
#
#                    # 找到顶分型，形成一笔
#                    top_idx = i
#                    top_time = kline_df_no_inclusion.iloc[i]['timestamp']
#                    top_price = kline_df_no_inclusion.iloc[i]['high']
#
#                    # 找到顶分型，确认上一向下笔的结束时间
#                    if (len(pens)>0):
#                        pens[-1]["bottom_index"] = bottom_idx
#                        pens[-1]["bottom_time"] = bottom_time
#                        pens[-1]["bottom_price"] = bottom_price
#
#                    # 添加新笔
#                    pens.append({
#                        "top_index": top_idx,
#                        "bottom_index": bottom_idx,
#                        "top_time": top_time,
#                        "bottom_time": bottom_time,
#                        "top_price": top_price,
#                        "bottom_price": bottom_price,
#                        "direction": "Up"
#                    })
#                    break
#                i += 1
#
#        # 如果没有形成分型，继续向前遍历
#        else:
#            i += 1
#
#    return pens
#
#
#
#
## 合并后的K线画笔的函数，数据够多时要求五段呈现连续方向的版本
#def find_pens_from_kline_complete(kline_df_no_inclusion):
#    """
#    从 K 线数据中直接找出缠论的笔（起点和终点）
#    参数:
#        kline_df_no_inclusion: 无包含的 K 线数据 DataFrame，包含 'timestamp', 'high', 'low'
#    返回:
#        pens: 包含 (start_index, end_index, start_time, end_time, top_price, bottom_price) 的笔列表
#    """
#    pens = []  # 存储笔的信息
#    i = 1  # 从第二根 K 线开始
#
#    while i < len(kline_df_no_inclusion) - 1:
#        # 判断顶分型
#        if (kline_df_no_inclusion.iloc[i]['high'] > kline_df_no_inclusion.iloc[i - 1]['high'] and
#            kline_df_no_inclusion.iloc[i]['high'] > kline_df_no_inclusion.iloc[i + 1]['high'] and
#            kline_df_no_inclusion.iloc[i]['low'] > kline_df_no_inclusion.iloc[i - 1]['low'] and
#            kline_df_no_inclusion.iloc[i]['low'] > kline_df_no_inclusion.iloc[i + 1]['low']):
#
#            # 找到顶分型，继续寻找底分型
#            top_idx = i
#            top_time = kline_df_no_inclusion.iloc[i]['timestamp']
#            top_price = kline_df_no_inclusion.iloc[i]['high']
#            i += 4  # 至少间隔一个 K 线
#            while i < len(kline_df_no_inclusion) - 1:
#                # 判断底分型
#                # 必须五段呈现连续方向的命令是必要的，数据不够多时comment掉，用pens_fix将就一下
#                if (kline_df_no_inclusion.iloc[i]['low'] < kline_df_no_inclusion.iloc[i - 1]['low'] and
#                    kline_df_no_inclusion.iloc[i]['low'] < kline_df_no_inclusion.iloc[i + 1]['low'] and
#                    kline_df_no_inclusion.iloc[i]['high'] < kline_df_no_inclusion.iloc[i - 1]['high'] and
#                    kline_df_no_inclusion.iloc[i]['high'] < kline_df_no_inclusion.iloc[i + 1]['high']) and (kline_df_no_inclusion.iloc[i-4]['high'] > kline_df_no_inclusion.iloc[i-3]['high'] and kline_df_no_inclusion.iloc[i-3]['high'] > kline_df_no_inclusion.iloc[i-2]['high'] and kline_df_no_inclusion.iloc[i-2]['high'] > kline_df_no_inclusion.iloc[i-1]['high']):
#
#                    # 找到底分型，形成一笔,但这一笔还没有确认
#                    bottom_idx = i
#                    bottom_time = kline_df_no_inclusion.iloc[i]['timestamp']
#                    bottom_price = kline_df_no_inclusion.iloc[i]['low']
#
#                    # 找到底分型，确认上一向上笔的结束时间
#                    if (len(pens)>0):
#                        pens[-1]["top_index"] = top_idx
#                        pens[-1]["top_time"] = top_time
#                        pens[-1]["top_price"] = top_price
#
#                    # 添加新笔
#                    pens.append({
#                        "top_index": top_idx,
#                        "bottom_index": bottom_idx,
#                        "top_time": top_time,
#                        "bottom_time": bottom_time,
#                        "top_price": top_price,
#                        "bottom_price": bottom_price,
#                        "direction": "Down"
#                    })
#                    break
#                i += 1
#
#        # 判断底分型
#        elif (kline_df_no_inclusion.iloc[i]['low'] < kline_df_no_inclusion.iloc[i - 1]['low'] and
#              kline_df_no_inclusion.iloc[i]['low'] < kline_df_no_inclusion.iloc[i + 1]['low'] and
#              kline_df_no_inclusion.iloc[i]['high'] < kline_df_no_inclusion.iloc[i - 1]['high'] and
#              kline_df_no_inclusion.iloc[i]['high'] < kline_df_no_inclusion.iloc[i + 1]['high']):
#
#            # 找到底分型，继续寻找顶分型
#            bottom_idx = i
#            bottom_time = kline_df_no_inclusion.iloc[i]['timestamp']
#            bottom_price = kline_df_no_inclusion.iloc[i]['low']
#            i += 4  # 至少间隔一个 K 线
#            while i < len(kline_df_no_inclusion) - 1:
#                # 判断顶分型
#                # 必须五段呈现连续方向的命令是必要的，数据不够多时comment掉，用pens_fix将就一下
#                if (kline_df_no_inclusion.iloc[i]['high'] > kline_df_no_inclusion.iloc[i - 1]['high'] and
#                    kline_df_no_inclusion.iloc[i]['high'] > kline_df_no_inclusion.iloc[i + 1]['high'] and
#                    kline_df_no_inclusion.iloc[i]['low'] > kline_df_no_inclusion.iloc[i - 1]['low'] and
#                    kline_df_no_inclusion.iloc[i]['low'] > kline_df_no_inclusion.iloc[i + 1]['low']) and (kline_df_no_inclusion.iloc[i-4]['low'] < kline_df_no_inclusion.iloc[i-3]['low'] and
#                        kline_df_no_inclusion.iloc[i-3]['low'] < kline_df_no_inclusion.iloc[i-2]['low'] and
#                        kline_df_no_inclusion.iloc[i-2]['low'] < kline_df_no_inclusion.iloc[i-1]['low']):
#
#                    # 找到顶分型，形成一笔
#                    top_idx = i
#                    top_time = kline_df_no_inclusion.iloc[i]['timestamp']
#                    top_price = kline_df_no_inclusion.iloc[i]['high']
#
#                    # 找到顶分型，确认上一向下笔的结束时间
#                    if (len(pens)>0):
#                        pens[-1]["bottom_index"] = bottom_idx
#                        pens[-1]["bottom_time"] = bottom_time
#                        pens[-1]["bottom_price"] = bottom_price
#
#                    # 添加新笔
#                    pens.append({
#                        "top_index": top_idx,
#                        "bottom_index": bottom_idx,
#                        "top_time": top_time,
#                        "bottom_time": bottom_time,
#                        "top_price": top_price,
#                        "bottom_price": bottom_price,
#                        "direction": "Up"
#                    })
#                    break
#                i += 1
#
#        # 如果没有形成分型，继续向前遍历
#        else:
#            i += 1
#
#    return pens



# 合并后的K线画笔的函数因为数据不够多时不要求五段呈现连续方向，所以结果需要稍微调整增加可用性
def pens_fix(pens):
    """
    修正笔数据：如果出现连续同向的笔，就将它们合并为一笔。
    合并规则：
        1. 取合并笔的最高点（top_price）和最低点（bottom_price）。
        2. 起始时间为最早的开始时间，结束时间为最晚的结束时间。
        3. 方向的判断依据为 "top_time" 是否比 "bottom_time" 大。
    参数:
        pens: 包含每一笔信息的列表，每个元素是字典，包含:
              'top_price', 'bottom_price', 'top_time', 'bottom_time', 'direction'
    返回:
        fixed_pens: 修正后的笔列表
    """
    
    # 重新确定每笔方向性
    current_pen_i = 0
    while current_pen_i < len(pens):
        # 检查 bottom_price 是否大于等于 top_price
        if pens[current_pen_i]['bottom_price'] >= pens[current_pen_i]['top_price']:
            # 交换价格
            pens[current_pen_i]['top_price'], pens[current_pen_i]['bottom_price'] = (
                pens[current_pen_i]['bottom_price'],
                pens[current_pen_i]['top_price']
            )
            # 交换索引
            pens[current_pen_i]['top_index'], pens[current_pen_i]['bottom_index'] = (
                pens[current_pen_i]['bottom_index'],
                pens[current_pen_i]['top_index']
            )
            # 交换时间
            pens[current_pen_i]['top_time'], pens[current_pen_i]['bottom_time'] = (
                pens[current_pen_i]['bottom_time'],
                pens[current_pen_i]['top_time']
            )
        # 判断方向
        pens[current_pen_i]['direction'] = (
            "Down" if pens[current_pen_i]['top_time'] < pens[current_pen_i]['bottom_time'] else "Up"
        )
        current_pen_i += 1
        
            
    
    # 组合同向的错误
    if not pens:
        return []
    fixed_pens = [pens[0]]  # 初始化结果，加入第一笔
    current_pen_i = 1
    while (current_pen_i < len(pens)):
        last_pen = fixed_pens[-1]

        # 如果当前笔方向与上一笔方向相同，进行合并
        if last_pen['direction'] == pens[current_pen_i]['direction']:
            if last_pen['direction'] == "Up":
                merged_pen = {
                    "top_price": pens[current_pen_i]['top_price'],
                    "bottom_price": last_pen['bottom_price'],
                    "top_time": max(pens[current_pen_i]['top_time'], pens[current_pen_i]['bottom_time']),
                    "bottom_time": last_pen['bottom_time'],
                    "top_index": max(pens[current_pen_i]['top_index'], pens[current_pen_i]['bottom_index']),
                    "bottom_index": last_pen['bottom_index'],
                    "direction": last_pen['direction']
                }
            elif last_pen['direction'] == "Down":
                merged_pen = {
                    "top_price": last_pen['top_price'],
                    "bottom_price": pens[current_pen_i]['bottom_price'],
                    "top_time": last_pen['top_time'],
                    "bottom_time": max(pens[current_pen_i]['top_time'], pens[current_pen_i]['bottom_time']),
                    "top_index": last_pen['top_index'],
                    "bottom_index": max(pens[current_pen_i]['top_index'], pens[current_pen_i]['bottom_index']),
                    "direction": last_pen['direction']
                }
            fixed_pens[-1] = merged_pen  # 更新最后一笔
            current_pen_i+=1
        else:
            # 如果方向不同，直接加入当前笔
            fixed_pens.append(pens[current_pen_i])
            current_pen_i+=1

    return fixed_pens
    
    
    
    

def generate_feature_sequence(pens, partition_pens_start_index, feature_sequence_for_segment=False):
    """
    根据笔的输入生成特征序列（不考虑缺口）
    参数:
        pens: 包含每一笔信息的列表，每个元素是字典，包含:
              'top_price', 'bottom_price', 'top_time', 'bottom_time', 'direction'
    返回:
        feature_sequence: 特征序列，每个元素是字典，包含:
                          'timestamp', 'open', 'close', 'high', 'low'
    """
    feature_sequence = []


    # 跳一个取一个生成特征序列
    for i in range(0, len(pens) - 1, 2):
        curr = pens[i]
        next_ = pens[i + 1]

        if not feature_sequence_for_segment:
            feature = {
                "timestamp": curr['top_time'] if curr['direction'] == "Up" else curr['bottom_time'],  # 当前笔的结束时间
                "open": curr['bottom_price'] if curr['direction'] == "Up" else curr['top_price'],     # 当前笔的开盘价
                "close": next_['top_price'] if next_['direction'] == "Up" else next_['bottom_price'], # 下一笔的收盘价
                "high": next_['top_price'],                                   # 两笔的最高价
                "low": next_['bottom_price'],                             # 两笔的最低价
                "index": i + partition_pens_start_index + 1,
                "timestamp_feature_complete": next_["timestamp_pen_complete"],
                "price_feature_complete": next_["price_pen_complete"]
            }
        else:
            feature = {
                "timestamp": curr['top_time'] if curr['direction'] == "Up" else curr['bottom_time'],  # 当前笔的结束时间
                "open": curr['bottom_price'] if curr['direction'] == "Up" else curr['top_price'],  # 当前笔的开盘价
                "close": next_['top_price'] if next_['direction'] == "Up" else next_['bottom_price'],  # 下一笔的收盘价
                "high": next_['top_price'],  # 两笔的最高价
                "low": next_['bottom_price'],  # 两笔的最低价
                "index": i + partition_pens_start_index + 1
            }


        feature_sequence.append(feature)

    return feature_sequence

"""
# 这个函数还有bug，从第一笔开始画还是从第二笔开始画影响很大
def merge_pens_to_segments(pens):

    type_three_buy_sell = []

    feature_sequence = pd.DataFrame(generate_feature_sequence(pens, 0))
    standard_feature_sequence = handle_kline_inclusion_with_trend_for_feature_sequence(feature_sequence,
                                                                                       pens[0]['direction'], 0)

    # print("********************************")
    # print(f"第0笔方向是{pens[0]['direction']}")
    # print(f"特征序列长度是是{len(standard_feature_sequence)}")
    # print("第0笔低点")
    # print(standard_feature_sequence.iloc[0]['low'])
    # print("第1笔低点")
    # print(standard_feature_sequence.iloc[1]['low'])
    # print((pens[0]['direction'] == "Up" and (standard_feature_sequence.iloc[0]['low'] > standard_feature_sequence.iloc[1]['low'])))


    if len(standard_feature_sequence) > 1:
        if ((pens[0]['direction'] == "Down" and (standard_feature_sequence.iloc[0]['high'] < standard_feature_sequence.iloc[1]['high']))
            or (pens[0]['direction'] == "Up" and (standard_feature_sequence.iloc[0]['low'] > standard_feature_sequence.iloc[1]['low']))):
            partition_pens_start_index = 1
        else:
            partition_pens_start_index = 0
    else:
        partition_pens_start_index = 0
    # partition_pens_start_index = 0

    segments = []


    has_gap = False
    # print(f'len(pens) = {len(pens)}')
    while partition_pens_start_index < len(pens):
        # print("now looking for next segment")
        partition_pens = pens[partition_pens_start_index:]
        feature_sequence = pd.DataFrame(generate_feature_sequence(partition_pens, partition_pens_start_index))
        standard_feature_sequence = handle_kline_inclusion_with_trend_for_feature_sequence(feature_sequence, partition_pens[0]['direction'], partition_pens_start_index)
        # print([(standard_feature_sequence.iloc[i]['index'], standard_feature_sequence.iloc[i]['high']) for i in range(len(standard_feature_sequence))])
        # print(partition_pens[0]['direction'])
        # print(partition_pens_start_index)
        # print(standard_feature_sequence)
        if partition_pens[0]['direction']=="Up":
            direction = "Up"
            if len(standard_feature_sequence) < 3:
                break
            # 初始化线段
            segment = {
                "start": standard_feature_sequence.iloc[0],
                "end": None
            }
            # 遍历特征序列，寻找符合线段结束条件的位置
            # 向上的笔开始最初只关心顶分型，只有出现缺口才开始关注下一段的底分型
            # find_difenxing_if_gap这是一个修正项， 出现了gap会把它改false，gap后找到了底分会把他变回true
            find_difenxing_if_gap = True
            
            for i in range(1, len(standard_feature_sequence) - 1):
                prev = standard_feature_sequence.iloc[i - 1]
                curr = standard_feature_sequence.iloc[i]
                next_ = standard_feature_sequence.iloc[i + 1]
                # print(prev['index'], curr['index'], next_['index'])

                # 判断分型
                if direction == "Up":
                    # 顶分型：High - Low - High
                    if prev['high'] < curr['high'] > next_['high']:
                        # print(f"find ding after up at {curr['index']}")
                        # print(i+1)
                        # 判断是否存在缺口（没有重叠的区域）
                        has_gap = (prev['high'] < curr['low'])
                        if not has_gap:
                            # print(f"no gap 在向上笔后的顶分型, 在 笔 {curr['index']}")
                            # print("no gap")
                            segment["end"] = curr

                            segment_complete = {
                                "top_price": segment["end"]['high'],
                                "bottom_price": pens[partition_pens_start_index]["bottom_price"],
                                "top_time": segment["end"]['timestamp'],
                                "bottom_time": pens[partition_pens_start_index]["bottom_time"],
                                "top_index": segment["end"]['index'],
                                "bottom_index": partition_pens_start_index,
                                "direction": "Up",
                                "timestamp_segment_complete": next_["timestamp_feature_complete"],
                                "price_segment_complete": next_["price_feature_complete"]
                            }
                            
                            # 提取目标时间戳
                            # end_timestamp = segment["end"]["timestamp"]
                            # # 遍历 pens 查找对应的索引
                            # found_index = None
                            # for idx, pen in enumerate(pens):
                            #     # 检查 top_time 和 bottom_time 是否匹配
                            #     if pen["top_time"] == end_timestamp or pen["bottom_time"] == end_timestamp:
                            #         found_index = idx
                            #         break
                            found_index = segment["end"]["index"]
                            # print(found_index)
                            partition_pens_start_index = found_index
                            # print(f"next partition_pens_start_index start from {partition_pens_start_index}")
                            segments.append(segment_complete)
                            break
                        elif has_gap:
                            #特征序列的顶分型中，第一和第二元素间存在特征序列的缺口，如果从该分型最高点开始的向下一笔开始的序列的特征序列出现底分型，那么该线段在该顶分型的高点处结束，该高点是该线段的终点；
                            # 提取目标时间戳
                            segment["end"] = curr

                            #end_timestamp = segment["end"]["timestamp"]
                            # 遍历 pens 查找对应的索引
                            #found_index = None
                            #for idx, pen in enumerate(pens):
                            #    # 检查 top_time 和 bottom_time 是否匹配
                            #    if pen["top_time"] == end_timestamp or pen["bottom_time"] == end_timestamp:
                            #        found_index = idx
                            #        break
                            found_index = segment["end"]["index"]
                            # print(found_index)
                            partition_pens_start_index_after_gap = found_index
                            # partition_pens_start_index_after_gap = found_index + 1
                            partition_pens_after_gap = pens[partition_pens_start_index_after_gap:]
                            feature_sequence_after_gap = pd.DataFrame(generate_feature_sequence(partition_pens_after_gap, partition_pens_start_index_after_gap))
                            standard_feature_sequence_after_gap = handle_kline_inclusion_with_trend_for_feature_sequence(feature_sequence_after_gap, "Down", partition_pens_start_index_after_gap)

                            # if curr['index'] == 31:
                            #     print("缺口后找底分型")
                            #     print(standard_feature_sequence_after_gap)
                            find_difenxing_if_gap = False
                            #for j in range(1, len(standard_feature_sequence_after_gap) - 2):
                            for j in range(1, len(standard_feature_sequence_after_gap) - 1):
                                prev_after_gap = standard_feature_sequence_after_gap.iloc[j - 1]
                                curr_after_gap = standard_feature_sequence_after_gap.iloc[j]
                                next_after_gap = standard_feature_sequence_after_gap.iloc[j + 1]
                                #如果分型还未出现就创了新高，表示延续原来的线段
                                if curr_after_gap['high'] >= curr['high']:
                                    break
                                # 未出现新高再判断判断底分型
                                # 底分型：Low - High - Low
                                elif prev_after_gap['low'] > curr_after_gap['low'] < next_after_gap['low']:
                                    # if curr['index'] == 31:
                                    #     print("找到底分型")
                                    find_difenxing_if_gap = True
                                    break
                            if find_difenxing_if_gap:
                                segment["end"] = curr


                                segment_complete = {
                                    "top_price": segment["end"]['high'],
                                    "bottom_price": pens[partition_pens_start_index]["bottom_price"],
                                    "top_time": segment["end"]['timestamp'],
                                    "bottom_time": pens[partition_pens_start_index]["bottom_time"],
                                    "top_index": segment["end"]['index'],
                                    "bottom_index": partition_pens_start_index,
                                    "direction": "Up",
                                    "timestamp_segment_complete": next_after_gap["timestamp_feature_complete"],
                                    "price_segment_complete": next_after_gap["price_feature_complete"]
                                }
                                found_index = segment["end"]["index"]
                                partition_pens_start_index = found_index
                                #partition_pens_start_index = found_index + 1
                                segments.append(segment_complete)
                                break
                    # 前一个线段结束点被突破，回拉没有回到线段结束点，就去突破前再往前一段的底点结束
                    elif (segments and (curr['low'] <= segments[-1]['bottom_price'])):
                        if (next_['high'] <= segments[-1]['bottom_price']):
                            has_gap = False #如果前面出现gap，在这种情况下先不管了
                            # if curr['index'] < segments[-1]['bottom_index'] + 6: #考虑笔数较少，是合并入前一个线段：
                            #     segments[-1]["bottom_price"] = curr['low']
                            #     segments[-1]["bottom_time"] = curr['timestamp']
                            #     segments[-1]["bottom_index"] = curr['index']
                            #     found_index = curr['index']
                            #     partition_pens_start_index = found_index

                            # 可以考虑换一个路子试试代码，不是在第二个特征序列K线起点结束当前线段，而是在找底的时候就选前面几个特征序列最低点，找顶就找几个特征序列最高点

                            # print(f"线段{len(segments)} 是 比较复杂的线段， 我个人的处理方法是直接在第二个特征序列K线起点结束当前线段")
                            # print(f"这里近似是笔中枢的三类卖点，值得高度关注！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！")
                            segment["end"] = feature_sequence.iloc[1]


                            segment_complete = {
                                "top_price": segment["end"]['high'],
                                "bottom_price": pens[partition_pens_start_index]["bottom_price"],
                                "top_time": segment["end"]['timestamp'],
                                "bottom_time": pens[partition_pens_start_index]["bottom_time"],
                                "top_index": segment["end"]['index'],
                                "bottom_index": partition_pens_start_index,
                                "direction": "Up",
                                "timestamp_segment_complete": next_["timestamp_feature_complete"],
                                "price_segment_complete": next_["price_feature_complete"]
                            }
                            found_index = segment["end"]["index"]
                            partition_pens_start_index = found_index
                            segments.append(segment_complete)

                            type_three_buy_sell.append({"time": next_['timestamp'], "price": next_['high'], "buy_or_sell": "Sell"})

                            break
                            
          
                    
            
            if (segment["end"] is None) or (has_gap and (not find_difenxing_if_gap)):
                #if (segment["end"] is None):
                partition_pens_start_index = len(pens)
                #特征序列中未找到分形，未找到符合条件的第一段线段结束点
                break
            #else:
            #    partition_pens_start_index = partition_pens_start_index + 2
        elif partition_pens[0]['direction']=="Down":
            # print("looking for di when down")
            direction = "Down"
            if len(standard_feature_sequence) < 3:
                break
            # 初始化线段
            segment = {
                "start": standard_feature_sequence.iloc[0],
                "end": None
            }
            # 遍历特征序列，寻找符合线段结束条件的位置
            # 向下的笔开始最初只关心底分型，只有出现缺口才开始关注下一段的顶分型
            # find_dingfenxing_if_gap这是一个修正项， 出现了gap会把它改false，gap后找到了顶分会把他变回true
            find_dingfenxing_if_gap = True
            
            for i in range(1, len(standard_feature_sequence) - 1):
                prev = standard_feature_sequence.iloc[i - 1]
                curr = standard_feature_sequence.iloc[i]
                next_ = standard_feature_sequence.iloc[i + 1]
                # 判断分型
                if direction == "Down":

                    # 底分型：Low - High - Low
                    if prev['low'] > curr['low'] < next_['low']:

                        # 判断是否存在缺口（没有重叠的区域）
                        has_gap = (prev['low'] > curr['high'])
                        if not has_gap:
                            segment["end"] = curr


                            segment_complete = {
                                "top_price": pens[partition_pens_start_index]["top_price"],
                                "bottom_price": segment["end"]['low'],
                                "top_time": pens[partition_pens_start_index]["top_time"],
                                "bottom_time": segment["end"]['timestamp'],
                                "top_index": partition_pens_start_index,
                                "bottom_index":segment["end"]['index'],
                                "direction": "Down",
                                "timestamp_segment_complete": next_["timestamp_feature_complete"],
                                "price_segment_complete": next_["price_feature_complete"]
                            }

                            found_index = segment["end"]["index"]
                            # print(found_index)
                            partition_pens_start_index = found_index
                            
                            segments.append(segment_complete)
                            break
                        if has_gap:
                            #特征序列的顶分型中，第一和第二元素间存在特征序列的缺口，如果从该分型最高点开始的向下一笔开始的序列的特征序列出现底分型，那么该线段在该顶分型的高点处结束，该高点是该线段的终点；
                            # 提取目标时间戳
                            segment["end"] = curr
                            end_timestamp = segment["end"]["timestamp"]

                            found_index = segment["end"]["index"]
                            # print(found_index)
                            partition_pens_start_index_after_gap = found_index
                            
                            partition_pens_after_gap = pens[partition_pens_start_index_after_gap:]
                            feature_sequence_after_gap = pd.DataFrame(generate_feature_sequence(partition_pens_after_gap, partition_pens_start_index_after_gap))
                            standard_feature_sequence_after_gap = handle_kline_inclusion_with_trend_for_feature_sequence(feature_sequence_after_gap, "Up", partition_pens_start_index_after_gap)
                            
                            find_dingfenxing_if_gap = False
                            #for j in range(1, len(standard_feature_sequence_after_gap) - 2):
                            for j in range(1, len(standard_feature_sequence_after_gap) - 1):
                                prev_after_gap = standard_feature_sequence_after_gap.iloc[j - 1]
                                curr_after_gap = standard_feature_sequence_after_gap.iloc[j]
                                next_after_gap = standard_feature_sequence_after_gap.iloc[j + 1]
                                
                                #如果分型还未出现就创了新低，表示延续原来的线段
                                if curr_after_gap['low'] <= curr['low']:
                                    break
                                # 未出现新低再判断判断顶分型
                                # 顶分型：High - Low - High
                                if prev_after_gap['high'] < curr_after_gap['high'] > next_after_gap['high']:
                                    find_dingfenxing_if_gap = True
                                    break
                            if find_dingfenxing_if_gap:
                                segment["end"] = curr

                                segment_complete = {
                                    "top_price": pens[partition_pens_start_index]["top_price"],
                                    "bottom_price": segment["end"]['low'],
                                    "top_time": pens[partition_pens_start_index]["top_time"],
                                    "bottom_time": segment["end"]['timestamp'],
                                    "top_index": partition_pens_start_index,
                                    "bottom_index": segment["end"]['index'],
                                    "direction": "Down",
                                    "timestamp_segment_complete": next_after_gap["timestamp_feature_complete"],
                                    "price_segment_complete": next_after_gap["price_feature_complete"]
                                }

                                found_index = segment["end"]["index"]
                                partition_pens_start_index = found_index

                                
                                segments.append(segment_complete)
                                break
                    elif (segments and (curr['high'] >= segments[-1]['top_price'])):
                        if (next_['low'] >= segments[-1]['top_price']):
                            has_gap = False #如果前面出现gap，在这种情况下先不管了
                            # print(f"线段{len(segments)} 是 比较复杂的线段， 我个人的处理方法是直接在第二个特征序列K线起点结束当前线段")
                            # print(f"这里近似是笔的三类买点，值得高度关注！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！")
                            segment["end"] = feature_sequence.iloc[1]
                            segment_complete = {
                                "top_price": pens[partition_pens_start_index]["top_price"],
                                "bottom_price": segment["end"]['low'],
                                "top_time": pens[partition_pens_start_index]["top_time"],
                                "bottom_time": segment["end"]['timestamp'],
                                "top_index": partition_pens_start_index,
                                "bottom_index": segment["end"]['index'],
                                "direction": "Down",
                                "timestamp_segment_complete": next_["timestamp_feature_complete"],
                                "price_segment_complete": next_["price_feature_complete"]
                            }
                            found_index = segment["end"]["index"]
                            partition_pens_start_index = found_index
                            segments.append(segment_complete)

                            type_three_buy_sell.append({"time": next_['timestamp'], "price": next_['low'], "buy_or_sell": "Buy"})
                            break

                           
            
            if (segment["end"] is None) or (has_gap and (not find_dingfenxing_if_gap)):
                #if (segment["end"] is None):
                partition_pens_start_index = len(pens)
                #特征序列中未找到分形，未找到符合条件的第一段线段结束点
                break
            #else:
            #    partition_pens_start_index = partition_pens_start_index + 2
    #print(pd.DataFrame(segments))
    return segments, type_three_buy_sell
"""


# 这个函数还有bug，从第一笔开始画还是从第二笔开始画影响很大
def merge_pens_to_segments(pens, merge_segments_to_segments=False):
    type_three_buy_sell = []

    feature_sequence = pd.DataFrame(generate_feature_sequence(pens, 0, merge_segments_to_segments))
    standard_feature_sequence = handle_kline_inclusion_with_trend_for_feature_sequence(feature_sequence,
                                                                                       pens[0]['direction'], 0, merge_segments_to_segments)

    # print("********************************")
    # print(f"第0笔方向是{pens[0]['direction']}")
    # print(f"特征序列长度是是{len(standard_feature_sequence)}")
    # print("第0笔低点")
    # print(standard_feature_sequence.iloc[0]['low'])
    # print("第1笔低点")
    # print(standard_feature_sequence.iloc[1]['low'])
    # print((pens[0]['direction'] == "Up" and (standard_feature_sequence.iloc[0]['low'] > standard_feature_sequence.iloc[1]['low'])))

    if len(standard_feature_sequence) > 1:
        if ((pens[0]['direction'] == "Down" and (
                standard_feature_sequence.iloc[0]['high'] < standard_feature_sequence.iloc[1]['high']))
                or (pens[0]['direction'] == "Up" and (
                        standard_feature_sequence.iloc[0]['low'] > standard_feature_sequence.iloc[1]['low']))):
            partition_pens_start_index = 1
        else:
            partition_pens_start_index = 0
    else:
        partition_pens_start_index = 0
    # partition_pens_start_index = 0

    segments = []

    has_gap = False
    # print(f'len(pens) = {len(pens)}')
    while partition_pens_start_index < len(pens):
        # print("now looking for next segment")
        partition_pens = pens[partition_pens_start_index:]
        feature_sequence = pd.DataFrame(generate_feature_sequence(partition_pens, partition_pens_start_index, merge_segments_to_segments))
        standard_feature_sequence = handle_kline_inclusion_with_trend_for_feature_sequence(feature_sequence,
                                                                                           partition_pens[0][
                                                                                               'direction'],
                                                                                           partition_pens_start_index, merge_segments_to_segments)
        # print([(standard_feature_sequence.iloc[i]['index'], standard_feature_sequence.iloc[i]['high']) for i in range(len(standard_feature_sequence))])
        # print(partition_pens[0]['direction'])
        # print(partition_pens_start_index)
        # print(standard_feature_sequence)
        if partition_pens[0]['direction'] == "Up":
            direction = "Up"
            if len(standard_feature_sequence) < 3:
                break
            # 初始化线段
            segment = {
                "start": standard_feature_sequence.iloc[0],
                "end": None
            }
            # 遍历特征序列，寻找符合线段结束条件的位置
            # 向上的笔开始最初只关心顶分型，只有出现缺口才开始关注下一段的底分型
            # find_difenxing_if_gap这是一个修正项， 出现了gap会把它改false，gap后找到了底分会把他变回true
            find_difenxing_if_gap = True

            for i in range(1, len(standard_feature_sequence) - 1):
                prev = standard_feature_sequence.iloc[i - 1]
                curr = standard_feature_sequence.iloc[i]
                next_ = standard_feature_sequence.iloc[i + 1]
                # print(prev['index'], curr['index'], next_['index'])

                # 判断分型
                if direction == "Up":
                    # 顶分型：High - Low - High
                    if prev['high'] < curr['high'] > next_['high']:
                        # print(f"find ding after up at {curr['index']}")
                        # print(i+1)
                        # 判断是否存在缺口（没有重叠的区域）
                        has_gap = (prev['high'] < curr['low'])
                        if not has_gap:
                            # print(f"no gap 在向上笔后的顶分型, 在 笔 {curr['index']}")
                            # print("no gap")
                            segment["end"] = curr

                            segment_complete = {
                                "top_price": segment["end"]['high'],
                                "bottom_price": pens[partition_pens_start_index]["bottom_price"],
                                "top_time": segment["end"]['timestamp'],
                                "bottom_time": pens[partition_pens_start_index]["bottom_time"],
                                "top_index": segment["end"]['index'],
                                "bottom_index": partition_pens_start_index,
                                "direction": "Up",
                                # "timestamp_segment_complete": next_["timestamp_feature_complete"],
                                # "price_segment_complete": next_["price_feature_complete"],
                                "complex_fix": None
                            }
                            if not merge_segments_to_segments:
                                segment_complete.update({
                                    "timestamp_segment_complete": next_["timestamp_feature_complete"],
                                    "price_segment_complete": next_["price_feature_complete"]
                                })

                            # 提取目标时间戳
                            # end_timestamp = segment["end"]["timestamp"]
                            # # 遍历 pens 查找对应的索引
                            # found_index = None
                            # for idx, pen in enumerate(pens):
                            #     # 检查 top_time 和 bottom_time 是否匹配
                            #     if pen["top_time"] == end_timestamp or pen["bottom_time"] == end_timestamp:
                            #         found_index = idx
                            #         break
                            found_index = segment["end"]["index"]
                            # print(found_index)
                            partition_pens_start_index = found_index
                            # print(f"next partition_pens_start_index start from {partition_pens_start_index}")
                            segments.append(segment_complete)
                            break
                        elif has_gap:
                            # 特征序列的顶分型中，第一和第二元素间存在特征序列的缺口，如果从该分型最高点开始的向下一笔开始的序列的特征序列出现底分型，那么该线段在该顶分型的高点处结束，该高点是该线段的终点；
                            # 提取目标时间戳
                            segment["end"] = curr

                            # end_timestamp = segment["end"]["timestamp"]
                            # 遍历 pens 查找对应的索引
                            # found_index = None
                            # for idx, pen in enumerate(pens):
                            #    # 检查 top_time 和 bottom_time 是否匹配
                            #    if pen["top_time"] == end_timestamp or pen["bottom_time"] == end_timestamp:
                            #        found_index = idx
                            #        break
                            found_index = segment["end"]["index"]
                            # print(found_index)
                            partition_pens_start_index_after_gap = found_index
                            # partition_pens_start_index_after_gap = found_index + 1
                            partition_pens_after_gap = pens[partition_pens_start_index_after_gap:]
                            feature_sequence_after_gap = pd.DataFrame(
                                generate_feature_sequence(partition_pens_after_gap,
                                                          partition_pens_start_index_after_gap, merge_segments_to_segments))
                            standard_feature_sequence_after_gap = handle_kline_inclusion_with_trend_for_feature_sequence(
                                feature_sequence_after_gap, "Down", partition_pens_start_index_after_gap, merge_segments_to_segments)

                            # if curr['index'] == 31:
                            #     print("缺口后找底分型")
                            #     print(standard_feature_sequence_after_gap)
                            find_difenxing_if_gap = False
                            # for j in range(1, len(standard_feature_sequence_after_gap) - 2):
                            for j in range(1, len(standard_feature_sequence_after_gap) - 1):
                                prev_after_gap = standard_feature_sequence_after_gap.iloc[j - 1]
                                curr_after_gap = standard_feature_sequence_after_gap.iloc[j]
                                next_after_gap = standard_feature_sequence_after_gap.iloc[j + 1]
                                # 如果分型还未出现就创了新高，表示延续原来的线段
                                if curr_after_gap['high'] >= curr['high']:
                                    break
                                # 未出现新高再判断判断底分型
                                # 底分型：Low - High - Low
                                elif prev_after_gap['low'] > curr_after_gap['low'] < next_after_gap['low']:
                                    # if curr['index'] == 31:
                                    #     print("找到底分型")
                                    find_difenxing_if_gap = True
                                    break
                            if find_difenxing_if_gap:
                                segment["end"] = curr

                                segment_complete = {
                                    "top_price": segment["end"]['high'],
                                    "bottom_price": pens[partition_pens_start_index]["bottom_price"],
                                    "top_time": segment["end"]['timestamp'],
                                    "bottom_time": pens[partition_pens_start_index]["bottom_time"],
                                    "top_index": segment["end"]['index'],
                                    "bottom_index": partition_pens_start_index,
                                    "direction": "Up",
                                    # "timestamp_segment_complete": next_after_gap["timestamp_feature_complete"],
                                    # "price_segment_complete": next_after_gap["price_feature_complete"],
                                    "complex_fix": None
                                }
                                if not merge_segments_to_segments:
                                    segment_complete.update({
                                        "timestamp_segment_complete": next_after_gap["timestamp_feature_complete"],
                                        "price_segment_complete": next_after_gap["price_feature_complete"]
                                    })
                                found_index = segment["end"]["index"]
                                partition_pens_start_index = found_index
                                # partition_pens_start_index = found_index + 1
                                segments.append(segment_complete)
                                break
                    # 前一个线段结束点被突破，回拉没有回到线段结束点，就去突破前再往前一段的底点结束
                    elif (segments and (curr['low'] <= segments[-1]['bottom_price'])):
                        # if (next_['high'] <= segments[-1]['bottom_price']):
                        has_gap = False  # 如果前面出现gap，在这种情况下先不管了
                        # if curr['index'] < segments[-1]['bottom_index'] + 6: #考虑笔数较少，是合并入前一个线段：
                        #     segments[-1]["bottom_price"] = curr['low']
                        #     segments[-1]["bottom_time"] = curr['timestamp']
                        #     segments[-1]["bottom_index"] = curr['index']
                        #     found_index = curr['index']
                        #     partition_pens_start_index = found_index

                        # 可以考虑换一个路子试试代码，不是在第二个特征序列K线起点结束当前线段，而是在找底的时候就选前面几个特征序列最低点，找顶就找几个特征序列最高点

                        # print(f"线段{len(segments)} 是 比较复杂的线段， 我个人的处理方法是直接在第二个特征序列K线起点结束当前线段")
                        # print(f"这里近似是笔中枢的三类卖点，值得高度关注！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！")
                        segment["end"] = feature_sequence.iloc[1]

                        segment_complete = {
                            "top_price": segment["end"]['high'],
                            "bottom_price": pens[partition_pens_start_index]["bottom_price"],
                            "top_time": segment["end"]['timestamp'],
                            "bottom_time": pens[partition_pens_start_index]["bottom_time"],
                            "top_index": segment["end"]['index'],
                            "bottom_index": partition_pens_start_index,
                            "direction": "Up",
                            # "timestamp_segment_complete": next_["timestamp_feature_complete"],
                            # "price_segment_complete": next_["price_feature_complete"],
                            "complex_fix": "incomplete" #前面的线段无法被新线段破环需要延长,这个线段是临时的处理方法，它和它的下一段要合并进前一段
                        }
                        if not merge_segments_to_segments:
                            segment_complete.update({
                                "timestamp_segment_complete": next_["timestamp_feature_complete"],
                                "price_segment_complete": next_["price_feature_complete"]
                            })

                        found_index = segment["end"]["index"]
                        partition_pens_start_index = found_index
                        segments.append(segment_complete)

                        type_three_buy_sell.append(
                            {"time": next_['timestamp'], "price": next_['high'], "buy_or_sell": "Sell"})

                        break

            if (segment["end"] is None) or (has_gap and (not find_difenxing_if_gap)):
                # if (segment["end"] is None):
                partition_pens_start_index = len(pens)
                # 特征序列中未找到分形，未找到符合条件的第一段线段结束点
                break
            # else:
            #    partition_pens_start_index = partition_pens_start_index + 2
        elif partition_pens[0]['direction'] == "Down":
            # print("looking for di when down")
            direction = "Down"
            if len(standard_feature_sequence) < 3:
                break
            # 初始化线段
            segment = {
                "start": standard_feature_sequence.iloc[0],
                "end": None
            }
            # 遍历特征序列，寻找符合线段结束条件的位置
            # 向下的笔开始最初只关心底分型，只有出现缺口才开始关注下一段的顶分型
            # find_dingfenxing_if_gap这是一个修正项， 出现了gap会把它改false，gap后找到了顶分会把他变回true
            find_dingfenxing_if_gap = True

            for i in range(1, len(standard_feature_sequence) - 1):
                prev = standard_feature_sequence.iloc[i - 1]
                curr = standard_feature_sequence.iloc[i]
                next_ = standard_feature_sequence.iloc[i + 1]
                # 判断分型
                if direction == "Down":

                    # 底分型：Low - High - Low
                    if prev['low'] > curr['low'] < next_['low']:

                        # 判断是否存在缺口（没有重叠的区域）
                        has_gap = (prev['low'] > curr['high'])
                        if not has_gap:
                            segment["end"] = curr

                            segment_complete = {
                                "top_price": pens[partition_pens_start_index]["top_price"],
                                "bottom_price": segment["end"]['low'],
                                "top_time": pens[partition_pens_start_index]["top_time"],
                                "bottom_time": segment["end"]['timestamp'],
                                "top_index": partition_pens_start_index,
                                "bottom_index": segment["end"]['index'],
                                "direction": "Down",
                                # "timestamp_segment_complete": next_["timestamp_feature_complete"],
                                # "price_segment_complete": next_["price_feature_complete"],
                                "complex_fix": None
                            }
                            if not merge_segments_to_segments:
                                segment_complete.update({
                                    "timestamp_segment_complete": next_["timestamp_feature_complete"],
                                    "price_segment_complete": next_["price_feature_complete"],
                                })

                            found_index = segment["end"]["index"]
                            # print(found_index)
                            partition_pens_start_index = found_index

                            segments.append(segment_complete)
                            break
                        if has_gap:
                            # 特征序列的顶分型中，第一和第二元素间存在特征序列的缺口，如果从该分型最高点开始的向下一笔开始的序列的特征序列出现底分型，那么该线段在该顶分型的高点处结束，该高点是该线段的终点；
                            # 提取目标时间戳
                            segment["end"] = curr
                            end_timestamp = segment["end"]["timestamp"]

                            found_index = segment["end"]["index"]
                            # print(found_index)
                            partition_pens_start_index_after_gap = found_index

                            partition_pens_after_gap = pens[partition_pens_start_index_after_gap:]
                            feature_sequence_after_gap = pd.DataFrame(
                                generate_feature_sequence(partition_pens_after_gap,
                                                          partition_pens_start_index_after_gap, merge_segments_to_segments))
                            standard_feature_sequence_after_gap = handle_kline_inclusion_with_trend_for_feature_sequence(
                                feature_sequence_after_gap, "Up", partition_pens_start_index_after_gap, merge_segments_to_segments)

                            find_dingfenxing_if_gap = False
                            # for j in range(1, len(standard_feature_sequence_after_gap) - 2):
                            for j in range(1, len(standard_feature_sequence_after_gap) - 1):
                                prev_after_gap = standard_feature_sequence_after_gap.iloc[j - 1]
                                curr_after_gap = standard_feature_sequence_after_gap.iloc[j]
                                next_after_gap = standard_feature_sequence_after_gap.iloc[j + 1]

                                # 如果分型还未出现就创了新低，表示延续原来的线段
                                if curr_after_gap['low'] <= curr['low']:
                                    break
                                # 未出现新低再判断判断顶分型
                                # 顶分型：High - Low - High
                                if prev_after_gap['high'] < curr_after_gap['high'] > next_after_gap['high']:
                                    find_dingfenxing_if_gap = True
                                    break
                            if find_dingfenxing_if_gap:
                                segment["end"] = curr

                                if not merge_segments_to_segments:
                                    segment_complete = {
                                        "top_price": pens[partition_pens_start_index]["top_price"],
                                        "bottom_price": segment["end"]['low'],
                                        "top_time": pens[partition_pens_start_index]["top_time"],
                                        "bottom_time": segment["end"]['timestamp'],
                                        "top_index": partition_pens_start_index,
                                        "bottom_index": segment["end"]['index'],
                                        "direction": "Down",
                                        "timestamp_segment_complete": next_after_gap["timestamp_feature_complete"],
                                        "price_segment_complete": next_after_gap["price_feature_complete"],
                                        "complex_fix": None
                                    }
                                else:
                                    segment_complete = {
                                        "top_price": pens[partition_pens_start_index]["top_price"],
                                        "bottom_price": segment["end"]['low'],
                                        "top_time": pens[partition_pens_start_index]["top_time"],
                                        "bottom_time": segment["end"]['timestamp'],
                                        "top_index": partition_pens_start_index,
                                        "bottom_index": segment["end"]['index'],
                                        "direction": "Down",
                                        "complex_fix": None
                                    }

                                found_index = segment["end"]["index"]
                                partition_pens_start_index = found_index

                                segments.append(segment_complete)
                                break
                    elif (segments and (curr['high'] >= segments[-1]['top_price'])):
                        # if (next_['low'] >= segments[-1]['top_price']):
                        has_gap = False  # 如果前面出现gap，在这种情况下先不管了
                        # print(f"线段{len(segments)} 是 比较复杂的线段， 我个人的处理方法是直接在第二个特征序列K线起点结束当前线段")
                        # print(f"这里近似是笔的三类买点，值得高度关注！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！")
                        segment["end"] = feature_sequence.iloc[1]
                        if not merge_segments_to_segments:
                            segment_complete = {
                                "top_price": pens[partition_pens_start_index]["top_price"],
                                "bottom_price": segment["end"]['low'],
                                "top_time": pens[partition_pens_start_index]["top_time"],
                                "bottom_time": segment["end"]['timestamp'],
                                "top_index": partition_pens_start_index,
                                "bottom_index": segment["end"]['index'],
                                "direction": "Down",
                                "timestamp_segment_complete": next_["timestamp_feature_complete"],
                                "price_segment_complete": next_["price_feature_complete"],
                                "complex_fix": "incomplete" #前面的线段无法被新线段破环需要延长,这个线段是临时的处理方法，它和它的下一段要合并进前一段
                            }
                        else:
                            segment_complete = {
                                "top_price": pens[partition_pens_start_index]["top_price"],
                                "bottom_price": segment["end"]['low'],
                                "top_time": pens[partition_pens_start_index]["top_time"],
                                "bottom_time": segment["end"]['timestamp'],
                                "top_index": partition_pens_start_index,
                                "bottom_index": segment["end"]['index'],
                                "direction": "Down",
                                "complex_fix": "incomplete"  # 前面的线段无法被新线段破环需要延长,这个线段是临时的处理方法，它和它的下一段要合并进前一段
                            }
                        found_index = segment["end"]["index"]
                        partition_pens_start_index = found_index
                        segments.append(segment_complete)

                        type_three_buy_sell.append(
                            {"time": next_['timestamp'], "price": next_['low'], "buy_or_sell": "Buy"})
                        break

            if (segment["end"] is None) or (has_gap and (not find_dingfenxing_if_gap)):
                # if (segment["end"] is None):
                partition_pens_start_index = len(pens)
                # 特征序列中未找到分形，未找到符合条件的第一段线段结束点
                break
            # else:
            #    partition_pens_start_index = partition_pens_start_index + 2
    if any(segment["complex_fix"] == "incomplete" for segment in segments):
        new_segments = []
        i = 0
        while i < len(segments):
            if segments[i].get("complex_fix") == "incomplete":
                # If it's the first segment, add it to new_segments
                if i == 0:
                    new_segments.append(segments[i])
                    i = i + 1
                elif i == len(segments) - 1:
                    i = i + 1
                    # Remove the segment from the original list
                    break
                else:
                    # Merge with the previous segment if it's not the first one
                    # if segments[i+1] == "incomplete"
                    segment_complex_fix = {}
                    if new_segments[-1]["direction"] == "Down":
                        if new_segments[-1]["top_price"] > segments[i+1]["bottom_price"]:
                            if not merge_segments_to_segments:
                                segment_complex_fix = {
                                    "top_price": new_segments[-1]["top_price"],
                                    "bottom_price": segments[i+1]['bottom_price'],
                                    "top_time": new_segments[-1]["top_time"],
                                    "bottom_time": segments[i+1]['bottom_time'],
                                    "top_index": new_segments[-1]["top_index"],
                                    "bottom_index": segments[i+1]['bottom_index'],
                                    "direction": "Down",
                                    "timestamp_segment_complete": segments[i+1]["timestamp_segment_complete"],
                                    "price_segment_complete": segments[i+1]["price_segment_complete"],
                                    "complex_fix": segments[i+1]["complex_fix"]
                                }
                            else:
                                segment_complex_fix = {
                                    "top_price": new_segments[-1]["top_price"],
                                    "bottom_price": segments[i + 1]['bottom_price'],
                                    "top_time": new_segments[-1]["top_time"],
                                    "bottom_time": segments[i + 1]['bottom_time'],
                                    "top_index": new_segments[-1]["top_index"],
                                    "bottom_index": segments[i + 1]['bottom_index'],
                                    "direction": "Down",
                                    "complex_fix": segments[i + 1]["complex_fix"]
                                }
                            new_segments[-1].update(segment_complex_fix)
                            i = i + 2
                        else:
                            # segments[i]["complex_fix"] = None
                            new_segments.append(segments[i])
                            i = i + 1
                    elif new_segments[-1]["direction"] == "Up":
                        if new_segments[-1]["bottom_price"] < segments[i + 1]["top_price"]:
                            if not merge_segments_to_segments:
                                segment_complex_fix = {
                                    "top_price": segments[i+1]["top_price"],
                                    "bottom_price": new_segments[-1]['bottom_price'],
                                    "top_time": segments[i+1]["top_time"],
                                    "bottom_time": new_segments[-1]['bottom_time'],
                                    "top_index": segments[i+1]["top_index"],
                                    "bottom_index": new_segments[-1]['bottom_index'],
                                    "direction": "Up",
                                    "timestamp_segment_complete": segments[i+1]["timestamp_segment_complete"],
                                    "price_segment_complete": segments[i+1]["price_segment_complete"],
                                    "complex_fix": segments[i+1]["complex_fix"]
                                }
                            else:
                                segment_complex_fix = {
                                    "top_price": segments[i + 1]["top_price"],
                                    "bottom_price": new_segments[-1]['bottom_price'],
                                    "top_time": segments[i + 1]["top_time"],
                                    "bottom_time": new_segments[-1]['bottom_time'],
                                    "top_index": segments[i + 1]["top_index"],
                                    "bottom_index": new_segments[-1]['bottom_index'],
                                    "direction": "Up",
                                    "complex_fix": segments[i + 1]["complex_fix"]
                                }
                            new_segments[-1].update(segment_complex_fix)
                            i = i + 2
                        else:
                            # segments[i]["complex_fix"] = None
                            new_segments.append(segments[i])
                            i = i + 1
            else:
                # If the segment is complete, just append it to new_segments
                new_segments.append(segments[i])
                i = i + 1
        segments = new_segments

    # print(pd.DataFrame(segments))
    return segments, type_three_buy_sell





def merge_pens_to_segments_based_on_pen_zhongshu(pens, pen_zhongshus_clean, merge_segments_to_segments=False):
    type_three_buy_sell = []
    segments = []



    direction_before = pen_zhongshus_clean[0]["direction"]
    first_pen_this_qushi_index = pen_zhongshus_clean[0]["core_pens_index"][-1] - 1
    for idx_pen_zhongshu, pen_zhongshu in enumerate(pen_zhongshus_clean):
        if pen_zhongshu["direction"] != direction_before:
            last_pen_index = pen_zhongshus_clean[idx_pen_zhongshu-1]["core_pens_index"][-1] + 1

            # if not merge_segments_to_segments:
            #     segment_last_complete = {
            #         "top_price": pens[last_pen_index]["top_price"] if direction_before == "Up" else pens[first_pen_this_qushi_index]["top_price"],
            #         "bottom_price": pens[first_pen_this_qushi_index]["bottom_price"] if direction_before == "Up" else pens[last_pen_index]["bottom_price"],
            #         "top_time": pens[last_pen_index]["top_time"] if direction_before == "Up" else pens[first_pen_this_qushi_index]["top_time"],
            #         "bottom_time": pens[first_pen_this_qushi_index]["bottom_time"] if direction_before == "Up" else pens[last_pen_index]["bottom_time"],
            #         "top_index": last_pen_index if direction_before == "Up" else first_pen_this_qushi_index,
            #         "bottom_index": first_pen_this_qushi_index if direction_before == "Up" else last_pen_index,
            #         "direction": direction_before,
            #         "timestamp_segment_complete": pens[last_pen_index]["top_time"] if direction_before == "Up" else pens[last_pen_index]["bottom_time"],
            #         "price_segment_complete": pens[last_pen_index]["top_price"] if direction_before == "Up" else pens[last_pen_index]["bottom_price"],
            #         "complex_fix": "complete"
            #     }
            # else:
            #     segment_last_complete = {
            #         "top_price": pens[last_pen_index]["top_price"] if direction_before == "Up" else
            #         pens[first_pen_this_qushi_index]["top_price"],
            #         "bottom_price": pens[first_pen_this_qushi_index]["bottom_price"] if direction_before == "Up" else
            #         pens[last_pen_index]["bottom_price"],
            #         "top_time": pens[last_pen_index]["top_time"] if direction_before == "Up" else
            #         pens[first_pen_this_qushi_index]["top_time"],
            #         "bottom_time": pens[first_pen_this_qushi_index]["bottom_time"] if direction_before == "Up" else
            #         pens[last_pen_index]["bottom_time"],
            #         "top_index": last_pen_index if direction_before == "Up" else first_pen_this_qushi_index,
            #         "bottom_index": first_pen_this_qushi_index if direction_before == "Up" else last_pen_index,
            #         "direction": direction_before,
            #         "complex_fix": "complete"
            #     }
            segment_last_complete = {
                "top_price": pens[last_pen_index]["top_price"] if direction_before == "Up" else
                pens[first_pen_this_qushi_index]["top_price"],
                "bottom_price": pens[first_pen_this_qushi_index]["bottom_price"] if direction_before == "Up" else
                pens[last_pen_index]["bottom_price"],
                "top_time": pens[last_pen_index]["top_time"] if direction_before == "Up" else
                pens[first_pen_this_qushi_index]["top_time"],
                "bottom_time": pens[first_pen_this_qushi_index]["bottom_time"] if direction_before == "Up" else
                pens[last_pen_index]["bottom_time"],
                "top_index": last_pen_index if direction_before == "Up" else first_pen_this_qushi_index,
                "bottom_index": first_pen_this_qushi_index if direction_before == "Up" else last_pen_index,
                "direction": direction_before,
                "complex_fix": "complete"
            }
            # "timestamp_segment_complete" 和"price_segment_complete"错了，是笔三mai的时间，需要改

            segments.append(segment_last_complete)

            first_pen_this_qushi_index = last_pen_index + 1
            direction_before = pen_zhongshu["direction"]



    return segments, type_three_buy_sell


# 寻找笔中枢的函数
def find_zhongshu(pens, zgzd_type="classical"):
    """
    从缠论的笔中找出所有中枢，支持延伸和离开笔确认，允许两种 ZG/ZD 逻辑
    参数:
        pens: 包含每一笔信息的列表，每个元素是字典，包含:
              'top_price', 'bottom_price', 'top_time', 'bottom_time'
        zgzd_type: 中枢高低区间的计算逻辑：
                   "classical" - 确立 ZG/ZD 后不再更新
                   "practical" - ZG/ZD 随后续笔动态更新
    返回:
        zhongshus: 包含每个中枢的高点区间（ZG）、低点区间（ZD）、时间范围和构成的核心笔列表
    """
    zhongshus = []  # 存储所有中枢
    i = 0  # 从第一笔开始

    while i < len(pens) - 5:  # 至少需要 5 笔才能开始判断
        # 判断进入笔和离开笔方向是否一致
        first_pen = pens[i]
        second_pen = pens[i + 1]
        third_pen = pens[i + 2]
        fourth_pen = pens[i + 3]
        fifth_pen = pens[i + 4]

        # 判断进入笔和离开笔的方向是否一致
        # 初始化中枢的高低区间
        # zg = min(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
        # zd = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
        # zg = min(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
        # zd = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
        zg = min(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
        zd = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
        if (zg > zd) and (zg <= first_pen['top_price']) and (zd >= first_pen['bottom_price']):
                start_time = min(second_pen['top_time'], second_pen['bottom_time'])
                # end_time = max(fourth_pen['top_time'], fourth_pen['bottom_time'])
                # end_time = max(third_pen['top_time'], third_pen['bottom_time'])
                end_time = max(second_pen['top_time'], second_pen['bottom_time'])
                
                # core_pens = [second_pen, third_pen, fourth_pen]
                # core_pens = [second_pen, third_pen]
                core_pens = [second_pen]

                # 如果是 "classical"，初始 ZG/ZD 不更新
                classical_zg = zg
                classical_zd = zd
                
                
                #标记中枢有没有结束
                zhongshu_stop = False
                

                # 延伸中枢
                # j = i + 4
                # j = i + 3
                j = i + 2
                #for j in range(i + 4, len(pens) - 1):
                while j < len(pens) - 1: # 至少留一笔用于离开确认
                    next_pen = pens[j]
                    
                    next_next_pen = pens[j + 1]

                    if ((next_pen['direction'] == 'Down') and (next_pen['bottom_price'] < zd)) or ((next_pen['direction'] == 'Up') and (next_pen['top_price'] > zg)): # 暂时离开,
                        if (((next_pen['direction'] == 'Down') and (next_next_pen['top_price'] < zd)) or ((next_pen['direction'] == 'Up') and (next_next_pen['bottom_price'] > zg))):  # 确认离开, 延续前趋势
                            # i = j - 1  # 从离开笔重新开始判断， 要减一因为离开的最后一笔要视为中枢后的方向的第一笔
                            i = j
                            zhongshu_stop = True
                            break
                        elif (((next_pen['direction'] == 'Down') and (next_next_pen['top_price'] > zg)) or ((next_pen['direction'] == 'Up') and (next_next_pen['bottom_price'] < zd))) and (next_pen['direction'] == first_pen['direction']):  # 反向离开, 有可能开启新的走势，也可以是中枢扩张，单独画一个中枢便于分析
                            i = j
                            zhongshu_stop = True
                            break
                        else:
                            # 再次回到中枢，延续中枢
                            if zgzd_type == "practical":
                                zg = min(zg, next_pen['top_price'])
                                zd = max(zd, next_pen['bottom_price'])
                            end_time = max(next_pen['top_time'], next_pen['bottom_time'])
                            #end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                            core_pens.append(next_pen)
                            #core_pens.append(next_next_pen)
                            j += 1 ###这里可能要加二因为后面两笔都被考察过了是否适合写入中枢
                    else:
                        # 继续延伸
                        if zgzd_type == "practical":
                            zg = min(zg, next_pen['top_price'])
                            zd = max(zd, next_pen['bottom_price'])
                        end_time = max(next_pen['top_time'], next_pen['bottom_time'])
                        core_pens.append(next_pen)
                        j += 1
                # 如果遍历结束没有离开笔，停止
                if not zhongshu_stop:
                    i = len(pens)

                # 添加中枢
                if (len(core_pens) >= 3):
                    zhongshu = {
                        "ZG": classical_zg if zgzd_type == "classical" else zg,
                        "ZD": classical_zd if zgzd_type == "classical" else zd,
                        "start_time": start_time,
                        "end_time": end_time,
                        "core_pens": core_pens,
                        "GG": max([pen["top_price"] for pen in core_pens]),
                        "DD": min([pen["bottom_price"] for pen in core_pens])
                    }
                    zhongshus.append(zhongshu)
            #else:
            #    # 如果进入笔和离开笔方向不一致，或者第三笔突破原走势极值，跳过
            #    i += 1
        else:
            # 三段没有重合
            i += 1
    return zhongshus


# 寻找笔中枢的函数
def find_zhongshu_new(pens, zgzd_type="classical"):
    """
    从缠论的笔中找出所有中枢，支持延伸和离开笔确认，允许两种 ZG/ZD 逻辑
    参数:
        pens: 包含每一笔信息的列表，每个元素是字典，包含:
              'top_price', 'bottom_price', 'top_time', 'bottom_time'
        zgzd_type: 中枢高低区间的计算逻辑：
                   "classical" - 确立 ZG/ZD 后不再更新
                   "practical" - ZG/ZD 随后续笔动态更新
    返回:
        zhongshus: 包含每个中枢的高点区间（ZG）、低点区间（ZD）、时间范围和构成的核心笔列表
    """
    zhongshus = []  # 存储所有中枢
    i = 0  # 从第一笔开始
    zoushi_direction = pens[0]['direction'] #当前走势的方向，也就是中枢前一笔的方向

    while i < len(pens) - 5:  # 至少需要 5 笔才能开始判断
        # 判断进入笔和离开笔方向是否一致
        first_pen = pens[i]
        second_pen = pens[i + 1]
        third_pen = pens[i + 2]
        fourth_pen = pens[i + 3]
        fifth_pen = pens[i + 4]

        # 判断进入笔和离开笔的方向是否一致
        # 初始化中枢的高低区间
        # zg = min(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
        # zd = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
        # zg = min(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
        # zd = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
        GG = max(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
        DD = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
        zg = min(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
        zd = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
        #if ((zg > zd) and (zg <= first_pen['top_price']) and (zd >= first_pen['bottom_price']) and (zg <= fifth_pen['top_price']) and (zd >= fifth_pen['bottom_price'])):

        newhigh_or_newlow = True
        zhuanzhe = True
        if zhongshus:
            newhigh_or_newlow = False
            zhuanzhe = False
            # 延续前方向后，创新高或者破新低, 但可能中枢扩展
            if (zg > zd) and (first_pen['direction'] == zhongshus[-1]['direction']):
                newhigh_or_newlow = (((first_pen['top_price'] > zhongshus[-1]["GG"]) and (first_pen['direction'] == 'Up')) or ((first_pen['bottom_price'] < zhongshus[-1]["DD"])  and (first_pen['direction'] == 'Down')))
                # if ((first_pen['direction'] == 'Down') and GG >= zhongshus[-1]["ZD"]) or ((first_pen['direction'] == 'Up') and DD >= zhongshus[-1]["ZG"]): #中枢扩展
                #     print(f"第 {i} 笔中枢扩展")
                # else:
                #     print(f"第 {i} 笔新中枢")
            elif (zg > zd) and (zoushi_direction != first_pen['direction']): # 转折出现但可能中枢扩展
                if ((first_pen['direction'] == 'Down') and GG >= zhongshus[-1]["ZD"]) or ((first_pen['direction'] == 'Up') and DD >= zhongshus[-1]["ZG"]):
                    # 上一个的中枢扩展或转折
                    # 先当中枢扩展处理
                    zhuanzhe = False
                    # 如果是转折，以前面是以上涨为例，如果第四笔不创新高，那第一笔开头就是一卖，是转折，第四笔就是一卖
                else: #转折
                    zoushi_direction = first_pen['direction']
                    zhuanzhe = True
                    # print(f"第 {i} 笔转折出现")

        if (zg > zd) and (newhigh_or_newlow or zhuanzhe):
            start_time = min(second_pen['top_time'], second_pen['bottom_time'])
            end_time = max(fourth_pen['top_time'], fourth_pen['bottom_time'])
            # end_time = max(third_pen['top_time'], third_pen['bottom_time'])
            # end_time = max(second_pen['top_time'], second_pen['bottom_time'])

            core_pens = [second_pen, third_pen, fourth_pen]
            # core_pens = [second_pen, third_pen]
            # core_pens = [second_pen]

            # 如果是 "classical"，初始 ZG/ZD 不更新
            classical_zg = zg
            classical_zd = zd

            # 标记中枢有没有结束
            zhongshu_stop = False

            # 延伸中枢
            j = i + 4
            # j = i + 3
            # j = i + 2
            # for j in range(i + 4, len(pens) - 1):
            while j < len(pens) - 2:  # 至少留二笔用于离开确认
                next_pen = pens[j]

                next_next_pen = pens[j + 1]


                if ((zoushi_direction == 'Down') and (next_pen['bottom_price'] < zd)) or (
                        (zoushi_direction == 'Up') and (next_pen['top_price'] > zg)):  # 下一笔暂时离开, 延续前趋势
                    if (((zoushi_direction == 'Down') and (next_next_pen['top_price'] < zd)) or (
                            (zoushi_direction == 'Up') and (next_next_pen['bottom_price'] > zg))):  # 确认离开, 延续前趋势
                        # i = j - 1  # 从离开笔重新开始判断， 要减一因为离开的最后一笔要视为中枢后的方向的第一笔
                        i = j
                        zhongshu_stop = True
                        break
                    elif (((zoushi_direction == 'Down') and (next_next_pen['top_price'] > zg)) or (
                            (zoushi_direction == 'Up') and (next_next_pen['bottom_price'] < zd))) and (
                            next_pen['direction'] == zoushi_direction):  # 反向离开, 有可能开启新的走势，也可以是中枢扩张
                        # 再往后看一笔，如果回到前中枢，就是中枢延续，否则，是为转折
                        if ((next_pen['direction'] == 'Down') and (pens[j + 2]['bottom_price'] > zg)) or (
                                (next_pen['direction'] == 'Up') and (pens[j + 2]['top_price'] < zd)):  # 没有回到中枢，转折
                            i = j + 1
                            zhongshu_stop = True
                            break
                        else:
                            #print(f"zd is {zd}, \n zg is {zg}, \n next_next_pen bottom_price is {next_next_pen['bottom_price']} \n next_pen direction{next_pen['direction']}")

                            # 再次回到中枢，延续中枢
                            if zgzd_type == "practical":
                                zg = min(zg, next_pen['top_price'])
                                zd = max(zd, next_pen['bottom_price'])
                            GG = max(next_pen["top_price"], GG)
                            DD = min(next_pen["bottom_price"], DD)
                            end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                            # end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                            core_pens.append(next_pen)
                            core_pens.append(next_next_pen)
                            j += 2  ###这里可能要加二因为后面两笔都被考察过了是否适合写入中枢
                    else:
                        # 再次回到中枢，延续中枢
                        if zgzd_type == "practical":
                            zg = min(zg, next_pen['top_price'])
                            zd = max(zd, next_pen['bottom_price'])
                        GG = max(next_pen["top_price"], GG)
                        DD = min(next_pen["bottom_price"], DD)
                        end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                        # end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                        core_pens.append(next_pen)
                        core_pens.append(next_next_pen)
                        j += 2  ###这里可能要加二因为后面两笔都被考察过了是否适合写入中枢
                elif ((zoushi_direction == 'Down') and (next_next_pen['top_price'] > zg)) or (
                        (zoushi_direction == 'Up') and (
                        next_next_pen['bottom_price'] < zd)):  # 下一笔没有离开, 下下笔反向离开, 有可能开启新的走势，也可以是中枢扩张
                    # 再往后看一笔，如果回到前中枢，就是中枢延续，否则，是为转折
                    if ((next_pen['direction'] == 'Down') and (pens[j + 2]['bottom_price'] > zg)) or (
                            (next_pen['direction'] == 'Up') and (pens[j + 2]['top_price'] < zd)):  # 没有回到中枢，转折
                        i = j + 1
                        zhongshu_stop = True
                        break
                    else:
                        # 再次回到中枢，延续中枢
                        if zgzd_type == "practical":
                            zg = min(zg, next_pen['top_price'])
                            zd = max(zd, next_pen['bottom_price'])
                        GG = max(next_pen["top_price"], GG)
                        DD = min(next_pen["bottom_price"], DD)
                        end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                        # end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                        core_pens.append(next_pen)
                        core_pens.append(next_next_pen)
                        j += 2  ###这里可能要加二因为后面两笔都被考察过了是否适合写入中枢

                else:
                    # 继续延伸
                    if zgzd_type == "practical":
                        zg = min(zg, next_pen['top_price'])
                        zd = max(zd, next_pen['bottom_price'])
                    end_time = max(next_pen['top_time'], next_pen['bottom_time'])
                    core_pens.append(next_pen)
                    j += 1
            # 如果遍历结束没有离开笔，停止
            if not zhongshu_stop:
                i = len(pens)

            # 添加中枢
            if (len(core_pens) >= 3):
                zhongshu = {
                    "ZG": classical_zg if zgzd_type == "classical" else zg,
                    "ZD": classical_zd if zgzd_type == "classical" else zd,
                    "start_time": start_time,
                    "end_time": end_time,
                    "core_pens": core_pens,
                    "GG": max([pen["top_price"] for pen in core_pens]),
                    "DD": min([pen["bottom_price"] for pen in core_pens]),
                    "direction": first_pen['direction'],
                    "zhongshu_jieshu": zhongshu_stop
                }
                zhongshus.append(zhongshu)

        # else:
        #    # 如果进入笔和离开笔方向不一致，或者第三笔突破原走势极值，跳过
        #    i += 1
        else:
            # 三段没有重合
            i += 1
    return zhongshus






def find_zhongshu_one_pen_brute_another_try(pens, zgzd_type="classical"):
    zhongshus = []  # 存储所有中枢
    zhuanzhes = []
    i = 0  # 从第一笔开始
    while i < len(pens) - 3:  # 至少需要 5 笔才能开始判断
        # 判断进入笔和离开笔方向是否一致
        first_pen = pens[i]
        second_pen = pens[i + 1]
        third_pen = pens[i + 2]
        # GG = max(first_pen['top_price'], second_pen['top_price'], third_pen['top_price'])
        # DD = max(first_pen['bottom_price'], second_pen['bottom_price'], third_pen['bottom_price'])
        GG = second_pen['top_price']
        DD = second_pen['bottom_price']
        zg = min(first_pen['top_price'], second_pen['top_price'], third_pen['top_price'])
        zd = max(first_pen['bottom_price'], second_pen['bottom_price'], third_pen['bottom_price'])

        if (zg > zd):
            # start_time = min(first_pen['top_time'], third_pen['bottom_time'])
            # end_time = max(first_pen['top_time'], third_pen['bottom_time'])
            start_time = min(second_pen['top_time'], second_pen['bottom_time'])
            end_time = max(second_pen['top_time'], second_pen['bottom_time'])
            #画中枢为了清晰，不把进入段和离开段画进中枢，但需要记录
            core_pens = [first_pen, second_pen, third_pen]
            core_pens_index = [i, i+1, i+2]
            # 如果是 "classical"，初始 ZG/ZD 不更新
            classical_zg = zg
            classical_zd = zd

            zhongshu = {
                "ZG": classical_zg if zgzd_type == "classical" else zg,
                "ZD": classical_zd if zgzd_type == "classical" else zd,
                "start_time": start_time,
                "end_time": end_time,
                "core_pens": core_pens,
                "core_pens_index": core_pens_index,
                "GG": max([pen["top_price"] for pen in core_pens]),
                "DD": min([pen["bottom_price"] for pen in core_pens]),
                "direction": first_pen['direction'],
                "zhongshu_jieshu": False, #zhongshu_stop,
                "kuozhang": 0 #times_kuozhan  # 中枢扩张次数
            }

            zhongshus.append(zhongshu)


            j = i + 2
            while j + 2 < len(pens):
                j = j + 2
                cijibodong_pen_1 = pens[j - 1]
                cijibodong_pen_2 = pens[j]
                # 第一种情况：走势中枢以及其延伸: 所有围绕走势中枢产生的前后两个次级波动都必须至少有一个触及走势中枢的区间
                if ((cijibodong_pen_1['direction'] == 'Down') and (not (
                zhongshus["ZD"][-1] <= cijibodong_pen_1['bottom_price'] <= zhongshus[-1]["ZG"])) and not (
                        zhongshus["ZD"][-1] <= cijibodong_pen_2['top_price'] <= zhongshus[-1]["ZG"])) or (
                        (cijibodong_pen_1['direction'] == 'Up') and (not (
                zhongshus["ZD"][-1] <= cijibodong_pen_1['top_price'] <= zhongshus[-1]["ZG"])) and not (
                        zhongshus["ZD"][-1] <= cijibodong_pen_2['bottom_price'] <= zhongshus[-1]["ZG"])):
                    break
                else:
                    zhongshus[-1]["end_time"] = max(cijibodong_pen_2['top_time'], cijibodong_pen_2['bottom_time'])
                    zhongshus[-1]["core_pens"].append(cijibodong_pen_1)
                    zhongshus[-1]["core_pens"].append(cijibodong_pen_2)
                    zhongshus[-1]["core_pens_index"].append(j - 1)
                    zhongshus[-1]["core_pens_index"].append(j)
                    zhongshus[-1]["GG"] = max(zhongshus[-1]["GG"], cijibodong_pen_1['top_price'])
                    zhongshus[-1]["DD"] = min(zhongshus[-1]["DD"], cijibodong_pen_1['bottom_price'])

        i = j
    return zhongshus, zhuanzhes


def find_zhongshu_one_pen_brute(pens, zgzd_type="classical"):
    zhongshus = []  # 存储所有中枢
    zhuanzhes = []
    i = 0  # 从第一笔开始
    while i <= len(pens) - 3:  # 至少需要 5 笔才能开始判断
        # 判断进入笔和离开笔方向是否一致
        first_pen = pens[i]
        second_pen = pens[i + 1]
        third_pen = pens[i + 2]
        # GG = max(first_pen['top_price'], second_pen['top_price'], third_pen['top_price'])
        # DD = max(first_pen['bottom_price'], second_pen['bottom_price'], third_pen['bottom_price'])
        GG = second_pen['top_price']
        DD = second_pen['bottom_price']
        zg = min(first_pen['top_price'], second_pen['top_price'], third_pen['top_price'])
        zd = max(first_pen['bottom_price'], second_pen['bottom_price'], third_pen['bottom_price'])

        if (zg > zd):
            start_time = min(second_pen['top_time'], second_pen['bottom_time'])
            end_time = max(second_pen['top_time'], second_pen['bottom_time'])
            core_pens = [second_pen]
            core_pens_index = [i+1]
            # 如果是 "classical"，初始 ZG/ZD 不更新
            classical_zg = zg
            classical_zd = zd

            zhongshu = {
                "ZG": classical_zg if zgzd_type == "classical" else zg,
                "ZD": classical_zd if zgzd_type == "classical" else zd,
                "start_time": start_time,
                "end_time": end_time,
                "core_pens": core_pens,
                "core_pens_index": core_pens_index,
                "GG": max([pen["top_price"] for pen in core_pens]),
                "DD": min([pen["bottom_price"] for pen in core_pens]),
                "direction": first_pen['direction'],
                "zhongshu_jieshu": False, #zhongshu_stop,
                "kuozhang": 0 #times_kuozhan  # 中枢扩张次数
            }

            zhongshus.append(zhongshu)


        i += 1
    return zhongshus, zhuanzhes

def find_zhongshu_one_pen_form(pens, zgzd_type="classical"):
    zhongshus_one_pen, _ = find_zhongshu_one_pen_brute(pens, zgzd_type="classical")
    zhuanzhes = []
    if len(zhongshus_one_pen) <= 0:
        return [], zhuanzhes
    zhongshus = [zhongshus_one_pen[0]]
    for zhongshu_one_pen in zhongshus_one_pen:
        #if zhongshu_one_pen["core_pens_index"][0] == zhongshus[-1]["core_pens_index"][-1] + 1:
        if max(zhongshu_one_pen['DD'], zhongshus[-1]["ZD"]) < min(zhongshu_one_pen['GG'], zhongshus[-1]["ZG"]):
            zhongshus[-1]["end_time"] = zhongshu_one_pen["end_time"]
            zhongshus[-1]["core_pens"].append(zhongshu_one_pen['core_pens'][0])
            zhongshus[-1]["core_pens_index"].append(zhongshu_one_pen["core_pens_index"][0])
            zhongshus[-1]["GG"] = max(zhongshus[-1]["GG"], zhongshu_one_pen["GG"])
            zhongshus[-1]["DD"] = min(zhongshus[-1]["DD"], zhongshu_one_pen["DD"])
            #zhongshus[-1]["direction"] = zhongshus[-1]["direction"]
            zhongshus[-1]["zhongshu_jieshu"] = True
            zhongshus[-1]["kuozhang"] = 0
        else:
            zhongshus.append(zhongshu_one_pen)


    # # 处理中枢扩展
    # zhongshus_kuozhang = [zhongshus[0]]
    # for zhongshu_index in range(1, len(zhongshus)):
    #     if (zhongshus_kuozhang[-1]["ZD"] < zhongshus[zhongshu_index]["GG"] < zhongshus_kuozhang[-1]["ZG"])  or (
    #             zhongshus_kuozhang[-1]["ZD"] < zhongshus[zhongshu_index]["DD"] < zhongshus_kuozhang[-1]["ZG"]):
    #         zhongshus_kuozhang[-1]["end_time"] = zhongshus[zhongshu_index]["end_time"]
    #
    #         # print(f"""zhongshu1 {zhongshus_kuozhang[-1]["core_pens_index"]}""")
    #         # print(f"""zhongshu2 {zhongshus[zhongshu_index]["core_pens_index"]}""")
    #         # print(
    #         #     f"""{[middle_index_in_kuozhang for middle_index_in_kuozhang in range(zhongshus_kuozhang[-1]["core_pens_index"][-1] + 1, zhongshus[zhongshu_index]["core_pens_index"][0])]}""")
    #
    #         zhongshus_kuozhang[-1]["core_pens"].extend([pens[middle_index_in_kuozhang] for middle_index_in_kuozhang in range(zhongshus_kuozhang[-1]["core_pens_index"][-1]+1, zhongshus[zhongshu_index]["core_pens_index"][0])])
    #         zhongshus_kuozhang[-1]["core_pens"].extend(zhongshus[zhongshu_index]["core_pens"])
    #         zhongshus_kuozhang[-1]["core_pens_index"].extend([middle_index_in_kuozhang for middle_index_in_kuozhang in range(zhongshus_kuozhang[-1]["core_pens_index"][-1]+1, zhongshus[zhongshu_index]["core_pens_index"][0])])
    #         zhongshus_kuozhang[-1]["core_pens_index"].extend(zhongshus[zhongshu_index]["core_pens_index"])
    #
    #         zhongshus_kuozhang[-1]["GG"] = max(zhongshus_kuozhang[-1]["GG"], zhongshus[zhongshu_index]["GG"])
    #         zhongshus_kuozhang[-1]["DD"] = min(zhongshus_kuozhang[-1]["DD"], zhongshus[zhongshu_index]["DD"])
    #
    #         zhongshus_kuozhang[-1]["zhongshu_jieshu"] = True
    #         zhongshus_kuozhang[-1]["kuozhang"] += 1
    #         # print(zhongshus_kuozhang[-1]["core_pens_index"])
    #
    #     else:
    #         zhongshus_kuozhang.append(zhongshus[zhongshu_index])

    # return zhongshus_kuozhang, zhuanzhes


    return zhongshus, zhuanzhes



def zhongshu_continue_fix(zhongshus, segments):
    new_zhongshus = []
    for zhongshu in zhongshus:
        expected = list(range(min(zhongshu["core_pens_index"]), max(zhongshu["core_pens_index"]) + 1))
        missing = sorted(set(expected) - set(zhongshu["core_pens_index"]))
        for num in missing:
            # 找到 num - 1 的索引，然后插入其后
            if (num - 1) in zhongshu["core_pens_index"]:
                idx = zhongshu["core_pens_index"].index(num - 1)
                zhongshu["core_pens_index"].insert(idx + 1, num)
                pen_add_fix = {
                    "top_price": segments[num+1]["top_price"] if segments[num-1]["direction"] == "Down" else segments[num-1]["top_price"],
                    "bottom_price": segments[num-1]["bottom_price"] if segments[num-1]["direction"] == "Down" else segments[num+1]["bottom_price"],
                    "top_time": segments[num+1]["top_time"] if segments[num-1]["direction"] == "Down" else segments[num-1]["top_time"],
                    "bottom_time": segments[num-1]["bottom_time"] if segments[num-1]["direction"] == "Down" else segments[num+1]["bottom_time"],
                    "top_index": segments[num+1]["top_index"]-1 if segments[num-1]["direction"] == "Down" else segments[num-1]["top_index"]+1,
                    "bottom_index": segments[num-1]["bottom_index"]+1 if segments[num-1]["direction"] == "Down" else segments[num+1]["bottom_index"]-1,
                    "direction": "Up" if segments[num-1]["direction"] == "Down" else "Down",
                    "timestamp_segment_complete": segments[num+1]["top_time"] if segments[num-1]["direction"] == "Down" else segments[num+1]["bottom_time"],
                    "price_segment_complete": segments[num+1]["top_price"] if segments[num-1]["direction"] == "Down" else segments[num+1]["bottom_price"],
                    "complex_fix": "complete"
                }
                zhongshu["core_pens"].insert(idx + 1, pen_add_fix)
                # print(zhongshu["core_pens_index"], idx, len(expected))
                # if idx+2 == len(expected):
                #     print(zhongshu["core_pens_index"])
                #     zhongshu["core_pens"] = zhongshu["core_pens"][: -1]
                #     zhongshu["core_pens_index"] = zhongshu["core_pens_index"][: -1]

        new_zhongshus.append(zhongshu)
    return new_zhongshus



# """
#将包含了一类买点的中枢切开，将中枢的离开段划分到中枢以外
def clean_zhongshu_detailed(zhongshus, segments, zgzd_type="classical"):
    # zhongshu = {
    #     "ZG": classical_zg if zgzd_type == "classical" else zg,
    #     "ZD": classical_zd if zgzd_type == "classical" else zd,
    #     "start_time": start_time,
    #     "end_time": end_time,
    #     "core_pens": core_pens,
    #     "core_pens_index": core_pens_index,
    #     "GG": max([pen["top_price"] for pen in core_pens]),
    #     "DD": min([pen["bottom_price"] for pen in core_pens]),
    #     "direction": first_pen['direction'],
    #     "zhongshu_jieshu": False,  # zhongshu_stop,
    #     "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
    # }
    zhuanzhes = []


    sanmai_info = ""
    if len(zhongshus) <= 0 or len(segments) <= 0:
        return [], zhuanzhes, sanmai_info


    # 如果最后一个线段没有画成中枢的一部分，并且高低点不触及最后一个中枢，就把这个线段单独当一个中枢画出了，这往往是三买三卖
    if len(segments) - 1 > zhongshus[-1]["core_pens_index"][-1]:
        next_seg_index = zhongshus[-1]["core_pens_index"][-1] + 1
        if (segments[next_seg_index]["direction"] == "Up") and (segments[next_seg_index]["bottom_price"] <= segments[next_seg_index]["top_price"] <= zhongshus[-1]["ZD"]):
            # 可能是向下的三卖
            sanmai_info = "short"
            zhongshu_last_temp_new = {
                "ZG": segments[next_seg_index]["top_price"],
                "ZD": segments[next_seg_index]["bottom_price"],
                "start_time": segments[next_seg_index]["bottom_time"],
                "end_time": segments[next_seg_index]["top_time"],
                "core_pens": [segments[next_seg_index]],
                "core_pens_index": [len(segments) - 1],
                "GG": segments[next_seg_index]["top_price"],
                "DD": segments[next_seg_index]["bottom_price"],
                "direction": "Down",
                "zhongshu_jieshu": False,  # zhongshu_stop,
                "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
            }
            zhongshus_rough = zhongshus + [zhongshu_last_temp_new]
        elif (segments[next_seg_index]["direction"] == "Down") and (segments[next_seg_index]["top_price"] >= segments[next_seg_index]["bottom_price"] >= zhongshus[-1]["ZG"]):
            # 可能是向上的三买
            sanmai_info = "long"
            zhongshu_last_temp_new = {
                "ZG": segments[next_seg_index]["top_price"],
                "ZD": segments[next_seg_index]["bottom_price"],
                "start_time": segments[next_seg_index]["top_time"],
                "end_time": segments[next_seg_index]["bottom_time"],
                "core_pens": [segments[next_seg_index]],
                "core_pens_index": [len(segments) - 1],
                "GG": segments[next_seg_index]["top_price"],
                "DD": segments[next_seg_index]["bottom_price"],
                "direction": "Up",
                "zhongshu_jieshu": False,  # zhongshu_stop,
                "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
            }
            zhongshus_rough = zhongshus + [zhongshu_last_temp_new]
        else:
            zhongshus_rough = zhongshus
    else:
        zhongshus_rough = zhongshus


    clean_zhongshus = []
    i = 0
    while i < len(zhongshus_rough):
        if 0 < i < len(zhongshus_rough) - 1:
            if (zhongshus_rough[i-1]["ZD"] < zhongshus_rough[i]["ZD"] > zhongshus_rough[i+1]["ZD"]): #包含一卖
                max_pen_index = max(
                    enumerate(zhongshus_rough[i]["core_pens"]),
                    key=lambda x: x[1]['top_price']
                )[0]
                if max_pen_index == 0 and zhongshus_rough[i]["core_pens"][max_pen_index]["direction"] == "Up":
                    # 第一段和第二段之间是一卖
                    if len(zhongshus_rough[i]["core_pens_index"]) >= 3:
                        # print([zhongshu['direction'] for zhongshu in zhongshus_rough[i]["core_pens"]])
                        last_index_should_include = True if zhongshus_rough[i]["core_pens"][-1]['direction'] == "Up" else False
                        zhongshu_1 = {
                            "ZG": None, # zhongshus_rough[i]["core_pens"][2]["top_price"], # zhongshus_rough[i]["ZG"],
                            "ZD": None, # max(zhongshus_rough[i]["core_pens"][2]["bottom_price"], zhongshus_rough[i]["core_pens"][3]["bottom_price"]) if len(zhongshus_rough[i]["core_pens"]) >=4 else zhongshus_rough[i]["core_pens"][2]["bottom_price"], # zhongshus_rough[i]["ZD"],
                            "start_time": zhongshus_rough[i]["core_pens"][2]["bottom_time"],
                            "end_time": zhongshus_rough[i]["core_pens"][-1]["top_time"] if last_index_should_include else zhongshus_rough[i]["core_pens"][-2]["top_time"],
                            "core_pens": zhongshus_rough[i]["core_pens"][2:] if last_index_should_include else zhongshus_rough[i]["core_pens"][2:-1],
                            "core_pens_index": zhongshus_rough[i]["core_pens_index"][2:] if last_index_should_include else zhongshus_rough[i]["core_pens_index"][2:-1],
                            "GG": None,
                            "DD": None,
                            "direction": "Down",
                            "zhongshu_jieshu": False,  # zhongshu_stop,
                            "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
                        }
                        if zgzd_type == "classical":
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else min(
                                [pen["top_price"] for pen in zhongshu_1["core_pens"][:2]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else max(
                                [pen["bottom_price"] for pen in zhongshu_1["core_pens"][:2]])
                        else:
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["GG"] = max([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["DD"] = min([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        clean_zhongshus.append(zhongshu_1)
                elif max_pen_index == 0 and zhongshus_rough[i]["core_pens"][max_pen_index]["direction"] == "Down":
                    # 第一段开始就是是一卖
                    if len(zhongshus_rough[i]["core_pens_index"]) >= 2:
                        last_index_should_include = True if zhongshus_rough[i]["core_pens"][-1][
                                                                'direction'] == "Up" else False
                        zhongshu_1 = {
                            "ZG": None, # zhongshus_rough[i]["core_pens"][1]["top_price"],  # zhongshus_rough[i]["ZG"],
                            "ZD": None, # max(zhongshus_rough[i]["core_pens"][1]["bottom_price"], zhongshus_rough[i]["core_pens"][2]["bottom_price"]) if len(zhongshus_rough[i]["core_pens"]) >= 3 else zhongshus_rough[i]["core_pens"][1]["bottom_price"],  # zhongshus_rough[i]["ZD"],
                            "start_time": zhongshus_rough[i]["core_pens"][1]["bottom_time"],
                            "end_time": zhongshus_rough[i]["core_pens"][-1][
                                "top_time"] if last_index_should_include else zhongshus_rough[i]["core_pens"][-2][
                                "top_time"],
                            "core_pens": zhongshus_rough[i]["core_pens"][1:] if last_index_should_include else
                            zhongshus_rough[i]["core_pens"][1:-1],
                            "core_pens_index": zhongshus_rough[i]["core_pens_index"][
                                               1:] if last_index_should_include else zhongshus_rough[i][
                                                                                         "core_pens_index"][1:-1],
                            "GG": None,
                            "DD": None,
                            "direction": "Down",
                            "zhongshu_jieshu": False,  # zhongshu_stop,
                            "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
                        }
                        if zgzd_type == "classical":
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else min(
                                [pen["top_price"] for pen in zhongshu_1["core_pens"][:2]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else max(
                                [pen["bottom_price"] for pen in zhongshu_1["core_pens"][:2]])
                        else:
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["GG"] = max([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["DD"] = min([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        clean_zhongshus.append(zhongshu_1)
                elif max_pen_index == len(zhongshus_rough[i]["core_pens"]) - 1:# and zhongshus_rough[i]["core_pens"][max_pen_index]["direction"] == "Up":
                    # 最后一段结束是一卖
                    if len(zhongshus_rough[i]["core_pens_index"]) >= 2:
                        first_index_should_include = True if zhongshus_rough[i]["core_pens"][0][
                                                                'direction'] == "Down" else False
                        zhongshu_1 = {
                            "ZG": None,
                            "ZD": None,
                            "start_time": zhongshus_rough[i]["core_pens"][0][
                                "top_time"] if first_index_should_include else zhongshus_rough[i]["core_pens"][1][
                                "top_time"],
                            "end_time": zhongshus_rough[i]["core_pens"][max_pen_index-1]["bottom_time"],
                            "core_pens": zhongshus_rough[i]["core_pens"][0:max_pen_index] if first_index_should_include else
                            zhongshus_rough[i]["core_pens"][1:max_pen_index],
                            "core_pens_index": zhongshus_rough[i]["core_pens_index"][
                                               0:max_pen_index] if first_index_should_include else zhongshus_rough[i][
                                                                                         "core_pens_index"][1:max_pen_index],
                            "GG": None,
                            "DD": None,
                            "direction": "Up",
                            "zhongshu_jieshu": False,  # zhongshu_stop,
                            "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
                        }
                        if zgzd_type == "classical":
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else min(
                                [pen["top_price"] for pen in zhongshu_1["core_pens"][:2]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else max(
                                [pen["bottom_price"] for pen in zhongshu_1["core_pens"][:2]])
                        else:
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["GG"] = max([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["DD"] = min([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        clean_zhongshus.append(zhongshu_1)
                elif max_pen_index == len(zhongshus_rough[i]["core_pens"]) - 2:# and zhongshus_rough[i]["core_pens"][max_pen_index]["direction"] == "Up":
                    # 最后一段和倒数第二段之间是一卖
                    if len(zhongshus_rough[i]["core_pens_index"]) >= 3:
                        first_index_should_include = True if zhongshus_rough[i]["core_pens"][0][
                                                                 'direction'] == "Down" else False
                        zhongshu_1 = {
                            "ZG": None,
                            "ZD": None,
                            "start_time": zhongshus_rough[i]["core_pens"][0][
                                "top_time"] if first_index_should_include else zhongshus_rough[i]["core_pens"][1][
                                "top_time"],
                            "end_time": zhongshus_rough[i]["core_pens"][max_pen_index-1]["bottom_time"],
                            "core_pens": zhongshus_rough[i]["core_pens"][0:max_pen_index] if first_index_should_include else
                            zhongshus_rough[i]["core_pens"][1:max_pen_index],
                            "core_pens_index": zhongshus_rough[i]["core_pens_index"][
                                               0:max_pen_index] if first_index_should_include else zhongshus_rough[i][
                                                                                            "core_pens_index"][1:max_pen_index],
                            "GG": None,
                            "DD": None,
                            "direction": "Up",
                            "zhongshu_jieshu": False,  # zhongshu_stop,
                            "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
                        }
                        if zgzd_type == "classical":
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else min(
                                [pen["top_price"] for pen in zhongshu_1["core_pens"][:2]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else max(
                                [pen["bottom_price"] for pen in zhongshu_1["core_pens"][:2]])
                        else:
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["GG"] = max([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["DD"] = min([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        clean_zhongshus.append(zhongshu_1)
                else:
                    # max_pen_index把中枢分成左右两边
                    first_index_should_include = True if zhongshus_rough[i]["core_pens"][0][
                                                             'direction'] == "Down" else False
                    last_index_should_include = True if zhongshus_rough[i]["core_pens"][-1][
                                                            'direction'] == "Up" else False
                    zhongshu_1 = {
                        "ZG": None,
                        "ZD": None,
                        "start_time": zhongshus_rough[i]["core_pens"][0][
                            "top_time"] if first_index_should_include else zhongshus_rough[i]["core_pens"][1][
                            "top_time"],
                        "end_time": zhongshus_rough[i]["core_pens"][max_pen_index-1]["bottom_time"],
                        "core_pens": zhongshus_rough[i]["core_pens"][0:max_pen_index] if first_index_should_include else
                        zhongshus_rough[i]["core_pens"][1:max_pen_index],
                        "core_pens_index": zhongshus_rough[i]["core_pens_index"][
                                           0:max_pen_index] if first_index_should_include else zhongshus_rough[i][
                                                                                        "core_pens_index"][1:max_pen_index],
                        "GG": None,
                        "DD": None,
                        "direction": "Up",
                        "zhongshu_jieshu": False,  # zhongshu_stop,
                        "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
                    }
                    if zgzd_type == "classical":
                        zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]]) if len(
                            zhongshu_1["core_pens"]) < 2 else min(
                            [pen["top_price"] for pen in zhongshu_1["core_pens"][:2]])
                        zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]]) if len(
                            zhongshu_1["core_pens"]) < 2 else max(
                            [pen["bottom_price"] for pen in zhongshu_1["core_pens"][:2]])
                    else:
                        zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                    zhongshu_1["GG"] = max([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                    zhongshu_1["DD"] = min([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])

                    zhongshu_2 = {
                        "ZG": None,  # zhongshus_rough[i]["core_pens"][2]["top_price"], # zhongshus_rough[i]["ZG"],
                        "ZD": None,
                        # max(zhongshus_rough[i]["core_pens"][2]["bottom_price"], zhongshus_rough[i]["core_pens"][3]["bottom_price"]) if len(zhongshus_rough[i]["core_pens"]) >=4 else zhongshus_rough[i]["core_pens"][2]["bottom_price"], # zhongshus_rough[i]["ZD"],
                        "start_time": zhongshus_rough[i]["core_pens"][max_pen_index+1]["bottom_time"],
                        "end_time": zhongshus_rough[i]["core_pens"][-1]["top_time"] if last_index_should_include else
                        zhongshus_rough[i]["core_pens"][-2]["top_time"],
                        "core_pens": zhongshus_rough[i]["core_pens"][max_pen_index+1:] if last_index_should_include else
                        zhongshus_rough[i]["core_pens"][max_pen_index+1:-1],
                        "core_pens_index": zhongshus_rough[i]["core_pens_index"][max_pen_index+1:] if last_index_should_include else
                        zhongshus_rough[i]["core_pens_index"][max_pen_index+1:-1],
                        "GG": None,
                        "DD": None,
                        "direction": "Down",
                        "zhongshu_jieshu": False,  # zhongshu_stop,
                        "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
                    }
                    if zgzd_type == "classical":
                        zhongshu_2["ZG"] = min([pen["top_price"] for pen in zhongshu_2["core_pens"]]) if len(
                            zhongshu_2["core_pens"]) < 2 else min(
                            [pen["top_price"] for pen in zhongshu_2["core_pens"][:2]])
                        zhongshu_2["ZD"] = max([pen["bottom_price"] for pen in zhongshu_2["core_pens"]]) if len(
                            zhongshu_2["core_pens"]) < 2 else max(
                            [pen["bottom_price"] for pen in zhongshu_2["core_pens"][:2]])
                    else:
                        zhongshu_2["ZG"] = min([pen["top_price"] for pen in zhongshu_2["core_pens"]])
                        zhongshu_2["ZD"] = max([pen["bottom_price"] for pen in zhongshu_2["core_pens"]])
                    zhongshu_2["GG"] = max([pen["top_price"] for pen in zhongshu_2["core_pens"]])
                    zhongshu_2["DD"] = min([pen["bottom_price"] for pen in zhongshu_2["core_pens"]])

                    clean_zhongshus.append(zhongshu_1)
                    clean_zhongshus.append(zhongshu_2)


            elif (zhongshus_rough[i-1]["ZD"] > zhongshus_rough[i]["ZD"] < zhongshus_rough[i+1]["ZD"]): #包含一买
                min_pen_index = min(
                    enumerate(zhongshus_rough[i]["core_pens"]),
                    key=lambda x: x[1]['bottom_price']
                )[0]
                if min_pen_index == 0 and zhongshus_rough[i]["core_pens"][min_pen_index]["direction"] == "Down":
                    # 第一段和第二段之间是一买
                    if len(zhongshus_rough[i]["core_pens_index"]) >= 3:
                        last_index_should_include = True if zhongshus_rough[i]["core_pens"][-1]['direction'] == "Down" else False
                        zhongshu_1 = {
                            "ZG": None, # zhongshus_rough[i]["core_pens"][2]["top_price"], # zhongshus_rough[i]["ZG"],
                            "ZD": None, # max(zhongshus_rough[i]["core_pens"][2]["bottom_price"], zhongshus_rough[i]["core_pens"][3]["bottom_price"]) if len(zhongshus_rough[i]["core_pens"]) >=4 else zhongshus_rough[i]["core_pens"][2]["bottom_price"], # zhongshus_rough[i]["ZD"],
                            "start_time": zhongshus_rough[i]["core_pens"][2]["top_time"],
                            "end_time": zhongshus_rough[i]["core_pens"][-1]["bottom_time"] if last_index_should_include else zhongshus_rough[i]["core_pens"][-2]["bottom_time"],
                            "core_pens": zhongshus_rough[i]["core_pens"][2:] if last_index_should_include else zhongshus_rough[i]["core_pens"][2:-1],
                            "core_pens_index": zhongshus_rough[i]["core_pens_index"][2:] if last_index_should_include else zhongshus_rough[i]["core_pens_index"][2:-1],
                            "GG": None,
                            "DD": None,
                            "direction": "Up",
                            "zhongshu_jieshu": False,  # zhongshu_stop,
                            "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
                        }
                        if zgzd_type == "classical":
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else min(
                                [pen["top_price"] for pen in zhongshu_1["core_pens"][:2]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else max(
                                [pen["bottom_price"] for pen in zhongshu_1["core_pens"][:2]])
                        else:
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["GG"] = max([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["DD"] = min([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        clean_zhongshus.append(zhongshu_1)
                elif min_pen_index == 0 and zhongshus_rough[i]["core_pens"][min_pen_index]["direction"] == "Up":
                    # 第一段开始就是是一买
                    if len(zhongshus_rough[i]["core_pens_index"]) >= 2:
                        last_index_should_include = True if zhongshus_rough[i]["core_pens"][-1][
                                                                'direction'] == "Down" else False
                        zhongshu_1 = {
                            "ZG": None, # zhongshus_rough[i]["core_pens"][1]["top_price"],  # zhongshus_rough[i]["ZG"],
                            "ZD": None, # max(zhongshus_rough[i]["core_pens"][1]["bottom_price"], zhongshus_rough[i]["core_pens"][2]["bottom_price"]) if len(zhongshus_rough[i]["core_pens"]) >= 3 else zhongshus_rough[i]["core_pens"][1]["bottom_price"],  # zhongshus_rough[i]["ZD"],
                            "start_time": zhongshus_rough[i]["core_pens"][1]["top_time"],
                            "end_time": zhongshus_rough[i]["core_pens"][-1][
                                "bottom_time"] if last_index_should_include else zhongshus_rough[i]["core_pens"][-2][
                                "bottom_time"],
                            "core_pens": zhongshus_rough[i]["core_pens"][1:] if last_index_should_include else
                            zhongshus_rough[i]["core_pens"][1:-1],
                            "core_pens_index": zhongshus_rough[i]["core_pens_index"][
                                               1:] if last_index_should_include else zhongshus_rough[i][
                                                                                         "core_pens_index"][1:-1],
                            "GG": None,
                            "DD": None,
                            "direction": "Up",
                            "zhongshu_jieshu": False,  # zhongshu_stop,
                            "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
                        }
                        if zgzd_type == "classical":
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else min(
                                [pen["top_price"] for pen in zhongshu_1["core_pens"][:2]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else max(
                                [pen["bottom_price"] for pen in zhongshu_1["core_pens"][:2]])
                        else:
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["GG"] = max([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["DD"] = min([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        clean_zhongshus.append(zhongshu_1)
                elif min_pen_index == len(zhongshus_rough[i]["core_pens"]) - 1:# and zhongshus_rough[i]["core_pens"][min_pen_index]["direction"] == "Down":
                    # 最后一段结束是一买
                    if len(zhongshus_rough[i]["core_pens_index"]) >= 2:
                        first_index_should_include = True if zhongshus_rough[i]["core_pens"][0][
                                                                'direction'] == "Up" else False
                        zhongshu_1 = {
                            "ZG": None,
                            "ZD": None,
                            "start_time": zhongshus_rough[i]["core_pens"][0][
                                "bottom_time"] if first_index_should_include else zhongshus_rough[i]["core_pens"][1][
                                "bottom_time"],
                            "end_time": zhongshus_rough[i]["core_pens"][min_pen_index-1]["top_time"],
                            "core_pens": zhongshus_rough[i]["core_pens"][0:min_pen_index] if first_index_should_include else
                            zhongshus_rough[i]["core_pens"][1:min_pen_index],
                            "core_pens_index": zhongshus_rough[i]["core_pens_index"][
                                               0:min_pen_index] if first_index_should_include else zhongshus_rough[i][
                                                                                         "core_pens_index"][1:min_pen_index],
                            "GG": None,
                            "DD": None,
                            "direction": "Down",
                            "zhongshu_jieshu": False,  # zhongshu_stop,
                            "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
                        }
                        if zgzd_type == "classical":
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else min(
                                [pen["top_price"] for pen in zhongshu_1["core_pens"][:2]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else max(
                                [pen["bottom_price"] for pen in zhongshu_1["core_pens"][:2]])
                        else:
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["GG"] = max([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["DD"] = min([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        clean_zhongshus.append(zhongshu_1)
                elif min_pen_index == len(zhongshus_rough[i]["core_pens"]) - 2:# and zhongshus_rough[i]["core_pens"][min_pen_index]["direction"] == "Down":
                    # 最后一段和倒数第二段之间是一买
                    if len(zhongshus_rough[i]["core_pens_index"]) >= 3:
                        first_index_should_include = True if zhongshus_rough[i]["core_pens"][0][
                                                                 'direction'] == "Up" else False
                        zhongshu_1 = {
                            "ZG": None,
                            "ZD": None,
                            "start_time": zhongshus_rough[i]["core_pens"][0][
                                "bottom_time"] if first_index_should_include else zhongshus_rough[i]["core_pens"][1][
                                "bottom_time"],
                            "end_time": zhongshus_rough[i]["core_pens"][min_pen_index-1]["top_time"],
                            "core_pens": zhongshus_rough[i]["core_pens"][0:min_pen_index] if first_index_should_include else
                            zhongshus_rough[i]["core_pens"][1:min_pen_index],
                            "core_pens_index": zhongshus_rough[i]["core_pens_index"][
                                               0:min_pen_index] if first_index_should_include else zhongshus_rough[i][
                                                                                            "core_pens_index"][1:min_pen_index],
                            "GG": None,
                            "DD": None,
                            "direction": "Down",
                            "zhongshu_jieshu": False,  # zhongshu_stop,
                            "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
                        }
                        if zgzd_type == "classical":
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else min(
                                [pen["top_price"] for pen in zhongshu_1["core_pens"][:2]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else max(
                                [pen["bottom_price"] for pen in zhongshu_1["core_pens"][:2]])
                        else:
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["GG"] = max([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["DD"] = min([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        clean_zhongshus.append(zhongshu_1)
                else:
                    # max_pen_index把中枢分成左右两边
                    first_index_should_include = True if zhongshus_rough[i]["core_pens"][0][
                                                             'direction'] == "Up" else False
                    last_index_should_include = True if zhongshus_rough[i]["core_pens"][-1][
                                                            'direction'] == "Down" else False

                    # print(zhongshus_rough[i]["core_pens_index"], min_pen_index)
                    zhongshu_1 = {
                        "ZG": None,
                        "ZD": None,
                        "start_time": zhongshus_rough[i]["core_pens"][0][
                            "bottom_time"] if first_index_should_include else zhongshus_rough[i]["core_pens"][1][
                            "bottom_time"],
                        "end_time": zhongshus_rough[i]["core_pens"][min_pen_index-1]["top_time"],
                        "core_pens": zhongshus_rough[i]["core_pens"][0:min_pen_index] if first_index_should_include else
                        zhongshus_rough[i]["core_pens"][1:min_pen_index],
                        "core_pens_index": zhongshus_rough[i]["core_pens_index"][
                                           0:min_pen_index] if first_index_should_include else zhongshus_rough[i][
                                                                                        "core_pens_index"][1:min_pen_index],
                        "GG": None,
                        "DD": None,
                        "direction": "Down",
                        "zhongshu_jieshu": False,  # zhongshu_stop,
                        "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
                    }
                    if zgzd_type == "classical":
                        zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]]) if len(
                            zhongshu_1["core_pens"]) < 2 else min(
                            [pen["top_price"] for pen in zhongshu_1["core_pens"][:2]])
                        zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]]) if len(
                            zhongshu_1["core_pens"]) < 2 else max(
                            [pen["bottom_price"] for pen in zhongshu_1["core_pens"][:2]])
                    else:
                        zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                    zhongshu_1["GG"] = max([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                    zhongshu_1["DD"] = min([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])

                    zhongshu_2 = {
                        "ZG": None,  # zhongshus_rough[i]["core_pens"][2]["top_price"], # zhongshus_rough[i]["ZG"],
                        "ZD": None,
                        # max(zhongshus_rough[i]["core_pens"][2]["bottom_price"], zhongshus_rough[i]["core_pens"][3]["bottom_price"]) if len(zhongshus_rough[i]["core_pens"]) >=4 else zhongshus_rough[i]["core_pens"][2]["bottom_price"], # zhongshus_rough[i]["ZD"],
                        "start_time": zhongshus_rough[i]["core_pens"][min_pen_index+1]["top_time"],
                        "end_time": zhongshus_rough[i]["core_pens"][-1]["bottom_time"] if last_index_should_include else
                        zhongshus_rough[i]["core_pens"][-2]["bottom_time"],
                        "core_pens": zhongshus_rough[i]["core_pens"][min_pen_index+1:] if last_index_should_include else
                        zhongshus_rough[i]["core_pens"][min_pen_index+1:-1],
                        "core_pens_index": zhongshus_rough[i]["core_pens_index"][min_pen_index+1:] if last_index_should_include else
                        zhongshus_rough[i]["core_pens_index"][min_pen_index+1:-1],
                        "GG": None,
                        "DD": None,
                        "direction": "Up",
                        "zhongshu_jieshu": False,  # zhongshu_stop,
                        "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
                    }
                    if zgzd_type == "classical":
                        zhongshu_2["ZG"] = min([pen["top_price"] for pen in zhongshu_2["core_pens"]]) if len(
                            zhongshu_2["core_pens"]) < 2 else min(
                            [pen["top_price"] for pen in zhongshu_2["core_pens"][:2]])
                        zhongshu_2["ZD"] = max([pen["bottom_price"] for pen in zhongshu_2["core_pens"]]) if len(
                            zhongshu_2["core_pens"]) < 2 else max(
                            [pen["bottom_price"] for pen in zhongshu_2["core_pens"][:2]])
                    else:
                        zhongshu_2["ZG"] = min([pen["top_price"] for pen in zhongshu_2["core_pens"]])
                        zhongshu_2["ZD"] = max([pen["bottom_price"] for pen in zhongshu_2["core_pens"]])
                    zhongshu_2["GG"] = max([pen["top_price"] for pen in zhongshu_2["core_pens"]])
                    zhongshu_2["DD"] = min([pen["bottom_price"] for pen in zhongshu_2["core_pens"]])

                    clean_zhongshus.append(zhongshu_1)
                    clean_zhongshus.append(zhongshu_2)
            else:
                # 趋势中间段
                if len(zhongshus_rough[i]["core_pens"]) >= 2:
                    if (zhongshus_rough[i - 1]["ZD"] <= zhongshus_rough[i]["ZD"] <= zhongshus_rough[i + 1][
                        "ZD"]):  # 向上中间段
                        first_index_should_include = True if zhongshus_rough[i]["core_pens"][0]['direction'] == "Down" else False
                        last_index_should_include = True if zhongshus_rough[i]["core_pens"][-1]['direction'] == "Down" else False
                        core_pens_zhongshu_1 = zhongshus_rough[i]["core_pens"][0:] if first_index_should_include else zhongshus_rough[i]["core_pens"][1:]
                        core_pens_zhongshu_1 = core_pens_zhongshu_1 if last_index_should_include else core_pens_zhongshu_1[:-1]

                        core_pens_index_zhongshu_1 = zhongshus_rough[i]["core_pens_index"][0:] if first_index_should_include else zhongshus_rough[i]["core_pens_index"][1:]
                        core_pens_index_zhongshu_1 = core_pens_index_zhongshu_1 if last_index_should_include else core_pens_index_zhongshu_1[:-1]

                        zhongshu_1 = {
                            "ZG": None,
                            "ZD": None,
                            "start_time": core_pens_zhongshu_1[0]["top_time"],
                            "end_time":core_pens_zhongshu_1[-1]["bottom_time"],
                            "core_pens": core_pens_zhongshu_1,
                            "core_pens_index": core_pens_index_zhongshu_1,
                            "GG": None,
                            "DD": None,
                            "direction": "Up",
                            "zhongshu_jieshu": False,  # zhongshu_stop,
                            "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
                        }
                        if zgzd_type == "classical":
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else min(
                                [pen["top_price"] for pen in zhongshu_1["core_pens"][:2]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else max(
                                [pen["bottom_price"] for pen in zhongshu_1["core_pens"][:2]])
                        else:
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["GG"] = max([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["DD"] = min([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])

                    elif (zhongshus_rough[i - 1]["ZD"] >= zhongshus_rough[i]["ZD"] >= zhongshus_rough[i + 1][
                        "ZD"]):  # 向下中间段
                        first_index_should_include = True if zhongshus_rough[i]["core_pens"][0][
                                                                 'direction'] == "Up" else False
                        last_index_should_include = True if zhongshus_rough[i]["core_pens"][-1][
                                                                'direction'] == "Up" else False

                        core_pens_zhongshu_1 = zhongshus_rough[i]["core_pens"][0:] if first_index_should_include else \
                        zhongshus_rough[i]["core_pens"][1:]
                        core_pens_zhongshu_1 = core_pens_zhongshu_1 if last_index_should_include else core_pens_zhongshu_1[
                                                                                                      :-1]

                        core_pens_index_zhongshu_1 = zhongshus_rough[i]["core_pens_index"][
                                                     0:] if first_index_should_include else zhongshus_rough[i][
                                                                                                "core_pens_index"][1:]
                        core_pens_index_zhongshu_1 = core_pens_index_zhongshu_1 if last_index_should_include else core_pens_index_zhongshu_1[
                                                                                                                  :-1]

                        zhongshu_1 = {
                            "ZG": None,
                            "ZD": None,
                            "start_time": core_pens_zhongshu_1[0]["bottom_time"],
                            "end_time": core_pens_zhongshu_1[-1]["top_time"],
                            "core_pens": core_pens_zhongshu_1,
                            "core_pens_index": core_pens_index_zhongshu_1,
                            "GG": None,
                            "DD": None,
                            "direction": "Down",
                            "zhongshu_jieshu": False,  # zhongshu_stop,
                            "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
                        }
                        if zgzd_type == "classical":
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else min(
                                [pen["top_price"] for pen in zhongshu_1["core_pens"][:2]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else max(
                                [pen["bottom_price"] for pen in zhongshu_1["core_pens"][:2]])
                        else:
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["GG"] = max([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["DD"] = min([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                else:
                    zhongshu_1 = zhongshus_rough[i]

                clean_zhongshus.append(zhongshu_1)
        else:
            #首尾段
            if len(zhongshus_rough[i]["core_pens"]) == 1:
                clean_zhongshus.append(zhongshus_rough[i])
            elif len(zhongshus_rough) == 1:
                clean_zhongshus.append(zhongshus_rough[i])
            else:
                if i == 0:
                    if (zhongshus_rough[i]["core_pens_index"][-1] + 2 == zhongshus_rough[i+1]["core_pens_index"][0]):
                        clean_zhongshus.append(zhongshus_rough[i])
                    elif (zhongshus_rough[i]["core_pens_index"][-1] + 1 == zhongshus_rough[i+1]["core_pens_index"][0]):
                        zhongshu_1 = {
                            "ZG": None,
                            "ZD": None,
                            "start_time": zhongshus_rough[i]["start_time"],
                            "end_time": max(zhongshus_rough[i]["core_pens"][-2]["top_time"], zhongshus_rough[i]["core_pens"][-2]["bottom_time"]),
                            "core_pens": zhongshus_rough[i]["core_pens"][:-1],
                            "core_pens_index": zhongshus_rough[i]["core_pens_index"][:-1],
                            "GG": None,
                            "DD": None,
                            "direction": "Down" if zhongshus_rough[i+1]["ZD"] < zhongshus_rough[i]["ZD"] else "Up",
                            "zhongshu_jieshu": False,  # zhongshu_stop,
                            "kuozhang": 0  # times_kuozhan  # 中枢扩张次数
                        }
                        if zgzd_type == "classical":
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else min(
                                [pen["top_price"] for pen in zhongshu_1["core_pens"][:2]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]]) if len(
                                zhongshu_1["core_pens"]) < 2 else max(
                                [pen["bottom_price"] for pen in zhongshu_1["core_pens"][:2]])
                        else:
                            zhongshu_1["ZG"] = min([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                            zhongshu_1["ZD"] = max([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["GG"] = max([pen["top_price"] for pen in zhongshu_1["core_pens"]])
                        zhongshu_1["DD"] = min([pen["bottom_price"] for pen in zhongshu_1["core_pens"]])
                        clean_zhongshus.append(zhongshu_1)
                elif i == len(zhongshus_rough) - 1:
                    if (zhongshus_rough[i]["core_pens_index"][0] - 2 == zhongshus_rough[i-1]["core_pens_index"][-1]):
                        clean_zhongshus.append(zhongshus_rough[i])
                    else:
                        #可能可以考虑修改，暂时看没啥问题
                        clean_zhongshus.append(zhongshus_rough[i])

        i = i + 1
    return clean_zhongshus, zhuanzhes, sanmai_info

#"""






def find_zhongshu_one_pen_20250202(pens, zgzd_type="classical"):
    zhongshus = []  # 存储所有中枢
    zhuanzhes = []
    return zhongshus, zhuanzhes





# 寻找笔中枢的函数
def find_zhongshu_based_on_looking_for_next_zhongshu(pens, zgzd_type="classical"):
    """
        从缠论的笔中找出所有中枢，支持延伸和离开笔确认，允许两种 ZG/ZD 逻辑
        参数:
            pens: 包含每一笔信息的列表，每个元素是字典，包含:
                  'top_price', 'bottom_price', 'top_time', 'bottom_time'
            zgzd_type: 中枢高低区间的计算逻辑：
                       "classical" - 确立 ZG/ZD 后不再更新
                       "practical" - ZG/ZD 随后续笔动态更新
        返回:
            zhongshus: 包含每个中枢的高点区间（ZG）、低点区间（ZD）、时间范围和构成的核心笔列表
        """

    zhongshus = []  # 存储所有中枢
    zhuanzhes = []
    if len(pens) < 5:
        return zhongshus
    i = 0  # 从第一笔开始
    zoushi_direction = pens[0]['direction']  # 当前走势的方向，也就是中枢前一笔的方向

    #
    # while i < len(pens):
    while i < len(pens) - 5:  # 至少需要 5 笔才能开始判断
        # 判断进入笔和离开笔方向是否一致
        first_pen = pens[i]
        second_pen = pens[i + 1]
        third_pen = pens[i + 2]
        fourth_pen = pens[i + 3]
        fifth_pen = pens[i + 4]

        zoushi_direction = first_pen['direction']

        # 判断进入笔和离开笔的方向是否一致
        # 初始化中枢的高低区间
        # zg = min(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
        # zd = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
        # zg = min(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
        # zd = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
        GG = max(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
        DD = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
        zg = min(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
        zd = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
        # if ((zg > zd) and (zg <= first_pen['top_price']) and (zd >= first_pen['bottom_price']) and (zg <= fifth_pen['top_price']) and (zd >= fifth_pen['bottom_price'])):

        if (zg > zd) and (((zoushi_direction == 'Up') and second_pen['bottom_price'] > first_pen['bottom_price']) or
                              ((zoushi_direction == 'Down') and second_pen['top_price'] < first_pen['top_price'])):
            # if zhongshus and (((zoushi_direction == 'Up') and fourth_pen['bottom_price'] < zhongshus[-1]['ZG']) or
            #                   ((zoushi_direction == 'Down') and fourth_pen['top_price'] > zhongshus[-1]['ZD'])):
            #     print(i)
            #     print(f"第{i+3}笔中枢扩展了，怎么处理我还没码")
            #     print(f"如果转折后第一个中枢高度上实际上是延续了上一个走势，那就应该包含上一笔并改正走势方向")


            start_time = min(second_pen['top_time'], second_pen['bottom_time'])
            end_time = max(fourth_pen['top_time'], fourth_pen['bottom_time'])
            # end_time = max(third_pen['top_time'], third_pen['bottom_time'])
            # end_time = max(second_pen['top_time'], second_pen['bottom_time'])

            core_pens = [second_pen, third_pen, fourth_pen]
            # core_pens = [second_pen, third_pen]
            # core_pens = [second_pen]

            # 如果是 "classical"，初始 ZG/ZD 不更新
            classical_zg = zg
            classical_zd = zd

            # 标记中枢有没有结束
            zhongshu_stop = False

            # 延伸中枢
            j = i + 4
            # j = i + 3
            # j = i + 2
            # for j in range(i + 4, len(pens) - 1):
            times_kuozhan = 0
            while j < len(pens) - 4:  # 至少留二笔用于离开确认
                next_pen = pens[j]         #same as fifth_pen #如果是同趋势新中枢，第一笔后新中枢开始，如果是转折，第一笔后转折，第二笔后是转折后的第一个中枢
                next_next_pen = pens[j + 1]
                next_third_pen = pens[j + 2]
                next_fourth_pen = pens[j + 3]
                next_fifth_pen = pens[j + 4]

                GG_same_dir = max(next_next_pen['top_price'], next_third_pen['top_price'], next_fourth_pen['top_price'])
                DD_same_dir = max(next_next_pen['bottom_price'], next_third_pen['bottom_price'], next_fourth_pen['bottom_price'])
                zg_same_dir = min(next_next_pen['top_price'], next_third_pen['top_price'], next_fourth_pen['top_price'])
                zd_same_dir = max(next_next_pen['bottom_price'], next_third_pen['bottom_price'], next_fourth_pen['bottom_price'])

                GG_zhuanzhe = max(next_third_pen['top_price'], next_fourth_pen['top_price'],
                                  next_fifth_pen['top_price'])
                DD_zhuanzhe = max(next_third_pen['bottom_price'], next_fourth_pen['bottom_price'],
                                  next_fifth_pen['bottom_price'])
                zg_zhuanzhe = min(next_third_pen['top_price'], next_fourth_pen['top_price'],
                                  next_fifth_pen['top_price'])
                zd_zhuanzhe = max(next_third_pen['bottom_price'], next_fourth_pen['bottom_price'],
                                  next_fifth_pen['bottom_price'])


                # 情况 1 出现中枢， 第五笔维持方向离开中枢
                ##### 情况 1.1 出现新中枢，第七笔不如第五笔强，新中枢和前中枢的(DD, GG)有重叠
                ########## 情况 1.1.1
                ##### 情况 1.2 不出现新中枢，第七笔不如第五笔强，新中枢和前中枢的(DD, GG)有重叠
                # 情况 2 出现中枢， 第四笔逆方向离开中枢，第五笔不能返回

                ##### 情况1 #####
                if ((zoushi_direction == 'Down') and (next_pen['bottom_price'] < zd)) or (
                        (zoushi_direction == 'Up') and (next_pen['top_price'] > zg)):  # 下一笔暂时离开, 延续前趋势
                    # print(f"第{j}笔延续趋势地离开中枢")
                    # if (zg_zhuanzhe > zd_zhuanzhe) and ((zoushi_direction == 'Down') and (DD_zhuanzhe > next_pen['bottom_price'])) or (
                    #     (zoushi_direction == 'Up') and (GG_zhuanzhe < next_pen['top_price'])):  #出现转折后的中枢，不能新高或新低
                    ##### 情况1.1 #####
                    if (zg_zhuanzhe > zd_zhuanzhe) and (
                            (zoushi_direction == 'Down') and (next_third_pen['bottom_price'] > next_pen['bottom_price']) and (DD_zhuanzhe > next_pen['bottom_price'])) or (
                            (zoushi_direction == 'Up') and (next_third_pen['top_price'] < next_pen['top_price']) and (GG_zhuanzhe < next_pen['top_price'])):  # 出现转折后的中枢，不能新高或新低
                        # if ((zoushi_direction == 'Down') and (DD_zhuanzhe < zg)) or (
                        #         (zoushi_direction == 'Up') and (GG_zhuanzhe > zd)): #中枢扩展了
                        #     # 先跳过这几笔，我再想想以后怎么修改
                        #     times_kuozhan += 1
                        #     print(f"第{j}笔和第{j + 1}笔间转折出现, {j+4}笔拉回中枢, 中枢扩展")
                        #     zg = min(second_pen['top_price'], next_fifth_pen['top_price']) if (zoushi_direction == 'Up') else next_next_pen['top_price']
                        #     zd = max(second_pen['bottom_price'], next_fifth_pen['bottom_price']) if (zoushi_direction == 'Down') else next_next_pen['bottom_price']
                        #     classical_zg = zg
                        #     classical_zd = zd
                        #     break
                        # else:
                        # print(f"第{j}笔和第{j+1}笔间转折出现")
                        ##### 情况1.1.1 #####
                        if ((zoushi_direction == 'Down') and (GG_zhuanzhe > first_pen['top_price'])) or (
                                (zoushi_direction == 'Up') and (DD_zhuanzhe < first_pen['bottom_price'])):
                        # if ((zoushi_direction == 'Down') and (GG_zhuanzhe > next_fifth_pen['top_price'])) or (
                        #         (zoushi_direction == 'Up') and (DD_zhuanzhe < next_fifth_pen['bottom_price'])):
                            # if zhuanzhes and ((zoushi_direction == 'Down' == zhuanzhes[-1]["direction"][-4:]) or (
                            #         (zoushi_direction == 'Up' == zhuanzhes[-1]["direction"][-4:]))):
                            #     if (zoushi_direction == 'Down' and (first_pen['bottom_price'] < third_pen['bottom_price'])) or (
                            #             zoushi_direction == 'Up' and (first_pen['top_price'] > third_pen['top_price'])):

                            previous_direction = ""
                            if zhuanzhes:
                                if 'Down' == zhuanzhes[-1]["direction"][-4:]:
                                    previous_direction = "Down"
                                else:
                                    previous_direction = "Up"
                            elif zhongshus:
                                if 'Down' == zhongshus[-1]["direction"]:
                                    previous_direction = "Down"
                                else:
                                    previous_direction = "Up"

                            ##### 情况1.1.1.1 #####
                            if previous_direction and ((zoushi_direction == 'Down' == previous_direction) or (
                                    (zoushi_direction == 'Up' == previous_direction))) and ((
                                    zoushi_direction == 'Down' and (first_pen['bottom_price'] < third_pen['bottom_price']) and (first_pen['bottom_price'] < fifth_pen['bottom_price'])) or (
                                        zoushi_direction == 'Up' and (first_pen['top_price'] > third_pen['top_price']) and (first_pen['top_price'] > fifth_pen['top_price']))):
                                        # print(f"第{i}笔和第{i + 1}笔间确定为转折")
                                        zhuanzhe = {
                                            "time": first_pen['top_time'] if first_pen['direction'] == "Up" else first_pen[
                                                'bottom_time'],
                                            "price": first_pen['top_price'] if first_pen['direction'] == "Up" else
                                            first_pen[
                                                'bottom_price'],
                                            "direction": "Up_to_Down" if first_pen['direction'] == "Up" else "Down_to_Up",
                                            "zhuanzhe_between_pens": [i, i+1],
                                        }
                                        zhuanzhes.append(zhuanzhe)
                                        i = i + 1
                                        core_pens = []
                                        zhongshu_stop = True
                                        break
                                # else:
                                #     print(f"第{i+2}笔和第{i + 3}笔间确定为转折")
                                #     zhuanzhe = {
                                #         "time": third_pen['top_time'] if third_pen['direction'] == "Up" else third_pen[
                                #             'bottom_time'],
                                #         "price": third_pen['top_price'] if third_pen['direction'] == "Up" else
                                #         third_pen[
                                #             'bottom_price'],
                                #         "direction": "Up_to_Down" if third_pen['direction'] == "Up" else "Down_to_Up",
                                #         "zhuanzhe_between_pens": [i+2, i+3],
                                #     }
                                #     zhuanzhes.append(zhuanzhe)
                                #     i = i + 3
                                #     core_pens = []
                                #     zhongshu_stop = True
                                #     break
                            ##### 情况1.1.1.2 #####
                            elif previous_direction and ((zoushi_direction == 'Down' != previous_direction) or (
                                    (zoushi_direction == 'Up' != previous_direction))):
                                # 短暂且较弱的盘整走势，适合解读为原走势中枢
                                # print(f"第{i}笔开始短暂且较弱的盘整走势，适合解读为原走势中枢, 后方有转折后的中枢，就是和转折后方向一样，转折不理解成转折")
                                zoushi_direction = 'Up' if zoushi_direction == 'Down' else 'Down'
                                core_pens.insert(0, first_pen)
                                core_pens.append(fifth_pen)
                                GG = max(second_pen['top_price'], third_pen['top_price'], first_pen['top_price'], fourth_pen['top_price'], fifth_pen['top_price'])
                                DD = max(second_pen['bottom_price'], third_pen['bottom_price'], first_pen['bottom_price'], fourth_pen['bottom_price'], fifth_pen['bottom_price'])
                                zg = min(second_pen['top_price'], third_pen['top_price'], first_pen['top_price'])
                                zd = max(second_pen['bottom_price'], third_pen['bottom_price'], first_pen['bottom_price'])



                                start_time = min(first_pen['top_time'], first_pen['bottom_time'])
                                end_time = max(fifth_pen['top_time'], fifth_pen['bottom_time'])

                                # 如果是 "classical"，初始 ZG/ZD 不更新
                                classical_zg = zg
                                classical_zd = zd
                                # 标记中枢有没有结束
                                zhongshu_stop = False
                                j += 1
                                i = i - 1
                                first_pen = pens[i]
                                second_pen = pens[i + 1]
                                third_pen = pens[i + 2]
                                fourth_pen = pens[i + 3]
                                fifth_pen = pens[i + 4]
                            ##### 情况1.1.1.3 #####
                            else:
                                # print(f"第{i+2}笔和第{i + 3}笔间确定为转折")
                                zhuanzhe = {
                                    "time": third_pen['top_time'] if third_pen['direction'] == "Up" else third_pen[
                                        'bottom_time'],
                                    "price": third_pen['top_price'] if third_pen['direction'] == "Up" else
                                    third_pen[
                                        'bottom_price'],
                                    "direction": "Up_to_Down" if third_pen['direction'] == "Up" else "Down_to_Up",
                                    "zhuanzhe_between_pens": [i, i + 1],
                                }
                                zhuanzhes.append(zhuanzhe)
                                i = i + 3
                                core_pens = []
                                zhongshu_stop = True
                                break

                        else:
                            # print(f"第{j}笔和第{j + 1}笔间确定为转折")
                            zhuanzhe = {
                                "time": next_pen['top_time'] if next_pen['direction'] == "Up" else next_pen['bottom_time'],
                                "price": next_pen['top_price'] if next_pen['direction'] == "Up" else next_pen['bottom_price'],
                                "direction": "Up_to_Down" if next_pen['direction'] == "Up" else "Down_to_Up",
                                "zhuanzhe_between_pens": [j, j+1],
                            }
                            zhuanzhes.append(zhuanzhe)
                            i = j + 1
                            zhongshu_stop = True
                            break
                    # elif (zg_zhuanzhe <= zd_zhuanzhe) and (((zoushi_direction == 'Down') and (DD_zhuanzhe > next_pen['bottom_price'])) or (
                    #     (zoushi_direction == 'Up') and (GG_zhuanzhe < next_pen['top_price']))): #不以中枢的形式转折，五笔内一路转折，不成中枢

                    elif (zg_zhuanzhe <= zd_zhuanzhe) and (
                            (zoushi_direction == 'Down') and (next_third_pen['bottom_price'] > next_pen['bottom_price']) and (DD_zhuanzhe > next_pen['bottom_price'])) or (
                            (zoushi_direction == 'Up') and (next_third_pen['top_price'] < next_pen['top_price']) and (GG_zhuanzhe < next_pen['top_price'])): #不以中枢的形式转折，五笔内一路转折，不成中枢
                        # print(f"第{j}笔和第{j + 1}笔间转折出现, 转折后没有快速出现中枢")

                        if ((zoushi_direction == 'Down') and (GG_zhuanzhe > first_pen['top_price'])) or (
                                (zoushi_direction == 'Up') and (DD_zhuanzhe < first_pen['bottom_price'])):
                            # if zhuanzhes and ((zoushi_direction == 'Down' == zhuanzhes[-1]["direction"][-4:]) or (
                            #         (zoushi_direction == 'Up' == zhuanzhes[-1]["direction"][-4:]))):
                            #     if (zoushi_direction == 'Down' and (first_pen['bottom_price'] < third_pen['bottom_price'])) or (
                            #             zoushi_direction == 'Up' and (first_pen['top_price'] > third_pen['top_price'])):
                            previous_direction = ""
                            if zhuanzhes:
                                if 'Down' == zhuanzhes[-1]["direction"][-4:]:
                                    previous_direction = "Down"
                                else:
                                    previous_direction = "Up"
                            elif zhongshus:
                                if 'Down' == zhongshus[-1]["direction"]:
                                    previous_direction = "Down"
                                else:
                                    previous_direction = "Up"

                            if previous_direction and (
                                    (zoushi_direction == 'Down' == previous_direction) or (
                                    (zoushi_direction == 'Up' == previous_direction))):
                                if ((zoushi_direction == 'Down' and (
                                        first_pen['bottom_price'] < third_pen['bottom_price'])) or (
                                        zoushi_direction == 'Up' and (
                                        first_pen['top_price'] > third_pen['top_price']))):
                                        # print(f"第{i}笔和第{i + 1}笔间确定为转折")
                                        zhuanzhe = {
                                            "time": first_pen['top_time'] if first_pen['direction'] == "Up" else first_pen[
                                                'bottom_time'],
                                            "price": first_pen['top_price'] if first_pen['direction'] == "Up" else
                                            first_pen[
                                                'bottom_price'],
                                            "direction": "Up_to_Down" if first_pen['direction'] == "Up" else "Down_to_Up",
                                            "zhuanzhe_between_pens": [i, i+1],
                                        }
                                        zhuanzhes.append(zhuanzhe)
                                        i = i + 1
                                        core_pens = []
                                        zhongshu_stop = True
                                        break
                                else:
                                    # print(f"第{i+2}笔和第{i + 3}笔间确定为转折")
                                    zhuanzhe = {
                                        "time": third_pen['top_time'] if third_pen['direction'] == "Up" else third_pen[
                                            'bottom_time'],
                                        "price": third_pen['top_price'] if third_pen['direction'] == "Up" else
                                        third_pen[
                                            'bottom_price'],
                                        "direction": "Up_to_Down" if third_pen['direction'] == "Up" else "Down_to_Up",
                                        "zhuanzhe_between_pens": [i + 2, i + 3],
                                    }
                                    zhuanzhes.append(zhuanzhe)
                                    i = i + 3
                                    core_pens = []
                                    zhongshu_stop = True
                                    break
                            else:
                                # 短暂且较弱的盘整走势，适合解读为原走势中枢
                                # print(f"第{i}笔开始短暂且较弱的盘整走势，适合解读为原走势中枢， 后方没有转折后的中枢，而是强劲地走原方向，转折不理解成转折")
                                zoushi_direction = 'Up' if zoushi_direction == 'Down' else 'Down'
                                core_pens.insert(0, first_pen)
                                core_pens.append(fifth_pen)
                                # print(f"这个中枢现在有{len(core_pens)}条线段")
                                GG = max(second_pen['top_price'], third_pen['top_price'], first_pen['top_price'], fourth_pen['top_price'], fifth_pen['top_price'])
                                DD = max(second_pen['bottom_price'], third_pen['bottom_price'], first_pen['bottom_price'], fourth_pen['bottom_price'], fifth_pen['bottom_price'])
                                zg = min(second_pen['top_price'], third_pen['top_price'], first_pen['top_price'])
                                zd = max(second_pen['bottom_price'], third_pen['bottom_price'], first_pen['bottom_price'])


                                start_time = min(first_pen['top_time'], first_pen['bottom_time'])
                                end_time = max(fifth_pen['top_time'], fifth_pen['bottom_time'])

                                # 如果是 "classical"，初始 ZG/ZD 不更新
                                classical_zg = zg
                                classical_zd = zd
                                # 标记中枢有没有结束
                                zhongshu_stop = False
                                j += 1
                                i = i - 1
                                first_pen = pens[i]
                                second_pen = pens[i + 1]
                                third_pen = pens[i + 2]
                                fourth_pen = pens[i + 3]
                                fifth_pen = pens[i + 4]
                                # core_pens = []
                        else:
                            # print(f"第{j}笔和第{j + 1}笔间确定为转折")
                            zhuanzhe = {
                                "time": next_pen['top_time'] if next_pen['direction'] == "Up" else next_pen[
                                    'bottom_time'],
                                "price": next_pen['top_price'] if next_pen['direction'] == "Up" else next_pen[
                                    'bottom_price'],
                                "direction": "Up_to_Down" if next_pen['direction'] == "Up" else "Down_to_Up",
                                "zhuanzhe_between_pens": [j, j+1],
                            }
                            zhuanzhes.append(zhuanzhe)
                            i = j + 1
                            core_pens = []
                            zhongshu_stop = True
                            break
                    elif ((zoushi_direction == 'Down') and (third_pen['bottom_price'] < min(DD_zhuanzhe, DD_same_dir))) or (
                            (zoushi_direction == 'Up') and (third_pen['top_price'] > max(GG_zhuanzhe, GG_same_dir))):
                        # print(f"三段线，不足以画出{zoushi_direction}中枢，后面转折，前面找的中枢视为转折")
                        zhuanzhe = {
                            "time": third_pen['top_time'] if third_pen['direction'] == "Up" else third_pen['bottom_time'],
                            "price": third_pen['top_price'] if third_pen['direction'] == "Up" else third_pen[
                                'bottom_price'],
                            "direction": "Up_to_Down" if third_pen['direction'] == "Up" else "Down_to_Up",
                            "zhuanzhe_between_pens": [j - 1, j],
                        }
                        zhuanzhes.append(zhuanzhe)
                        i = j - 1
                        core_pens = []
                        zhongshu_stop = True
                        break
                    elif (zg_same_dir > zd_same_dir): #延续前趋势的中枢
                        if (((zoushi_direction == 'Down') and (next_next_pen['top_price'] > zd)) or (
                                (zoushi_direction == 'Up') and (next_next_pen['bottom_price'] < zg))):
                            # 再次回到中枢，延续中枢
                            # print(f"第{j}笔后中枢扩展, 或中枢延伸")
                            if zgzd_type == "practical":
                                zg = min(zg, next_pen['top_price'])
                                zd = max(zd, next_pen['bottom_price'])
                            GG = max(next_pen["top_price"], GG)
                            DD = min(next_pen["bottom_price"], DD)
                            end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                            # end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                            core_pens.append(next_pen)
                            core_pens.append(next_next_pen)
                            j += 2  ###这里可能要加二因为后面两笔都被考察过了是否适合写入中枢
                        elif (((zoushi_direction == 'Down') and (GG_same_dir > zd)) or (
                            (zoushi_direction == 'Up') and (DD_same_dir < zg))): #中枢扩展, 或中枢延伸, 需要创新高或者新低
                            # 再次回到中枢，延续中枢
                            # print(f"第{j}笔后中枢扩展, 或中枢延伸")
                            if zgzd_type == "practical":
                                zg = min(zg, next_pen['top_price'])
                                zd = max(zd, next_pen['bottom_price'])
                            GG = max(next_pen["top_price"], GG)
                            DD = min(next_pen["bottom_price"], DD)
                            end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                            # end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                            core_pens.append(next_pen)
                            core_pens.append(next_next_pen)
                            j += 2  ###这里可能要加二因为后面两笔都被考察过了是否适合写入中枢
                        else: #突破后的中枢
                            i = j
                            # print(f"第{j}笔同向新中枢形成前的突破，后面紧接着中枢形成")
                            zhongshu_stop = True
                            break
                    elif ((zoushi_direction == 'Down') and (next_next_pen['top_price'] > zd)) or (
                                    (zoushi_direction == 'Up') and (next_next_pen['bottom_price'] < zg)):
                        # 普通的继续延伸
                        # print(f"第{j}笔后普通的中枢扩展")
                        if zgzd_type == "practical":
                            zg = min(zg, next_pen['top_price'])
                            zd = max(zd, next_pen['bottom_price'])
                        end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                        core_pens.append(next_pen)
                        core_pens.append(next_next_pen)
                        j += 2
                    else:
                       # print(f"第{j}笔到{j+4}笔是遗漏的情况")
                       i = j
                       zhongshu_stop = True
                       break
                ##### 情况2 #####
                elif ((zoushi_direction == 'Down') and (next_pen['bottom_price'] >= zg)) or (
                        (zoushi_direction == 'Up') and (next_pen['top_price'] <= zd)): #下一笔突破中枢方向和中枢相反，中枢扩展,或者重新定义原中枢方向
                    # print(f"第{j}笔与原趋势反向地离开中枢")
                    ##### 情况2.1 #####
                    if ((zoushi_direction == 'Down') and (
                                third_pen['bottom_price'] < min(DD_zhuanzhe, DD_same_dir))) or (
                                 (zoushi_direction == 'Up') and (
                                     third_pen['top_price'] > max(GG_zhuanzhe, GG_same_dir))):
                        # print(f"第{i}开始笔三段线，不足以画出{zoushi_direction}中枢，后面转折，后面还没中枢")
                        zhuanzhe = {
                            "time": third_pen['top_time'] if third_pen['direction'] == "Up" else third_pen[
                                'bottom_time'],
                            "price": third_pen['top_price'] if third_pen['direction'] == "Up" else third_pen[
                                'bottom_price'],
                            "direction": "Up_to_Down" if third_pen['direction'] == "Up" else "Down_to_Up",
                            "zhuanzhe_between_pens": [j - 1, j]
                        }
                        zhuanzhes.append(zhuanzhe)
                        i = j - 1
                        core_pens = []
                        zhongshu_stop = True
                        break
                    ##### 情况2.2 #####
                    elif ((zoushi_direction == 'Down') and (next_third_pen['bottom_price'] < zg)) or (
                            (zoushi_direction == 'Up') and (next_third_pen['top_price'] > zd)): #中枢扩展
                        if zgzd_type == "practical":
                            zg = min(zg, next_pen['top_price'])
                            zd = max(zd, next_pen['bottom_price'])
                        end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                        # print(f"中枢扩展，基于第{j}笔的反向突破，第{j+2}笔明显在中枢外结束")
                        core_pens.append(next_pen)
                        core_pens.append(next_next_pen)
                        times_kuozhan += 1
                        j += 2
                    ##### 情况2.3 #####
                    # elif ((zoushi_direction == 'Down') and (GG_zhuanzhe > first_pen['top_price'])) or (
                    #         (zoushi_direction == 'Up') and (DD_zhuanzhe < first_pen['bottom_price'])):
                    elif ((zoushi_direction == 'Down') and (GG_zhuanzhe > first_pen['top_price'])) or (
                            (zoushi_direction == 'Up') and (DD_zhuanzhe < first_pen['bottom_price'])):
                        # if zhuanzhes and ((zoushi_direction == 'Down' == zhuanzhes[-1]["direction"][-4:]) or (
                        #         (zoushi_direction == 'Up' == zhuanzhes[-1]["direction"][-4:]))):
                        #     if (zoushi_direction == 'Down' and (
                        #             first_pen['bottom_price'] < third_pen['bottom_price'])) or (
                        #             zoushi_direction == 'Up' and (first_pen['top_price'] > third_pen['top_price'])):
                        previous_direction = ""
                        if zhuanzhes:
                            if 'Down' == zhuanzhes[-1]["direction"][-4:]:
                                previous_direction = "Down"
                            else:
                                previous_direction = "Up"
                        elif zhongshus:
                            if 'Down' == zhongshus[-1]["direction"]:
                                previous_direction = "Down"
                            else:
                                previous_direction = "Up"
                        ##### 情况2.3.1 #####
                        if previous_direction and ((zoushi_direction == 'Down' == previous_direction) or (
                                (zoushi_direction == 'Up' == previous_direction))):
                            if ((zoushi_direction == 'Down' and (
                                    first_pen['bottom_price'] < third_pen['bottom_price'])) or (
                                    zoushi_direction == 'Up' and (
                                    first_pen['top_price'] > third_pen['top_price']))):
                                # print(f"第{i}笔和第{i + 1}笔间确定为转折")
                                zhuanzhe = {
                                    "time": first_pen['top_time'] if first_pen['direction'] == "Up" else first_pen[
                                        'bottom_time'],
                                    "price": first_pen['top_price'] if first_pen['direction'] == "Up" else
                                    first_pen[
                                        'bottom_price'],
                                    "direction": "Up_to_Down" if first_pen['direction'] == "Up" else "Down_to_Up",
                                    "zhuanzhe_between_pens": [i, i + 1]
                                }
                                zhuanzhes.append(zhuanzhe)
                                i = i + 1
                                zhongshu_stop = True
                                break
                            else:
                                # print(f"第{i + 2}笔和第{i + 3}笔间确定为转折")
                                zhuanzhe = {
                                    "time": third_pen['top_time'] if third_pen['direction'] == "Up" else third_pen[
                                        'bottom_time'],
                                    "price": third_pen['top_price'] if third_pen['direction'] == "Up" else
                                    third_pen[
                                        'bottom_price'],
                                    "direction": "Up_to_Down" if third_pen['direction'] == "Up" else "Down_to_Up",
                                    "zhuanzhe_between_pens": [i+2, i+3]
                                }
                                zhuanzhes.append(zhuanzhe)
                                i = i + 3
                                zhongshu_stop = True
                                break
                        ##### 情况2.3.2 #####
                        else:
                            # 短暂且较弱的盘整走势，适合解读为原走势中枢
                            # print(f"第{i}笔开始短暂且较弱的盘整走势，适合解读为原走势中枢。具体来说是逆原方向的中枢扩展")
                            zoushi_direction = 'Up' if zoushi_direction == 'Down' else 'Down'
                            core_pens.insert(0, first_pen)
                            core_pens.append(fifth_pen)
                            GG = max(second_pen['top_price'], third_pen['top_price'], first_pen['top_price'], fourth_pen['top_price'], fifth_pen['top_price'])
                            DD = max(second_pen['bottom_price'], third_pen['bottom_price'], first_pen['bottom_price'], fourth_pen['bottom_price'], fifth_pen['bottom_price'])
                            zg = min(second_pen['top_price'], third_pen['top_price'], first_pen['top_price'])
                            zd = max(second_pen['bottom_price'], third_pen['bottom_price'], first_pen['bottom_price'])


                            start_time = min(first_pen['top_time'], first_pen['bottom_time'])
                            end_time = max(fifth_pen['top_time'], fifth_pen['bottom_time'])

                            # 如果是 "classical"，初始 ZG/ZD 不更新
                            classical_zg = zg
                            classical_zd = zd
                            # 标记中枢有没有结束
                            zhongshu_stop = False
                            j += 1
                            i = i - 1
                            first_pen = pens[i]
                            second_pen = pens[i + 1]
                            third_pen = pens[i + 2]
                            fourth_pen = pens[i + 3]
                            fifth_pen = pens[i + 4]
                    # print(f"第{j}笔与原趋势反向地离开中枢")
                    # print(i, j)
                    # print(zoushi_direction)
                    # print(next_pen['direction'])
                    # else:
                    #     print(f"第{j}笔和第{j + 1}笔间确定为转折")
                    #     zhuanzhe = {
                    #         "time": next_pen['top_time'] if next_pen['direction'] == "Up" else next_pen[
                    #             'bottom_time'],
                    #         "price": next_pen['top_price'] if next_pen['direction'] == "Up" else next_pen[
                    #             'bottom_price'],
                    #         "direction": "Up_to_Down" if next_pen['direction'] == "Up" else "Down_to_Up",
                    #         "zhuanzhe_between_pens": [j, j+1],
                    #     }
                    #     zhuanzhes.append(zhuanzhe)
                    #     i = j + 1
                    #     core_pens = []
                    #     zhongshu_stop = True
                    #     break
                else:
                    # 继续延伸
                    # print(f"{i+1}笔开始的中枢在延伸")
                    if zgzd_type == "practical":
                        zg = min(zg, next_pen['top_price'])
                        zd = max(zd, next_pen['bottom_price'])
                    end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                    core_pens.append(next_pen)
                    core_pens.append(next_next_pen)
                    j += 2
            # 如果遍历结束没有离开笔，停止
            if not zhongshu_stop:
                i = len(pens)

            # 添加中枢
            if (len(core_pens) >= 3):
                zhongshu = {
                    "ZG": classical_zg if zgzd_type == "classical" else zg,
                    "ZD": classical_zd if zgzd_type == "classical" else zd,
                    "start_time": start_time,
                    "end_time": end_time,
                    "core_pens": core_pens,
                    "GG": max([pen["top_price"] for pen in core_pens]),
                    "DD": min([pen["bottom_price"] for pen in core_pens]),
                    "direction": first_pen['direction'],
                    "zhongshu_jieshu": zhongshu_stop,
                    "kuozhan": times_kuozhan    #中枢扩展次数
                }
                zhongshus.append(zhongshu)

        # else:
        #    # 如果进入笔和离开笔方向不一致，或者第三笔突破原走势极值，跳过
        #    i += 1
        else:
            # 三段没有重合
            i += 1
    return zhongshus, zhuanzhes









# 寻找笔中枢的函数
def find_zhongshu_one_pen_can_be_a_zhongshu(pens, zgzd_type="classical"):
    """
    从缠论的笔中找出所有中枢，支持延伸和离开笔确认，允许两种 ZG/ZD 逻辑
    参数:
        pens: 包含每一笔信息的列表，每个元素是字典，包含:
              'top_price', 'bottom_price', 'top_time', 'bottom_time'
        zgzd_type: 中枢高低区间的计算逻辑：
                   "classical" - 确立 ZG/ZD 后不再更新
                   "practical" - ZG/ZD 随后续笔动态更新
    返回:
        zhongshus: 包含每个中枢的高点区间（ZG）、低点区间（ZD）、时间范围和构成的核心笔列表
    """
    zhongshus = []  # 存储所有中枢
    i = 0  # 从第一笔开始
    zoushi_direction = pens[0]['direction'] #当前走势的方向，也就是中枢前一笔的方向

    while i < len(pens) - 5:  # 至少需要 5 笔才能开始判断
        # 判断进入笔和离开笔方向是否一致
        first_pen = pens[i]
        second_pen = pens[i + 1]
        third_pen = pens[i + 2]
        fourth_pen = pens[i + 3]
        fifth_pen = pens[i + 4]


        single_pen_zhongshu = False
        # 考察一笔的中枢
        if first_pen['direction'] == 'Down':
            zg = second_pen['top_price']
            zd = second_pen['bottom_price']
            if (first_pen['top_price'] > zg) and (zd > third_pen['bottom_price']):
                if not ((zd < fifth_pen['bottom_price'] < zg) or  (zd < fifth_pen['top_price'] < zg)):
                    # print("单笔中枢")
                    GG = second_pen['top_price']
                    DD = second_pen['bottom_price']
                    single_pen_zhongshu = True
        elif first_pen['direction'] == 'Up':
            zg = second_pen['top_price']
            zd = second_pen['bottom_price']
            if (first_pen['bottom_price'] < zd) and (zg < third_pen['top_price']):
                if not ((zd < fifth_pen['bottom_price'] < zg) or  (zd < fifth_pen['top_price'] < zg)):
                    # print("单笔中枢")
                    GG = second_pen['top_price']
                    DD = second_pen['bottom_price']
                    single_pen_zhongshu = True
        if single_pen_zhongshu:
            zhongshu = {
                "ZG": zg,
                "ZD": zd,
                "start_time": min(second_pen['top_time'], second_pen['bottom_time']),
                "end_time": max(second_pen['top_time'], second_pen['bottom_time']),
                "core_pens": [second_pen],
                "GG": GG,
                "DD": DD,
                "direction": first_pen['direction']
            }
            zhongshus.append(zhongshu)
            i+=1

        if not single_pen_zhongshu:
            # 判断进入笔和离开笔的方向是否一致
            # 初始化中枢的高低区间
            # zg = min(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
            # zd = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
            # zg = min(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
            # zd = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
            GG = max(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
            DD = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
            zg = min(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
            zd = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
            #if ((zg > zd) and (zg <= first_pen['top_price']) and (zd >= first_pen['bottom_price']) and (zg <= fifth_pen['top_price']) and (zd >= fifth_pen['bottom_price'])):

            newhigh_or_newlow = True
            zhuanzhe = True
            if zhongshus:
                newhigh_or_newlow = False
                zhuanzhe = False
                # 延续前方向后，创新高或者破新低, 但可能中枢扩展
                if (zg > zd) and (first_pen['direction'] == zhongshus[-1]['direction']):
                    newhigh_or_newlow = (((first_pen['top_price'] > zhongshus[-1]["GG"]) and (first_pen['direction'] == 'Up')) or ((first_pen['bottom_price'] < zhongshus[-1]["DD"])  and (first_pen['direction'] == 'Down')))
                    # if ((first_pen['direction'] == 'Down') and GG >= zhongshus[-1]["ZD"]) or ((first_pen['direction'] == 'Up') and DD >= zhongshus[-1]["ZG"]): #中枢扩展
                    #     print("中枢扩展")
                    # else:
                    #     print("新中枢")
                elif (zg > zd) and (zoushi_direction != first_pen['direction']): # 转折出现但可能中枢扩展
                    if ((first_pen['direction'] == 'Down') and GG >= zhongshus[-1]["ZD"]) or ((first_pen['direction'] == 'Up') and DD >= zhongshus[-1]["ZG"]):
                        # 上一个的中枢扩展或转折
                        # 先当中枢扩展处理
                        zhuanzhe = False
                        # 如果是转折，以前面是以上涨为例，如果第四笔不创新高，拿第一笔开头就是一卖，是转折，第四笔就是一卖
                    else: #转折
                        zoushi_direction = first_pen['direction']
                        zhuanzhe = True
                        #print("转折出现")

            if (zg > zd) and (newhigh_or_newlow or zhuanzhe):
                start_time = min(second_pen['top_time'], second_pen['bottom_time'])
                end_time = max(fourth_pen['top_time'], fourth_pen['bottom_time'])
                # end_time = max(third_pen['top_time'], third_pen['bottom_time'])
                # end_time = max(second_pen['top_time'], second_pen['bottom_time'])

                core_pens = [second_pen, third_pen, fourth_pen]
                # core_pens = [second_pen, third_pen]
                # core_pens = [second_pen]

                # 如果是 "classical"，初始 ZG/ZD 不更新
                classical_zg = zg
                classical_zd = zd

                # 标记中枢有没有结束
                zhongshu_stop = False

                # 延伸中枢
                j = i + 4
                # j = i + 3
                # j = i + 2
                # for j in range(i + 4, len(pens) - 1):
                while j < len(pens) - 2:  # 至少留二笔用于离开确认
                    next_pen = pens[j]

                    next_next_pen = pens[j + 1]


                    if ((zoushi_direction == 'Down') and (next_pen['bottom_price'] < zd)) or (
                            (zoushi_direction == 'Up') and (next_pen['top_price'] > zg)):  # 下一笔暂时离开, 延续前趋势
                        if (((zoushi_direction == 'Down') and (next_next_pen['top_price'] < zd)) or (
                                (zoushi_direction == 'Up') and (next_next_pen['bottom_price'] > zg))):  # 确认离开, 延续前趋势
                            # i = j - 1  # 从离开笔重新开始判断， 要减一因为离开的最后一笔要视为中枢后的方向的第一笔
                            i = j
                            zhongshu_stop = True
                            break
                        elif (((zoushi_direction == 'Down') and (next_next_pen['top_price'] > zg)) or (
                                (zoushi_direction == 'Up') and (next_next_pen['bottom_price'] < zd))) and (
                                next_pen['direction'] == zoushi_direction):  # 反向离开, 有可能开启新的走势，也可以是中枢扩张
                            # 再往后看一笔，如果回到前中枢，就是中枢延续，否则，是为转折
                            if ((next_pen['direction'] == 'Down') and (pens[j + 2]['bottom_price'] > zg)) or (
                                    (next_pen['direction'] == 'Up') and (pens[j + 2]['top_price'] < zd)):  # 没有回到中枢，转折
                                i = j + 1
                                zhongshu_stop = True
                                break
                            else:
                                #print(f"zd is {zd}, \n zg is {zg}, \n next_next_pen bottom_price is {next_next_pen['bottom_price']} \n next_pen direction{next_pen['direction']}")

                                # 再次回到中枢，延续中枢
                                if zgzd_type == "practical":
                                    zg = min(zg, next_pen['top_price'])
                                    zd = max(zd, next_pen['bottom_price'])
                                GG = max(next_pen["top_price"], GG)
                                DD = min(next_pen["bottom_price"], DD)
                                end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                                # end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                                core_pens.append(next_pen)
                                core_pens.append(next_next_pen)
                                j += 2  ###这里可能要加二因为后面两笔都被考察过了是否适合写入中枢
                        else:
                            # 再次回到中枢，延续中枢
                            if zgzd_type == "practical":
                                zg = min(zg, next_pen['top_price'])
                                zd = max(zd, next_pen['bottom_price'])
                            GG = max(next_pen["top_price"], GG)
                            DD = min(next_pen["bottom_price"], DD)
                            end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                            # end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                            core_pens.append(next_pen)
                            core_pens.append(next_next_pen)
                            j += 2  ###这里可能要加二因为后面两笔都被考察过了是否适合写入中枢
                    elif ((zoushi_direction == 'Down') and (next_next_pen['top_price'] > zg)) or (
                            (zoushi_direction == 'Up') and (
                            next_next_pen['bottom_price'] < zd)):  # 下一笔没有离开, 下下笔反向离开, 有可能开启新的走势，也可以是中枢扩张
                        # 再往后看一笔，如果回到前中枢，就是中枢延续，否则，是为转折
                        if ((next_pen['direction'] == 'Down') and (pens[j + 2]['bottom_price'] > zg)) or (
                                (next_pen['direction'] == 'Up') and (pens[j + 2]['top_price'] < zd)):  # 没有回到中枢，转折
                            i = j + 1
                            zhongshu_stop = True
                            break
                        else:
                            # 再次回到中枢，延续中枢
                            if zgzd_type == "practical":
                                zg = min(zg, next_pen['top_price'])
                                zd = max(zd, next_pen['bottom_price'])
                            GG = max(next_pen["top_price"], GG)
                            DD = min(next_pen["bottom_price"], DD)
                            end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                            # end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                            core_pens.append(next_pen)
                            core_pens.append(next_next_pen)
                            j += 2  ###这里可能要加二因为后面两笔都被考察过了是否适合写入中枢

                    else:
                        # 继续延伸
                        if zgzd_type == "practical":
                            zg = min(zg, next_pen['top_price'])
                            zd = max(zd, next_pen['bottom_price'])
                        end_time = max(next_pen['top_time'], next_pen['bottom_time'])
                        core_pens.append(next_pen)
                        j += 1
                # 如果遍历结束没有离开笔，停止
                if not zhongshu_stop:
                    i = len(pens)

                # 添加中枢
                if (len(core_pens) >= 3):
                    zhongshu = {
                        "ZG": classical_zg if zgzd_type == "classical" else zg,
                        "ZD": classical_zd if zgzd_type == "classical" else zd,
                        "start_time": start_time,
                        "end_time": end_time,
                        "core_pens": core_pens,
                        "GG": max([pen["top_price"] for pen in core_pens]),
                        "DD": min([pen["bottom_price"] for pen in core_pens]),
                        "direction": first_pen['direction']
                    }
                    zhongshus.append(zhongshu)

            # else:
            #    # 如果进入笔和离开笔方向不一致，或者第三笔突破原走势极值，跳过
            #    i += 1
            else:
                # 三段没有重合
                i += 1
    return zhongshus








    


def new_zhongshu(current_pen):
    zhongshu = {
        "ZG": current_pen['top_price'],
        "ZD": current_pen['bottom_price'],
        "start_time": current_pen['top_time'] if current_pen['direction'] == 'Down' else current_pen['bottom_time'],
        "end_time": current_pen['bottom_time'] if current_pen['direction'] == 'Down' else current_pen['top_time'],
        "core_pens": [current_pen],
        "GG": current_pen['top_price'],
        "DD": current_pen['bottom_price']
    }
    return zhongshu




# 寻找笔中枢的函数
def find_zhongshu_csy_steps(pens):
    zhongshus = []  # 存储所有中枢
    i = 0  # 从第一笔开始
    current_direction = pens[0]['direction'] #前面筛选了数据的起点，所以可以保证i=0是一个趋势的起点
    last_pen = pens[i]
    zg = last_pen['top_price']
    zd = last_pen['bottom_price']
    i = 1  # 从第二笔开始
    current_pen = pens[i]
    next_pen = pens[i + 1]
    #根据前三笔，构建第一个中枢
    if current_pen['direction'] == 'Down':
        if current_pen['bottom_price'] >= zd:
            if next_pen['top_price'] <= zg: #第一笔上，第二笔下，第二笔不跌破第一笔，第三笔不突破前两笔高点，第三笔先算中枢第一段
                current_zhongshu = new_zhongshu(next_pen)
                i = 3
            else:  #第一笔上，第二笔下，第二笔不跌破第一笔，第三笔突破前两笔高点，第二笔算中枢
                current_zhongshu = new_zhongshu(current_pen)
                i = 2
        else:
            if next_pen['top_price'] < zd: #第一笔上，第二笔下突破，第三笔上不到第一笔低点，第二笔是向下趋势，第三笔出中枢
                current_zhongshu = new_zhongshu(next_pen)
                i = 3
            elif next_pen['top_price'] < zg: #第一笔上，第二笔下突破，第三笔上到第一笔低点但不到第一笔高点，前三笔构成中枢
                current_zhongshu = new_zhongshu(last_pen)
                current_zhongshu['core_pens'].append(current_pen)
                current_zhongshu['core_pens'].append(next_pen)
                current_zhongshu['ZG'] = next_pen['top_price']
                current_zhongshu['ZD'] = last_pen['bottom_price']
                current_zhongshu['end_time'] = next_pen['bottom_time']
                current_zhongshu['DD'] = min(current_pen['bottom_price'], current_zhongshu['DD'])
                i = 3
            else: #第一笔上，第二笔下突破，第三笔向上破第一笔高点，暂把第一笔当中枢
                current_zhongshu = new_zhongshu(last_pen)
                i = 1
        zhongshus.append(current_zhongshu)
    else:
        pass
    #elif current_pen['direction'] == 'Up':
    #    if current_pen['top_price'] <= zg:  # 中枢延伸或中枢诞生
    #        if len(current_zhongshu['core_pens']) >= 1:  # 中枢延伸





    """
    while i < len(pens) - 1:
        current_pen = pens[i]
        next_pen = pens[i+1]
        zg = min(last_pen['top_price'], current_pen['top_price'], next_pen['top_price'])
        zd = max(last_pen['bottom_price'], current_pen['bottom_price'], next_pen['bottom_price'])
        if current_pen['direction'] == 'Down':
            if current_pen['bottom_price'] >= zd: #中枢延伸或中枢诞生
                if len(current_zhongshu['core_pens']) >=1: #中枢延伸
                    current_zhongshu['core_pens'].append(current_pen)
                    current_zhongshu['end_time'] = current_pen['bottom_time']
                    current_zhongshu['DD'] = min(current_pen['bottom_price'], current_zhongshu['DD'])
                else: #中枢新生
                    last_zhongshu = deepcopy(current_zhongshu)
                    current_zhongshu = new_zhongshu(current_pen)       
        elif current_pen['direction'] == 'Up':
            if current_pen['top_price'] <= zg: #中枢延伸或中枢诞生
                if len(current_zhongshu['core_pens']) >=1: #中枢延伸
        """

    return zhongshus






# 寻找笔中枢的函数
def find_zhongshu_csy_inverse_look_steps(pens):
    zhongshus = []  # 存储所有中枢
    i = len(pens)-1  # 从第一笔开始
    last_pen = pens[i]
    zg = last_pen['top_price']
    zd = last_pen['bottom_price']
    i = len(pens)-2  # 从第二笔开始
    current_pen = pens[i]
    next_pen = pens[len(pens)-3]
    #根据前三笔，构建第一个中枢
    if current_pen['direction'] == 'Down':
        if current_pen['bottom_price'] >= zd:
            if next_pen['top_price'] <= zg: #第一笔上，第二笔下，第二笔不跌破第一笔，第三笔不突破前两笔高点，第三笔先算中枢第一段
                current_zhongshu = new_zhongshu(next_pen)
                i = len(pens)-4
            else:  #第一笔上，第二笔下，第二笔不跌破第一笔，第三笔突破前两笔高点，第二笔算中枢
                current_zhongshu = new_zhongshu(current_pen)
                i = len(pens)-3
        else:
            if next_pen['top_price'] < zd: #第一笔上，第二笔下突破，第三笔上不到第一笔低点，第二笔是向下趋势，第三笔出中枢
                current_zhongshu = new_zhongshu(next_pen)
                i = len(pens)-4
            elif next_pen['top_price'] < zg: #第一笔上，第二笔下突破，第三笔上到第一笔低点但不到第一笔高点，前三笔构成中枢
                current_zhongshu = new_zhongshu(last_pen)
                current_zhongshu['core_pens'].append(current_pen)
                current_zhongshu['core_pens'].append(next_pen)
                current_zhongshu['ZG'] = next_pen['top_price']
                current_zhongshu['ZD'] = last_pen['bottom_price']
                current_zhongshu['end_time'] = next_pen['bottom_time']
                current_zhongshu['DD'] = min(current_pen['bottom_price'], current_zhongshu['DD'])
                i = len(pens)-4
            else: #第一笔上，第二笔下突破，第三笔向上破第一笔高点，暂把第一笔当中枢
                current_zhongshu = new_zhongshu(last_pen)
                i = len(pens)-2
        zhongshus.append(current_zhongshu)
    #elif current_pen['direction'] == 'Up':
    #    if current_pen['top_price'] <= zg:  # 中枢延伸或中枢诞生
    #        if len(current_zhongshu['core_pens']) >= 1:  # 中枢延伸





    """
    while i < len(pens) - 1:
        current_pen = pens[i]
        next_pen = pens[i+1]
        zg = min(last_pen['top_price'], current_pen['top_price'], next_pen['top_price'])
        zd = max(last_pen['bottom_price'], current_pen['bottom_price'], next_pen['bottom_price'])
        if current_pen['direction'] == 'Down':
            if current_pen['bottom_price'] >= zd: #中枢延伸或中枢诞生
                if len(current_zhongshu['core_pens']) >=1: #中枢延伸
                    current_zhongshu['core_pens'].append(current_pen)
                    current_zhongshu['end_time'] = current_pen['bottom_time']
                    current_zhongshu['DD'] = min(current_pen['bottom_price'], current_zhongshu['DD'])
                else: #中枢新生
                    last_zhongshu = deepcopy(current_zhongshu)
                    current_zhongshu = new_zhongshu(current_pen)       
        elif current_pen['direction'] == 'Up':
            if current_pen['top_price'] <= zg: #中枢延伸或中枢诞生
                if len(current_zhongshu['core_pens']) >=1: #中枢延伸
        """

    return zhongshus
    
    
    
    
    
# 寻找笔中枢的函数
def find_zhongshu_and_cijibie_qushi(pens, zgzd_type="classical"):
    """
    从缠论的笔中找出所有中枢，支持延伸和离开笔确认，允许两种 ZG/ZD 逻辑
    参数:
        pens: 包含每一笔信息的列表，每个元素是字典，包含:
              'top_price', 'bottom_price', 'top_time', 'bottom_time'
        zgzd_type: 中枢高低区间的计算逻辑：
                   "classical" - 确立 ZG/ZD 后不再更新
                   "practical" - ZG/ZD 随后续笔动态更新
    返回:
        zhongshus: 包含每个中枢的高点区间（ZG）、低点区间（ZD）、时间范围和构成的核心笔列表
    """
    zhongshus = []  # 存储所有中枢
    cijibie_qushis = [] # 存储连接中枢的趋势
    cijibie_qushis_index = []
    i = 0  # 从第一笔开始
    index_last_zhongshu_stop = 0
    zhongshu_least_bi = 3 # 中枢至少有几笔，以此画出不一样的结果

    
    while i < len(pens) - 5:  # 至少需要 5 笔才能开始判断
        # 判断进入笔和离开笔方向是否一致
        first_pen = pens[i]
        second_pen = pens[i + 1]
        third_pen = pens[i + 2]
        fourth_pen = pens[i + 3]
        fifth_pen = pens[i + 4]
        
        
        """
        max_five_pen = max(first_pen['top_price'], second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'], fifth_pen['top_price'])
        min_five_pen = min(first_pen['bottom_price'], second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'], fifth_pen['bottom_price'])
        # 考察前面结束的中枢是不是要扩张
        if (zhongshu_stop):
            if (max_five_pen < zhongshus[-1]["ZG"] and max_five_pen > zhongshus[-1]["ZD"]) or (min_five_pen < zhongshus[-1]["ZG"] and min_five_pen > zhongshus[-1]["ZD"]):
                zhongshus[-1]
        """
        
            
                
            

        # 判断进入笔和离开笔的方向是否一致
        # 初始化中枢的高低区间
        if zhongshu_least_bi == 3:
            zg = min(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
            zd = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
        elif zhongshu_least_bi == 2:
            zg = min(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
            zd = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
        elif zhongshu_least_bi == 1:
            zg = min(second_pen['top_price'], third_pen['top_price'], fourth_pen['top_price'])
            zd = max(second_pen['bottom_price'], third_pen['bottom_price'], fourth_pen['bottom_price'])
        if (zg > zd) and (zg <= first_pen['top_price']) and (zd >= first_pen['bottom_price']):
                start_time = min(second_pen['top_time'], second_pen['bottom_time'])
                if zhongshu_least_bi == 3:
                    end_time = max(fourth_pen['top_time'], fourth_pen['bottom_time'])
                    core_pens = [second_pen, third_pen, fourth_pen]
                    j = i + 4
                elif zhongshu_least_bi == 2:
                    end_time = max(third_pen['top_time'], third_pen['bottom_time'])
                    core_pens = [second_pen, third_pen]
                    j = i + 3
                elif zhongshu_least_bi == 1:
                    end_time = max(second_pen['top_time'], second_pen['bottom_time'])
                    core_pens = [second_pen]
                    j = i + 2
                

                # 如果是 "classical"，初始 ZG/ZD 不更新
                classical_zg = zg
                classical_zd = zd
                
                
                #标记中枢有没有结束
                zhongshu_stop = False
                

                # 延伸中枢
                #for j in range(i + 4, len(pens) - 1):
                while j < len(pens) - 1: # 至少留一笔用于离开确认
                    next_pen = pens[j]
                    
                    next_next_pen = pens[j + 1]

                    if ((next_pen['direction'] == 'Down') and (next_pen['bottom_price'] < zd)) or ((next_pen['direction'] == 'Up') and (next_pen['top_price'] > zg)): # 暂时离开,
                        if (((next_pen['direction'] == 'Down') and (next_next_pen['top_price'] < zd)) or ((next_pen['direction'] == 'Up') and (next_next_pen['bottom_price'] > zg))):  # 确认离开, 延续前趋势
                            # i = j - 1  # 从离开笔重新开始判断， 要减一因为离开的最后一笔要视为中枢后的方向的第一笔
                            # cijibie_qushis.append(pens[index_last_zhongshu_stop:i+1])
                            cijibie_qushis_index.append([index_last_zhongshu_stop, i+1])
                            i = j
                            index_last_zhongshu_stop = j
                            zhongshu_stop = True
                            break
                        elif (((next_pen['direction'] == 'Down') and (next_next_pen['top_price'] > zg)) or ((next_pen['direction'] == 'Up') and (next_next_pen['bottom_price'] < zd))) and (next_pen['direction'] == first_pen['direction']):  # 反向离开, 有可能开启新的走势，也可以是中枢扩张，单独画一个中枢便于分析
                            # cijibie_qushis.append(pens[index_last_zhongshu_stop:i+1])
                            cijibie_qushis_index.append([index_last_zhongshu_stop, i+1])
                            i = j
                            index_last_zhongshu_stop = j
                            zhongshu_stop = True
                            break
                        else:
                            # 再次回到中枢，延续中枢
                            if zgzd_type == "practical":
                                zg = min(zg, next_pen['top_price'])
                                zd = max(zd, next_pen['bottom_price'])
                            end_time = max(next_pen['top_time'], next_pen['bottom_time'])
                            #end_time = max(next_next_pen['top_time'], next_next_pen['bottom_time'])
                            core_pens.append(next_pen)
                            #core_pens.append(next_next_pen)
                            j += 1 ###这里可能要加二因为后面两笔都被考察过了是否适合写入中枢
                    else:
                        # 继续延伸
                        if zgzd_type == "practical":
                            zg = min(zg, next_pen['top_price'])
                            zd = max(zd, next_pen['bottom_price'])
                        end_time = max(next_pen['top_time'], next_pen['bottom_time'])
                        core_pens.append(next_pen)
                        j += 1
                # 如果遍历结束没有离开笔，停止
                if not zhongshu_stop:
                    i = len(pens)

                # 添加中枢
                # 中枢要求三段，但这里两段就把它先存下来，如果后面是趋势延续就不要这一段，如果后面是转折就不要这一段，如果后面是中枢扩张就把这一段扩张
                if (len(core_pens) >= 2):
                    zhongshu = {
                        "ZG": classical_zg if zgzd_type == "classical" else zg,
                        "ZD": classical_zd if zgzd_type == "classical" else zd,
                        "start_time": start_time,
                        "end_time": end_time,
                        "core_pens": core_pens,
                        "GG": max([pen["top_price"] for pen in core_pens]),
                        "DD": min([pen["bottom_price"] for pen in core_pens])
                    }
                    #print(f'zhongshu top price is {zhongshu["GG"]} and zhongshu bottom price is {zhongshu["DD"]}')
                    zhongshus.append(zhongshu)
                #elif (len(core_pens) < 2) and (len(core_pens) > 0):
                #    cijibie_qushis_index[-2][1] = deepcopy(cijibie_qushis_index[-1][1])
                #    cijibie_qushis_index.pop(-1)
            #else:
            #    # 如果进入笔和离开笔方向不一致，或者第三笔突破原走势极值，跳过
            #    i += 1
        else:
            # 三段没有重合
            i += 1
    last_start_index = 999999999
    last_end_index = 999999999
    for qushi_index in range(len(cijibie_qushis_index)):
        cijibie_qushis.append(pens[cijibie_qushis_index[qushi_index][0]:cijibie_qushis_index[qushi_index][1]])
        """
        if cijibie_qushis_index[qushi_index][0] == last_end_index+zhongshu_least_bi:
            cijibie_qushis[-1] = pens[last_start_index:cijibie_qushis_index[qushi_index][1]]
            last_end_index = cijibie_qushis_index[qushi_index][1]
        else:
            cijibie_qushis.append(pens[cijibie_qushis_index[qushi_index][0]:cijibie_qushis_index[qushi_index][1]])
            last_start_index = cijibie_qushis_index[qushi_index][0]
            last_end_index = cijibie_qushis_index[qushi_index][1]
        """
    return zhongshus, cijibie_qushis
    
    
    
    
    
    

    
    
#
# def draw_zhongshu(fig, zhongshus, row, col, level):
#     """
#     在 K 线图上绘制中枢的方框
#     参数:
#         fig: Plotly 图表对象
#         zhongshus: 中枢列表，每个中枢是一个字典，包含 'ZG', 'ZD', 'start_time', 'end_time'
#         row: 绘制在的图表行
#         col: 绘制在的图表列
#     """
#     if (level=="pen"):
#         for zhongshu in zhongshus:
#             # 添加中枢的矩形框
#             fig.add_shape(
#                 type="rect",
#                 # x0=zhongshu["start_time"],
#                 # x1=zhongshu["end_time"],
#                 x0=ensure_datetime(zhongshu["start_time"]),
#                 x1=ensure_datetime(zhongshu["end_time"]),
#                 y0=zhongshu["ZD"],
#                 y1=zhongshu["ZG"],
#                 line=dict(color="blue", width=2),
#                 fillcolor="rgba(0, 0, 255, 0.2)",  # 半透明蓝色
#                 xref=f'x{col}',
#                 yref=f'y{row}',
#             )
          
            
            
# 计算 MACD、DIF、DEA 和柱状图
def calculate_macd(MACD_kline_df, fast_period=12, slow_period=26, signal_period=9):
    """
    计算 MACD 指标（DIF、DEA 和 MACD 柱状图）
    参数:
        df: 包含 'close' 列的 DataFrame
        fast_period: 快速 EMA 周期
        slow_period: 慢速 EMA 周期
        signal_period: 信号线 EMA 周期
    返回:
        df: 包含 'DIF', 'DEA', 'MACD' 的 DataFrame
    """
    MACD_kline_df['EMA_fast'] = MACD_kline_df['close'].ewm(span=fast_period, adjust=False).mean()
    MACD_kline_df['EMA_slow'] = MACD_kline_df['close'].ewm(span=slow_period, adjust=False).mean()
    MACD_kline_df['DIF'] = MACD_kline_df['EMA_fast'] - MACD_kline_df['EMA_slow']  # DIF 线
    MACD_kline_df['DEA'] = MACD_kline_df['DIF'].ewm(span=signal_period, adjust=False).mean()  # DEA 线
    MACD_kline_df['MACD'] = (MACD_kline_df['DIF'] - MACD_kline_df['DEA']) * 2  # MACD 柱状图（放大倍数为 2）
    return MACD_kline_df





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
                line=dict(color="purple", width=3),
                fillcolor="rgba(0, 0, 255, 0.2)",  # 半透明蓝色
                xref=f'x{col}',
                yref=f'y{row}',
            )



def ensure_datetime(ts):
    return datetime.fromisoformat(ts) if isinstance(ts, str) else ts

# def convert_timestamps(obj):
#     if isinstance(obj, list):
#         return [convert_timestamps(o) for o in obj]
#     elif isinstance(obj, dict):
#         return {
#             k: convert_timestamps(v) for k, v in obj.items()
#         }
#     elif isinstance(obj, (pd.Timestamp, datetime)):
#         return str(obj)
#     else:
#         return obj
# def convert_timestamps(obj):
#     if isinstance(obj, list):
#         return [convert_timestamps(o) for o in obj]
#     elif isinstance(obj, dict):
#         return {k: convert_timestamps(v) for k, v in obj.items()}
#     elif isinstance(obj, (pd.Timestamp, datetime)):
#         return obj.isoformat(timespec="seconds")  # 转成形如 '2024-12-16T20:30:02'
#     else:
#         return obj


def convert_timestamps(obj):
    if isinstance(obj, list):
        return [convert_timestamps(o) for o in obj]
    elif isinstance(obj, dict):
        return {k: convert_timestamps(v) for k, v in obj.items()}
    elif isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat(timespec="seconds")
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()  # 转为 Python 原生 int 或 float
    else:
        return obj




def save_new_segments_fix_to_checkpoint(segments_fix, segment_zhongshus_clean, stock_name_and_market, seconds_level=6):
    save_dir = f"checkpoint_segment_{seconds_level}_seconds"
    os.makedirs(save_dir, exist_ok=True)

    filename = f"{stock_name_and_market}_segments.ndjson"
    file_path = os.path.join(save_dir, filename)

    if not segment_zhongshus_clean:
        print("segment_zhongshus_clean is empty. Nothing will be saved.")
        return

    if len(segment_zhongshus_clean) <= 1:
        upper_index_limit = max(len(segments_fix) - 5, 1)
    else:
        upper_index_limit = segment_zhongshus_clean[-1]["core_pens_index"][0]

    # 先按 index 限制过滤
    filtered_segments = [seg for i, seg in enumerate(segments_fix) if i < upper_index_limit]


    # 如果文件存在，尝试读取最后一条的完成时间
    last_complete_time = None
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if lines:
            try:
                last_segment = json.loads(lines[-1])
                last_complete_time = pd.Timestamp(max(last_segment["top_time"], last_segment["bottom_time"]))
            except Exception as e:
                print(f"Failed to parse last line of existing NDJSON file: {e}")
                return
        # 如果文件为空，不设置 last_complete_time，直接跳过时间限制

    # 如果有 last_complete_time，再进行时间过滤
    if last_complete_time is not None:
        cut_index = len(filtered_segments)
        for i in reversed(range(len(filtered_segments))):
            seg = filtered_segments[i]
            min_time = min(seg["top_time"], seg["bottom_time"])
            if isinstance(min_time, str):
                min_time = pd.Timestamp(min_time)
            if min_time < last_complete_time:
                cut_index = i + 1
                break
        # filtered_segments = filtered_segments[cut_index:]
        # 权宜之计，靠谱的解决就是把把每次处理的总时长变长一点，让完整的中枢走出来
        if min(filtered_segments[0]["top_time"], filtered_segments[0]["bottom_time"]) >= last_complete_time:
            filtered_segments = filtered_segments[0:]
        else:
            filtered_segments = filtered_segments[cut_index:]

    if not filtered_segments:
        print("No new segments to save.")
        return

    # 写入 NDJSON 文件（追加模式）
    with open(file_path, 'a', encoding='utf-8') as f:
        for seg in filtered_segments:
            seg_str = json.dumps(convert_timestamps(seg), ensure_ascii=False)
            f.write(seg_str + '\n')

    print(f"Appended {len(filtered_segments)} new segments to {file_path} (NDJSON format)")





def save_new_segments_fix_to_checkpoint_pen(fixed_pens, pen_zhongshus, stock_name_and_market, seconds_level=6):
    save_dir = f"checkpoint_pen_{seconds_level}_seconds"
    os.makedirs(save_dir, exist_ok=True)

    filename = f"{stock_name_and_market}_segments.ndjson"
    file_path = os.path.join(save_dir, filename)

    if not pen_zhongshus:
        print("pen_zhongshus is empty. Nothing will be saved.")
        return

    if len(pen_zhongshus) <= 1:
        upper_index_limit = max(len(pen_zhongshus) - 5, 1)
    else:
        upper_index_limit = pen_zhongshus[-1]["core_pens_index"][0]

    # 先按 index 限制过滤
    filtered_segments = [seg for i, seg in enumerate(fixed_pens) if i < upper_index_limit]


    # 如果文件存在，尝试读取最后一条的完成时间
    last_complete_time = None
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if lines:
            try:
                last_segment = json.loads(lines[-1])
                last_complete_time = pd.Timestamp(max(last_segment["top_time"], last_segment["bottom_time"]))
            except Exception as e:
                print(f"Failed to parse last line of existing NDJSON file: {e}")
                return
        # 如果文件为空，不设置 last_complete_time，直接跳过时间限制

    # 如果有 last_complete_time，再进行时间过滤
    if last_complete_time is not None:
        cut_index = len(filtered_segments)
        for i in reversed(range(len(filtered_segments))):
            seg = filtered_segments[i]
            min_time = min(seg["top_time"], seg["bottom_time"])
            if isinstance(min_time, str):
                min_time = pd.Timestamp(min_time)
            if min_time < last_complete_time:
                cut_index = i + 1
                break
        # filtered_segments = filtered_segments[cut_index:]
        # 权宜之计，靠谱的解决就是把把每次处理的总时长变长一点，让完整的中枢走出来
        if min(filtered_segments[0]["top_time"], filtered_segments[0]["bottom_time"]) >= last_complete_time:
            filtered_segments = filtered_segments[0:]
        else:
            filtered_segments = filtered_segments[cut_index:]

    if not filtered_segments:
        print("No new segments to save.")
        return

    # 写入 NDJSON 文件（追加模式）
    with open(file_path, 'a', encoding='utf-8') as f:
        for seg in filtered_segments:
            seg_str = json.dumps(convert_timestamps(seg), ensure_ascii=False)
            f.write(seg_str + '\n')

    print(f"Appended {len(filtered_segments)} new segments to {file_path} (NDJSON format)")




def save_new_pen_zhongshu_to_checkpoint(pen_zhongshus, stock_name_and_market, seconds_level=6):
    save_dir = f"checkpoint_pen_zhongshus_{seconds_level}_seconds"
    os.makedirs(save_dir, exist_ok=True)

    filename = f"{stock_name_and_market}_pen_zhongshus.ndjson"
    file_path = os.path.join(save_dir, filename)

    if not pen_zhongshus:
        print("pen_zhongshus is empty. Nothing will be saved.")
        return



    if len(pen_zhongshus) <= 16:
        upper_index_limit = 5
    else:
        upper_index_limit = len(pen_zhongshus) - 15

    # 先按 index 限制过滤
    filtered_pen_zhongshus = [pen_zhongshu for i, pen_zhongshu in enumerate(pen_zhongshus) if i < upper_index_limit]


    # 如果文件存在，尝试读取最后一条的完成时间
    last_complete_time = None
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if lines:
            try:
                last_zhongshu = json.loads(lines[-1])
                last_complete_time = pd.Timestamp(last_zhongshu["end_time"])
            except Exception as e:
                print(f"Failed to parse last line of existing NDJSON file: {e}")
                return
        # 如果文件为空，不设置 last_complete_time，直接跳过时间限制

    # 如果有 last_complete_time，再进行时间过滤
    if last_complete_time is not None:
        cut_index = len(filtered_pen_zhongshus)
        for i in reversed(range(len(filtered_pen_zhongshus))):
            zhongshu = filtered_pen_zhongshus[i]
            min_time = zhongshu["start_time"]
            if isinstance(min_time, str):
                min_time = pd.Timestamp(min_time)
            if min_time < last_complete_time:
                cut_index = i + 1
                break

        # 权宜之计，靠谱的解决就是把把每次处理的总时长变长一点，让完整的中枢走出来
        if filtered_pen_zhongshus[0]["start_time"] >= last_complete_time:
            filtered_pen_zhongshus = filtered_pen_zhongshus[0:]
        else:
            filtered_pen_zhongshus = filtered_pen_zhongshus[cut_index:]

    if not filtered_pen_zhongshus:
        print("No new pen_zhongshus to save.")
        return

    # 写入 NDJSON 文件（追加模式）
    with open(file_path, 'a', encoding='utf-8') as f:
        for zhongshu in filtered_pen_zhongshus:
            zhongshu_str = json.dumps(convert_timestamps(zhongshu), ensure_ascii=False)
            f.write(zhongshu_str + '\n')

    print(f"Appended {len(filtered_pen_zhongshus)} new pen_zhongshus to {file_path} (NDJSON format)")




def load_segments_from_ndjson(file_path):
    segments = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                segments.append(json.loads(line.strip()))
                # try:
                #     segments.append(json.loads(line.strip()))
                # except json.JSONDecodeError as e:
                #     print(f"Error at line {line}")
                #     raise e
    return segments

# load_structure_from_ndjson 作用和load_segments_from_ndjson一样 都是按行读取ndjson,泛化一下

def load_structure_from_ndjson(file_path):
    structure = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                structure.append(json.loads(line.strip()))
    return structure


def merge_segments_fix_with_checkpoint(segments_fix, stock_name_and_market, seconds_level=6, for_segment=True):
    if for_segment:
        folder_path = f"checkpoint_segment_{seconds_level}_seconds"
    else:
        folder_path = f"checkpoint_pen_{seconds_level}_seconds"
    file_path = os.path.join(folder_path, f"{stock_name_and_market}_segments.ndjson")

    if not os.path.exists(file_path):
        print("No existing file. Returning original segments_fix.")
        return segments_fix

    existing_segments = load_segments_from_ndjson(file_path)
    if not existing_segments:
        print("Existing NDJSON is empty. Returning original segments_fix.")
        return segments_fix

    last_seg = existing_segments[-1]
    last_time = pd.Timestamp(max(last_seg["top_time"], last_seg["bottom_time"]))

    # 倒序查找切割点，提高效率
    cut_index = len(segments_fix)
    for i in reversed(range(len(segments_fix))):
        seg = segments_fix[i]
        min_time = pd.Timestamp(min(seg["top_time"], seg["bottom_time"]))
        #if min_time <= last_time: ?????????????设为<= 最后的输出会遗漏一段，但可以避免新线段不完整是错线的风险
        if min_time < last_time:
            cut_index = i + 1
            break


    new_segments = segments_fix[cut_index:]

    print(f"Merging {len(new_segments)} new segments with {len(existing_segments)} existing segments.")
    return existing_segments + convert_timestamps(new_segments)





def merge_zhongshu_with_checkpoint(pen_zhongshus, stock_name_and_market, seconds_level=6):
    folder_path = f"checkpoint_pen_zhongshus_{seconds_level}_seconds"
    file_path = os.path.join(folder_path, f"{stock_name_and_market}_pen_zhongshus.ndjson")

    if not os.path.exists(file_path):
        print("No existing file. Returning original pen_zhongshus.")
        return pen_zhongshus, pen_zhongshus

    existing_pen_zhongshus = load_structure_from_ndjson(file_path)
    if not existing_pen_zhongshus:
        print("Existing NDJSON is empty. Returning original pen_zhongshus.")
        return pen_zhongshus, pen_zhongshus

    last_pen_zhongshu = existing_pen_zhongshus[-1]
    last_time = pd.Timestamp(last_pen_zhongshu["end_time"])

    # 倒序查找切割点，提高效率
    cut_index = len(pen_zhongshus)
    for i in reversed(range(len(pen_zhongshus))):
        pen_zhongshu = pen_zhongshus[i]
        min_time = pd.Timestamp(pen_zhongshu["start_time"])
        #if min_time <= last_time: ?????????????设为<= 最后的输出会遗漏一段，但可以避免新线段不完整是错线的风险
        if min_time < last_time:
            cut_index = i + 1
            break


    new_zhongshus = pen_zhongshus[cut_index:]

    new_add_index_from = existing_pen_zhongshus[-1]["core_pens_index"][-1]
    minus_index = pen_zhongshus[cut_index-1]["core_pens_index"][-1]
    for i_new_zhongshu in range(len(new_zhongshus)):
        new_zhongshus[i_new_zhongshu]["core_pens_index"] = [
            x - minus_index + new_add_index_from for x in new_zhongshus[i_new_zhongshu]["core_pens_index"]
        ]


    print(f"Merging {len(new_zhongshus)} new zhongshus with {len(existing_pen_zhongshus)} existing segments.")
    return existing_pen_zhongshus + convert_timestamps(new_zhongshus), new_zhongshus





def greater_then_least_samelevel_tolerant(current_seg_num, previous_seg_num):
    least_samelevel = {1: 1, 2: 1, 3: 3, 4: 3, 5: 3}#, 7: 5}#, 9: 6, 11: 7, 13: 8, 15: 10}
    if current_seg_num <= 5:
        return previous_seg_num >= least_samelevel[current_seg_num]
    else:
        return previous_seg_num >= (current_seg_num * 2 + 2) // 3

def greater_then_least_samelevel_strict(current_seg_num, previous_seg_num):
    return previous_seg_num >= current_seg_num

def same_level_or_higher_level_before(history_long_time_segment_zhongshus_clean, history_long_time_segments, greater_then_least_samelevel=greater_then_least_samelevel_tolerant):
    # 检查中枢升级
    last_zhongshu_dierection = history_long_time_segment_zhongshus_clean[-1]["direction"]
    last_zhongshu_segment_number = len(history_long_time_segment_zhongshus_clean[-1]["core_pens_index"])

    find_same_level = False
    look_backward = True
    i = -2
    while look_backward:
        if history_long_time_segment_zhongshus_clean[i]["direction"] == last_zhongshu_dierection:
            if greater_then_least_samelevel(last_zhongshu_segment_number,
                                            len(history_long_time_segment_zhongshus_clean[i]["core_pens_index"])):
                # 如果同方向上有同级别中枢，可以参与
                look_backward = False
                find_same_level = True
            else:
                i -= 1
        else:
            if i < -2:
                # 看看和后面一段中枢能不能组合，不能组合后面线段长度+2处理：
                if greater_then_least_samelevel(last_zhongshu_segment_number, 2 + len(
                        history_long_time_segment_zhongshus_clean[i + 1]["core_pens_index"])):
                    look_backward = False
                    find_same_level = True
                elif max(history_long_time_segment_zhongshus_clean[i]["DD"],
                         history_long_time_segment_zhongshus_clean[i + 1]["DD"]) <= min(
                        history_long_time_segment_zhongshus_clean[i]["GG"],
                        history_long_time_segment_zhongshus_clean[i + 1]["GG"]):
                    # 中枢扩张带来的转折
                    if greater_then_least_samelevel(last_zhongshu_segment_number, 2 + len(
                            history_long_time_segment_zhongshus_clean[i + 1]["core_pens_index"]) + len(
                            history_long_time_segment_zhongshus_clean[i + 1]["core_pens_index"])):
                        look_backward = False
                        find_same_level = True
                    else:
                        look_backward = False
                else:
                    look_backward = False
            else:
                # 如果是个盘整，不参与
                look_backward = False
    return find_same_level



def check_zhongshu_kuozhang(zhongshu_prev, zhongshu_post):
    return max(zhongshu_prev["DD"], zhongshu_post["DD"]) <= min(zhongshu_prev["GG"], zhongshu_post["GG"])

def zhongshu_kuozhang_merge_same_dir(zhongshu_prev, zhongshu_post, segments):
    zhongshu_kuozhanged = {
        "ZG": min(zhongshu_prev["GG"], zhongshu_post["GG"]),
        "ZD": max(zhongshu_prev["DD"], zhongshu_post["DD"]),
        "start_time": zhongshu_prev["start_time"],
        "end_time": zhongshu_post["end_time"],
        "core_pens": zhongshu_prev["core_pens"] + [segments[zhongshu_prev["core_pens_index"][-1]+1]] + zhongshu_post["core_pens"],
        "core_pens_index": zhongshu_prev["core_pens_index"] + [zhongshu_prev["core_pens_index"][-1]+1] + zhongshu_post["core_pens_index"],
        "GG": max(zhongshu_prev["GG"], zhongshu_post["GG"]),
        "DD": min(zhongshu_prev["DD"], zhongshu_post["DD"]),
        "direction": zhongshu_prev["direction"],
        "zhongshu_jieshu": zhongshu_post["zhongshu_jieshu"],  # zhongshu_stop,
        "kuozhang": zhongshu_prev["kuozhang"]+1  # times_kuozhan  # 中枢扩张次数
    }
    return zhongshu_kuozhanged



class CurrentPlay:
    def __init__(self):
        self.reset()
        self.last_operation_seg_complete_time_zuokong = pd.to_datetime("2000-12-17 15:19:07")
        self.last_operation_seg_complete_time_zuoduo = pd.to_datetime("2000-12-17 15:19:07")
        # self.compare_pen_min_or_max = None #做空介入后，线段后笔的极大值，或做多后，线段后笔的极小值，以避免重复介入


    def reset(self):
        self.operation_direction = None  # 只能是 'Up' 或 'Down'
        self.yimai_time = None
        self.yimai_price = None
        self.yimai_status = "inactivate"  # 可为 long/short/candidate_*/inactivate
        self.ermai_time = None
        self.ermai_price = None
        self.ermai_status = "inactivate"  # 可为 long/short/inactivate
        self.yimai_ermai_in_same_center = False
        self.center_count_in_trend = 0
        self.support_price = None
        self.kuozhang = False
        self.join_price = None
        self.support_price_old_big_zhongshu = None



    def set_operation_direction(self, direction: str):
        if direction not in ['Up', 'Down']:
            raise ValueError("operation_direction must be 'Up' or 'Down'")
        self.operation_direction = direction

    def update_yimai(self, time, price, status=None):
        self.yimai_time = time
        self.yimai_price = price
        if status:
            self.set_yimai_status(status)

    def update_yimai_by_direction(self, segment, last_direction):
        """
        根据上一个中枢方向 last_direction 自动设定当前操作方向，并更新一买。

        Args:
            segment: dict，包含 bottom_time / bottom_price / top_time / top_price 等字段
            last_direction: str，"Up" 或 "Down"
        """
        if last_direction == "Down":
            self.set_operation_direction("Up")
        else:
            self.set_operation_direction("Down")
        if self.operation_direction == "Up":
            self.update_yimai(
                segment["bottom_time"],
                segment["bottom_price"],
                status="candidate_long"
            )
        elif self.operation_direction == "Down":
            self.update_yimai(
                segment["top_time"],
                segment["top_price"],
                status="candidate_short"
            )
        else:
            raise ValueError("operation_direction must be 'Up' or 'Down' before calling update_yimai_by_direction")

    def check_beichi(self, zhongshu, segment_new, segment_old, last_direction):
        """
        判断是否构成背驰：segment_new 和 segment_old 的波动区间对比。
        """
        if last_direction not in {"Up", "Down"}:
            raise ValueError("last_direction must be 'Up' or 'Down'")

        cores = [s for s in zhongshu["core_pens"] if s["direction"] == last_direction]

        if cores:
            if last_direction == "Down":
                ref = min(cores, key=lambda s: s["bottom_price"])
                final_new = ref if ref["bottom_price"] <= segment_new["bottom_price"] else segment_new
            else:  # "Up"
                ref = max(cores, key=lambda s: s["top_price"])
                final_new = ref if ref["top_price"] >= segment_new["top_price"] else segment_new
        else:
            final_new = segment_new

        def rng(s):
            return s["top_price"] - s["bottom_price"]

        return rng(final_new) < rng(segment_old)


    def check_beichi_and_update_yimai(self, zhongshu, segment_new, segment_old, last_direction):
        if last_direction not in {"Up", "Down"}:
            raise ValueError("last_direction must be 'Up' or 'Down'")

        if segment_old["direction"] != last_direction:
            raise ValueError("segment_old.direction does not match last_direction")

        cores = [s for s in zhongshu["core_pens"] if s["direction"] == last_direction]

        if cores:
            if last_direction == "Down":
                ref = min(cores, key=lambda s: s["bottom_price"])
                final_new = ref if ref["bottom_price"] <= segment_new["bottom_price"] else segment_new
            else:  # "Up"
                ref = max(cores, key=lambda s: s["top_price"])
                final_new = ref if ref["top_price"] >= segment_new["top_price"] else segment_new
        else:
            final_new = segment_new

        def rng(s):
            return s["top_price"] - s["bottom_price"]

        if rng(final_new) < rng(segment_old):
            self.update_yimai_by_direction(final_new, last_direction)




    def update_ermai(self, time, price, status=None):
        self.ermai_time = time
        self.ermai_price = price
        if status:
            self.set_ermai_status(status)

    def update_ermai_by_direction(self, segment):
        """
        根据当前操作方向更新二买（long / short）。
        """
        if self.operation_direction == "Up":
            self.update_ermai(
                segment["bottom_time"],
                segment["bottom_price"],
                status="long"
            )
        elif self.operation_direction == "Down":
            self.update_ermai(
                segment["top_time"],
                segment["top_price"],
                status="short"
            )
        else:
            raise ValueError("operation_direction must be 'Up' or 'Down' before calling update_ermai_by_direction")

    def set_yimai_status(self, status):
        valid_status = {"long", "short", "candidate_long", "candidate_short", "inactivate"}
        if status not in valid_status:
            raise ValueError(f"Invalid yimai_status: {status}")
        self.yimai_status = status


    def set_ermai_status(self, status):
        valid_status = {"long", "short", "inactivate"}
        if status not in valid_status:
            raise ValueError(f"Invalid ermai_status: {status}")
        self.ermai_status = status
        # 同步 yimai_status（只有当 ermai 是 long/short 时）
        if status in {"long", "short"}:
            self.yimai_status = status

    def detect_zhongshu_expansion(self, beichi_check_segment_new, based_on_zhongshu) -> bool:
        """
        检查是否出现中枢扩张（扩展）现象。

        Args:
            beichi_check_segment_new: dict, 当前笔段，包含 bottom_price / top_price
            based_on_zhongshu: dict, 上一个中枢，作为扩展判断基准，包含 bottom_price / top_price

        Returns:
            bool: True 表示出现扩张，False 表示没有扩张
        """
        if self.operation_direction == "Up":
            return beichi_check_segment_new["top_price"] >= based_on_zhongshu["ZD"]
        elif self.operation_direction == "Down":
            return beichi_check_segment_new["bottom_price"] <= based_on_zhongshu["ZG"]
        else:
            raise ValueError("operation_direction must be 'Up' or 'Down'")

    def check_ermai_by_compare_to_yimai(self, segment) -> bool:
        """
        检查 segments_fix[-1] 是否满足二买/二卖确认标准：
        - Up: 当前段最低价 > 一买价格
        - Down: 当前段最高价 < 一买价格
        """
        if self.yimai_price is None:
            raise ValueError("yimai_price is not set")

        if self.operation_direction == "Up":
            return segment["bottom_price"] > self.yimai_price
        elif self.operation_direction == "Down":
            return segment["top_price"] < self.yimai_price
        else:
            raise ValueError("operation_direction must be 'Up' or 'Down'")


    def update_support_price(self, new_price_compare_to):
        if self.support_price is None:
            self.support_price = new_price_compare_to
        else:
            if self.operation_direction == "Up":
                if new_price_compare_to > self.support_price:
                        self.support_price = new_price_compare_to
            elif self.operation_direction == "Down":
                if new_price_compare_to < self.support_price:
                    self.support_price = new_price_compare_to
            else:
                raise ValueError("operation_direction must be 'Up' or 'Down'")


    def handle_ermai_confirmation(self,
                                  segment,
                                  df_row,
                                  info_save_mode=False,
                                  print_return_info=False,
                                  show_fig=False,
                                  write_func=None,
                                  plot_if_func=None,
                                  plot_complete_func=None,
                                  show_func=None,
                                  ersan_lianmai=False,
                                  zhongshu_before_ersanlianmai=None):
        """
        封装：更新 ermai、保存信息、画图
        """
        # 1. 更新 ermai
        self.update_ermai_by_direction(segment)

        # 2. 设置支撑价为当前的一买价格，但如果是二三连买，就要根据前面的中枢设定support_price
        if ersan_lianmai:
            if self.operation_direction == "Up":
                self.update_support_price(zhongshu_before_ersanlianmai["ZG"])
            elif self.operation_direction == "Down":
                self.update_support_price(zhongshu_before_ersanlianmai["ZD"])
            else:
                raise ValueError("operation_direction must be 'Up' or 'Down'")
        else:
            self.update_support_price(self.yimai_price)


        # 3. 打印信息（可选）
        if print_return_info:
            print(f"二mai建仓, 建仓价格{df_row['price']}, 建仓时间{df_row['timestamp']}")

        # 4. 保存信息（可选）
        if info_save_mode and write_func is not None:
            data_ermai = {
                "sanmai_state": "二买确认" if self.operation_direction == "Up" else "二卖确认",
                "price": f"{df_row['price']}",
                "time": f"{df_row['timestamp']}"
            }
            write_func(data_ermai)

        # 5. 显示图（可选）
        if show_fig and plot_if_func is not None and plot_complete_func is not None:
            direction_label = 'long' if self.operation_direction == "Up" else 'short'
            plot_if_func(direction_label, "visualize_for_test")
            plot_complete_func(direction_label, "visualize_for_test")
            if show_func is not None:
                show_func()  # 通常是 fig.show


    def check_zhisun_based_on_price(self, current_price, zhisun_compare_price):
        """
        判断是否触发止损。
        当前状态为 long 时，若 current_price < yimai_price 则止损；
        当前状态为 short 时，若 current_price > yimai_price 则止损。
        """
        if self.yimai_status == "long":
            return current_price < zhisun_compare_price
        elif self.yimai_status == "short":
            return current_price > zhisun_compare_price
        else:
            return False

    def check_zhisun(self, current_price):
        """
        判断是否触发止损。
        当前状态为 long 时，若 current_price < yimai_price 则止损；
        当前状态为 short 时，若 current_price > yimai_price 则止损。
        """

        # if self.yimai_status == "long":
        #     return current_price < self.support_price
        # elif self.yimai_status == "short":
        #     return current_price > self.support_price
        # else:
        #     return False
        return self.check_zhisun_based_on_price(current_price, self.support_price)

    def handle_pingcang(self,
                      df_row,
                      info_save_mode=False,
                      print_return_info=False,
                      show_fig=False,
                      write_func=None,
                      plot_if_func=None,
                      plot_complete_func=None,
                      show_func=None):
        """
        封装：平仓操作，包括打印、保存信息、画图、状态重置
        """
        # 1. 打印信息（可选）
        if print_return_info:
            print(f"平仓头寸止盈止损, 平仓价格{df_row['price']}, 平仓时间{df_row['timestamp']}")

        # 2. 保存信息（可选）
        if info_save_mode and write_func is not None:
            data = {
                "sanmai_state": "平仓",
                "price": f"{df_row['price']}",
                "time": f"{df_row['timestamp']}"
            }
            write_func(data)

        # 3. 显示图（可选）
        if show_fig and plot_if_func is not None and plot_complete_func is not None:
            plot_if_func("stop", "visualize_for_test")
            plot_complete_func("stop", "visualize_for_test")
            if show_func is not None:
                show_func()

        # 4. 重置状态
        self.reset()

    def handle_jiancang(self,
                      df_row,
                      info_save_mode=False,
                      print_return_info=False,
                      show_fig=False,
                      write_func=None,
                      plot_if_func=None,
                      plot_complete_func=None,
                      show_func=None,
                      jiancang_percent=None):
        """
        封装：平仓操作，包括打印、保存信息、画图、状态重置
        """
        # 1. 打印信息（可选）
        if print_return_info:
            print(f"减仓头寸, 减仓价格{df_row['price']}, 减仓时间{df_row['timestamp']}")

        # 2. 保存信息（可选）
        if info_save_mode and write_func is not None:
            data = {
                "sanmai_state": "减仓",
                "price": f"{df_row['price']}",
                "time": f"{df_row['timestamp']}"
            }
            write_func(data)

        # 3. 显示图（可选）
        if show_fig and plot_if_func is not None and plot_complete_func is not None:
            plot_if_func("stop", "visualize_for_test")
            plot_complete_func("stop", "visualize_for_test")
            if show_func is not None:
                show_func()

    def has_three_segments_after_ermai(self, segments_fix):
        count = 0
        for seg in reversed(segments_fix):
            # if seg["timestamp_segment_complete"] > self.ermai_time:
            if max(seg["top_time"], seg["bottom_time"]) > self.ermai_time:
                count += 1
                if count >= 3:
                    return True
        return False

    def zhiying_or_keep_operation(self,
                           zhongshus,
                           segments_fix,
                           df_row,
                           info_save_mode=False,
                           print_return_info=False,
                           show_fig=False,
                           write_func=None,
                           plot_if_func=None,
                           plot_complete_func=None,
                           show_func=None,
                           sanmai_info="",
                           new_zhongshu_clean=None,
                           golden_magic_number=0.73
                           ):
        """
        止盈逻辑，适用于 long 和 short，触发后调用 handle_pingcang。
        """

        if self.yimai_status not in {"long", "short"}:
            return

        should_close = False

        # if len(zhongshus) <= 1:
        #     #"当前中枢太长，显然已经升级，不该等待"
        #     # print("当前中枢太长，显然已经升级，不该等待")
        #     should_close = True



        #######-----这里要用超参了，沿着操作方向够不够强的参数，可以试试0.618这种黄金分割值，显然，这个值越大越保守，越小越激进-----#######
        # golden_magic_number = 0.73

        if not should_close:
            if sanmai_info != "":
                zhongshu_new = new_zhongshu_clean
                zhongshu_old = zhongshus[-1]
            else:
                zhongshu_new = zhongshus[-1]
                zhongshu_old = zhongshus[-2]
            if zhongshu_new["start_time"] > self.ermai_time:


                # print(f"检查时zhongshus的长度为{len(zhongshus)}")
                # print(f"""新中枢始于{zhongshu_new["start_time"]}, 新中枢终于{zhongshu_new["end_time"]}, 在二买时间{self.ermai_time}之后""")
                # print(f"""最后一个segment的时间{segments_fix[-1]["bottom_time"]}, {segments_fix[-1]["top_time"]}""")
                if zhongshu_new["direction"] != self.operation_direction:
                    should_close = True
                    print("逆向中枢出现，笔走势已经结束, 止损")
                    # 破了止盈，又破了二mai，就撤退吧
                elif self.check_zhisun(df_row['price']) and self.check_zhisun_based_on_price(df_row['price'],
                                                                                               self.ermai_price):
                    should_close = True
                    print("破了止盈，又破了二mai, 止损")
                elif segments_fix[-1]["direction"] == self.operation_direction:
                    should_close = (segments_fix[-1]["top_price"] - segments_fix[-1][
                        "bottom_price"]) < golden_magic_number * (
                                               segments_fix[-2]["top_price"] - segments_fix[-2]["bottom_price"])
                    print(f"检查笔的力度，笔力度减弱是{should_close}")
                    # if self.operation_direction == "Up":
                    #     # # print(f"检查新中枢")
                    #     should_close = self.check_beichi(
                    #         zhongshu_old,
                    #         segments_fix[zhongshu_old["core_pens_index"][-1] + 1],
                    #         segments_fix[zhongshu_old["core_pens_index"][0] - 1],
                    #         "Up"
                    #     ) or ((len(zhongshu_new["core_pens_index"]) >= len(zhongshu_old["core_pens_index"])) and self.check_beichi(
                    #         zhongshu_new,
                    #         segments_fix[zhongshu_new["core_pens_index"][-1] + 1],
                    #         segments_fix[zhongshu_new["core_pens_index"][0] - 1],
                    #         "Up"
                    #     ))
                    # else:  # "Down"
                    #     should_close = self.check_beichi(
                    #         zhongshu_old,
                    #         segments_fix[zhongshu_old["core_pens_index"][-1] + 1],
                    #         segments_fix[zhongshu_old["core_pens_index"][0] - 1],
                    #         "Down"
                    #     ) or ((len(zhongshu_new["core_pens_index"]) >= len(zhongshu_old["core_pens_index"])) and self.check_beichi(
                    #         zhongshu_new,
                    #         segments_fix[zhongshu_new["core_pens_index"][-1] + 1],
                    #         segments_fix[zhongshu_new["core_pens_index"][0] - 1],
                    #         "Down"
                    #     ))
                if not should_close:
                    # self.support_price = zhongshu_old["ZG"] if self.operation_direction == "Up" else zhongshu_old["ZD"]
                    if self.operation_direction == "Up":
                        self.update_support_price(zhongshu_old["ZG"])
                    else:
                        self.update_support_price(zhongshu_old["ZD"])

            else:
                # if self.has_three_segments_after_ermai(segments_fix) and (len(zhongshu_new["core_pens_index"]) >= len(zhongshu_old["core_pens_index"])):
                #     # print(f"二买形成后已有三段，未见新中枢，并且这个中枢线段数已经超过前一个中枢")
                if self.has_three_segments_after_ermai(segments_fix) and (segments_fix[-1]["direction"] == self.operation_direction) and (segments_fix[-1]["top_price"] - segments_fix[-1]["bottom_price"]) < golden_magic_number * (segments_fix[-2]["top_price"] - segments_fix[-2]["bottom_price"]):
                    if self.operation_direction == "Up":
                        should_close = (segments_fix[-1]["top_price"] < zhongshu_new["GG"]) and (segments_fix[-1]["direction"] == "Up")
                        if (should_close):
                            print(f"""平仓因为二买形成后已有三段，未见新中枢, 这一笔价格{segments_fix[-1]["top_price"]},破位了GG{zhongshu_new["GG"]}""")
                    else:
                        should_close = (segments_fix[-1]["bottom_price"] > zhongshu_new["DD"]) and (segments_fix[-1]["direction"] == "Down")
                        if (should_close):
                            print(f"""平仓因为二卖形成后已有三段，未见新中枢, 这一笔价格{segments_fix[-1]["bottom_price"]},破位了DD{zhongshu_new["DD"]}""")

        if should_close:
            # print("平仓止盈了")
            self.handle_pingcang(
                df_row=df_row,
                info_save_mode=info_save_mode,
                print_return_info=print_return_info,
                show_fig=show_fig,
                write_func=write_func,
                plot_if_func=plot_if_func,
                plot_complete_func=plot_complete_func,
                show_func=show_func
            )

    def zhiying_or_keep_operation_for_pen(self,
                           zhongshus,
                           segments_fix,
                           df_row,
                           info_save_mode=False,
                           print_return_info=False,
                           show_fig=False,
                           write_func=None,
                           plot_if_func=None,
                           plot_complete_func=None,
                           show_func=None,
                           sanmai_info="",
                           new_zhongshu_clean=None,
                           golden_magic_number=0.73
                           ):
        """
        止盈逻辑，适用于 long 和 short，触发后调用 handle_pingcang。
        """

        if self.yimai_status not in {"long", "short"}:
            return

        should_close = False

        # if len(zhongshus) <= 1:
        #     #"当前中枢太长，显然已经升级，不该等待"
        #     # print("当前中枢太长，显然已经升级，不该等待")
        #     should_close = True



        #######-----这里要用超参了，沿着操作方向够不够强的参数，可以试试0.618这种黄金分割值，显然，这个值越大越保守，越小越激进-----#######
        # golden_magic_number = 0.73

        if not should_close:
            if sanmai_info != "":
                zhongshu_new = new_zhongshu_clean
                zhongshu_old = zhongshus[-1]
            else:
                zhongshu_new = zhongshus[-1]
                zhongshu_old = zhongshus[-2]
            if zhongshu_new["start_time"] > self.ermai_time:


                # print(f"检查时zhongshus的长度为{len(zhongshus)}")
                # print(f"""新中枢始于{zhongshu_new["start_time"]}, 新中枢终于{zhongshu_new["end_time"]}, 在二买时间{self.ermai_time}之后""")
                # print(f"""最后一个segment的时间{segments_fix[-1]["bottom_time"]}, {segments_fix[-1]["top_time"]}""")
                if zhongshu_new["direction"] != self.operation_direction:
                    should_close = True
                    print("逆向中枢出现，笔走势已经结束, 止损")
                    # 破了止盈，就撤退吧
                elif self.check_zhisun(df_row['price']):# and self.check_zhisun_based_on_price(df_row['price'],self.ermai_price):
                    should_close = True
                    print("破了止盈, 止损")
                # elif segments_fix[-1]["direction"] == self.operation_direction:
                #     should_close = (segments_fix[-1]["top_price"] - segments_fix[-1][
                #         "bottom_price"]) < golden_magic_number * (
                #                                segments_fix[-2]["top_price"] - segments_fix[-2]["bottom_price"])
                #     print(f"检查笔的力度，笔力度减弱是{should_close}")
                    # if self.operation_direction == "Up":
                    #     # # print(f"检查新中枢")
                    #     should_close = self.check_beichi(
                    #         zhongshu_old,
                    #         segments_fix[zhongshu_old["core_pens_index"][-1] + 1],
                    #         segments_fix[zhongshu_old["core_pens_index"][0] - 1],
                    #         "Up"
                    #     ) or ((len(zhongshu_new["core_pens_index"]) >= len(zhongshu_old["core_pens_index"])) and self.check_beichi(
                    #         zhongshu_new,
                    #         segments_fix[zhongshu_new["core_pens_index"][-1] + 1],
                    #         segments_fix[zhongshu_new["core_pens_index"][0] - 1],
                    #         "Up"
                    #     ))
                    # else:  # "Down"
                    #     should_close = self.check_beichi(
                    #         zhongshu_old,
                    #         segments_fix[zhongshu_old["core_pens_index"][-1] + 1],
                    #         segments_fix[zhongshu_old["core_pens_index"][0] - 1],
                    #         "Down"
                    #     ) or ((len(zhongshu_new["core_pens_index"]) >= len(zhongshu_old["core_pens_index"])) and self.check_beichi(
                    #         zhongshu_new,
                    #         segments_fix[zhongshu_new["core_pens_index"][-1] + 1],
                    #         segments_fix[zhongshu_new["core_pens_index"][0] - 1],
                    #         "Down"
                    #     ))
                if not should_close:
                    # self.support_price = zhongshu_old["ZG"] if self.operation_direction == "Up" else zhongshu_old["ZD"]
                    if self.operation_direction == "Up":
                        self.update_support_price(zhongshu_old["ZG"])
                    else:
                        self.update_support_price(zhongshu_old["ZD"])

            # else:
            #     # if self.has_three_segments_after_ermai(segments_fix) and (len(zhongshu_new["core_pens_index"]) >= len(zhongshu_old["core_pens_index"])):
            #     #     # print(f"二买形成后已有三段，未见新中枢，并且这个中枢线段数已经超过前一个中枢")
            #     if self.has_three_segments_after_ermai(segments_fix) and (segments_fix[-1]["direction"] == self.operation_direction) and (segments_fix[-1]["top_price"] - segments_fix[-1]["bottom_price"]) < golden_magic_number * (segments_fix[-2]["top_price"] - segments_fix[-2]["bottom_price"]):
            #
            #     # if (not same_level_or_higher_level_before(zhongshus, segments_fix)):#二买之后一直没有新中枢
            #         if self.operation_direction == "Up":
            #             should_close = (segments_fix[-1]["top_price"] < zhongshu_new["GG"]) and (segments_fix[-1]["direction"] == "Up")
            #             if (should_close):
            #                 print(f"""平仓因为二买形成后已有三段，未见新中枢, 这一笔价格{segments_fix[-1]["top_price"]},破位了GG{zhongshu_new["GG"]}""")
            #         else:
            #             should_close = (segments_fix[-1]["bottom_price"] > zhongshu_new["DD"]) and (segments_fix[-1]["direction"] == "Down")
            #             if (should_close):
            #                 print(f"""平仓因为二卖形成后已有三段，未见新中枢, 这一笔价格{segments_fix[-1]["bottom_price"]},破位了DD{zhongshu_new["DD"]}""")

        if should_close:
            # print("平仓止盈了")
            self.handle_pingcang(
                df_row=df_row,
                info_save_mode=info_save_mode,
                print_return_info=print_return_info,
                show_fig=show_fig,
                write_func=write_func,
                plot_if_func=plot_if_func,
                plot_complete_func=plot_complete_func,
                show_func=show_func
            )


if __name__ == "__main__":


    parser = argparse.ArgumentParser(description="K线与走势分析参数设置")

    # 添加超参数
    parser.add_argument("--zgzd_type", type=str, choices=["classical", "practical"], default="classical",
                        help="中枢类型 ('classical' 或 'practical')")
    parser.add_argument("--dingdi_start_from", type=int, default=1,
                        help="从哪个顶或底开始计算，影响走势多义性")
    parser.add_argument("--group_size", type=int, default=2,
                        help="时间级别，group_size=10 为分钟K线，group_size=1 为 6 秒K线")
    parser.add_argument("--group_size_for_MACD", type=int, default=10,
                    help="MACD的K线基于的时间级别，一般要设的比group_size的时间级别大，建议为group_size的5倍, 选择全部数据时最好不要低于20")
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
    GROUP_SIZE = args.group_size  # 图的时间级别，group_size=10就是分钟K线， group_size=1就是6秒K线，6秒K线只是点不是K线
    STOCK_NAME_AND_MARKET = args.stock_name_and_market  # "NVDA_NASDAQ" "AAPL_NASDAQ" "AMZN_NASDAQ" "META_NASDAQ" "MSFT_NASDAQ" "SNOW_NYSE" "TIGR_NASDAQ" "TSLA_NASDAQ" "U_NYSE" "AVGO_NASDAQ"
    ALL_DATA_NOT_SINGLE_DAY = not args.not_all_data_but_single_day
    IF_SINGLE_DAY_DATE = args.if_single_day_date
    PRINT_PROCESS_INFO = args.print_process_info
    GROUP_SIZE_FOR_MACD = args.group_size_for_MACD
    if ALL_DATA_NOT_SINGLE_DAY:
        #####################读取某个股的全部数据###########################
        df = read_all_csv_of_one_stock(stock_name_and_market=STOCK_NAME_AND_MARKET)
    else:
        #####################读取某个股的单天数据###########################
        df = read_single_csv_of_one_stock(file_path=f'data/{STOCK_NAME_AND_MARKET}_prices_{IF_SINGLE_DAY_DATE}.csv')





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
    if PRINT_PROCESS_INFO:
        print("笔处理完毕，开始修复不合理的连续笔")
    #pens = find_pens_from_kline_complete(kline_df_no_inclusion)
    # pens_fix 函数，它会合并 find_pens_from_kline 的结果中连续同向的笔，并重新计算合并后的每笔的最高点、最低点、起始时间和结束时间
    pens_fix = pens_fix(pens)
    if PRINT_PROCESS_INFO:
        print("笔修复处理完毕，开始找线段")





    # 用笔组合成线段
    segments = merge_pens_to_segments(pens_fix)
    # segments = merge_pens_to_segments(pens)
    if PRINT_PROCESS_INFO:
        print("线段处理完毕，开始找中枢")

    # 调用寻找中枢的函数
    #zgzd_type="classical"
    #zgzd_type="practical"
    pen_zhongshus = find_zhongshu(pens_fix, zgzd_type=ZGZD_TYPE)
    if PRINT_PROCESS_INFO:
        print("中枢处理完毕，开始画图")

    if PRINT_PROCESS_INFO:
        print("数据处理完毕，开始画图")
        
        
        
        
        
    MACD_kline_df = generate_kline_data_group_points(df, group_size=GROUP_SIZE_FOR_MACD)
    

    # 计算 MACD 值
    MACD_kline_df = calculate_macd(MACD_kline_df)



    # 创建子图布局
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        subplot_titles=('Price Trend', 'Original K-Line Chart', 'K-Line Chart After Handling Inclusion'), row_heights=[0.3, 0.4, 0.3, 0.3])
    #fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
    #                    subplot_titles=('Price Trend', 'K-Line Chart After Handling Inclusion'))

    # 添加第一幅图（折线图）
    fig.add_trace(
        go.Scatter(x=df['timestamp'], y=df['price'], mode='lines+markers', name='Price'),
        row=3, col=1
    )
    
    

    # 添加第二幅图（K 线图）
    for i in range(len(kline_df)):
        # 判断 K 线是上升还是下降
        color = 'green' if kline_df.iloc[i]['close'] > kline_df.iloc[i]['open'] else 'red'
        fig.add_trace(
            go.Candlestick(
                x=[kline_df.iloc[i]['timestamp']],
                open=[kline_df.iloc[i]['open']],
                close=[kline_df.iloc[i]['close']],
                high=[kline_df.iloc[i]['high']],
                low=[kline_df.iloc[i]['low']],
                increasing_line_color=color,  # 上升颜色
                decreasing_line_color=color,  # 下降颜色
                showlegend=False
            ),
            row=4, col=1
        )


        
    # 处理后的 K 线图
    for i in range(len(kline_df_no_inclusion)):
        color = 'green' if kline_df_no_inclusion.iloc[i]['close'] > kline_df_no_inclusion.iloc[i]['open'] else 'red'
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
            row=2, col=1
        )
        
        
    # Add Pens to the chart
    for pen in pens:
        fig.add_trace(
            go.Scatter(
                x=[pen['top_time'], pen['bottom_time']],
                y=[pen['top_price'], pen['bottom_price']],
                mode='lines',
                line=dict(color='pink', width=4),
                name='Pen',
                showlegend=False
            ),
            row=2, col=1
        )


    # Add fixed Pens to the chart
    for pen in pens_fix:
        fig.add_trace(
            go.Scatter(
                x=[pen['top_time'], pen['bottom_time']],
                y=[pen['top_price'], pen['bottom_price']],
                mode='lines',
                line=dict(color='purple', width=2),
                name='Penfix',
                showlegend=False
            ),
            row=2, col=1
        )
        
        
        
    # Add Zhongshu Rectangles to the chart
    draw_zhongshu(fig, pen_zhongshus, row=2, col=1, level="pen")




    if segments:
        for segment in segments:
            fig.add_trace(
                go.Scatter(
                    x=[segment['top_time'], segment['bottom_time']],
                    y=[segment['top_price'], segment['bottom_price']],
                    mode='lines',
                    line=dict(color='white', width=2),
                    name='segment',
                    showlegend=False
                ),
                row=2, col=1
            )
            
            
            
            
    # DIF 线 (MACD 线) 和 DEA 线 (Signal 线)
    fig.add_trace(go.Scatter(
        x=MACD_kline_df['timestamp'], y=MACD_kline_df['DIF'], mode='lines', name="DIF (MACD Line)", line=dict(color='blue')
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=MACD_kline_df['timestamp'], y=MACD_kline_df['DEA'], mode='lines', name="DEA (Signal Line)", line=dict(color='red')
    ), row=1, col=1)

    # MACD 柱状图（增加宽度）
    fig.add_trace(go.Bar(
        x=MACD_kline_df['timestamp'],
        y=MACD_kline_df['MACD'],
        name="MACD Histogram",
        width=GROUP_SIZE_FOR_MACD,
        marker_color=['green' if m >= 0 else 'red' for m in MACD_kline_df['MACD']]
    ), row=1, col=1)
    # width=50,  # 增加柱状图宽度（时间戳单位为纳秒，具体数值根据数据调整）


    # 更新布局
    fig.update_layout(
        title=f'{STOCK_NAME_AND_MARKET} Price Trend and K-Line Chart Before and After Handling Inclusion Without Night Times',
        xaxis=dict(
            type='category',  # 使用分类轴
            title="MACD Indicator"
        ),
        xaxis2=dict(
            type='category',  # 第二幅图的 X 轴为分类轴， Plotly 的 Candlestick 图会为 X 轴分配连续时间轴，导致即使没有数据的时间段（如夜晚时间）也会显示。我们通过将 X 轴类型设置为分类轴 (xaxis.type='category') 解决了这个问题，需要对其他图也进行类似设置
            title="bi and zhongshu"
        ),
        xaxis3=dict(
            type='category',  # 第三幅图的 X 轴为分类轴
            title="basic price info"
        ),
        xaxis4=dict(
            type='category',  # 使用分类轴
            title="handle_kline_inclusion"
        ),
        yaxis=dict(
            title="Price"
        ),
        template='plotly_dark',
        height=3000
    )
    
    


    # 显示图表
    fig.show()


