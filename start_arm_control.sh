#!/bin/bash
# 机械臂控制系统启动脚本

echo "Air Unit - 机械臂控制系统"
echo "========================"

# 检查串口是否存在
check_port() {
    if [ ! -c "$1" ]; then
        echo "错误: 串口 $1 不存在"
        return 1
    fi
    return 0
}

echo "检查串口..."
check_port "/dev/ttyUSB2" || exit 1
check_port "/dev/ttyUSB3" || exit 1  
check_port "/dev/ttyUSB4" || exit 1

echo "所有串口检查通过"
echo ""

# 设置串口权限
echo "设置串口权限..."
sudo chmod 666 /dev/ttyUSB2 /dev/ttyUSB3 /dev/ttyUSB4

echo "启动机械臂控制程序..."
echo "输入端口: /dev/ttyUSB2"
echo "输出端口: /dev/ttyUSB3 (机械臂1), /dev/ttyUSB4 (机械臂2)"
echo ""
echo "按 Ctrl+C 停止程序"
echo ""

# 启动主程序
cd /home/fabbo/Documents/Air-Unit
python3 modules/arm.py
