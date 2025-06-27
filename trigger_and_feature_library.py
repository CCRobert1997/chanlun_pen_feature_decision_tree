from abc import ABC, abstractmethod
import pandas as pd
import os

class QuantStrategy(ABC):
    @abstractmethod
    def construct_label_and_extra_feature(self, *args, **kwarg):
        """子类必须实现这个方法"""
        """构建标签和额外备注的特征，额外备注的特征不一定使用"""
        pass

    @abstractmethod
    def construct_X_features(self, *args, **kwargs):
        """子类必须实现这个方法"""
        """构建自变量特征"""
        pass

    @abstractmethod
    def generate_training_sample(self, *args, **kwarg):
        """子类必须实现这个方法"""
        """模型训练时生成训练集合"""
        pass

    @abstractmethod
    def trigger_signals_detect(self, *args, **kwarg):
        """子类必须实现这个方法"""
        """基于模型训练的结果，检测买入信号的逻辑"""
        pass

    @abstractmethod
    def join_market_operation(self, *args, **kwarg):
        """子类必须实现这个方法"""
        """检测到买入信号，那就要执行这个method完成交易状态的更新，交易状态变成做多或者做空"""
        pass

    @abstractmethod
    def detect_during_operation(self, *args, **kwarg):
        """子类必须实现这个方法"""
        """检测到买入信号后，盯盘，决定要不要离场"""
        pass

    @abstractmethod
    def handle_info(self, *args, **kwarg):
        """子类必须实现这个方法"""
        """在买入或离场时登记信息"""
        pass

















#统计转折
class QuantStrategy0001(QuantStrategy):
    def __init__(self, STOCK_NAME_AND_MARKET=None, seconds_size=6):
        self.STOCK_NAME_AND_MARKET = STOCK_NAME_AND_MARKET
        self.seconds_size = seconds_size
        # 后面笔中枢至少走出min_same_trend_length个盈利方向
        self.min_same_trend_length = 2 #3 #1代表最极端的转折就行，别的不管，等于1的时候相当于有介入中枢，和转折走出的第一个中枢两个中枢
        self.join_zhongshu_length_bar = 6 # 最后一个中枢长度至少为6，这个中枢我才考虑去参与，这个用在训练集过滤
        self.join_zhongshu_length_bar_online = self.join_zhongshu_length_bar - 2  # 这是对应join_zhongshu_length_bar的，实盘中超过这个长度，我就开始监测介不介入了
        self.extra_feature_names = ["segment_length_num_pen_zhongshu", "last_zhongshu_len"]
        self.lag = 50 #根据前面20个中枢分析， 后面一些命名用到了20， 19， 18什么的就不更改了，就是self.lag， self.lag-1， self.lag-2的意思
        self.reset()


    def reset(self):
        self.strategy_name = 'QuantStrategy0001'
        self.feature_eng_folder_path = f"checkpoint_PFT/checkpoint_pen_zhongshus_6_seconds_feature_eng_{self.strategy_name}"
        self.new_operation_direction = ""
        self.operation_direction = ""
        self.join_price = None
        self.join_time = None
        self.zhongshu_formed_time = None
        self.num_zhongshu = None
        self.trigger_case_id = None

    def handle_info(self, case, operation_price, operation_time):
        operation_state = ""
        if case == "quit":
            operation_state = "平仓" + self.strategy_name
        elif case == "long":
            operation_state = "做多" + self.strategy_name
        elif case == "short":
            operation_state = "做空" + self.strategy_name
        # 保存信息
        data = {
            "sanmai_state": operation_state,
            "price": operation_price,
            "time": operation_time
        }
        ermai_folder_path = "machine_learning_caozuo"
        ermai_file_name = f"{self.STOCK_NAME_AND_MARKET}_{self.seconds_size}_second_machine_learning_caozuo.csv"
        ermai_file_path = os.path.join(ermai_folder_path, ermai_file_name)
        os.makedirs(ermai_folder_path, exist_ok=True)
        file_exists = os.path.isfile(ermai_file_path)
        df_data_sanmai = pd.DataFrame([data])
        df_data_sanmai.to_csv(ermai_file_path, mode='a', header=not file_exists, index=False, encoding='utf-8-sig')


    def join_market_operation(self, closest_zhongshu_end_time, closest_zhongshu_ZG, second_closest_zhongshu_ZD, join_price, join_time):
        self.new_operation_direction = "long" if closest_zhongshu_ZG <= \
                                                     second_closest_zhongshu_ZD else "short"
        if self.new_operation_direction != self.operation_direction:
            if not self.operation_direction:
                print(f"0001策略建新仓 价格{join_price}, 方向{self.new_operation_direction}!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            else:
                print(f"0001策略平仓后建新仓 价格{join_price}, 方向{self.new_operation_direction}!!!!!!!!!!!!!!!!!!!!!!!!!")
            self.operation_direction = self.new_operation_direction
            self.join_price = join_price
            self.join_time = join_time
            self.zhongshu_formed_time = min(pd.to_datetime(join_time), pd.to_datetime(closest_zhongshu_end_time))
            # strategy.zhongshu_support_price = history_long_time_pen_zhongshus[-1]["ZD"] if strategy.operation_direction=="long" else history_long_time_pen_zhongshus[-1]["ZG"]
            self.num_zhongshu = 1  # 当前方向第一个中枢
            self.handle_info(self.operation_direction, self.join_price, self.join_time) #建仓信息登记

    def detect_during_operation(self, closest_zhongshu_end_time, closest_zhongshu_start_time, closest_zhongshu_ZG, closest_zhongshu_ZD, second_closest_zhongshu_ZG, second_closest_zhongshu_ZD, current_time, current_price):
        if pd.to_datetime(closest_zhongshu_start_time) > pd.to_datetime(self.zhongshu_formed_time):
            self.num_zhongshu = self.num_zhongshu + 1  # 介入后总共出现的中枢数
            if self.num_zhongshu >= self.min_same_trend_length - 1: #self.num_zhongshu >= self.min_same_trend_length可能吃到的利润太少了，想办法优化一下止盈， 比如冒险一点就self.num_zhongshu >= self.min_same_trend_length + 1
                print(f"---------------------止盈 {current_price}---------------------")
                self.handle_info("quit", current_price, current_time)  # 平仓信息登记
                self.reset()
            # elif self.operation_direction == "long" and ((closest_zhongshu_ZG <= second_closest_zhongshu_ZD) or (current_price < second_closest_zhongshu_ZG)): #猥琐一点
            # elif self.operation_direction == "long" and (closest_zhongshu_ZG <= second_closest_zhongshu_ZD): #最激进
            elif self.operation_direction == "long" and ((closest_zhongshu_ZG <= second_closest_zhongshu_ZD) or (current_price < second_closest_zhongshu_ZD)): #激进一点
                print(f"---------------------止盈止损 {current_price}---------------------")
                self.handle_info("quit", current_price, current_time)  # 平仓信息登记
                self.reset()
            # elif self.operation_direction == "short" and ((closest_zhongshu_ZD >= second_closest_zhongshu_ZG) or (current_price > second_closest_zhongshu_ZD)): #猥琐一点
            # elif self.operation_direction == "short" and (closest_zhongshu_ZD >= second_closest_zhongshu_ZG): #最激进
            elif self.operation_direction == "short" and ((closest_zhongshu_ZD >= second_closest_zhongshu_ZG) or (current_price > second_closest_zhongshu_ZG)):  #激进一点
                print(f"---------------------止盈止损 {current_price}---------------------")
                self.handle_info("quit", current_price, current_time)  # 平仓信息登记
                self.reset()
            else:
                self.zhongshu_formed_time = min(pd.to_datetime(current_time),
                                                    pd.to_datetime(closest_zhongshu_end_time))
                print("时间推进,让利润奔跑")


    def trigger_signals_detect(self, data_X, last_pen_zhongshu_len, pen_zhongshus):
        triggered = False
        if last_pen_zhongshu_len >= self.join_zhongshu_length_bar_online:
            #实盘中超过这个长度，我就开始监测介不介入了, 做中阴阶段获得突破
            triggered = self.trigger_rule(data_X)
        return triggered

    # @abstractmethod
    def trigger_rule(self, data_X):
        ############################################
        ############################################
        #########从决策树生成拷贝过来的段落#############
        if data_X["num_fake_segment_recent"] <= 6.5000 and data_X[
            "lowest_level_check_beichi_now_strength"] <= 0.0328 and data_X[
            "lowest_level_check_beichi_pre_zhongshu_num"] <= 1.5000 and data_X["core_pen_len_<=6"] > 0.5000 and \
                data_X["core_pen_len_<=6"] <= 4.5000 and data_X[
            "lowest_level_check_beichi_pre_strength"] <= 0.0145 and data_X[
            "index_longest_in_20_pen_zhongshus"] > 0.5000 and data_X[
            "index_longest_in_20_pen_zhongshus"] <= 7.5000 and data_X[
            "lowest_level_check_beichi_pre_strength"] <= 0.0080 and data_X["num_fake_segment_recent"] > 5.5000 and \
                data_X["core_pen_len_<=2"] <= 2.5000 and data_X["index_longest_in_20_pen_zhongshus"] > 3.5000 and \
                data_X["lowest_level_check_beichi_now_strength"] <= 0.0204 and data_X[
            "lowest_level_check_beichi_pre_strength"] > -0.0032 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] <= 18.5000 and data_X[
            "lowest_level_check_beichi_pre_strength"] <= 0.0034:
            self.trigger_case_id = 1
            return True
        elif data_X["num_fake_segment_recent"] <= 6.5000 and data_X[
            "lowest_level_check_beichi_now_strength"] <= 0.0328 and data_X[
            "lowest_level_check_beichi_pre_zhongshu_num"] <= 1.5000 and data_X["core_pen_len_<=6"] > 0.5000 and \
                data_X["core_pen_len_<=6"] <= 4.5000 and data_X[
            "lowest_level_check_beichi_pre_strength"] > 0.0145 and data_X[
            "lowest_level_check_beichi_pre_strength"] <= 0.0198 and data_X["core_pen_len_<=6"] <= 1.5000 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] <= 25.5000 and data_X["core_pen_len_<=8"] <= 1.5000:
            self.trigger_case_id = 2
            return True
        elif data_X["num_fake_segment_recent"] <= 6.5000 and data_X[
            "lowest_level_check_beichi_now_strength"] <= 0.0328 and data_X[
            "lowest_level_check_beichi_pre_zhongshu_num"] > 1.5000 and data_X[
            "lowest_level_check_beichi_now_strength"] > 0.0225 and data_X[
            "index_longest_in_20_pen_zhongshus"] <= 14.0000 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] > 13.5000:
            self.trigger_case_id = 3
            return True
        elif data_X["num_fake_segment_recent"] <= 6.5000 and data_X[
            "lowest_level_check_beichi_now_strength"] > 0.0328 and data_X[
            "lowest_level_check_beichi_now_strength"] > 0.0531 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] > 10.5000 and data_X["num_fake_segment_recent"] > 4.5000 and \
                data_X["lowest_level_check_beichi_now_strength"] <= 0.1247 and data_X[
            "lowest_level_check_beichi_now_zhongshu_num"] <= 4.5000 and data_X["core_pen_len_<=8"] > 3.5000 and \
                data_X["core_pen_len_<=6"] <= 4.5000:
            self.trigger_case_id = 4
            return True
        elif data_X["num_fake_segment_recent"] > 6.5000 and data_X["lowest_level_check_beichi_ratio"] <= 3.3622 and \
                data_X["lowest_level_check_beichi_now_strength"] <= 0.0982 and data_X[
            "lowest_level_check_beichi_now_strength"] <= 0.0288 and data_X[
            "lowest_level_check_beichi_ratio"] <= 2.5800 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] <= 36.5000 and data_X[
            "lowest_level_check_beichi_ratio"] > 0.5406 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] > 8.5000 and data_X[
            "lowest_level_check_beichi_ratio"] <= 0.7364 and data_X[
            "lowest_level_check_beichi_pre_strength"] > 0.0032 and data_X["core_pen_len_<=8"] > 2.5000 and data_X[
            "lowest_level_check_beichi_pre_strength"] <= 0.0146 and data_X["core_pen_len_<=2"] <= 3.5000 and data_X[
            "lowest_level_check_beichi_ratio"] <= 0.6818 and data_X["lowest_level_check_beichi_ratio"] <= 0.6250 and \
                data_X["lowest_level_check_beichi_pre_strength"] > 0.0101:
            self.trigger_case_id = 5
            return True
        elif data_X["num_fake_segment_recent"] > 6.5000 and data_X["lowest_level_check_beichi_ratio"] <= 3.3622 and \
                data_X["lowest_level_check_beichi_now_strength"] <= 0.0982 and data_X[
            "lowest_level_check_beichi_now_strength"] > 0.0288 and data_X["core_pen_len_>8"] > 1.5000 and data_X[
            "core_pen_len_<=4"] > 1.5000 and data_X["core_pen_len_<=4"] <= 4.5000 and data_X[
            "lowest_level_check_beichi_now_strength"] > 0.0333 and data_X[
            "index_longest_in_20_pen_zhongshus"] <= 13.5000:
            self.trigger_case_id = 6
            return True
        elif data_X["num_fake_segment_recent"] > 6.5000 and data_X["lowest_level_check_beichi_ratio"] <= 3.3622 and \
                data_X["lowest_level_check_beichi_now_strength"] > 0.0982 and data_X[
            "lowest_level_check_beichi_now_strength"] <= 0.1568 and data_X["num_fake_segment_recent"] <= 10.5000 and \
                data_X["num_pens_longest_in_20_pen_zhongshus"] <= 22.5000 and data_X[
            "index_longest_in_20_pen_zhongshus"] <= 16.5000 and data_X["lowest_level_kuozhan_times"] <= 2.5000 and \
                data_X["core_pen_len_<=2"] > 0.5000:
            self.trigger_case_id = 7
            return True
        elif data_X["num_fake_segment_recent"] > 6.5000 and data_X["lowest_level_check_beichi_ratio"] > 3.3622 and \
                data_X["lowest_level_check_beichi_pre_strength"] <= 0.0713 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] > 8.5000 and data_X[
            "lowest_level_check_beichi_pre_strength"] > 0.0249 and data_X[
            "index_longest_in_20_pen_zhongshus"] > 2.0000 and data_X[
            "lowest_level_check_beichi_now_strength"] > 0.0072:
            self.trigger_case_id = 8
            return True
        else:
            return False
        #########从决策树生成拷贝过来的段落#############
        ############################################
        ############################################





    def determine_relation_direction(self, pen_a, pen_b):
        """
        判断两个中枢之间的相对方向：
        - 若 pen_a["ZD"] >= pen_b["ZG"]，则为 "Down"
        - 否则为 "Up"
        """
        return "Down" if pen_a["ZD"] >= pen_b["ZG"] else "Up"

    def construct_label_and_extra_feature(self, pen_zhongshus, start_index=0, max_lookahead=10):
        """
        构造标签Y ('Chance' 或 'NoChance') 以及属性Z（segment_length_num_pen_zhongshu）。
        限制向后最多lookahead步以查找趋势反转。
        要求至少 min_same_trend_length 个中枢方向一致。
        """

        extra_feature = {'segment_length_num_pen_zhongshu': None, 'last_zhongshu_len': None}

        required_end = start_index + self.lag - 2 + self.min_same_trend_length + 1  # 至少需要这么多中枢
        if required_end >= len(pen_zhongshus):
            return None, extra_feature

        # 条件 1：dir_19_20 和 dir_20_21 不同（先发生反转）
        pen19 = pen_zhongshus[start_index + self.lag - 2]
        pen20 = pen_zhongshus[start_index + self.lag - 1]
        pen21 = pen_zhongshus[start_index + self.lag]

        dir_19_20 = self.determine_relation_direction(pen19, pen20)
        dir_20_21 = self.determine_relation_direction(pen20, pen21)

        if dir_19_20 == dir_20_21:
            extra_feature = {'segment_length_num_pen_zhongshu': None, 'last_zhongshu_len': None}
            extra_feature.update({
                'segment_length_num_pen_zhongshu': None,
                "last_zhongshu_len": len(pen20["core_pens"])
            })
            return "NoChance", extra_feature




        # 条件 2：方向一致性检查
        base_dir = dir_20_21
        for offset in range(1, self.min_same_trend_length):
            a = pen_zhongshus[start_index + self.lag - 1 + offset]
            b = pen_zhongshus[start_index + self.lag + offset]
            if self.determine_relation_direction(a, b) != base_dir:
                extra_feature.update({
                    'segment_length_num_pen_zhongshu': None,
                    "last_zhongshu_len": len(pen20["core_pens"])
                })
                return "NoChance", extra_feature

        # 条件 3：反转 + 趋势新低/新高
        ref_pen_a = pen_zhongshus[start_index + self.lag - 1]
        # ref_pen_b = pen_zhongshus[start_index + self.lag + self.min_same_trend_length - 1]
        reference_low = ref_pen_a["DD"]  # min(ref_pen_a["DD"], ref_pen_b["DD"])
        reference_high = ref_pen_a["GG"]  # max(ref_pen_a["GG"], ref_pen_b["GG"])

        current_index = start_index + self.lag + self.min_same_trend_length - 1
        steps = 0

        while current_index + 1 < len(pen_zhongshus) and steps < max_lookahead:
            dir_now = self.determine_relation_direction(pen_zhongshus[current_index], pen_zhongshus[current_index + 1])
            if dir_now != base_dir:
                final_pen = pen_zhongshus[current_index + 1]
                ##################增加介入机会，比较莽的#######################
                segment_length = current_index + 2 - (start_index + self.lag)
                extra_feature.update({
                    'segment_length_num_pen_zhongshu': segment_length,
                    "last_zhongshu_len": len(pen20["core_pens"])
                })
                return "Chance", extra_feature
                ##################增加介入机会，比较莽的#######################

                # if base_dir == "Down":
                #     if final_pen["GG"] < reference_low:
                #         segment_length = current_index + 2 - (start_index + self.lag)
                #         extra_feature.update({
                #             'segment_length_num_pen_zhongshu': segment_length,
                #             "last_zhongshu_len": len(pen20["core_pens"])
                #         })
                #         return "Chance", extra_feature
                #     else:
                #         extra_feature.update({
                #             'segment_length_num_pen_zhongshu': None,
                #             "last_zhongshu_len": len(pen20["core_pens"])
                #         })
                #         return "NoChance", extra_feature
                # else:  # base_dir == "Up"
                #     if final_pen["DD"] > reference_high:
                #         segment_length = current_index + 2 - (start_index + self.lag)
                #         extra_feature.update({
                #             'segment_length_num_pen_zhongshu': segment_length,
                #             "last_zhongshu_len": len(pen20["core_pens"])
                #         })
                #         return "Chance", extra_feature
                #     else:
                #         extra_feature.update({
                #             'segment_length_num_pen_zhongshu': None,
                #             "last_zhongshu_len": len(pen20["core_pens"])
                #         })
                #         return "NoChance", extra_feature

            current_index += 1
            steps += 1

        extra_feature.update({
            'segment_length_num_pen_zhongshu': None,
            "last_zhongshu_len": len(pen20["core_pens"])
        })
        return None, None

    def construct_X_features(self, pen_zhongshus, start_index=0):
        """
        构造X特征字典，使用第 start_index 到 start_index+19 的 20 个中枢。
        """
        if start_index + self.lag > len(pen_zhongshus):
            return None

        features = {}
        pen_zhongshus_lag_20 = pen_zhongshus[start_index:start_index + self.lag]
        dir_19_20 = self.determine_relation_direction(pen_zhongshus_lag_20[self.lag-2], pen_zhongshus_lag_20[self.lag-1])

        # 特征 1: closest_pen_trend_length, 最近一个笔的走势，是几个笔中枢构成的
        trend_len = 1
        for i in range(self.lag-2, 0, -1):
            if self.determine_relation_direction(pen_zhongshus_lag_20[i - 1], pen_zhongshus_lag_20[i]) == dir_19_20:
                trend_len += 1
            else:
                break
        m = self.lag - trend_len
        features["closest_pen_trend_length"] = trend_len

        trend_pens = pen_zhongshus_lag_20[m-1:self.lag-1]  # 第20个中枢不能算入特征，因为第20个中枢在实际操作时一般是未完成的

        # 特征 2: core_pen_len 分布， 最近一个笔的走势，里面的中枢包含的笔数的分布情况
        lens = [len(p["core_pens"]) for p in trend_pens]
        features.update({
            "core_pen_len_<=2": sum(l <= 2 for l in lens),
            "core_pen_len_<=4": sum(l <= 4 for l in lens),
            "core_pen_len_<=6": sum(l <= 6 for l in lens),
            "core_pen_len_<=8": sum(l <= 8 for l in lens),
            "core_pen_len_>8": sum(l > 8 for l in lens),
        })

        # 特征 3: 背驰结构与强度，最近一个笔的走势, 有没有构成背驰
        longest_zhongshu = max(trend_pens, key=lambda z: len(z["core_pens"]))
        idx_longest = trend_pens.index(longest_zhongshu)
        now_num = len(trend_pens) - 1 - idx_longest
        pre_num = idx_longest

        features["lowest_level_check_beichi_now_zhongshu_num"] = now_num
        features["lowest_level_check_beichi_pre_zhongshu_num"] = pre_num

        m_pen = pen_zhongshus_lag_20[m]
        if dir_19_20 == "Up":
            pre_strength = (longest_zhongshu["GG"] - m_pen["DD"]) / m_pen["DD"]
            now_strength = (pen_zhongshus_lag_20[self.lag-1]["ZG"] - longest_zhongshu["DD"]) / m_pen["DD"]
        else:
            pre_strength = (m_pen["GG"] - longest_zhongshu["DD"]) / m_pen["GG"]
            now_strength = (longest_zhongshu["GG"] - pen_zhongshus_lag_20[self.lag-1]["ZD"]) / m_pen["GG"]

        features["lowest_level_check_beichi_pre_strength"] = pre_strength
        features["lowest_level_check_beichi_now_strength"] = now_strength
        features["lowest_level_check_beichi_ratio"] = pre_strength / now_strength if now_strength != 0 else float("inf")

        # 特征 4: kuozhan_times， 这20个中枢里中枢扩展的次数
        kuozhan_times = 0
        for i in range(self.lag-2, 0, -1):
            if self.determine_relation_direction(pen_zhongshus_lag_20[i], pen_zhongshus_lag_20[i + 1]) != self.determine_relation_direction(pen_zhongshus_lag_20[i - 1], pen_zhongshus_lag_20[i]):
                kuozhan_times += 1
            else:
                break
        features["lowest_level_kuozhan_times"] = kuozhan_times

        # 特征 5: 拖拽力, 这20个笔中枢中最长的中枢，是否会对当前笔走势方向构成回拉的力量
        max_core_pen_len = -1
        index_longest = -1
        for i, pen in enumerate(pen_zhongshus_lag_20[:-1]): # 同样第20个中枢不能算入特征，因为第20个中枢在实际操作时一般是未完成的
            l = len(pen["core_pens"])
            if l > max_core_pen_len:
                max_core_pen_len = l
                big_zhongshu = pen
                index_longest = i

        features["index_longest_in_20_pen_zhongshus"] = index_longest
        features["num_pens_longest_in_20_pen_zhongshus"] = max_core_pen_len

        if dir_19_20 == "Up":
            features["drag_force"] = 1 if big_zhongshu["ZG"] < pen_zhongshus_lag_20[self.lag-1]["ZD"] else 0
        else:
            features["drag_force"] = 1 if big_zhongshu["ZD"] > pen_zhongshus_lag_20[self.lag-1]["ZG"] else 0



        # 特征 6: 中枢升级
        dir_temp = self.determine_relation_direction(pen_zhongshus_lag_20[self.lag-2], pen_zhongshus_lag_20[self.lag-1])
        fake_segment = [{"dir": dir_temp, "trend_len": 1}]
        num_seg = 0
        for i in range(self.lag - 2, 0, -1):
            if self.determine_relation_direction(pen_zhongshus_lag_20[i - 1], pen_zhongshus_lag_20[i]) == dir_temp:
                fake_segment[num_seg]["trend_len"] += 1
            else:
                num_seg += 1
                dir_temp = self.determine_relation_direction(pen_zhongshus_lag_20[i - 1], pen_zhongshus_lag_20[i])
                fake_segment.append({"dir": dir_temp, "trend_len": 1})
        features["num_fake_segment_recent"] = len(fake_segment)

        return features


    def generate_training_sample(self, pen_zhongshus, start_index=0, max_lookahead=10):
        """
        统一生成 X（特征字典）, Y（标签）, Z（趋势延续长度） 样本。
        若数据不足或不满足要求，返回 (None, None, None)
        """
        # 构造 X
        X = self.construct_X_features(pen_zhongshus, start_index)
        if X is None:
            return None, None, None

        # 构造 Y 和 Z
        Y, Z = self.construct_label_and_extra_feature(pen_zhongshus, start_index, max_lookahead=max_lookahead)
        if Y is None:
            return None, None, None

        return X, Y, Z

    def filter_valid_samples(self, df):
        """
        过滤满足以下条件的样本：
        - last_zhongshu_len >= 6
        """
        if not df.empty:
            return df[df['last_zhongshu_len'] >= self.join_zhongshu_length_bar]
        else:
            return df



















#统计延续
class QuantStrategy0002(QuantStrategy):
    def __init__(self, STOCK_NAME_AND_MARKET=None, seconds_size=6):
        self.STOCK_NAME_AND_MARKET = STOCK_NAME_AND_MARKET
        self.seconds_size = seconds_size
        # 后面笔中枢至少走出min_same_trend_length个盈利方向
        self.min_same_trend_length = 1 #3 #1代表最极端的转折就行，别的不管，等于1的时候相当于有介入中枢，和转折走出的第一个中枢两个中枢
        self.join_zhongshu_length_bar = 6 # 最后一个中枢长度至少为6，这个中枢我才考虑去参与，这个用在训练集过滤
        self.join_zhongshu_length_bar_online = self.join_zhongshu_length_bar - 2  # 这是对应join_zhongshu_length_bar的，实盘中超过这个长度，我就开始监测介不介入了
        self.extra_feature_names = ["segment_length_num_pen_zhongshu", "last_zhongshu_len"]
        self.lag = 50 #根据前面20个中枢分析， 后面一些命名用到了20， 19， 18什么的就不更改了，就是self.lag， self.lag-1， self.lag-2的意思
        self.reset()


    def reset(self):
        self.strategy_name = 'QuantStrategy0002'
        self.feature_eng_folder_path = f"checkpoint_PFT/checkpoint_pen_zhongshus_6_seconds_feature_eng_{self.strategy_name}"
        self.new_operation_direction = ""
        self.operation_direction = ""
        self.join_price = None
        self.join_time = None
        self.zhongshu_formed_time = None
        self.num_zhongshu = None
        self.trigger_case_id = None

    def handle_info(self, case, operation_price, operation_time):
        operation_state = ""
        if case == "quit":
            operation_state = "平仓" + self.strategy_name
        elif case == "long":
            operation_state = "做多" + self.strategy_name + f"tiggerID{self.trigger_case_id}"
        elif case == "short":
            operation_state = "做空" + self.strategy_name + f"tiggerID{self.trigger_case_id}"
        # 保存信息
        data = {
            "sanmai_state": operation_state,
            "price": operation_price,
            "time": operation_time
        }
        ermai_folder_path = "machine_learning_caozuo"
        ermai_file_name = f"{self.STOCK_NAME_AND_MARKET}_{self.seconds_size}_second_machine_learning_caozuo.csv"
        ermai_file_path = os.path.join(ermai_folder_path, ermai_file_name)
        os.makedirs(ermai_folder_path, exist_ok=True)
        file_exists = os.path.isfile(ermai_file_path)
        df_data_sanmai = pd.DataFrame([data])
        df_data_sanmai.to_csv(ermai_file_path, mode='a', header=not file_exists, index=False, encoding='utf-8-sig')


    def join_market_operation(self, closest_zhongshu_end_time, closest_zhongshu_ZG, second_closest_zhongshu_ZD, join_price, join_time):
        self.new_operation_direction = "short" if closest_zhongshu_ZG <= \
                                                     second_closest_zhongshu_ZD else "long"
        if self.new_operation_direction != self.operation_direction:
            if not self.operation_direction:
                print(f"0001策略建新仓 价格{join_price}, 方向{self.new_operation_direction}!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            else:
                print(f"0001策略平仓后建新仓 价格{join_price}, 方向{self.new_operation_direction}!!!!!!!!!!!!!!!!!!!!!!!!!")
            self.operation_direction = self.new_operation_direction
            self.join_price = join_price
            self.join_time = join_time
            self.zhongshu_formed_time = min(pd.to_datetime(join_time), pd.to_datetime(closest_zhongshu_end_time))
            # strategy.zhongshu_support_price = history_long_time_pen_zhongshus[-1]["ZD"] if strategy.operation_direction=="long" else history_long_time_pen_zhongshus[-1]["ZG"]
            self.num_zhongshu = 1  # 当前方向第一个中枢
            self.handle_info(self.operation_direction, self.join_price, self.join_time) #建仓信息登记

    def detect_during_operation(self, closest_zhongshu_end_time, closest_zhongshu_start_time, closest_zhongshu_ZG, closest_zhongshu_ZD, second_closest_zhongshu_ZG, second_closest_zhongshu_ZD, current_time, current_price):
        if pd.to_datetime(closest_zhongshu_start_time) > pd.to_datetime(self.zhongshu_formed_time):
            self.num_zhongshu = self.num_zhongshu + 1  # 介入后总共出现的中枢数
            if self.num_zhongshu >= self.min_same_trend_length - 1: #self.num_zhongshu >= self.min_same_trend_length可能吃到的利润太少了，想办法优化一下止盈， 比如冒险一点就self.num_zhongshu >= self.min_same_trend_length + 1
                print(f"---------------------止盈 {current_price}---------------------")
                self.handle_info("quit", current_price, current_time)  # 平仓信息登记
                self.reset()
            # elif self.operation_direction == "long" and ((closest_zhongshu_ZG <= second_closest_zhongshu_ZD) or (current_price < second_closest_zhongshu_ZG)): #猥琐一点
            # elif self.operation_direction == "long" and (closest_zhongshu_ZG <= second_closest_zhongshu_ZD): #最激进
            elif self.operation_direction == "long" and ((closest_zhongshu_ZG <= second_closest_zhongshu_ZD) or (current_price < second_closest_zhongshu_ZD)): #激进一点
                print(f"---------------------止盈止损 {current_price}---------------------")
                self.handle_info("quit", current_price, current_time)  # 平仓信息登记
                self.reset()
            # elif self.operation_direction == "short" and ((closest_zhongshu_ZD >= second_closest_zhongshu_ZG) or (current_price > second_closest_zhongshu_ZD)): #猥琐一点
            # elif self.operation_direction == "short" and (closest_zhongshu_ZD >= second_closest_zhongshu_ZG): #最激进
            elif self.operation_direction == "short" and ((closest_zhongshu_ZD >= second_closest_zhongshu_ZG) or (current_price > second_closest_zhongshu_ZG)):  #激进一点
                print(f"---------------------止盈止损 {current_price}---------------------")
                self.handle_info("quit", current_price, current_time)  # 平仓信息登记
                self.reset()
            else:
                self.zhongshu_formed_time = min(pd.to_datetime(current_time),
                                                    pd.to_datetime(closest_zhongshu_end_time))
                print("时间推进,让利润奔跑")

    def trigger_signals_detect(self, data_X, last_pen_zhongshu_len, pen_zhongshus):
        triggered = False
        if last_pen_zhongshu_len >= self.join_zhongshu_length_bar_online and (self.determine_relation_direction(pen_zhongshus[-1], pen_zhongshus[-2]) != self.determine_relation_direction(pen_zhongshus[-2], pen_zhongshus[-3])):
            #实盘中超过这个长度，我就开始监测介不介入了, 做中阴阶段获得突破
            triggered = self.trigger_rule(data_X)
        return triggered

    # @abstractmethod
    def trigger_rule(self, data_X):
        ############################################
        ############################################
        #########从决策树生成拷贝过来的段落#############
        if data_X["lowest_level_check_beichi_now_strength"] <= 0.0089 and data_X[
            "lowest_level_check_beichi_now_strength"] <= -0.0028 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] > 17.5000:
            self.trigger_case_id = 1
            return True
        else:
            return False
        #########从决策树生成拷贝过来的段落#############
        ############################################
        ############################################




    def determine_relation_direction(self, pen_a, pen_b):
        """
        判断两个中枢之间的相对方向：
        - 若 pen_a["ZD"] >= pen_b["ZG"]，则为 "Down"
        - 否则为 "Up"
        """
        return "Down" if pen_a["ZD"] >= pen_b["ZG"] else "Up"

    def construct_label_and_extra_feature(self, pen_zhongshus, start_index=0, max_lookahead=10):
        """
        构造标签Y ('Chance' 或 'NoChance') 以及属性Z（segment_length_num_pen_zhongshu）。
        限制向后最多lookahead步以查找趋势反转。
        要求至少 min_same_trend_length 个中枢方向一致。
        """

        extra_feature = {'segment_length_num_pen_zhongshu': None, 'last_zhongshu_len': None}

        required_end = start_index + self.lag - 2 + self.min_same_trend_length + 1  # 至少需要这么多中枢
        if required_end >= len(pen_zhongshus):
            return None, extra_feature

        # 条件 1：dir_19_20 和 dir_20_21 不同（先发生反转）
        pen18 = pen_zhongshus[start_index + self.lag - 3]
        pen19 = pen_zhongshus[start_index + self.lag - 2]
        pen20 = pen_zhongshus[start_index + self.lag - 1]
        pen21 = pen_zhongshus[start_index + self.lag]

        dir_18_19 = self.determine_relation_direction(pen18, pen19)
        dir_19_20 = self.determine_relation_direction(pen19, pen20)
        dir_20_21 = self.determine_relation_direction(pen20, pen21)

        if (dir_19_20 != dir_20_21) or (dir_18_19 == dir_20_21):
            extra_feature = {'segment_length_num_pen_zhongshu': None, 'last_zhongshu_len': None}
            extra_feature.update({
                'segment_length_num_pen_zhongshu': None,
                "last_zhongshu_len": len(pen20["core_pens"])
            })
            return "NoChance", extra_feature




        # 条件 2：方向一致性检查
        base_dir = dir_20_21
        for offset in range(1, self.min_same_trend_length):
            a = pen_zhongshus[start_index + self.lag - 1 + offset]
            b = pen_zhongshus[start_index + self.lag + offset]
            if self.determine_relation_direction(a, b) != base_dir:
                extra_feature.update({
                    'segment_length_num_pen_zhongshu': None,
                    "last_zhongshu_len": len(pen20["core_pens"])
                })
                return "NoChance", extra_feature

        # 条件 3：反转 + 趋势新低/新高
        ref_pen_a = pen_zhongshus[start_index + self.lag - 1]
        # ref_pen_b = pen_zhongshus[start_index + self.lag + self.min_same_trend_length - 1]
        reference_low = ref_pen_a["DD"]  # min(ref_pen_a["DD"], ref_pen_b["DD"])
        reference_high = ref_pen_a["GG"]  # max(ref_pen_a["GG"], ref_pen_b["GG"])

        current_index = start_index + self.lag + self.min_same_trend_length - 1
        steps = 0

        while current_index + 1 < len(pen_zhongshus) and steps < max_lookahead:
            dir_now = self.determine_relation_direction(pen_zhongshus[current_index], pen_zhongshus[current_index + 1])
            if dir_now != base_dir:
                final_pen = pen_zhongshus[current_index + 1]
                ##################增加介入机会，比较莽的#######################
                segment_length = current_index + 2 - (start_index + self.lag)
                extra_feature.update({
                    'segment_length_num_pen_zhongshu': segment_length,
                    "last_zhongshu_len": len(pen20["core_pens"])
                })
                return "Chance", extra_feature
                ##################增加介入机会，比较莽的#######################

                # if base_dir == "Down":
                #     if final_pen["GG"] < reference_low:
                #         segment_length = current_index + 2 - (start_index + self.lag)
                #         extra_feature.update({
                #             'segment_length_num_pen_zhongshu': segment_length,
                #             "last_zhongshu_len": len(pen20["core_pens"])
                #         })
                #         return "Chance", extra_feature
                #     else:
                #         extra_feature.update({
                #             'segment_length_num_pen_zhongshu': None,
                #             "last_zhongshu_len": len(pen20["core_pens"])
                #         })
                #         return "NoChance", extra_feature
                # else:  # base_dir == "Up"
                #     if final_pen["DD"] > reference_high:
                #         segment_length = current_index + 2 - (start_index + self.lag)
                #         extra_feature.update({
                #             'segment_length_num_pen_zhongshu': segment_length,
                #             "last_zhongshu_len": len(pen20["core_pens"])
                #         })
                #         return "Chance", extra_feature
                #     else:
                #         extra_feature.update({
                #             'segment_length_num_pen_zhongshu': None,
                #             "last_zhongshu_len": len(pen20["core_pens"])
                #         })
                #         return "NoChance", extra_feature

            current_index += 1
            steps += 1

        extra_feature.update({
            'segment_length_num_pen_zhongshu': None,
            "last_zhongshu_len": len(pen20["core_pens"])
        })
        return None, None

    def construct_X_features(self, pen_zhongshus, start_index=0):
        """
        构造X特征字典，使用第 start_index 到 start_index+19 的 20 个中枢。
        """
        if start_index + self.lag > len(pen_zhongshus):
            return None

        features = {}
        pen_zhongshus_lag_20 = pen_zhongshus[start_index:start_index + self.lag]
        dir_18_19 = self.determine_relation_direction(pen_zhongshus_lag_20[self.lag-3], pen_zhongshus_lag_20[self.lag-2])

        # 特征 1: closest_pen_trend_length, 最近一个笔的走势，是几个笔中枢构成的
        trend_len = 2
        for i in range(self.lag-3, 0, -1):
            if self.determine_relation_direction(pen_zhongshus_lag_20[i - 1], pen_zhongshus_lag_20[i]) == dir_18_19:
                trend_len += 1
            else:
                break
        m = self.lag - trend_len
        features["closest_pen_trend_length"] = trend_len

        trend_pens = pen_zhongshus_lag_20[m-1:self.lag-2]  # 第20个中枢不能算入特征，因为第20个中枢在实际操作时一般是未完成的

        # 特征 2: core_pen_len 分布， 最近一个笔的走势，里面的中枢包含的笔数的分布情况
        lens = [len(p["core_pens"]) for p in trend_pens]
        features.update({
            "core_pen_len_<=2": sum(l <= 2 for l in lens),
            "core_pen_len_<=4": sum(l <= 4 for l in lens),
            "core_pen_len_<=6": sum(l <= 6 for l in lens),
            "core_pen_len_<=8": sum(l <= 8 for l in lens),
            "core_pen_len_>8": sum(l > 8 for l in lens),
        })

        # 特征 3: 背驰结构与强度，最近一个笔的走势, 有没有构成背驰
        longest_zhongshu = max(trend_pens, key=lambda z: len(z["core_pens"]))
        idx_longest = trend_pens.index(longest_zhongshu)
        now_num = len(trend_pens) - 1 - idx_longest
        pre_num = idx_longest

        features["lowest_level_check_beichi_now_zhongshu_num"] = now_num
        features["lowest_level_check_beichi_pre_zhongshu_num"] = pre_num

        m_pen = pen_zhongshus_lag_20[m]
        if dir_18_19 == "Up":
            pre_strength = (longest_zhongshu["GG"] - m_pen["DD"]) / m_pen["DD"]
            now_strength = (pen_zhongshus_lag_20[self.lag-1]["ZG"] - longest_zhongshu["DD"]) / m_pen["DD"]
        else:
            pre_strength = (m_pen["GG"] - longest_zhongshu["DD"]) / m_pen["GG"]
            now_strength = (longest_zhongshu["GG"] - pen_zhongshus_lag_20[self.lag-1]["ZD"]) / m_pen["GG"]

        features["lowest_level_check_beichi_pre_strength"] = pre_strength
        features["lowest_level_check_beichi_now_strength"] = now_strength
        features["lowest_level_check_beichi_ratio"] = pre_strength / now_strength if now_strength != 0 else float("inf")

        # 特征 4: kuozhan_times， 这20个中枢里中枢扩展的次数
        kuozhan_times = 0
        for i in range(self.lag-3, 0, -1):
            if self.determine_relation_direction(pen_zhongshus_lag_20[i], pen_zhongshus_lag_20[i + 1]) != self.determine_relation_direction(pen_zhongshus_lag_20[i - 1], pen_zhongshus_lag_20[i]):
                kuozhan_times += 1
            else:
                break
        features["lowest_level_kuozhan_times"] = kuozhan_times

        # 特征 5: 拖拽力, 这20个笔中枢中最长的中枢，是否会对当前笔走势方向构成回拉的力量
        max_core_pen_len = -1
        index_longest = -1
        for i, pen in enumerate(pen_zhongshus_lag_20[:-2]): # 同样第20个中枢不能算入特征，因为第20个中枢在实际操作时一般是未完成的,这里右侧交易所以第19个也不算
            l = len(pen["core_pens"])
            if l > max_core_pen_len:
                max_core_pen_len = l
                big_zhongshu = pen
                index_longest = i

        features["index_longest_in_20_pen_zhongshus"] = index_longest
        features["num_pens_longest_in_20_pen_zhongshus"] = max_core_pen_len

        if dir_18_19 == "Up":
            features["drag_force"] = 1 if big_zhongshu["ZG"] < pen_zhongshus_lag_20[self.lag-1]["ZD"] else 0
        else:
            features["drag_force"] = 1 if big_zhongshu["ZD"] > pen_zhongshus_lag_20[self.lag-1]["ZG"] else 0



        # 特征 6: 中枢升级
        dir_temp = self.determine_relation_direction(pen_zhongshus_lag_20[self.lag-3], pen_zhongshus_lag_20[self.lag-2])
        fake_segment = [{"dir": dir_temp, "trend_len": 1}]
        num_seg = 0
        for i in range(self.lag - 3, 0, -1):
            if self.determine_relation_direction(pen_zhongshus_lag_20[i - 1], pen_zhongshus_lag_20[i]) == dir_temp:
                fake_segment[num_seg]["trend_len"] += 1
            else:
                num_seg += 1
                dir_temp = self.determine_relation_direction(pen_zhongshus_lag_20[i - 1], pen_zhongshus_lag_20[i])
                fake_segment.append({"dir": dir_temp, "trend_len": 1})
        features["num_fake_segment_recent"] = len(fake_segment)

        return features


    def generate_training_sample(self, pen_zhongshus, start_index=0, max_lookahead=10):
        """
        统一生成 X（特征字典）, Y（标签）, Z（趋势延续长度） 样本。
        若数据不足或不满足要求，返回 (None, None, None)
        """
        # 构造 X
        X = self.construct_X_features(pen_zhongshus, start_index)
        if X is None:
            return None, None, None

        # 构造 Y 和 Z
        Y, Z = self.construct_label_and_extra_feature(pen_zhongshus, start_index, max_lookahead=max_lookahead)
        if Y is None:
            return None, None, None

        return X, Y, Z

    def filter_valid_samples(self, df):
        """
        过滤满足以下条件的样本：
        - last_zhongshu_len >= 6
        """
        if not df.empty:
            return df[df['last_zhongshu_len'] >= self.join_zhongshu_length_bar]
        else:
            return df


class QuantStrategyNVDA_NASDAQ(QuantStrategy0002):
    def trigger_rule(self, data_X):
        if data_X["lowest_level_check_beichi_now_strength"] <= 0.0089 and data_X[
            "lowest_level_check_beichi_now_strength"] <= -0.0028 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] > 17.5000:
            self.trigger_case_id = 1
            return True
        else:
            return False



class QuantStrategyAMZN_NASDAQ(QuantStrategy0002):
    def trigger_rule(self, data_X):
        if data_X["lowest_level_check_beichi_now_strength"] <= 0.0085 and data_X[
            "num_fake_segment_recent"] > 21.5000 and data_X["index_longest_in_20_pen_zhongshus"] > 4.0000 and data_X[
            "lowest_level_check_beichi_ratio"] > 0.6577:
            self.trigger_case_id = 1
            return True
        else:
            return False


class QuantStrategyMETA_NASDAQ(QuantStrategy0002):
    def trigger_rule(self, data_X):
        if data_X["lowest_level_check_beichi_now_strength"] <= 0.0107 and data_X[
            "lowest_level_check_beichi_pre_strength"] > -0.0018 and data_X[
            "lowest_level_check_beichi_ratio"] <= 7.2421 and data_X["lowest_level_check_beichi_ratio"] > -0.8813 and \
                data_X["lowest_level_check_beichi_now_strength"] > -0.0213 and data_X[
            "lowest_level_check_beichi_now_strength"] <= 0.0037 and data_X["core_pen_len_<=2"] <= 0.5000:
            self.trigger_case_id = 1
            return True
        else:
            return False

# class QuantStrategyMSFT_NASDAQ(QuantStrategy0002):
#     def trigger_rule(self, data_X):
#         super().trigger_rule(data_X)

class QuantStrategySNOW_NYSE(QuantStrategy0002):
    def trigger_rule(self, data_X):
        if data_X["lowest_level_check_beichi_now_strength"] <= 0.0208 and data_X["core_pen_len_<=4"] > 0.5000 and \
                data_X["lowest_level_check_beichi_now_strength"] <= 0.0097 and data_X[
            "lowest_level_check_beichi_ratio"] > -0.8786 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] > 19.0000 and data_X[
            "lowest_level_check_beichi_pre_strength"] <= 0.0141:
            self.trigger_case_id = 1
            return True
        else:
            return False


# class QuantStrategyTIGR_NASDAQ(QuantStrategy0002):
#     def trigger_rule(self, data_X):
#         super().trigger_rule(data_X)
#
# class QuantStrategyTSLA_NASDAQ(QuantStrategy0002):
#     def trigger_rule(self, data_X):
#         super().trigger_rule(data_X)

class QuantStrategyU_NYSE(QuantStrategy0002):
    def trigger_rule(self, data_X):
        if data_X["lowest_level_check_beichi_now_strength"] <= 0.0290 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] > 13.5000 and data_X[
            "lowest_level_check_beichi_now_strength"] <= 0.0141 and data_X["num_fake_segment_recent"] <= 28.5000 and \
                data_X["index_longest_in_20_pen_zhongshus"] > 3.5000 and data_X[
            "num_fake_segment_recent"] <= 25.5000 and data_X["drag_force"] <= 0.5000:
            self.trigger_case_id = 1
            return True
        elif data_X["lowest_level_check_beichi_now_strength"] <= 0.0290 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] > 13.5000 and data_X[
            "lowest_level_check_beichi_now_strength"] > 0.0141 and data_X["core_pen_len_<=8"] > 1.5000 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] <= 22.0000 and data_X["num_fake_segment_recent"] > 21.5000:
            self.trigger_case_id = 2
            return True
        else:
            return False


class QuantStrategyAVGO_NASDAQ(QuantStrategy0002):
    def trigger_rule(self, data_X):
        if data_X["lowest_level_check_beichi_now_strength"] <= 0.0134 and data_X[
            "lowest_level_check_beichi_ratio"] <= -0.0624 and data_X["lowest_level_kuozhan_times"] <= 2.5000 and \
                data_X["num_pens_longest_in_20_pen_zhongshus"] > 15.5000 and data_X[
            "lowest_level_check_beichi_pre_strength"] > -0.0028:
            self.trigger_case_id = 1
            return True
        else:
            return False


# class QuantStrategyAAPL_NASDAQ(QuantStrategy0002):
#     def trigger_rule(self, data_X):
#         super().trigger_rule(data_X)
#
# class QuantStrategyLLY_NYSE(QuantStrategy0002):
#     def trigger_rule(self, data_X):
#         super().trigger_rule(data_X)

class QuantStrategyNVO_NYSE(QuantStrategy0002):
    def trigger_rule(self, data_X):
        if data_X["lowest_level_check_beichi_now_strength"] <= 0.0112 and data_X["drag_force"] <= 0.5000 and data_X[
            "lowest_level_check_beichi_ratio"] > -0.3844 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] <= 22.5000 and data_X[
            "lowest_level_check_beichi_now_strength"] > -0.0501 and data_X["core_pen_len_<=4"] <= 1.5000 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] > 15.0000 and data_X["lowest_level_kuozhan_times"] <= 2.5000:
            self.trigger_case_id = 1
            return True
        else:
            return False



class QuantStrategyADBE_NASDAQ(QuantStrategy0002):
    def trigger_rule(self, data_X):
        if data_X["lowest_level_check_beichi_now_strength"] <= 0.0143 and data_X[
            "lowest_level_check_beichi_ratio"] <= 3.5249 and data_X["num_fake_segment_recent"] <= 26.5000 and \
                data_X["index_longest_in_20_pen_zhongshus"] <= 37.5000 and data_X[
            "index_longest_in_20_pen_zhongshus"] <= 5.5000 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] > 17.5000:
            self.trigger_case_id = 1
            return True
        elif data_X["lowest_level_check_beichi_now_strength"] <= 0.0143 and data_X[
            "lowest_level_check_beichi_ratio"] <= 3.5249 and data_X["num_fake_segment_recent"] <= 26.5000 and \
                data_X["index_longest_in_20_pen_zhongshus"] <= 37.5000 and data_X[
            "index_longest_in_20_pen_zhongshus"] > 5.5000 and data_X["num_fake_segment_recent"] > 20.5000 and \
                data_X["lowest_level_check_beichi_ratio"] > 0.5303 and data_X[
            "lowest_level_check_beichi_now_strength"] > 0.0009:
            self.trigger_case_id = 2
            return True
        else:
            return False


class QuantStrategyTSM_NYSE(QuantStrategy0002):
    def trigger_rule(self, data_X):
        if data_X["lowest_level_check_beichi_now_strength"] <= 0.0080 and data_X[
            "num_fake_segment_recent"] > 16.5000 and data_X["index_longest_in_20_pen_zhongshus"] > 1.5000 and \
                data_X["index_longest_in_20_pen_zhongshus"] <= 44.5000 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] > 12.5000 and data_X[
            "lowest_level_check_beichi_ratio"] <= -0.2189 and data_X["index_longest_in_20_pen_zhongshus"] > 5.0000:
            self.trigger_case_id = 1
            return True
        elif data_X["lowest_level_check_beichi_now_strength"] > 0.0080 and data_X["core_pen_len_<=4"] > 1.5000 and \
                data_X["lowest_level_check_beichi_ratio"] > 0.4112 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] <= 29.5000 and data_X[
            "lowest_level_check_beichi_ratio"] <= 3.5368 and data_X["index_longest_in_20_pen_zhongshus"] <= 37.5000:
            self.trigger_case_id = 3
            return True
        else:
            return False



# class QuantStrategyPFE_NYSE(QuantStrategy0002):
#     def trigger_rule(self, data_X):
#         super().trigger_rule(data_X)

class QuantStrategyJPM_NYSE(QuantStrategy0002):
    def trigger_rule(self, data_X):
        if data_X["lowest_level_check_beichi_now_strength"] <= 0.0078 and data_X["core_pen_len_<=8"] > 0.5000 and \
                data_X["num_fake_segment_recent"] > 16.5000 and data_X[
            "index_longest_in_20_pen_zhongshus"] > 4.5000 and data_X[
            "lowest_level_check_beichi_pre_strength"] <= 0.0033 and data_X[
            "lowest_level_check_beichi_ratio"] > -10.7778 and data_X[
            "index_longest_in_20_pen_zhongshus"] > 5.5000 and data_X["lowest_level_kuozhan_times"] <= 4.0000 and \
                data_X["index_longest_in_20_pen_zhongshus"] > 27.5000 and data_X["core_pen_len_>8"] <= 0.5000:
            self.trigger_case_id = 1
            return True
        else:
            return False



class QuantStrategyBAC_NYSE(QuantStrategy0002):
    def trigger_rule(self, data_X):
        if data_X["lowest_level_check_beichi_now_strength"] <= 0.0078 and data_X[
            "lowest_level_check_beichi_pre_strength"] > -0.0018 and data_X[
            "lowest_level_check_beichi_now_strength"] > 0.0007 and data_X[
            "lowest_level_check_beichi_pre_strength"] > -0.0005 and data_X[
            "index_longest_in_20_pen_zhongshus"] <= 29.0000:
            self.trigger_case_id = 1
            return True
        else:
            return False



class QuantStrategyCOST_NASDAQ(QuantStrategy0002):
    def trigger_rule(self, data_X):
        if data_X["lowest_level_check_beichi_now_strength"] <= 0.0148 and data_X[
            "lowest_level_check_beichi_now_strength"] <= 0.0085 and data_X["closest_pen_trend_length"] <= 3.5000 and \
                data_X["index_longest_in_20_pen_zhongshus"] > 2.0000 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] > 16.5000 and data_X["num_fake_segment_recent"] > 15.5000 and \
                data_X["core_pen_len_<=8"] > 0.5000 and data_X[
            "lowest_level_check_beichi_now_strength"] <= 0.0071 and data_X["num_fake_segment_recent"] > 17.5000:
            self.trigger_case_id = 1
            return True
        else:
            return False

class QuantStrategyNFLX_NASDAQ(QuantStrategy0002):
    def trigger_rule(self, data_X):
        if data_X["lowest_level_check_beichi_now_strength"] <= 0.0081 and data_X["core_pen_len_>8"] <= 0.5000 and \
                data_X["lowest_level_check_beichi_now_strength"] > -0.0001 and data_X[
            "core_pen_len_<=6"] <= 3.0000 and data_X["num_pens_longest_in_20_pen_zhongshus"] <= 26.5000 and data_X[
            "num_pens_longest_in_20_pen_zhongshus"] <= 20.0000:
            self.trigger_case_id = 1
            return True
        else:
            return False


