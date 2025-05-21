import time
import json
import paho.mqtt.client as paho
from serial.tools import list_ports
import pydobot

MQTT_HOST = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "/robot/Dobot/jointRate"
JOINT_THRESHOLD = 1.0  # degrees per second

def get_first_available_port():
    available_ports = list_ports.comports()
    return available_ports[0].device if available_ports else None

def create_mqtt_client():
    client = paho.Client(paho.CallbackAPIVersion.VERSION1)

    def on_disconnect(client, userdata, rc):
        print("[WARNING] Disconnected from MQTT broker.")

    client.on_disconnect = on_disconnect
    return client

def safe_publish(client, topic, message):
    try:
        client.publish(topic, json.dumps(message))
    except Exception as e:
        print(f"[ERROR] Failed to publish MQTT message: {e}")

def publish_joint_rate_with_safety():
    port = get_first_available_port()
    if not port:
        print("No available serial ports found.")
        return

    try:
        device = pydobot.Dobot(port=port)
    except Exception as e:
        print(f"[ERROR] Failed to connect to robot: {e}")
        return

    client = create_mqtt_client()

    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            client.loop_start()
            break
        except Exception as e:
            print(f"[ERROR] MQTT connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)

    prev_joints = device.pose()
    prev_time = time.time()

    while True:
        try:
            time.sleep(1)
            current_joints = device.pose()
            current_time = time.time()
            dt = current_time - prev_time

            joint_deltas = {
                'j1': (current_joints[0] - prev_joints[0]) / dt,
                'j2': (current_joints[1] - prev_joints[1]) / dt,
                'j3': (current_joints[2] - prev_joints[2]) / dt,
                'j4': (current_joints[3] - prev_joints[3]) / dt,
            }

            filtered_joints = {
                joint: round(rate, 2) if abs(rate) >= JOINT_THRESHOLD else 0
                for joint, rate in joint_deltas.items()
            }

            message = {
                "nodeID": "dobot-01",
                "rate": filtered_joints,
                "unixtime": int(current_time)
            }

            safe_publish(client, MQTT_TOPIC, message)
            print("[PUBLISH]", message)

            prev_joints = current_joints
            prev_time = current_time

        except Exception as e:
            print(f"[ERROR] Runtime error: {e}")

            # Failsafe message
            failsafe_message = {
                "nodeID": "dobot-01",
                "rate": {"j1": 0, "j2": 0, "j3": 0, "j4": 0},
                "unixtime": int(time.time())
            }
            print("[FAILSAFE] Sending zero joint rates due to error or disconnect.")
            safe_publish(client, MQTT_TOPIC, failsafe_message)

            # Attempt to reconnect MQTT
            client.loop_stop()
            time.sleep(2)
            try:
                client.reconnect()
                client.loop_start()
                print("[INFO] Reconnected to MQTT broker.")
            except Exception as e:
                print(f"[ERROR] Reconnection failed: {e}. Retrying in 5 seconds...")
                time.sleep(5)

if __name__ == "__main__":
    publish_joint_rate_with_safety()
