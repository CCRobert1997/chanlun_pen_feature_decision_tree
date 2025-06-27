import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
from datetime import time as datetime_time
import pandas as pd
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.preprocessing import PolynomialFeatures
from sklearn.svm import OneClassSVM
from sklearn.metrics import precision_score
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.tree import _tree
from sklearn.metrics import confusion_matrix, classification_report


import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from trigger_and_feature_library import *
from chanlun_utils import draw_zhongshu, merge_segments_fix_with_checkpoint, load_segments_from_ndjson, ensure_datetime, find_zhongshu_one_pen_form



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
                       "TSM_NYSE": QuantStrategy,
                       "PFE_NYSE": QuantStrategy,
                       "JPM_NYSE": QuantStrategy,
                       "BAC_NYSE": QuantStrategy,
                       "COST_NASDAQ": QuantStrategy,
                       "NFLX_NASDAQ": QuantStrategy}
# STOCK_NAME_AND_MARKETS = ["NVDA_NASDAQ"]


# 加载并拼接所有 CSV 文件
# strategy = QuantStrategy0001()
strategy = QuantStrategy0002()
# strategy = STOCK_QuantStrategy[STOCK_NAME_AND_MARKETS[0]]()

folder_path = strategy.feature_eng_folder_path

all_files = [f for f in os.listdir(folder_path) if f.endswith(".csv")]

df_list = []
for f in all_files:
    df = pd.read_csv(os.path.join(folder_path, f))
    if not df.empty and df.dropna(how="all", axis=1).shape[1] > 0:
        df_list.append(df)

df_all = pd.concat(df_list, ignore_index=True)

# 自动选择 X：所有列中除去 'label' 和 'segment_length_num_pen_zhongshu'
auto_X_columns = [col for col in df_all.columns if col not in ["label"]+strategy.extra_feature_names]

# 筛选数据
df_model = df_all[auto_X_columns + ["label"]].copy()
df_model.dropna(inplace=True)




X = df_model[auto_X_columns]
y = df_model["label"]

# 标准化
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# PCA 降维
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)

# 绘图
plt.figure(figsize=(8, 6))
colors = {"Chance": "red", "NoChance": "blue"}
for label in ["Chance", "NoChance"]:
    mask = y == label
    plt.scatter(X_pca[mask, 0], X_pca[mask, 1], label=label, alpha=0.6, c=colors[label], s=10)
plt.xlabel("PCA Component 1")
plt.ylabel("PCA Component 2")
plt.title("PCA Visualization of Zhongshu Features")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()





# X_tsne = TSNE(n_components=2, perplexity=30, random_state=42).fit_transform(X)
#
# plt.figure(figsize=(8, 6))
# for label in ["Chance", "NoChance"]:
#     mask = y == label
#     plt.scatter(X_tsne[mask, 0], X_tsne[mask, 1], label=label, alpha=0.6, s=10, c=colors[label])
# plt.title("t-SNE Projection")
# plt.legend()
# plt.grid(True)
# plt.tight_layout()
# plt.show()






# THRESHHOLD_CHANCE = 0.95
# CLASS_WEIGHT = "balanced" #{"Chance": 5, "NoChance": 1}
# MAX_DEPTH = 8
# RANDOM_STATE = 42
THRESHHOLD_CHANCE = 0.8
CLASS_WEIGHT = {"Chance": 5, "NoChance": 1}#{"Chance": 5, "NoChance": 1}#{"Chance": 1, "NoChance": 1}#{"Chance": 5, "NoChance": 1}
MAX_DEPTH = 10#18#14
RANDOM_STATE = 49





X = df_model[auto_X_columns]
y = df_model["label"]
Z = df_all[strategy.extra_feature_names]


# 训练决策树模型
clf_tree = DecisionTreeClassifier(class_weight=CLASS_WEIGHT, max_depth=MAX_DEPTH, random_state=RANDOM_STATE)
clf_tree.fit(X, y)

# 可视化决策树
plt.figure(figsize=(20, 10))
plot_tree(clf_tree, feature_names=auto_X_columns, class_names=clf_tree.classes_, filled=True)
plt.title("Decision Tree for Zhongshu Classification")
plt.show()

# 获取预测概率
y_proba = clf_tree.predict_proba(X)

# 类别顺序（0: Chance, 1: NoChance）
chance_index = list(clf_tree.classes_).index("Chance")

# 自定义阈值，例如只有当Chance的概率大于0.9才预测为Chance
threshold = THRESHHOLD_CHANCE
y_pred_high_conf = [
    "Chance" if prob[chance_index] > threshold else "NoChance"
    for prob in y_proba
]

# 找出预测为 Chance 的条目并提取 segment_length_num_pen_zhongshu
chance_indices = [i for i, pred in enumerate(y_pred_high_conf) if pred == "Chance"]
segment_lengths_predicted_chance = Z.iloc[chance_indices]
segment_lengths_predicted_chance = segment_lengths_predicted_chance.reset_index(drop=True)
print(segment_lengths_predicted_chance)



# 混淆矩阵和报告
conf_matrix_thresh = confusion_matrix(y, y_pred_high_conf, labels=["Chance", "NoChance"])
report_thresh = classification_report(y, y_pred_high_conf, labels=["Chance", "NoChance"])
print("Confusion Matrix with threshold = {:.2f}:\n".format(threshold), conf_matrix_thresh)
print("\nClassification Report with threshold = {:.2f}:\n".format(threshold), report_thresh)




from collections import Counter
# 找出所有样本的叶节点编号
high_conf_leaf_indices = clf_tree.apply(X.values)

# 过滤预测为 Chance 的样本对应的叶节点
chance_leaf_nodes = [
    node for pred, node in zip(y_pred_high_conf, high_conf_leaf_indices) if pred == "Chance"
]

# 统计各叶节点中 high-confidence Chance 样本数量
chance_leaf_node_counts = Counter(chance_leaf_nodes)
chance_leaf_node_df = pd.DataFrame([
    {"leaf_node": node, "count": count}
    for node, count in chance_leaf_node_counts.items()
])
print(chance_leaf_node_df)










from collections import defaultdict

# 初始化结构统计每个叶子节点上的 label 数量
leaf_label_distribution = defaultdict(lambda: {"Chance": 0, "NoChance": 0})

# 获取所有样本的预测叶子节点索引
leaf_indices = clf_tree.apply(X.values)

# 累加统计
for leaf_index, label in zip(leaf_indices, y):
    leaf_label_distribution[leaf_index][label] += 1

# 转换为 DataFrame 展示
leaf_distribution_df = pd.DataFrame([
    {"leaf_node": node, "Chance": counts["Chance"], "NoChance": counts["NoChance"]}
    for node, counts in leaf_label_distribution.items()
])
leaf_distribution_df["chance_to_nochance_ratio"] = leaf_distribution_df["Chance"] / (leaf_distribution_df["NoChance"] + 1e-6)
leaf_distribution_df = leaf_distribution_df.sort_values(by="chance_to_nochance_ratio", ascending=False)
pd.set_option('display.max_rows', None)
print(leaf_distribution_df)

# count = (leaf_distribution_df["NoChance"] == 0) & (leaf_distribution_df["Chance"] >= 4)
count = (leaf_distribution_df["NoChance"] + leaf_distribution_df["Chance"] >= 7) & (leaf_distribution_df["chance_to_nochance_ratio"] >= 5)
# count_2 = (leaf_distribution_df["NoChance"] > 0) & (leaf_distribution_df["chance_to_nochance_ratio"] >= 4)
# num_satisfying_leaves = count.sum() + count_2.sum()
total_chance = leaf_distribution_df.loc[count, "Chance"].sum()
total_lose = leaf_distribution_df.loc[count, "NoChance"].sum()
# print(f"好节点个数 {num_satisfying_leaves}")
print(f"接纳节点个数 {count.sum()}")
print(f"接纳的节点总的机会数 {total_chance}")
print(f"接纳的节点总的失败数 {total_lose}")
print(f"""高频率节点数{((leaf_distribution_df["NoChance"] + leaf_distribution_df["Chance"] >= 20) & (leaf_distribution_df["chance_to_nochance_ratio"] >= 1.5)).sum()}""")

# dangerous_count = (leaf_distribution_df["NoChance"] == 1) & (leaf_distribution_df["Chance"] >= 4)
# num_dangerous_leaves = dangerous_count.sum()
# print(f"误导性节点个数 {num_dangerous_leaves}")





# 以 leaf_node = 77 为例（你可以换成你感兴趣的节点编号）
target_leaf_node = leaf_distribution_df.iloc[0]["leaf_node"] #排第一的节点
# target_leaf_node = 20
# target_leaf_node = 10
# 获取所有样本的叶节点编号
leaf_indices = clf_tree.apply(X.values)
# 找出属于该叶子节点的样本索引
matching_indices = [i for i, node in enumerate(leaf_indices) if node == target_leaf_node]
# 获取这些样本对应的 Z 值
Z_in_leaf = Z.iloc[matching_indices].reset_index(drop=True)
# 打印查看
print(f"Z values in leaf node {target_leaf_node}:")
print(Z_in_leaf)


# Step 4: 绘图，异色标识
plt.figure(figsize=(8, 6))
plt.scatter(X_pca[:, 0], X_pca[:, 1], c='gray', alpha=0.5, label='Other Samples')
plt.scatter(X_pca[matching_indices, 0], X_pca[matching_indices, 1], c='red', label=f'Leaf {target_leaf_node}')
plt.legend()
plt.title("PCA Visualization with Highlighted Leaf Node")
plt.xlabel("PC1")
plt.ylabel("PC2")
plt.grid(True)
plt.show()



target_leaf_node = leaf_distribution_df.iloc[1]["leaf_node"] #排第二的节点
leaf_indices = clf_tree.apply(X.values)
matching_indices = [i for i, node in enumerate(leaf_indices) if node == target_leaf_node]
Z_in_leaf = Z.iloc[matching_indices].reset_index(drop=True)
print(f"Z values in leaf node {target_leaf_node}:")
print(Z_in_leaf)

# Step 4: 绘图，异色标识
plt.figure(figsize=(8, 6))
plt.scatter(X_pca[:, 0], X_pca[:, 1], c='gray', alpha=0.5, label='Other Samples')
plt.scatter(X_pca[matching_indices, 0], X_pca[matching_indices, 1], c='red', label=f'Leaf {target_leaf_node}')
plt.legend()
plt.title("PCA Visualization with Highlighted Leaf Node")
plt.xlabel("PC1")
plt.ylabel("PC2")
plt.grid(True)
plt.show()






def get_leaf_conditions(decision_tree, feature_names, target_leaf_ids):
    tree_ = decision_tree.tree_
    feature = tree_.feature
    threshold = tree_.threshold

    paths = {}  # leaf_id -> list of (feature, operator, threshold)

    def recurse(node_id, path):
        if tree_.feature[node_id] != _tree.TREE_UNDEFINED:
            feat_name = feature_names[feature[node_id]]
            thresh = threshold[node_id]
            left_path = path + [(feat_name, "<=", thresh)]
            recurse(tree_.children_left[node_id], left_path)
            right_path = path + [(feat_name, ">", thresh)]
            recurse(tree_.children_right[node_id], right_path)
        else:
            if node_id in target_leaf_ids:
                paths[node_id] = path

    recurse(0, [])
    return paths


# 假设 leaf_label_distribution 和 leaf_distribution_df 已经存在
target_leaf_ids = leaf_distribution_df[count]["leaf_node"].tolist()

feature_columns = X.columns.tolist()
leaf_conditions = get_leaf_conditions(clf_tree, feature_columns, target_leaf_ids)

# # 打印结果
# for node_id, conds in leaf_conditions.items():
#     print(f"\nLeaf Node {node_id} 分裂条件:")
#     for feat, op, thresh in conds:
#         print(f"  {feat} {op} {thresh:.4f}")


# 转换为 Python if 语句格式
print("triggered = False\nif last_pen_zhongshu_len >= self.join_zhongshu_length_bar_online:")
python_if_blocks = []
data_instance_name = "data_X"
operation_command = """return True"""
trigger_case_id = 0
for node_id, conds in leaf_conditions.items():
    trigger_case_id += 1
    lines = [f"{feat} {op} {thresh:.4f}" for feat, op, thresh in conds]
    python_block = f"""{"    if " if trigger_case_id==1 else "    elif "}""" + " and ".join([f"""{data_instance_name}["{feat}"] {op} {thresh:.4f}""" for feat, op, thresh in conds]) + f":\n        self.trigger_case_id = {trigger_case_id}\n        {operation_command}"
    python_if_blocks.append((node_id, python_block))
    print(python_block)
print("    else:\n       return False")
