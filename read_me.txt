检查是否有在向服务器抓取三买信息，
ps aux | grep pull_sanmai_caozuo_csv_file_from_server.sh
没有的话要重启：
bash nohup_run_pull_sanmai_caozuo_csv_file_from_server.sh

检查是否有在向服务器抓取二买信息，
ps aux | grep pull_ermai_caozuo_csv_file_from_server.sh
没有的话要重启：
bash nohup_run_pull_ermai_caozuo_csv_file_from_server.sh

检查是否有在向服务器抓取机器学习买点信息，
ps aux | grep pull_machine_learning_caozuo_csv_file_from_server.sh
没有的话要重启：
bash nohup_run_pull_machine_learning_caozuo_csv_file_from_server.sh


检查闹钟本地服务器
ps aux | grep alert_server.py 
ps aux | grep alert_server_ermai_6seconds.py
ps aux | grep alert_server_machine_learning.py





开盘前准备：
1.检查是否有在向服务器抓取三买信息，
ps aux | grep pull_sanmai_caozuo_csv_file_from_server.sh
ps aux | grep pull_ermai_caozuo_csv_file_from_server.sh
ps aux | grep pull_machine_learning_caozuo_csv_file_from_server.sh
没有就重启 
bash nohup_run_pull_sanmai_caozuo_csv_file_from_server.sh
bash nohup_run_pull_ermai_caozuo_csv_file_from_server.sh
bash nohup_run_pull_machine_learning_caozuo_csv_file_from_server.sh
2.检查闹钟服务器， 
ps aux | grep alert_server.py (这个老版本，被淘汰了)
ps aux | grep alert_server_ermai.py
ps aux | grep alert_server_machine_learning.py
不在工作就重启，记得要先打开闹钟APP再启动alert_server_ermai.py，启动alert_server_ermai.py通过下面这句:
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






















nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market AAPL_NASDAQ  > AAPL_NASDAQ_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market NVDA_NASDAQ  > NVDA_NASDAQ_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market AMZN_NASDAQ  > AMZN_NASDAQ_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market META_NASDAQ  > META_NASDAQ_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market MSFT_NASDAQ  > MSFT_NASDAQ_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market SNOW_NYSE  > SNOW_NYSE_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market TIGR_NASDAQ  > TIGR_NASDAQ_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market TSLA_NASDAQ  > TSLA_NASDAQ_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market U_NYSE  > U_NYSE_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market AVGO_NASDAQ  > AVGO_NASDAQ_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market LLY_NYSE  > LLY_NYSE_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market NVO_NYSE  > NVO_NYSE_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market ADBE_NASDAQ  > ADBE_NASDAQ_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market TSM_NYSE  > TSM_NYSE_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market PFE_NYSE  > PFE_NYSE_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market JPM_NYSE  > JPM_NYSE_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market BAC_NYSE  > BAC_NYSE_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market COST_NASDAQ  > COST_NASDAQ_find_ermai.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 1 --group_size_for_low_level 1 --stock_name_and_market NFLX_NASDAQ  > NFLX_NASDAQ_find_ermai.log 2>&1 &






nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market AAPL_NASDAQ  > AAPL_NASDAQ_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market NVDA_NASDAQ  > NVDA_NASDAQ_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market AMZN_NASDAQ  > AMZN_NASDAQ_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market META_NASDAQ  > META_NASDAQ_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market MSFT_NASDAQ  > MSFT_NASDAQ_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market SNOW_NYSE  > SNOW_NYSE_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market TIGR_NASDAQ  > TIGR_NASDAQ_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market TSLA_NASDAQ  > TSLA_NASDAQ_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market U_NYSE  > U_NYSE_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market AVGO_NASDAQ  > AVGO_NASDAQ_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market LLY_NYSE  > LLY_NYSE_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market NVO_NYSE  > NVO_NYSE_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market ADBE_NASDAQ  > ADBE_NASDAQ_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market TSM_NYSE  > TSM_NYSE_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market PFE_NYSE  > PFE_NYSE_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market JPM_NYSE  > JPM_NYSE_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market BAC_NYSE  > BAC_NYSE_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market COST_NASDAQ  > COST_NASDAQ_find_ermai4.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 4 --group_size_for_low_level 4 --stock_name_and_market NFLX_NASDAQ  > NFLX_NASDAQ_find_ermai4.log 2>&1 &





nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market AAPL_NASDAQ  > AAPL_NASDAQ_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market NVDA_NASDAQ  > NVDA_NASDAQ_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market AMZN_NASDAQ  > AMZN_NASDAQ_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market META_NASDAQ  > META_NASDAQ_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market MSFT_NASDAQ  > MSFT_NASDAQ_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market SNOW_NYSE  > SNOW_NYSE_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market TIGR_NASDAQ  > TIGR_NASDAQ_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market TSLA_NASDAQ  > TSLA_NASDAQ_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market U_NYSE  > U_NYSE_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market AVGO_NASDAQ  > AVGO_NASDAQ_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market LLY_NYSE  > LLY_NYSE_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market NVO_NYSE  > NVO_NYSE_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market ADBE_NASDAQ  > ADBE_NASDAQ_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market TSM_NYSE  > TSM_NYSE_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market PFE_NYSE  > PFE_NYSE_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market JPM_NYSE  > JPM_NYSE_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market BAC_NYSE  > BAC_NYSE_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market COST_NASDAQ  > COST_NASDAQ_find_ermai10.log 2>&1 &
nohup python find_ermai_singlelevel_decision_two_way_form_segment_for_visualization.py --print_process_info --info_save_to_file_mode --show_fig_when_sell_buy_action --group_size_for_high_level 10 --group_size_for_low_level 10 --stock_name_and_market NFLX_NASDAQ  > NFLX_NASDAQ_find_ermai10.log 2>&1 &