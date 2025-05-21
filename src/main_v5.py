import sys
import paho.mqtt.client as paho
import json
import threading
import queue
import time
from serial.tools import list_ports
import pydobot

MQTT_HOST = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "/robot/Dobot/jointValues"

command_queue = queue.Queue()
prev_command = None

def get_first_available_port():
    available_ports = list_ports.comports()
    print(f'Available ports: {[x.device for x in available_ports]}')
    return available_ports[0].device if available_ports else None

def process_command(device):
    global prev_command
    while True:
        cmd = command_queue.get()
        if cmd is None:
            break

        if cmd == prev_command:
            command_queue.task_done()
            continue  # Skip duplicate command
        prev_command = cmd

        try:
            data = cmd['data']
            move_type = cmd['moveType']
            end_effector = data.get('endEffector', {})

            wait_flag = str(data.get('status', 'true')).lower() == 'true'

            # Clear queue in device to avoid lagging commands
            #device.queue_clear()

            if move_type == 'joint':
                device.move_joint_to(
                    float(data['j1']),
                    float(data['j2']),
                    float(data['j3']),
                    float(data['j4']),
                    wait=wait_flag
                )
            else:
                device.move_to(
                    float(data['x']),
                    float(data['y']),
                    float(data['z']),
                    float(data['r']),
                    wait=wait_flag
                )

            match end_effector.get('type'):
                case "grip":
                    device.grip(enable=str(end_effector.get('enable', 'false')).lower() == 'true')
                case "suck":
                    device.suck(enable=str(end_effector.get('enable', 'false')).lower() == 'true')

        except Exception as e:
            print(f"[ERROR] Command processing failed: {e}")
        finally:
            command_queue.task_done()

def message_handling(client, userdata, msg):
    try:
        raw_data = json.loads(msg.payload.decode())
        command_queue.put(raw_data)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to decode message: {e}")

def main():
    port = get_first_available_port()
    if not port:
        print("No available serial ports found.")
        sys.exit(1)

    try:
        device = pydobot.Dobot(port=port, verbose=True)
        device.move_joint_to(0, 0, 0, 0, wait=False)
    except Exception as e:
        print(f"[ERROR] Failed to connect to robot: {e}")
        sys.exit(1)

    # Start worker thread
    worker_thread = threading.Thread(target=process_command, args=(device,))
    worker_thread.daemon = True
    worker_thread.start()

    client = paho.Client(paho.CallbackAPIVersion.VERSION1)
    client.on_message = message_handling

    try:
        if client.connect(MQTT_HOST, MQTT_PORT, 60) != 0:
            print("Couldn't connect to the MQTT broker.")
            sys.exit(1)

        client.subscribe(MQTT_TOPIC)
        print("Listening for MQTT messages. Press CTRL+C to exit...")
        client.loop_forever()

    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Exiting...")
    except Exception as e:
        print(f"[ERROR] MQTT client error: {e}")
    finally:
        print("Cleaning up...")
        command_queue.put(None)
        worker_thread.join()
        device.close()
        client.disconnect()

if __name__ == "__main__":
    
    main()  