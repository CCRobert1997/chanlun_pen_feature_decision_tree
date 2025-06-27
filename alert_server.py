# from flask import Flask, jsonify
# import datetime
#
# app = Flask(__name__)
#
# @app.route('/check-alarm')
# def check_alarm():
#     current_time = datetime.datetime.now().strftime('%H:%M')
#     if current_time == '08:00':  # 设定闹钟时间
#         return 'ALARM'
#     return 'NO'
#
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000)

#
# import asyncio
# import websockets
# import datetime
#
# # 连接的客户端集合
# clients = set()
#
#
# async def notify_clients():
#     """ 定期检查当前时间，如果是 08:00，通知所有连接的客户端 """
#     while True:
#         now = datetime.datetime.now().strftime("%H:%M")
#         print(now)
#         if clients:  # 只有当有客户端连接时才发送
#             print("yes")
#         if now == "09:54":  # 触发时间
#             print("🔔 触发 ALARM，通知客户端！")
#             if clients:  # 只有当有客户端连接时才发送
#                 await asyncio.wait([client.send("ALARM") for client in clients])
#             await asyncio.sleep(60)  # 触发后等待 60 秒，避免重复发送
#
#         await asyncio.sleep(1)  # 每秒检查一次时间
#
#
# async def handler(websocket, path):
#     """ 处理 WebSocket 客户端连接 """
#     clients.add(websocket)
#     print(f"✅ 客户端已连接: {websocket.remote_address}")
#     try:
#         async for message in websocket:
#             print(f"📩 收到消息: {message}")
#     except websockets.exceptions.ConnectionClosedError as e:
#         print(f"❌ 客户端断开: {e}")
#     except Exception as e:
#         print(f"🔥 服务器发生错误: {e}")
#     finally:
#         clients.remove(websocket)
#
# async def main():
#     try:
#         server = await websockets.serve(handler, "0.0.0.0", 6000)
#         print("✅ WebSocket 服务器已启动，监听 0.0.0.0:6000")
#         await server.wait_closed()
#     except Exception as e:
#         print(f"🔥 服务器启动失败: {e}")
#
#
# # async def main():
# #     server = await websockets.serve(handler, "0.0.0.0", 5000)  # 服务器监听端口 5000
# #     print("✅ WebSocket 服务器启动，等待客户端连接...")
# #
# #     await asyncio.gather(server.wait_closed(), notify_clients())  # 运行 WebSocket 服务器 & 时间检测任务
#
#
# asyncio.run(main())



import time
import requests
import datetime
import os
from collections import deque



MAC_IP = "127.0.0.1"  # 你的 Mac 本机 IP 地址
ALARM_URL = f"http://{MAC_IP}:5111/alarm"



# 本地目录
directory = "/Users/shangyu/Desktop/ShangyuChen/STOCK/chanlun/chanlun_sanmai_v1/sanmai_caozuo"
# 文件列表
csv_30seconds_level = [
    "NVDA_NASDAQ_30_second_sanmai_caozuo.csv", "AMZN_NASDAQ_30_second_sanmai_caozuo.csv",
    "META_NASDAQ_30_second_sanmai_caozuo.csv", "MSFT_NASDAQ_30_second_sanmai_caozuo.csv",
    "SNOW_NYSE_30_second_sanmai_caozuo.csv", "TIGR_NASDAQ_30_second_sanmai_caozuo.csv",
    "TSLA_NASDAQ_30_second_sanmai_caozuo.csv", "U_NYSE_30_second_sanmai_caozuo.csv",
    "AVGO_NASDAQ_30_second_sanmai_caozuo.csv", "AAPL_NASDAQ_30_second_sanmai_caozuo.csv",
    "LLY_NYSE_30_second_sanmai_caozuo.csv", "NVO_NYSE_30_second_sanmai_caozuo.csv",
    "ADBE_NASDAQ_30_second_sanmai_caozuo.csv", "TSM_NYSE_30_second_sanmai_caozuo.csv",
    "PFE_NYSE_30_second_sanmai_caozuo.csv", "JPM_NYSE_30_second_sanmai_caozuo.csv",
    "BAC_NYSE_30_second_sanmai_caozuo.csv", "COST_NASDAQ_30_second_sanmai_caozuo.csv",
    "NFLX_NASDAQ_30_second_sanmai_caozuo.csv"
]
# 创建字典
file_line_count = {}
# 遍历文件列表
for file in csv_30seconds_level:
    file_path = os.path.join(directory, file)

    if os.path.exists(file_path):  # 检查文件是否存在
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            file_line_count[file] = max(len(lines) - 1, 0)  # 计算去掉 header 后的行数，避免负数
    else:
        file_line_count[file] = 0  # 文件不存在，赋值 0
# 输出结果
# print(file_line_count)





while True:
    message = ""
    for file in csv_30seconds_level:
        file_path = os.path.join(directory, file)

        if os.path.exists(file_path):  # 检查文件是否存在
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if len(lines) - 1 > file_line_count[file]:
                    num_new_message = len(lines) - 1 - file_line_count[file]
                    file_line_count[file] = max(len(lines) - 1, 0)
                    # 仅读取最后一行
                    with open(file_path, "r", encoding="utf-8") as f:
                        last_few_line = deque(f, maxlen=num_new_message)
                    new_info = "\n" + file[:10] +  "".join(last_few_line)
                    message += new_info
    if message:
        # print(f"🔔 触发闹钟！通知 Mac {message}")
        try:
            response = requests.post(ALARM_URL, data=message.encode('utf-8'))
            print(f"✅ 服务器响应: {response.text}")
        except Exception as e:
            print(f"❌ 发送失败: {e}")
        #time.sleep(30)  # 触发后等 0.5 分钟，避免重复触发

    time.sleep(10)  # 每10秒检查时间




    
    
    
