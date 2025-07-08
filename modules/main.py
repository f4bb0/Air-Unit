import time
import signal
import sys
import logging
from typing import Optional
from datetime import datetime
from GNSS import GNSS
from MQTT import MQTTClient, DataPublisher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AirUnitGNSSSystem:
    def __init__(self, config: dict = None):
        """
        Air Unit GNSS系统主类
        
        Args:
            config: 配置字典
        """
        # 默认配置
        self.config = {
            'gnss': {
                'port': '/dev/ttyUSB1',
                'baudrate': 9600,
                'timeout': 1.0
            },
            'mqtt': {
                'broker_host': '47.109.142.1',
                'broker_port': 1883,
                'client_id': 'air_unit_gnss',
                'username': None,
                'password': None,
                'keepalive': 60
            },
            'publish_interval': 2.0,
            'retry_delay': 5.0,
            'max_retries': 3
        }
        
        # 更新配置
        if config:
            self._update_config(config)
        
        # 初始化组件
        self.gnss: Optional[GNSS] = None
        self.mqtt: Optional[MQTTClient] = None
        self.gnss_publisher: Optional[DataPublisher] = None
        
        # 状态标志
        self.is_running = False
        self.gnss_connected = False
        self.mqtt_connected = False
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _update_config(self, config: dict):
        """递归更新配置"""
        for key, value in config.items():
            if isinstance(value, dict) and key in self.config:
                self.config[key].update(value)
            else:
                self.config[key] = value
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"接收到信号 {signum}，正在关闭系统...")
        self.shutdown()
        sys.exit(0)
    
    def initialize(self) -> bool:
        """初始化系统组件"""
        logger.info("初始化Air Unit GNSS系统...")
        
        # 初始化GNSS
        try:
            self.gnss = GNSS(
                port=self.config['gnss']['port'],
                baudrate=self.config['gnss']['baudrate'],
                timeout=self.config['gnss']['timeout']
            )
            logger.info("GNSS模块初始化成功")
        except Exception as e:
            logger.error(f"GNSS模块初始化失败: {e}")
            return False
        
        # 初始化MQTT
        try:
            self.mqtt = MQTTClient(
                broker_host=self.config['mqtt']['broker_host'],
                broker_port=self.config['mqtt']['broker_port'],
                client_id=self.config['mqtt']['client_id'],
                username=self.config['mqtt']['username'],
                password=self.config['mqtt']['password'],
                keepalive=self.config['mqtt']['keepalive']
            )
            logger.info("MQTT客户端初始化成功")
        except Exception as e:
            logger.error(f"MQTT客户端初始化失败: {e}")
            return False
        
        return True
    
    def connect_gnss(self) -> bool:
        """连接GNSS设备"""
        retry_count = 0
        max_retries = self.config['max_retries']
        
        while retry_count < max_retries:
            try:
                if self.gnss.start_reading():
                    self.gnss_connected = True
                    logger.info("GNSS设备连接成功")
                    return True
                else:
                    raise Exception("GNSS启动失败")
            except Exception as e:
                retry_count += 1
                logger.warning(f"GNSS连接失败 ({retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    time.sleep(self.config['retry_delay'])
        
        logger.error("GNSS连接失败，已达到最大重试次数")
        return False
    
    def connect_mqtt(self) -> bool:
        """连接MQTT代理"""
        retry_count = 0
        max_retries = self.config['max_retries']
        
        while retry_count < max_retries:
            try:
                if self.mqtt.connect():
                    self.mqtt_connected = True
                    logger.info("MQTT代理连接成功")
                    return True
                else:
                    raise Exception("MQTT连接失败")
            except Exception as e:
                retry_count += 1
                logger.warning(f"MQTT连接失败 ({retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    time.sleep(self.config['retry_delay'])
        
        logger.error("MQTT连接失败，已达到最大重试次数")
        return False
    
    def start(self) -> bool:
        """启动系统"""
        if not self.initialize():
            logger.error("系统初始化失败")
            return False
        
        # 连接GNSS
        if not self.connect_gnss():
            logger.error("GNSS连接失败")
            return False
        
        # 连接MQTT
        if not self.connect_mqtt():
            logger.error("MQTT连接失败")
            return False
        
        # 创建GNSS数据发布器
        try:
            self.gnss_publisher = DataPublisher(self.mqtt)
            
            # 设置GNSS数据获取回调
            def get_gnss_data():
                if self.gnss and self.gnss.is_fix_valid():
                    return self.gnss.get_all_data()
                return None
            
            self.gnss_publisher.set_data_callback(get_gnss_data)
            self.gnss_publisher.start_publishing("gnss", interval=self.config['publish_interval'])
            
            logger.info(f"开始发布GNSS数据，间隔: {self.config['publish_interval']}秒")
        except Exception as e:
            logger.error(f"GNSS发布器启动失败: {e}")
            return False
        
        self.is_running = True
        self.start_time = time.time()
        logger.info("Air Unit GNSS系统启动成功")
        
        # 简化启动信息发布
        startup_info = {
            "gnss_port": self.config['gnss']['port'],
            "publish_interval": self.config['publish_interval'],
            "client_id": self.config['mqtt']['client_id'],
            "startup_time": datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        }
        
        self.mqtt.publish_system_info("startup", startup_info)
        return True
    
    def run(self):
        """运行主循环"""
        if not self.start():
            logger.error("系统启动失败")
            return False
        
        logger.info("系统运行中... (Ctrl+C停止)")
        
        try:
            last_status_time = time.time()
            status_interval = 2.0
            
            while self.is_running:
                current_time = time.time()
                
                # 检查连接状态
                self._check_connections()
                
                # 定期发布状态报告
                if current_time - last_status_time >= status_interval:
                    self._publish_status_report()
                    last_status_time = current_time
                
                # 简化GPS数据显示 - 只在有效时显示
                if self.gnss and self.gnss.is_fix_valid():
                    data = self.gnss.get_all_data()
                    # 每10秒显示一次GPS信息
                    if int(current_time) % 10 == 0:
                        logger.info(f"GPS: {data['latitude']:.6f}, {data['longitude']:.6f}, 卫星: {data['satellites']}")
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("用户停止")
        except Exception as e:
            logger.error(f"运行错误: {e}")
        finally:
            self.shutdown()

    def _check_connections(self):
        """检查连接状态"""
        # 检查GNSS连接
        if self.gnss and not self.gnss.is_running:
            logger.warning("GNSS连接丢失，尝试重连...")
            self.gnss_connected = False
            if self.connect_gnss():
                logger.info("GNSS重连成功")
        
        # 检查MQTT连接
        if self.mqtt and not self.mqtt.is_connected:
            logger.warning("MQTT连接丢失，尝试重连...")
            self.mqtt_connected = False
            if self.connect_mqtt():
                logger.info("MQTT重连成功")
    
    def _publish_status_report(self):
        """发布状态报告到vehicle主题"""
        if self.mqtt and self.mqtt.is_connected:
            status_data = {
                "gnss_connected": self.gnss_connected,
                "mqtt_connected": self.mqtt_connected,
                "gps_fix_valid": self.gnss.is_fix_valid() if self.gnss else False,
                "uptime_seconds": int(time.time() - getattr(self, 'start_time', time.time()))
            }
            
            if self.gnss:
                gps_data = self.gnss.get_all_data()
                status_data.update({
                    "satellites": gps_data.get('satellites'),
                    "fix_quality": gps_data.get('fix_quality')
                })
            
            # 简化状态发布日志
            self.mqtt.publish_system_info("status_report", status_data)

    def shutdown(self):
        """关闭系统"""
        logger.info("正在关闭...")
        self.is_running = False
        
        # 停止发布器
        if self.gnss_publisher:
            self.gnss_publisher.stop_publishing()
        
        # 发布关闭信息
        if self.mqtt and self.mqtt.is_connected:
            self.mqtt.publish_system_info("shutdown", {
                "shutdown_time": datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                "uptime_seconds": int(time.time() - getattr(self, 'start_time', time.time()))
            })
            
            # 显示统计
            self.mqtt.print_publish_stats()
        
        # 断开连接
        if self.mqtt:
            self.mqtt.disconnect()
        if self.gnss:
            self.gnss.disconnect()
        
        logger.info("系统已关闭")


def main():
    """主函数"""
    # 配置示例
    config = {
        'gnss': {
            'port': '/dev/ttyUSB1',
            'baudrate': 9600
        },
        'mqtt': {
            'broker_host': '47.109.142.1',
            'broker_port': 1883,
            'client_id': 'air_unit_gnss_001'
        },
        'publish_interval': 2.0  # 改回2.0秒，每2秒发送一次
    }
    
    # 创建并运行系统
    system = AirUnitGNSSSystem(config)
    system.run()


if __name__ == "__main__":
    main()
    config = {
        'gnss': {
            'port': '/dev/ttyUSB1',
            'baudrate': 9600
        },
        'mqtt': {
            'broker_host': '47.109.142.1',
            'broker_port': 1883,
            'client_id': 'air_unit_gnss_001'
        },
        'publish_interval': 2.0  # 改回2.0秒，每2秒发送一次
    }
    
    # 创建并运行系统
    system = AirUnitGNSSSystem(config)
    system.run()


if __name__ == "__main__":
    main()
