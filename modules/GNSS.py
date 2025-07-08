import serial
import time
import threading
from typing import Optional, Dict, Any

class GNSS:
    def __init__(self, port: str = '/dev/ttyUSB1', baudrate: int = 9600, timeout: float = 1.0):
        """
        初始化GNSS模块
        
        Args:
            port: 串口端口名
            baudrate: 波特率
            timeout: 超时时间
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None
        self.is_running = False
        self.data_lock = threading.Lock()
        
        # 存储解析后的数据
        self.gps_data = {
            'latitude': None,
            'longitude': None,
            'altitude': None,
            'speed': None,
            'course': None,
            'satellites': None,
            'fix_quality': None,
            'timestamp': None,
            'date': None,
            'hdop': None
        }
    
    def connect(self) -> bool:
        """连接串口"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            print(f"✅ GNSS连接: {self.port}")
            return True
        except Exception as e:
            print(f"❌ GNSS连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self.is_running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("📡 GNSS已断开")
    
    def start_reading(self):
        """开始读取数据"""
        if not self.serial_conn or not self.serial_conn.is_open:
            if not self.connect():
                return False
        
        self.is_running = True
        self.read_thread = threading.Thread(target=self._read_data)
        self.read_thread.daemon = True
        self.read_thread.start()
        return True
    
    def _read_data(self):
        """读取串口数据的线程函数"""
        while self.is_running:
            try:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('ascii', errors='ignore').strip()
                    if line.startswith('$'):
                        self._parse_nmea(line)
                else:
                    time.sleep(0.01)
            except Exception as e:
                # 简化错误日志，避免频繁打印
                print(f"GNSS读取错误: {e}")
                time.sleep(0.1)
    
    def _parse_nmea(self, sentence: str):
        """解析NMEA句子"""
        try:
            # 验证校验和
            if not self._validate_checksum(sentence):
                return
            
            parts = sentence.split(',')
            sentence_type = parts[0][3:]  # 去掉$GP前缀
            
            with self.data_lock:
                if sentence_type == 'GGA':
                    self._parse_gga(parts)
                elif sentence_type == 'RMC':
                    self._parse_rmc(parts)
                elif sentence_type == 'GSA':
                    self._parse_gsa(parts)
                elif sentence_type == 'GSV':
                    self._parse_gsv(parts)
                    
        except Exception as e:
            print(f"解析NMEA数据错误: {e}")
    
    def _parse_gga(self, parts: list):
        """解析GGA句子 - 全球定位系统定位数据"""
        if len(parts) >= 13:
            # 时间
            if parts[1]:
                self.gps_data['timestamp'] = self._parse_time(parts[1])
            
            # 纬度
            if parts[2] and parts[3]:
                self.gps_data['latitude'] = self._parse_coordinate(parts[2], parts[3])
            
            # 经度
            if parts[4] and parts[5]:
                self.gps_data['longitude'] = self._parse_coordinate(parts[4], parts[5])
            
            # 定位质量
            if parts[6]:
                self.gps_data['fix_quality'] = int(parts[6])
            
            # 卫星数量
            if parts[7]:
                self.gps_data['satellites'] = int(parts[7])
            
            # 水平精度因子
            if parts[8]:
                self.gps_data['hdop'] = float(parts[8])
            
            # 海拔高度
            if parts[9]:
                self.gps_data['altitude'] = float(parts[9])
    
    def _parse_rmc(self, parts: list):
        """解析RMC句子 - 推荐最小定位信息"""
        if len(parts) >= 10:
            # 时间
            if parts[1]:
                self.gps_data['timestamp'] = self._parse_time(parts[1])
            
            # 日期
            if parts[9]:
                self.gps_data['date'] = self._parse_date(parts[9])
            
            # 纬度
            if parts[3] and parts[4]:
                self.gps_data['latitude'] = self._parse_coordinate(parts[3], parts[4])
            
            # 经度
            if parts[5] and parts[6]:
                self.gps_data['longitude'] = self._parse_coordinate(parts[5], parts[6])
            
            # 速度 (节)
            if parts[7]:
                self.gps_data['speed'] = float(parts[7]) * 1.852  # 转换为km/h
            
            # 航向
            if parts[8]:
                self.gps_data['course'] = float(parts[8])
    
    def _parse_gsa(self, parts: list):
        """解析GSA句子 - GNSS DOP和有效卫星"""
        pass  # 可根据需要实现
    
    def _parse_gsv(self, parts: list):
        """解析GSV句子 - GNSS卫星可见信息"""
        pass  # 可根据需要实现
    
    def _parse_coordinate(self, coord_str: str, direction: str) -> float:
        """解析坐标"""
        if not coord_str or not direction:
            return None
        
        # DDMM.MMMM格式转换为十进制度数
        if len(coord_str) >= 4:
            degrees = int(coord_str[:2] if direction in ['N', 'S'] else coord_str[:3])
            minutes = float(coord_str[2:] if direction in ['N', 'S'] else coord_str[3:])
            decimal_degrees = degrees + minutes / 60.0
            
            if direction in ['S', 'W']:
                decimal_degrees = -decimal_degrees
            
            return decimal_degrees
        return None
    
    def _parse_time(self, time_str: str) -> str:
        """解析时间 HHMMSS.SS"""
        if len(time_str) >= 6:
            hours = time_str[:2]
            minutes = time_str[2:4]
            # 支持毫秒级精度
            if '.' in time_str and len(time_str) > 6:
                seconds_with_ms = time_str[4:]
                # 确保毫秒部分有3位
                if '.' in seconds_with_ms:
                    sec_part, ms_part = seconds_with_ms.split('.')
                    ms_part = ms_part[:3].ljust(3, '0')  # 截取或补齐到3位
                    return f"{hours}:{minutes}:{sec_part}.{ms_part}"
                else:
                    seconds = time_str[4:6]
                    return f"{hours}:{minutes}:{seconds}.000"
            else:
                seconds = time_str[4:6]
                return f"{hours}:{minutes}:{seconds}.000"
        return None
    
    def _parse_date(self, date_str: str) -> str:
        """解析日期 DDMMYY"""
        if len(date_str) >= 6:
            day = date_str[:2]
            month = date_str[2:4]
            year = "20" + date_str[4:6]
            return f"{year}-{month}-{day}"
        return None
    
    def _validate_checksum(self, sentence: str) -> bool:
        """验证NMEA校验和"""
        if '*' not in sentence:
            return False
        
        try:
            data, checksum = sentence.split('*')
            calculated_checksum = 0
            for char in data[1:]:  # 跳过$符号
                calculated_checksum ^= ord(char)
            
            return format(calculated_checksum, '02X') == checksum.upper()
        except:
            return False
    
    def get_position(self) -> Dict[str, Any]:
        """获取当前位置信息"""
        with self.data_lock:
            return {
                'latitude': self.gps_data['latitude'],
                'longitude': self.gps_data['longitude'],
                'altitude': self.gps_data['altitude']
            }
    
    def get_all_data(self) -> Dict[str, Any]:
        """获取所有GPS数据"""
        with self.data_lock:
            return self.gps_data.copy()
    
    def is_fix_valid(self) -> bool:
        """检查GPS定位是否有效"""
        with self.data_lock:
            return (self.gps_data['fix_quality'] is not None and 
                   self.gps_data['fix_quality'] > 0 and
                   self.gps_data['latitude'] is not None and
                   self.gps_data['longitude'] is not None)


# 使用示例
if __name__ == "__main__":
    gnss = GNSS(port='/dev/ttyUSB1', baudrate=9600)
    
    if gnss.start_reading():
        print("开始读取GNSS数据...")
        
        try:
            while True:
                time.sleep(2)
                data = gnss.get_all_data()
                
                if gnss.is_fix_valid():
                    print(f"位置: {data['latitude']:.6f}, {data['longitude']:.6f}")
                    print(f"高度: {data['altitude']}m")
                    print(f"速度: {data['speed']}km/h")
                    print(f"卫星数: {data['satellites']}")
                    print(f"时间: {data['timestamp']}")
                    print("-" * 40)
                else:
                    print("等待GPS定位...")
                    
        except KeyboardInterrupt:
            print("\n停止读取...")
        finally:
            gnss.disconnect()
