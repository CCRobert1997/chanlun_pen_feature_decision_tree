数据准备：
在服务器上：bash command_list_find_signal_machine_learning_pen_and_pen_zhongshu_track_only.sh
这个任务会对不同股票在线执行find_ermai_penlevel_zhongshu_ML_for_visualization_pen_and_penzhongshu_track_only.py
会在checkpoint_pen_6_seconds和checkpoint_pen_zhongshus_6_seconds这两个文件夹存储笔和笔中枢信息。


特征预处理：
运行python machine_learning/chanlun_feature_engineer.py之前，现在的策略，我是对单个股票训练单独的模型
修改代码，只针对一个股票名字
STOCK_NAME_AND_MARKETS = ["NFLX_NASDAQ"]
strategy = STOCK_QuantStrategy[STOCK_NAME_AND_MARKETS[0]]()
运行后
checkpoint_PFT/checkpoint_pen_zhongshus_6_seconds_feature_eng_QuantStrategy0002下会出现一个针对这个股票的csv文件

模型训练：
运行python machine_learning/chanlun_feature_based_machine_learning_decision_tree.py
当前代码会基于checkpoint_PFT/checkpoint_pen_zhongshus_6_seconds_feature_eng_QuantStrategy0002下所有文件训练
所以训练前要保证checkpoint_PFT/checkpoint_pen_zhongshus_6_seconds_feature_eng_QuantStrategy0002只有一个csv文件，也就是一个股票的文件

运行后会看到几幅图：
1. 真实label的PCA二维图
2. 标注了最有效识别Chance的PCA二维图
3. 标注了第二有效识别Chance的PCA二维图

这个有效其实就是识别Chance的precision高，即识别为Chance且真实样本为Chance。
筛选比标准其实是这样的
count = (leaf_distribution_df["NoChance"] + leaf_distribution_df["Chance"] >= 7) & (leaf_distribution_df["chance_to_nochance_ratio"] >= 5)
就是说这个节点下的训练样本数要大，要有统计意义，然后Chance数/NoChance数要足够大，失败的机会要足够小。
7这个数字是要被调整的，因为我往往只保留排名第一的节点，被我选中的节点数一般不超过两个。
要肉眼看一下，标注了有效leaf的PCA二维图其点的分布是否变出比较显著的聚类  这个聚类是不是真实label的PCA二维图想要的，以此来选择上面这个数字7改成几。要是不理想，就不把这只股票放进策略里了。



完成识别代码：
最后有效的leaf会在python machine_learning/chanlun_feature_based_machine_learning_decision_tree.py输出结果的最下面有一段类似于
triggered = False
if last_pen_zhongshu_len >= self.join_zhongshu_length_bar_online:
    if data_X["lowest_level_check_beichi_now_strength"] <= 0.0081 and data_X["core_pen_len_>8"] <= 0.5000 and data_X["lowest_level_check_beichi_now_strength"] > -0.0001 and data_X["core_pen_len_<=6"] <= 3.0000 and data_X["num_pens_longest_in_20_pen_zhongshus"] <= 26.5000 and data_X["num_pens_longest_in_20_pen_zhongshus"] <= 20.0000:
        self.trigger_case_id = 1
        return True
    else:
       return False

这个样子的代码，把这个代码复制到对应股票在trigger_and_feature_library.py的class的trigger_rule方法下面。
class QuantStrategyNFLX_NASDAQ(QuantStrategy0002):
    def trigger_rule(self, data_X):



运行识别代码：
在服务器上：
bash command_list_find_signal_machine_learning_selected_stock_based_on_whether_ML_class_exist.sh
这是对所有建立了QuantStrategy0002的子class的识别策略的股票进行信号监测的。
运行前注意检查修改find_ermai_penlevel_zhongshu_ML_for_visualization.py
搜索########################线上实盘到全时间回测记得切换#########################
确保所有############################### 线上实盘用 ###############################包围的字段被uncomment
所有############################### 全时间回测用 ###############################包围的字段被comment









再往下是运行中的交易辅助程序：


检查是否有在向服务器抓取机器学习买点信息，
ps aux | grep pull_machine_learning_caozuo_csv_file_from_server.sh
没有的话要重启：
bash nohup_run_pull_machine_learning_caozuo_csv_file_from_server.sh


检查闹钟本地服务器
ps aux | grep alert_server_machine_learning.py





开盘前准备：
1.检查是否有在向服务器抓取三买信息，
ps aux | grep pull_machine_learning_caozuo_csv_file_from_server.sh
没有就重启 
bash nohup_run_pull_machine_learning_caozuo_csv_file_from_server.sh
2.检查闹钟服务器， 
ps aux | grep alert_server_machine_learning.py
不在工作就重启，记得要先打开闹钟APP再启动alert_server_machine_learning.py，启动alert_server_machine_learning.py通过下面这句:
bash nohup_run_local_server_to_send_message_to_ring.sh


在服务器上开启可视化：
nohup python ermai_caozuo_visualization.py  > ermai_caozuo_visualization.log 2>&1 &
nohup python machine_learning_caozuo_visualization.py  > machine_learning_caozuo_visualization.log 2>&1 &
映射到本地端口一般是7010

如果运行在master node节点
ssh -L 7010:localhost:7010 -i /Users/shangyu/Desktop/ShangyuChen/IT_Tool/ssh_keys/newKey ubuntu@118.138.234.44
如果运行在16核cpu节点
ssh -L 7010:localhost:7010 -i /Users/shangyu/Desktop/ShangyuChen/IT_Tool/ssh_keys/newKey ubuntu@118.138.233.245


服务器上：

bash command_list_find_signal_machine_learning_pen_and_pen_zhongshu_track_only.sh 
就是让pen和pen_zhongshu一直在构造，然后存储到checkpoint_pen_6_seconds和checkpoint_pen_zhongshus_6_seconds
可以在服务器打这个 这么检查
ps aux | grep find_ermai_penlevel_zhongshu_ML_for_visualization_pen_and_penzhongshu_track_only.py

bash command_list_find_signal_machine_learning_selected_stock_based_on_whether_ML_class_exist.sh
这是监听买卖信号
可以在服务器打这个 这么检查
ps aux | grep find_ermai_penlevel_zhongshu_ML_for_visualization.py










