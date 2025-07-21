#!/bin/bash

# --- 配置区 (请根据你的实际情况修改喵) ---
PYTHON_SCRIPT="modules/simple_lidar_mqtt.py" # 替换成你的Python脚本的绝对路径喵
COMPOSE_FILE="/home/orangepi/podman/compose.yaml" # 替换成你的podman-compose.yaml文件的绝对路径喵
COMPOSE_DIR=$(dirname "${COMPOSE_FILE}") # 自动提取 compose 文件所在的目录喵
CONTAINER_NAME="my-arch-container" # 替换成你要进入的容器的服务名 (在compose文件里定义的)喵
COMMAND_IN_CONTAINER="gst-launch-1.0 v4l2src device=/dev/video0 ! image/jpeg,width=1920,height=1080,framerate=60/1 ! jpegdec ! videoconvert ! x264enc tune=zerolatency speed-preset=ultrafast intra-refresh=true key-int-max=60 ! h264parse ! mpegtsmux ! srtsink uri=\"srt://47.109.142.1:10000?mode=caller&streamid=push_auth_key&latency=50\"" # GStreamer pipeline for video streaming
# podman exec -it my-arch-container /bin/bash


# 日志文件路径 (建议放在一个专门的日志目录，比如 /tmp/ 或 /var/log/my_app/喵)
LOG_DIR="/tmp/my_app_logs" # 日志文件存放目录，请确保有写入权限喵
PYTHON_LOG="${LOG_DIR}/python_script.log"
PODMAN_COMPOSE_LOG="${LOG_DIR}/podman_compose.log"
CONTAINER_COMMAND_LOG="${LOG_DIR}/container_command.log"

# Screen 会话名称，方便识别喵
SCREEN_SESSION_PYTHON="my_python_app"
SCREEN_SESSION_PODMAN="my_podman_compose"
SCREEN_SESSION_CONTAINER_CMD="my_container_cmd"
# --- 配置区结束喵 ---

# 检查视频设备并设置权限
echo "检查视频设备 /dev/video0 是否存在喵..."
while [ ! -e /dev/video0 ]; do
    echo "未找到视频设备，请插入摄像头，等待 3 秒后重新检查喵..."
    sleep 3
done

echo "找到视频设备 /dev/video0 啦喵！"

echo "--- 开始执行并行自动化脚本啦喵！---"

# 创建日志目录（如果不存在的话喵）
mkdir -p "${LOG_DIR}"
if [ $? -ne 0 ]; then
    echo "喵呜！无法创建日志目录: ${LOG_DIR}，请检查权限喵！"
    exit 1
fi

# 1. 在 Screen 会话中后台运行 Python 脚本喵
echo "正在后台运行 Python 脚本: ${PYTHON_SCRIPT} (日志: ${PYTHON_LOG}) 喵..."
# `screen -dmS 会话名 命令` 会在后台创建一个没有附加的会话并执行命令喵
# `>>` 表示追加输出到日志文件，`2>&1` 表示将标准错误也重定向到标准输出喵
screen -dmS "${SCREEN_SESSION_PYTHON}" bash -c "python3 \"${PYTHON_SCRIPT}\" >> \"${PYTHON_LOG}\" 2>&1"
if [ $? -ne 0 ]; then
    echo "喵呜！启动 Python Screen 会话失败了，请检查喵！"
    exit 1
fi
echo "Python 脚本已在 Screen 会话 '${SCREEN_SESSION_PYTHON}' 中后台启动喵！"

echo "---"

# 2. 在 Screen 会话中后台运行 Podman Compose 服务喵
echo "正在后台启动 Podman Compose 服务喵 (文件: ${COMPOSE_FILE}, 日志: ${PODMAN_COMPOSE_LOG}) ..."
# 需要先 cd 到 compose 目录，再执行 podman-compose 命令喵
screen -dmS "${SCREEN_SESSION_PODMAN}" bash -c "cd \"${COMPOSE_DIR}\" && podman-compose -f \"${COMPOSE_FILE}\" up -d >> \"${PODMAN_COMPOSE_LOG}\" 2>&1"
if [ $? -ne 0 ]; then
    echo "喵呜！启动 Podman Compose Screen 会话失败了，请检查喵！"
    exit 1
fi
echo "Podman Compose 服务已在 Screen 会话 '${SCREEN_SESSION_PODMAN}' 中后台启动喵！"

echo "---"

# 3. 在 Screen 会话中进入容器执行命令喵
# 注意：这里可能需要等待 Podman Compose 启动完成，才能进入容器喵
echo "正在等待 Podman Compose 容器启动，请耐心等待 15 秒喵..."
sleep 15 # 给予足够的时间让容器启动并稳定，你可以根据需要调整喵

echo "正在后台进入容器 '${CONTAINER_NAME}' 执行命令: '${COMMAND_IN_CONTAINER}' (日志: ${CONTAINER_COMMAND_LOG}) 喵..."
screen -dmS "${SCREEN_SESSION_CONTAINER_CMD}" bash -c "podman exec \"${CONTAINER_NAME}\" bash -c \"${COMMAND_IN_CONTAINER}\" >> \"${CONTAINER_COMMAND_LOG}\" 2>&1"
if [ $? -ne 0 ]; then
    echo "喵呜！启动容器内命令 Screen 会话失败了，请检查喵！"
    exit 1
fi
echo "容器内命令已在 Screen 会话 '${SCREEN_SESSION_CONTAINER_CMD}' 中后台启动喵！"

echo "---"
echo "所有任务已在各自的 Screen 会话中后台启动啦喵！"
echo "你可以使用 'screen -ls' 查看会话列表喵。"
echo "要查看某个任务的输出，可以使用 'screen -r 会话名'，比如 'screen -r ${SCREEN_SESSION_PYTHON}' 喵。"
echo "要分离会话（不关闭），请按 Ctrl+A, D 喵。"
echo "要停止所有 Screen 会话，可能需要手动 killall screen 或者 screen -X -S 会话名 quit 喵。"
echo "别忘了查看 ${LOG_DIR} 目录下的日志文件喵！"
echo "--- 自动化脚本执行完毕啦喵！---"