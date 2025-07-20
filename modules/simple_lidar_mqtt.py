#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import threading
from paho.mqtt import client as mqtt_client
from laser import init_serial, AX_LIDAR_Init, AX_LIDAR_Start, AX_LIDAR_Stop, LD_DataHandle, ax_lidar_data, LD_F_LEN, LD_HEADER1, LD_HEADER2, LD_ALARM_DistanceMin

# MQTT配置
BROKER = '47.109.142.1'  # 修改为你的MQTT服务器地址
PORT = 1883
TOPIC = 'lidar'

def connect_mqtt():
    """连接MQTT服务器"""
    client = mqtt_client.Client()
    client.connect(BROKER, PORT)
    return client

def publish_data(client):
    """发布所有雷达数据"""
    data = {
        'timestamp': time.time(),
        'lidar_data': ax_lidar_data.copy()  # 发送完整的360度数据
    }
    
    client.publish(TOPIC, json.dumps(data, separators=(',', ':')))
    print(f"发送完整雷达数据 - 时间戳: {data['timestamp']}")

def read_lidar_thread(ser):
    """读取雷达数据线程"""
    uart4_rx_con = 0
    uart4_rx_buf = [0] * 100
    
    while True:
        if ser.in_waiting:
            res = ser.read(1)[0]
            if uart4_rx_con < 2:
                if (uart4_rx_con == 0 and res == LD_HEADER1) or (uart4_rx_con == 1 and res == LD_HEADER2):
                    uart4_rx_buf[uart4_rx_con] = res
                    uart4_rx_con += 1
            else:
                uart4_rx_buf[uart4_rx_con] = res
                uart4_rx_con += 1
                if uart4_rx_con >= LD_F_LEN:
                    LD_DataHandle(uart4_rx_buf)
                    uart4_rx_con = 0

def main():
    # 初始化串口和雷达
    ser = init_serial()
    if not ser:
        print("串口初始化失败")
        return
    
    AX_LIDAR_Init(ser)
    time.sleep(1)
    AX_LIDAR_Start(ser)
    
    # 连接MQTT
    client = connect_mqtt()
    print("MQTT已连接，开始读取雷达数据...")
    
    # 启动读取线程
    threading.Thread(target=read_lidar_thread, args=(ser,), daemon=True).start()
    
    try:
        while True:
            publish_data(client)
            time.sleep(0.1)  # 每100ms发送一次
    except KeyboardInterrupt:
        AX_LIDAR_Stop(ser)
        ser.close()
        client.disconnect()
        print("程序已停止")

if __name__ == "__main__":
    main()
