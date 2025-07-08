#!/usr/bin/env python3
"""
测试机械臂控制功能
用于模拟发送测试数据到串口
"""
import serial
import time
import sys

def send_test_data():
    """发送测试数据到 ttyUSB2"""
    try:
        # 打开串口连接到 ttyUSB2 进行测试
        ser = serial.Serial('/dev/ttyUSB2', baudrate=115200, timeout=1)
        
        # 测试数据：03 FF D0 C7 + 12个16进制数
        # 前6个数对应机械臂1，后6个数对应机械臂2
        test_data = bytes([
            0x03, 0xFF, 0xD0, 0xC7,  # 帧头
            0x31, 0x31, 0x37, 0x35, 0x31, 0x32,  # 机械臂1的6个参数
            0x37, 0x32, 0x31, 0x34, 0x33, 0x39   # 机械臂2的6个参数
        ])
        
        print("Sending test data to /dev/ttyUSB2...")
        print(f"Data: {' '.join(f'{b:02X}' for b in test_data)}")
        
        # 发送数据
        ser.write(test_data)
        
        print("Test data sent successfully")
        
    except Exception as e:
        print(f"Error sending test data: {e}")
        print("Make sure /dev/ttyUSB2 is available")
        
    finally:
        if 'ser' in locals():
            ser.close()

def monitor_output_ports():
    """监控输出串口的数据"""
    try:
        print("Monitoring output ports...")
        ser3 = serial.Serial('/dev/ttyUSB3', baudrate=115200, timeout=1)
        ser4 = serial.Serial('/dev/ttyUSB4', baudrate=115200, timeout=1)
        
        print("Listening on /dev/ttyUSB3 and /dev/ttyUSB4...")
        
        while True:
            # 检查 ttyUSB3
            if ser3.in_waiting > 0:
                data3 = ser3.readline().decode('utf-8')
                if data3:
                    print(f"ttyUSB3 (ARM1): {data3.strip()}")
            
            # 检查 ttyUSB4
            if ser4.in_waiting > 0:
                data4 = ser4.readline().decode('utf-8')
                if data4:
                    print(f"ttyUSB4 (ARM2): {data4.strip()}")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nStopping monitor...")
    except Exception as e:
        print(f"Error monitoring ports: {e}")
    finally:
        if 'ser3' in locals():
            ser3.close()
        if 'ser4' in locals():
            ser4.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "send":
            send_test_data()
        elif sys.argv[1] == "monitor":
            monitor_output_ports()
        else:
            print("Usage: python test_arm_control.py [send|monitor]")
    else:
        print("Usage: python test_arm_control.py [send|monitor]")
        print("  send    - Send test data to ttyUSB2")
        print("  monitor - Monitor output from ttyUSB3 and ttyUSB4")
