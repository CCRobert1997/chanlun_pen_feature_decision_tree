eval "$(ssh-agent -s)"
ssh-add /Users/shangyu/Desktop/ShangyuChen/IT_Tool/ssh_keys/newKey

nohup bash /Users/shangyu/Desktop/ShangyuChen/STOCK/chanlun/chanlun_sanmai_v1/pull_sanmai_caozuo_csv_file_from_server.sh > /Users/shangyu/Desktop/ShangyuChen/STOCK/chanlun/chanlun_sanmai_v1/scp_pull_sanmai_caozuo_csv_file_from_server_sh.log 2>&1 &
