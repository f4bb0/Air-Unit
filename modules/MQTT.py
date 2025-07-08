import paho.mqtt.client as mqtt
import json
import time
import threading
import socket
import subprocess
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

# 设置MQTT专用日志记录器
mqtt_logger = logging.getLogger('mqtt_client')
mqtt_logger.setLevel(logging.INFO)

class MQTTClient:
    def __init__(self, 
                 broker_host: str = "47.109.142.1", 
                 broker_port: int = 1883,
                 client_id: str = "air_unit_client",
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 keepalive: int = 60,
                 debug_mode: bool = False):
        """
        初始化MQTT客户端
        
        Args:
            broker_host: MQTT代理服务器地址
            broker_port: MQTT代理服务器端口
            client_id: 客户端ID
            username: 用户名
            password: 密码
            keepalive: 保活时间
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        self.username = username
        self.password = password
        self.keepalive = keepalive
        
        self.client = mqtt.Client(client_id=self.client_id)
        self.is_connected = False
        self.connection_lock = threading.Lock()
        
        # 设置回调函数
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
        
        # 设置认证
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        
        # 主题配置
        self.base_topic = "vehicle"
        
        # 调试模式
        self.debug_mode = debug_mode
        if debug_mode:
            mqtt_logger.setLevel(logging.DEBUG)
            
        # 发送统计
        self.publish_stats = {
            'total_attempts': 0,
            'successful_sends': 0,
            'failed_sends': 0,
            'topics_used': set()
        }
        
        # 添加消息确认追踪
        self.pending_messages = {}
        self.message_counter = 0

    def _check_network_connectivity(self) -> bool:
        """检查网络连接性"""
        try:
            # 检查是否能ping通代理服务器
            result = subprocess.run(['ping', '-c', '1', '-W', '3', self.broker_host], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"网络连通性检查: {self.broker_host} 可达")
                return True
            else:
                print(f"网络连通性检查: {self.broker_host} 不可达")
                return False
        except Exception as e:
            print(f"网络连通性检查失败: {e}")
            return False
    
    def _check_port_connectivity(self) -> bool:
        """检查端口连接性"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.broker_host, self.broker_port))
            sock.close()
            
            if result == 0:
                print(f"端口连接性检查: {self.broker_host}:{self.broker_port} 可连接")
                return True
            else:
                print(f"端口连接性检查: {self.broker_host}:{self.broker_port} 连接失败 (错误码: {result})")
                return False
        except Exception as e:
            print(f"端口连接性检查失败: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        connection_results = {
            0: "连接成功",
            1: "协议版本错误",
            2: "客户端ID无效",
            3: "服务器不可用",
            4: "用户名或密码错误",
            5: "未授权"
        }
        
        if rc == 0:
            self.is_connected = True
            print(f"已连接到MQTT代理: {self.broker_host}:{self.broker_port}")
        else:
            self.is_connected = False
            error_msg = connection_results.get(rc, f"未知错误 (代码: {rc})")
            print(f"MQTT连接失败: {error_msg}")
    
    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        self.is_connected = False
        if rc != 0:
            print("意外断开连接，尝试重连...")
            self._reconnect()
    
    def _on_publish(self, client, userdata, mid):
        """发布消息回调"""
        if mid in self.pending_messages:
            topic = self.pending_messages[mid]
            # 简化确认消息
            if self.debug_mode:
                print(f"✅ 确认: {topic} (MID: {mid})")
            del self.pending_messages[mid]

    def connect(self) -> bool:
        """连接到MQTT代理"""
        print(f"尝试连接到MQTT代理: {self.broker_host}:{self.broker_port}")
        
        # 检查网络连接性
        if not self._check_network_connectivity():
            print("网络连接检查失败，请检查网络设置")
            return False
        
        # 检查端口连接性
        if not self._check_port_connectivity():
            print("端口连接检查失败，请检查防火墙设置或服务器状态")
            return False
        
        try:
            with self.connection_lock:
                print("开始建立MQTT连接...")
                self.client.connect(self.broker_host, self.broker_port, self.keepalive)
                self.client.loop_start()
                
                # 等待连接确认，增加超时时间
                timeout = time.time() + 15
                while not self.is_connected and time.time() < timeout:
                    time.sleep(0.1)
                
                if self.is_connected:
                    print("MQTT连接建立成功")
                else:
                    print("MQTT连接超时")
                
                return self.is_connected
        except socket.gaierror as e:
            print(f"DNS解析错误: {e}")
            return False
        except ConnectionRefusedError as e:
            print(f"连接被拒绝: {e}")
            print("可能的原因:")
            print("1. MQTT服务器未运行")
            print("2. 端口被防火墙阻止")
            print("3. 服务器配置问题")
            return False
        except socket.timeout as e:
            print(f"连接超时: {e}")
            return False
        except Exception as e:
            print(f"MQTT连接错误: {e}")
            print(f"错误类型: {type(e).__name__}")
            return False
    
    def disconnect(self):
        """断开MQTT连接"""
        with self.connection_lock:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
                self.is_connected = False
                print("MQTT连接已断开")
    
    def _reconnect(self):
        """重连"""
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries and not self.is_connected:
            try:
                print(f"尝试重连... ({retry_count + 1}/{max_retries})")
                
                # 重连前检查网络
                if not self._check_network_connectivity():
                    print("网络不可达，跳过此次重连")
                    time.sleep(5)
                    retry_count += 1
                    continue
                
                time.sleep(2 ** retry_count)  # 指数退避
                self.client.reconnect()
                
                # 等待重连结果
                timeout = time.time() + 10
                while not self.is_connected and time.time() < timeout:
                    time.sleep(0.1)
                
                if self.is_connected:
                    print("重连成功")
                    break
                else:
                    print("重连失败")
                    
                retry_count += 1
            except Exception as e:
                print(f"重连失败: {e}")
                retry_count += 1
    
    def publish(self, topic: str, payload: Any, qos: int = 1, retain: bool = False) -> bool:
        """
        发布消息到指定主题
        """
        if not self.is_connected:
            print("❌ MQTT未连接")
            return False
        
        try:
            self.publish_stats['total_attempts'] += 1
            self.publish_stats['topics_used'].add(topic)
            
            # 如果payload是字典，自动添加时间戳并转换为JSON
            if isinstance(payload, dict):
                if 'timestamp' not in payload:
                    # 精确到毫秒的时间戳
                    payload['timestamp'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                message = json.dumps(payload, ensure_ascii=False)
            else:
                message = str(payload)
            
            # 简化发送信息
            if self.debug_mode:
                print(f"📤 发送: {topic} ({len(message)}字节)")
                if isinstance(payload, dict):
                    summary = {k: v for k, v in payload.items() if k != 'timestamp'}
                    print(f"   内容: {summary}")
            
            # 发送消息
            result = self.client.publish(topic, message, qos=qos, retain=retain)
            
            # 追踪消息
            if result.mid:
                self.pending_messages[result.mid] = topic
            
            # 检查发送结果
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.publish_stats['successful_sends'] += 1
                if self.debug_mode:
                    print(f"✅ 发送成功: {topic}")
                return True
            else:
                self.publish_stats['failed_sends'] += 1
                error_msgs = {
                    mqtt.MQTT_ERR_NO_CONN: "未连接",
                    mqtt.MQTT_ERR_PROTOCOL: "协议错误",
                    mqtt.MQTT_ERR_INVAL: "参数无效"
                }
                error_msg = error_msgs.get(result.rc, f"错误{result.rc}")
                print(f"❌ 发送失败: {topic} ({error_msg})")
                return False
            
        except Exception as e:
            self.publish_stats['failed_sends'] += 1
            print(f"❌ 发送异常: {e}")
            return False
    
    def publish_data(self, data_type: str, data: Dict[str, Any], qos: int = 1) -> bool:
        """
        发布数据到vehicle主题
        
        Args:
            data_type: 数据类型 (如 'gnss', 'radar', 'system')
            data: 数据字典
            qos: 服务质量等级
        """
        # 直接发布到vehicle主题，不再使用子主题
        mqtt_logger.info(f"🎯 发布{data_type}数据到vehicle主题")
        
        # 在payload中添加数据类型标识
        payload = {
            "type": data_type,
            "data": data
        }
        
        return self.publish(self.base_topic, payload, qos)
    
    def publish_system_info(self, info_type: str, info_data: Dict = None, qos: int = 1) -> bool:
        """
        发布系统信息到vehicle主题
        
        Args:
            info_type: 信息类型 (如 'status', 'startup', 'shutdown', 'error')
            info_data: 信息数据
            qos: 服务质量等级
        """
        payload = {
            "type": "system",
            "info_type": info_type,
            "data": info_data or {}
        }
        
        # 简化系统信息日志
        if self.debug_mode:
            print(f"📊 系统信息: {info_type}")
        
        return self.publish(self.base_topic, payload, qos)
    
    # 保持向后兼容的方法
    def publish_status(self, status: str, additional_info: Dict = None, qos: int = 1) -> bool:
        """
        发布状态信息 (向后兼容，实际发送到vehicle主题)
        
        Args:
            status: 状态字符串
            additional_info: 额外信息
            qos: 服务质量等级
        """
        status_data = {"status": status}
        if additional_info:
            status_data.update(additional_info)
        
        return self.publish_system_info("status", status_data, qos)
    
    def get_publish_stats(self) -> Dict[str, Any]:
        """获取发送统计信息"""
        stats = self.publish_stats.copy()
        stats['topics_used'] = list(stats['topics_used'])
        stats['success_rate'] = (
            (stats['successful_sends'] / stats['total_attempts'] * 100) 
            if stats['total_attempts'] > 0 else 0
        )
        return stats
    
    def print_publish_stats(self):
        """打印发送统计"""
        stats = self.get_publish_stats()
        print(f"\n📈 MQTT统计: {stats['successful_sends']}/{stats['total_attempts']} ({stats['success_rate']:.1f}%)")

    def set_base_topic(self, topic: str):
        """设置基础主题"""
        self.base_topic = topic
    
    def get_connection_status(self) -> bool:
        """获取连接状态"""
        return self.is_connected
    
    def test_connection_and_publish(self) -> bool:
        """测试连接和发布功能"""
        if not self.is_connected:
            print("❌ 未连接到MQTT代理")
            return False
        
        print("🧪 开始MQTT连接和发布测试...")
        
        # 测试1: 发布简单字符串消息
        print("\n📝 测试1: 发布简单字符串消息")
        success1 = self.publish("test/string", "Hello MQTT!", qos=1)
        time.sleep(1)
        
        # 测试2: 发布JSON消息
        print("\n📝 测试2: 发布JSON消息")
        test_json = {
            "test_id": "mqtt_test_001",
            "message": "测试JSON消息",
            "value": 42
        }
        success2 = self.publish("test/json", test_json, qos=1)
        time.sleep(1)
        
        # 测试3: 发布到vehicle主题
        print("\n📝 测试3: 发布到vehicle主题")
        vehicle_data = {
            "type": "test",
            "data": {
                "test_type": "connectivity_test",
                "timestamp": datetime.now().isoformat()
            }
        }
        success3 = self.publish("vehicle", vehicle_data, qos=1)
        time.sleep(1)
        
        # 测试4: 发布保留消息
        print("\n📝 测试4: 发布保留消息")
        retained_msg = {
            "type": "status",
            "data": {
                "client_id": self.client_id,
                "status": "online",
                "last_seen": datetime.now().isoformat()
            }
        }
        success4 = self.publish("vehicle/status", retained_msg, qos=1, retain=True)
        time.sleep(1)
        
        print(f"\n📊 测试结果汇总:")
        print(f"   简单字符串: {'✅' if success1 else '❌'}")
        print(f"   JSON消息: {'✅' if success2 else '❌'}")
        print(f"   Vehicle主题: {'✅' if success3 else '❌'}")
        print(f"   保留消息: {'✅' if success4 else '❌'}")
        
        # 显示待确认消息
        if self.pending_messages:
            print(f"⏳ 待确认消息: {len(self.pending_messages)}条")
            for mid, topic in self.pending_messages.items():
                print(f"   MID {mid}: {topic}")
        
        return all([success1, success2, success3, success4])


# 通用数据发布器
class DataPublisher:
    def __init__(self, mqtt_client: MQTTClient):
        """
        通用数据发布器
        
        Args:
            mqtt_client: MQTT客户端实例
        """
        self.mqtt = mqtt_client
        self.is_publishing = False
        self.publish_interval = 2.0
        self.publish_thread = None
        self.data_callback = None
        
        # 发布统计
        self.publish_count = 0
        self.success_count = 0
        self.last_publish_time = None
    
    def set_data_callback(self, callback: Callable[[], Dict[str, Any]]):
        """
        设置数据获取回调函数
        
        Args:
            callback: 返回要发布数据的函数
        """
        self.data_callback = callback
    
    def start_publishing(self, data_type: str, interval: float = 2.0):
        """
        开始自动发布数据
        
        Args:
            data_type: 数据类型
            interval: 发布间隔（秒）
        """
        if not self.data_callback:
            print("错误: 未设置数据回调函数")
            return False
        
        self.data_type = data_type
        self.publish_interval = interval
        self.is_publishing = True
        
        self.publish_thread = threading.Thread(target=self._publish_loop)
        self.publish_thread.daemon = True
        self.publish_thread.start()
        
        print(f"开始自动发布{data_type}数据，间隔: {interval}秒")
        return True
    
    def stop_publishing(self):
        """停止自动发布"""
        self.is_publishing = False
        if self.publish_thread:
            self.publish_thread.join()
        
        # 简化停止日志
        if self.publish_count > 0:
            success_rate = self.success_count / self.publish_count * 100
            print(f"📊 {self.data_type}发布统计: {self.success_count}/{self.publish_count} ({success_rate:.1f}%)")

    def _publish_loop(self):
        """发布循环"""
        while self.is_publishing:
            try:
                if self.mqtt.is_connected and self.data_callback:
                    data = self.data_callback()
                    if data:
                        self.publish_count += 1
                        success = self.mqtt.publish_data(self.data_type, data)
                        
                        if success:
                            self.success_count += 1
                            self.last_publish_time = datetime.now()
                            # 简化成功日志，只在调试模式显示
                            if self.mqtt.debug_mode:
                                print(f"✅ {self.data_type} ({self.success_count}/{self.publish_count})")
                        else:
                            print(f"❌ {self.data_type}数据发布失败")
                
                time.sleep(self.publish_interval)
                
            except Exception as e:
                print(f"发布错误: {e}")
                time.sleep(1)
            return False
        
        self.data_type = data_type
        self.publish_interval = interval
        self.is_publishing = True
        
        self.publish_thread = threading.Thread(target=self._publish_loop)
        self.publish_thread.daemon = True
        self.publish_thread.start()
        
        print(f"开始自动发布{data_type}数据，间隔: {interval}秒")
        return True
    
    def stop_publishing(self):
        """停止自动发布"""
        self.is_publishing = False
        if self.publish_thread:
            self.publish_thread.join()
        
        # 输出发布统计
        if self.publish_count > 0:
            success_rate = self.success_count / self.publish_count * 100
            mqtt_logger.info(f"📊 发布统计 - 总计: {self.publish_count}, 成功: {self.success_count}, 成功率: {success_rate:.1f}%")
            if self.last_publish_time:
                mqtt_logger.info(f"🕐 最后发布时间: {self.last_publish_time}")
        
        print("停止自动发布数据")
    
    def _publish_loop(self):
        """发布循环"""
        while self.is_publishing:
            try:
                if self.mqtt.is_connected and self.data_callback:
                    data = self.data_callback()
                    if data:
                        self.publish_count += 1
                        mqtt_logger.info(f"🔄 第{self.publish_count}次发布{self.data_type}数据")
                        
                        success = self.mqtt.publish_data(self.data_type, data)
                        
                        if success:
                            self.success_count += 1
                            self.last_publish_time = datetime.now()
                            mqtt_logger.info(f"📈 发布成功率: {self.success_count}/{self.publish_count} ({self.success_count/self.publish_count*100:.1f}%)")
                            print(f"✅ 已发布{self.data_type}数据 ({self.success_count}/{self.publish_count})")
                        else:
                            mqtt_logger.warning(f"⚠️ 第{self.publish_count}次发布失败")
                            print(f"❌ 发布{self.data_type}数据失败")
                    else:
                        mqtt_logger.debug(f"⏭️ 跳过发布{self.data_type}数据 - 无有效数据")
                else:
                    if not self.mqtt.is_connected:
                        mqtt_logger.warning("⚠️ MQTT未连接，暂停发布")
                    if not self.data_callback:
                        mqtt_logger.error("❌ 数据回调函数未设置")
                
                time.sleep(self.publish_interval)
                
            except Exception as e:
                mqtt_logger.error(f"💥 发布循环异常: {e}")
                print(f"发布循环错误: {e}")
                time.sleep(1)


# 使用示例
if __name__ == "__main__":
    # 配置日志到控制台
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 正在启动MQTT连接测试...")
    
    # 创建MQTT客户端 (开启调试模式)
    mqtt_client = MQTTClient(
        broker_host="47.109.142.1",
        broker_port=1883,
        client_id="air_unit_debug_test",
        debug_mode=True
    )
    
    # 测试连接
    print("🔌 测试MQTT连接...")
    if mqtt_client.connect():
        print("✅ MQTT连接测试成功")
        
        # 运行连接和发布测试
        mqtt_client.test_connection_and_publish()
        
        # 等待消息确认
        print("\n⏳ 等待消息确认...")
        time.sleep(5)
        
        # 显示最终统计
        mqtt_client.print_publish_stats()
        
        # 检查是否还有待确认消息
        if mqtt_client.pending_messages:
            print(f"⚠️ 仍有 {len(mqtt_client.pending_messages)} 条消息未收到确认:")
            for mid, topic in mqtt_client.pending_messages.items():
                print(f"   MID {mid}: {topic}")
        else:
            print("✅ 所有消息都已收到服务器确认")
        
        mqtt_client.disconnect()
    else:
        print("❌ MQTT连接失败，请检查网络和服务器状态")
