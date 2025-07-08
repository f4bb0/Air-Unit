import time
import threading
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# 设置雷达日志记录器
radar_logger = logging.getLogger('radar')
radar_logger.setLevel(logging.INFO)

class RadarModule:
    def __init__(self, radar_type: str = "generic", config: Dict[str, Any] = None):
        """
        雷达模块基类
        
        Args:
            radar_type: 雷达类型
            config: 配置参数
        """
        self.radar_type = radar_type
        self.config = config or {}
        self.is_running = False
        self.data_lock = threading.Lock()
        
        # 雷达数据
        self.radar_data = {
            'targets': [],
            'timestamp': None,
            'range_max': self.config.get('range_max', 100),  # 最大探测距离(米)
            'status': 'disconnected'
        }
        
        radar_logger.info(f"初始化{radar_type}雷达模块")
    
    def connect(self) -> bool:
        """连接雷达设备"""
        try:
            # 这里应该实现具体的雷达连接逻辑
            radar_logger.info(f"连接{self.radar_type}雷达设备")
            with self.data_lock:
                self.radar_data['status'] = 'connected'
            return True
        except Exception as e:
            radar_logger.error(f"雷达连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开雷达连接"""
        self.is_running = False
        with self.data_lock:
            self.radar_data['status'] = 'disconnected'
        radar_logger.info("雷达连接已断开")
    
    def start_detection(self) -> bool:
        """开始目标检测"""
        if not self.is_running:
            self.is_running = True
            self.detection_thread = threading.Thread(target=self._detection_loop)
            self.detection_thread.daemon = True
            self.detection_thread.start()
            radar_logger.info("开始雷达目标检测")
            return True
        return False
    
    def stop_detection(self):
        """停止目标检测"""
        self.is_running = False
        if hasattr(self, 'detection_thread'):
            self.detection_thread.join()
        radar_logger.info("停止雷达目标检测")
    
    def _detection_loop(self):
        """检测循环 - 子类应该重写此方法"""
        while self.is_running:
            try:
                # 模拟检测数据
                targets = self._simulate_targets()
                
                with self.data_lock:
                    self.radar_data['targets'] = targets
                    # 精确到毫秒的时间戳
                    self.radar_data['timestamp'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                    self.radar_data['status'] = 'active'
                
                if targets:
                    radar_logger.debug(f"检测到{len(targets)}个目标")
                
                time.sleep(0.1)  # 100ms检测间隔
                
            except Exception as e:
                radar_logger.error(f"雷达检测循环错误: {e}")
                time.sleep(1)
    
    def _simulate_targets(self) -> List[Dict[str, Any]]:
        """模拟目标数据 - 实际实现中应该替换为真实数据"""
        import random
        
        targets = []
        # 随机生成0-3个目标
        for i in range(random.randint(0, 3)):
            target = {
                'id': f"T{i+1}",
                'distance': round(random.uniform(5, 50), 2),  # 距离(米)
                'angle': round(random.uniform(-90, 90), 1),   # 角度(度)
                'velocity': round(random.uniform(-10, 10), 2), # 速度(m/s)
                'strength': round(random.uniform(0.3, 1.0), 2) # 信号强度
            }
            targets.append(target)
        
        return targets
    
    def get_targets(self) -> List[Dict[str, Any]]:
        """获取当前检测到的目标"""
        with self.data_lock:
            return self.radar_data['targets'].copy()
    
    def get_all_data(self) -> Dict[str, Any]:
        """获取所有雷达数据"""
        with self.data_lock:
            return self.radar_data.copy()
    
    def is_active(self) -> bool:
        """检查雷达是否处于活动状态"""
        with self.data_lock:
            return self.radar_data['status'] == 'active'


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 创建雷达实例
    radar = RadarModule("test_radar", {"range_max": 80})
    
    if radar.connect():
        radar.start_detection()
        
        try:
            for i in range(10):
                time.sleep(2)
                data = radar.get_all_data()
                targets = data['targets']
                
                if targets:
                    print(f"检测到{len(targets)}个目标:")
                    for target in targets:
                        print(f"  目标{target['id']}: 距离{target['distance']}m, "
                              f"角度{target['angle']}°, 速度{target['velocity']}m/s")
                else:
                    print("未检测到目标")
                    
        except KeyboardInterrupt:
            print("\n停止检测...")
        finally:
            radar.stop_detection()
            radar.disconnect()
