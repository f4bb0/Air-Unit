#!/bin/bash

# --- 配置区 (请根据你的实际情况修改喵) ---
PYTHON_SCRIPT="/path/to/your/your_script.py" # 替换成你的Python脚本的绝对路径喵
COMPOSE_FILE="/path/to/your/podman-compose.yaml" # 替换成你的podman-compose.yaml文件的绝对路径喵
CONTAINER_NAME="your_service_name" # 替换成你要进入的容器的服务名 (在compose文件里定义的)喵
COMMAND_IN_CONTAINER="ls -lh /app" # 替换成你要在容器内执行的命令喵
# --- 配置区结束喵 ---

echo "--- 开始执行自动化脚本啦喵！---"

# 1. 运行 Python 脚本喵
echo "正在运行 Python 脚本: ${PYTHON_SCRIPT} 喵..."
if python3 "${PYTHON_SCRIPT}"; then
    echo "Python 脚本运行成功喵！"
else
    echo "喵呜！Python 脚本运行失败了，请检查喵！"
    exit 1 # 如果Python脚本失败，就退出脚本，不继续了喵
fi

echo "---"

# 2. 运行 Podman Compose 服务喵
echo "正在启动 Podman Compose 服务喵 (文件: ${COMPOSE_FILE}) ..."
# 切换到 compose 文件所在的目录，这样 podman compose 才能找到文件喵
COMPOSE_DIR=$(dirname "${COMPOSE_FILE}")
cd "${COMPOSE_DIR}" || { echo "喵呜！无法进入 compose 文件目录: ${COMPOSE_DIR}，请检查喵！"; exit 1; }

if podman-compose -f "${COMPOSE_FILE}" up -d; then
    echo "Podman Compose 服务已成功后台启动喵！"
else
    echo "喵呜！Podman Compose 启动失败了，请检查喵！"
    exit 1 # 如果compose失败，也退出喵
fi

echo "---"

# 3. 进入容器执行命令喵
echo "正在进入容器 '${CONTAINER_NAME}' 执行命令: '${COMMAND_IN_CONTAINER}' 喵..."

# 等待一下，确保容器完全启动喵
echo "给容器一点时间启动，等待 10 秒喵..."
sleep 10

# podman exec -it 容器名 命令
# 注意：-it 选项在非交互式脚本中可能导致问题。
# 如果你只是想执行命令并获取输出，可以去掉 -i 和 -t。
# 这里我假设你只想执行命令，不需要交互式输入。
if podman exec "${CONTAINER_NAME}" bash -c "${COMMAND_IN_CONTAINER}"; then
    echo "容器内命令执行成功喵！"
else
    echo "喵呜！容器内命令执行失败了，请检查容器状态或命令是否正确喵！"
    exit 1
fi

echo "--- 自动化脚本执行完毕啦喵！---"