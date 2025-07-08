import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

def on_connect(client, userdata, flags, rc):
    """连接回调"""
    if rc == 0:
        print(f"✅ 已连接到MQTT代理")
        # 订阅多个主题进行测试
        topics = [
            ("vehicle", 1),
            ("vehicle/+", 1),
            ("test/+", 1),
            ("#", 0)  # 订阅所有主题 (用于调试)
        ]
        
        for topic, qos in topics:
            client.subscribe(topic, qos)
            print(f"📡 已订阅主题: {topic} (QoS: {qos})")
    else:
        print(f"❌ 连接失败，错误代码: {rc}")

def on_message(client, userdata, msg):
    """消息回调"""
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        qos = msg.qos
        retain = msg.retain
        
        print(f"\n📨 收到消息:")
        print(f"   主题: {topic}")
        print(f"   QoS: {qos}")
        print(f"   保留: {retain}")
        print(f"   时间: {datetime.now().strftime('%H:%M:%S')}")
        
        # 尝试解析JSON
        try:
            data = json.loads(payload)
            print(f"   内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
        except:
            print(f"   内容: {payload}")
        
        print("-" * 50)
        
    except Exception as e:
        print(f"❌ 处理消息错误: {e}")

def on_subscribe(client, userdata, mid, granted_qos):
    """订阅确认回调"""
    print(f"✅ 订阅确认 - MID: {mid}, QoS: {granted_qos}")

def main():
    print("🚀 MQTT订阅测试工具")
    print("监听主题: vehicle, vehicle/+, test/+, #")
    print("按Ctrl+C停止\n")
    
    # 创建MQTT客户端
    client = mqtt.Client(client_id="mqtt_subscriber_test")
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_subscribe = on_subscribe
    
    try:
        # 连接到MQTT代理
        client.connect("47.109.142.1", 1883, 60)
        
        # 启动循环
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\n🛑 用户中断")
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        client.disconnect()
        print("📡 已断开连接")

if __name__ == "__main__":
    main()
