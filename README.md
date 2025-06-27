# 📊 Machine Learning Signal Detection Pipeline for Pen & Zhongshu Structure

This repository provides a pipeline for detecting buy signals using pen-level and pen-zhongshu level structure, trained and evaluated on a per-stock basis.

---

## 1. 📁 Data Preparation

### Step 1: Generate Raw Pen & Zhongshu Structures on Server

```bash
bash command_list_find_signal_machine_learning_pen_and_pen_zhongshu_track_only.sh
```

- This runs `find_ermai_penlevel_zhongshu_ML_for_visualization_pen_and_penzhongshu_track_only.py` for multiple stocks.
- Results are stored in:
  - `checkpoint_pen_6_seconds`
  - `checkpoint_pen_zhongshus_6_seconds`

---

## 2. ⚙️ Feature Engineering

### Step 2: Extract Features for a Single Stock

Edit `chanlun_feature_engineer.py`:

```python
STOCK_NAME_AND_MARKETS = ["NFLX_NASDAQ"]
strategy = STOCK_QuantStrategy[STOCK_NAME_AND_MARKETS[0]]()
```

Then run:

```bash
python machine_learning/chanlun_feature_engineer.py
```

Output will be a CSV file in:

```
checkpoint_PFT/checkpoint_pen_zhongshus_6_seconds_feature_eng_QuantStrategy0002/
```

---

## 3. 🤖 Model Training and Evaluation

### Step 3: Train the Decision Tree

**Make sure only the target stock's CSV is in the feature folder.**

Then run:

```bash
python machine_learning/chanlun_feature_based_machine_learning_decision_tree.py
```

### Output:
- PCA 2D projection of:
  1. True labels
  2. Best-performing leaf node (highest precision on "Chance")
  3. Second-best node

### Effective Leaf Node Criteria:

```python
count = (
    (leaf_distribution_df["NoChance"] + leaf_distribution_df["Chance"] >= 7) &
    (leaf_distribution_df["chance_to_nochance_ratio"] >= 5)
)
```

- Adjust `7` for statistical significance.
- Check PCA plots manually to determine if the cluster is meaningful.
- If the clustering is weak, do **not** include this stock in live trading.

---

## 4. ✅ Final Signal Rule Code Generation

At the end of training, you will see a code block like:

```python
triggered = False
if last_pen_zhongshu_len >= self.join_zhongshu_length_bar_online:
    if data_X["lowest_level_check_beichi_now_strength"] <= 0.0081 and ...
        self.trigger_case_id = 1
        return True
    else:
        return False
```

Paste this into:

```python
trigger_and_feature_library.py
```

Under the class for that stock:

```python
class QuantStrategyNFLX_NASDAQ(QuantStrategy0002):
    def trigger_rule(self, data_X):
        # paste the generated trigger rule here
```

---

## 5. 📡 Live Monitoring for Signals

### Step 4: Activate Live Signal Detection

```bash
bash command_list_find_signal_machine_learning_selected_stock_based_on_whether_ML_class_exist.sh
```

Before running, **check** this in `find_ermai_penlevel_zhongshu_ML_for_visualization.py`:

- Ensure:

```python
########################线上实盘到全时间回测记得切换#########################
```

- Uncomment blocks surrounded by:

```python
############################### 线上实盘用 ###############################
```

- Comment blocks surrounded by:

```python
############################### 全时间回测用 ###############################
```

---

## 6. 🔄 Support Scripts in Operation

### Check if Machine Learning CSV Grabber Is Running:

```bash
ps aux | grep pull_machine_learning_caozuo_csv_file_from_server.sh
```

If not running, restart:

```bash
bash nohup_run_pull_machine_learning_caozuo_csv_file_from_server.sh
```

### Check Alert Server (Local):

```bash
ps aux | grep alert_server_machine_learning.py
```

If not running, open the alert app and run:

```bash
bash nohup_run_local_server_to_send_message_to_ring.sh
```

---

## 7. 📈 Visualization

To enable visualization on server:

```bash
nohup python ermai_caozuo_visualization.py > ermai_caozuo_visualization.log 2>&1 &
nohup python machine_learning_caozuo_visualization.py > machine_learning_caozuo_visualization.log 2>&1 &
```

Port-forward to local:

- Master node:

```bash
ssh -L 7010:localhost:7010 -i ~/ssh_keys/newKey ubuntu@118.138.234.44
```

- 16-core CPU node:

```bash
ssh -L 7010:localhost:7010 -i ~/ssh_keys/newKey ubuntu@118.138.233.245
```

---

## 8. 🔍 Monitoring on Server

### Check if Pen & Zhongshu Construction Is Running

```bash
ps aux | grep find_ermai_penlevel_zhongshu_ML_for_visualization_pen_and_penzhongshu_track_only.py
```

### Check if Signal Detection Is Running

```bash
ps aux | grep find_ermai_penlevel_zhongshu_ML_for_visualization.py
```
