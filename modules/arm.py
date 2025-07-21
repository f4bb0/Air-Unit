import serial
import argparse
import threading
import json
import time

# 全局变量
ser_input = None  # ttyUSB2 输入
ser_output1 = None  # ttyUSB3 输出 (机械臂1)
ser_output2 = None  # ttyUSB4 输出 (机械臂2)

def parse_hex_data(hex_values):
    """
    解析16进制数据到机械臂参数
    hex_values: 12个16进制数的列表
    返回: 两个机械臂的参数字典
    """
    # 将16进制字符串转换为整数
    values = [int(hex_val, 16) for hex_val in hex_values]
    
    # 分成两组，每组6个参数对应一个机械臂
    arm1_values = values[:6]
    arm2_values = values[6:]
    
    # 构造机械臂控制JSON
    def create_arm_json(arm_values, arm_id):
        return {
            "T": 122,
            "b": arm_values[0],
            "s": arm_values[1], 
            "e": arm_values[2],
            "t": arm_values[3],
            "r": arm_values[4],
            "h": 180,
            # "h": arm_values[5],
            "spd": 10,
            "acc": 10
        }
    
    arm1_json = create_arm_json(arm1_values, 1)
    arm2_json = create_arm_json(arm2_values, 2)
    
    return arm1_json, arm2_json

def read_serial():
    """从ttyUSB2读取数据并解析"""
    buffer = b''
    while True:
        try:
            # 读取数据
            data = ser_input.read(1)
            if data:
                buffer += data
                
                # 查找帧头 03 FF D0 C7
                header = b'\x03\xFF\xD0\xC7'
                header_pos = buffer.find(header)
                
                if header_pos != -1:
                    # 找到帧头，提取数据部分
                    start_pos = header_pos + len(header)
                    
                    # 需要12个字节的数据 (12个16进制数)
                    if len(buffer) >= start_pos + 12:
                        hex_data = buffer[start_pos:start_pos + 12]
                        
                        # 将字节转换为16进制字符串
                        hex_strings = [f"{byte:02X}" for byte in hex_data]
                        
                        print(f"Received hex data: {' '.join(hex_strings)}")
                        
                        # 解析数据
                        arm1_json, arm2_json = parse_hex_data(hex_strings)
                        
                        # 发送到两个机械臂
                        send_to_arms(arm1_json, arm2_json)
                        
                        # 清理缓冲区
                        buffer = buffer[start_pos + 12:]
                        
                # 限制缓冲区大小
                if len(buffer) > 100:
                    buffer = buffer[-50:]
                    
        except Exception as e:
            print(f"Error reading serial: {e}")
            time.sleep(0.1)

def send_to_arms(arm1_json, arm2_json):
    """发送JSON数据到两个机械臂"""
    try:
        # 发送到机械臂1 (ttyUSB3)
        if ser_output1:
            json_str1 = json.dumps(arm1_json)
            ser_output1.write(json_str1.encode() + b'\n')
            print(f"Sent to ARM1: {json_str1}")
        
        # 发送到机械臂2 (ttyUSB4)  
        if ser_output2:
            json_str2 = json.dumps(arm2_json)
            ser_output2.write(json_str2.encode() + b'\n')
            print(f"Sent to ARM2: {json_str2}")
            
    except Exception as e:
        print(f"Error sending to arms: {e}")

def main():
    global ser_input, ser_output1, ser_output2
    
    try:
        # 打开串口
        print("Opening serial ports...")
        ser_input = serial.Serial('/dev/ttyUSB2', baudrate=115200, timeout=1)
        ser_output1 = serial.Serial('/dev/ttyUSB3', baudrate=115200, timeout=1)
        ser_output2 = serial.Serial('/dev/ttyUSB4', baudrate=115200, timeout=1)
        
        # 设置串口参数
        for ser in [ser_input, ser_output1, ser_output2]:
            ser.setRTS(False)
            ser.setDTR(False)
        
        print("Serial ports opened successfully")
        print("Input: /dev/ttyUSB2")
        print("Output1 (ARM1): /dev/ttyUSB3") 
        print("Output2 (ARM2): /dev/ttyUSB4")
        print("Waiting for data...")
        
        # 启动读取线程
        serial_recv_thread = threading.Thread(target=read_serial)
        serial_recv_thread.daemon = True
        serial_recv_thread.start()
        
        # 主循环
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        # 关闭串口
        if ser_input:
            ser_input.close()
        if ser_output1:
            ser_output1.close()
        if ser_output2:
            ser_output2.close()
        print("Serial ports closed")

if __name__ == "__main__":
    main()