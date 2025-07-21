import serial
import time

# 定义常量
LD_HEADER1 = 0xAA
LD_HEADER2 = 0x55
LD_F_LEN = 85
LD_PNAM = 25
LD_ALARM_DistanceMin = 50

# 初始化雷达数据数组
ax_lidar_data = [0] * 360

# 初始化串口
def init_serial():
    try:
        ser = serial.Serial(
            port='/dev/ttyUSB0',  # 根据实际情况修改串口号
            baudrate=230400,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        return ser
    except serial.SerialException as e:
        print(f"串口初始化失败: {e}")
        return None

# 初始化雷达
def AX_LIDAR_Init(ser):
    data = bytes([0x00])
    ser.write(data)

# 启动雷达
def AX_LIDAR_Start(ser):
    uart4_tx_buf = [0xAA, 0x55, 0xF0, 0x0F]
    for byte in uart4_tx_buf:
        ser.write(bytes([byte]))

# 停止雷达
def AX_LIDAR_Stop(ser):
    uart4_tx_buf = [0xAA, 0x55, 0xF5, 0x0A]
    for byte in uart4_tx_buf:
        ser.write(bytes([byte]))

# 数据处理
def LD_DataHandle(uart4_rx_buf2):
    global ax_lidar_data
    frame_data = []
    angle_start = (((uart4_rx_buf2[5] << 8) + (uart4_rx_buf2[4] >> 1)) / 64.0)
    angle_end = (((uart4_rx_buf2[7] << 8) + (uart4_rx_buf2[6] >> 1)) / 64.0)
    if angle_start > angle_end:
        angle_area = (angle_end + 360 - angle_start) / 24
    else:
        angle_area = (angle_end - angle_start) / 24

    for i in range(25):
        temp = angle_start + angle_area * i
        angle = temp % 360
        distance = ((uart4_rx_buf2[12 + i * 3] << 6) + (uart4_rx_buf2[11 + i * 3] >> 2))
        frame_data.append({'angle': angle, 'distance': distance})

    for point in frame_data:
        index = int(point['angle'])
        if 0 <=index < 360:
            ax_lidar_data[index] = point['distance']
        else:
            print('null')

# 主函数
def main():
    ser = init_serial()
    if ser is None:
        return

    AX_LIDAR_Init(ser)
    time.sleep(1)
    AX_LIDAR_Start(ser)

    uart4_rx_con = 0
    uart4_rx_buf = [0] * 100
    uart4_rx_buf2 = [0] * 100

    try:
        while True:
            if ser.in_waiting:
                res = ser.read(1)[0]
                if uart4_rx_con < 2:
                    if uart4_rx_con == 0:
                        if res == LD_HEADER1:
                            uart4_rx_buf[uart4_rx_con] = res
                            uart4_rx_con = 1
                    else:
                        if res == LD_HEADER2:
                            uart4_rx_buf[uart4_rx_con] = res
                            uart4_rx_con = 2
                else:
                    if uart4_rx_con < LD_F_LEN:
                        uart4_rx_buf[uart4_rx_con] = res
                        uart4_rx_con += 1
                    else:
                        uart4_rx_buf2 = uart4_rx_buf.copy()
                        uart4_rx_con = 0
                        LD_DataHandle(uart4_rx_buf2)

                        min_distance = 5000
                        min_angle = 0
                        for i in range(360):
                            if ax_lidar_data[i] > LD_ALARM_DistanceMin:
                                if ax_lidar_data[i] < min_distance:
                                    min_distance = ax_lidar_data[i]
                                    min_angle = i

                        print(f"{min_angle} {min_distance}")

    except KeyboardInterrupt:
        AX_LIDAR_Stop(ser)
        ser.close()

if __name__ == "__main__":
    main()