#!/bin/bash

OUTPUT_DIR="/etc/systemd/system"
LOG_DIR="/home/ubuntu/permanent_volume_for_master_node/STOCK/chanlun/data_read_and_process/logs2"
SCRIPT_PATH="/home/ubuntu/permanent_volume_for_master_node/STOCK/chanlun/data_read_and_process/read_data_of_some_underlying.py"
PYTHON_PATH="/home/ubuntu/permanent_volume_for_master_node/STOCK/chanlun/chanlun_env/bin/python"



# 服务信息
declare -a services=(
  "LLY:NYSE"
  "NVO:NYSE"
  "ADBE:NASDAQ"
  "TSM:NYSE"
  "PFE:NYSE"
  "JPM:NYSE"
  "BAC:NYSE"
  "COST:NASDAQ"
  "NFLX:NASDAQ"
)

# 创建服务文件
for service in "${services[@]}"; do
  IFS=":" read -r company market <<< "$service"
  service_name="read_data_${company,,}.service"  # 小写
  log_name="${company,,}"                       # 小写

  # 检查服务文件是否已存在
  if [ -f "${OUTPUT_DIR}/${service_name}" ]; then
    echo "Service ${service_name} already exists. Skipping..."
    continue
  fi

  # 创建服务文件
  cat <<EOF > "${OUTPUT_DIR}/${service_name}"
[Unit]
Description=Read Data for ${company}
After=network.target

[Service]
ExecStart=${PYTHON_PATH} ${SCRIPT_PATH} --company ${company} --market ${market}
WorkingDirectory=$(dirname "${SCRIPT_PATH}")
Restart=always
RestartSec=5
StandardOutput=append:${LOG_DIR}/${log_name}.log
StandardError=append:${LOG_DIR}/${log_name}.err
User=ubuntu
Group=ubuntu

[Install]
WantedBy=multi-user.target
EOF

  echo "Created service: ${service_name}"
done

# Reload and enable all services
sudo systemctl daemon-reload
for service in "${services[@]}"; do
  IFS=":" read -r company _ <<< "$service"
  service_name="read_data_${company,,}.service"
  sudo systemctl start "${service_name}"
  sudo systemctl enable "${service_name}"
done
