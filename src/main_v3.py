import sys
import paho.mqtt.client as paho
import json

# dobot
from serial.tools import list_ports
import pydobot

MQTT_HOST = "103.106.72.182"
MQTT_PORT = 1887
MQTT_TOPIC = "/robot/Dobot/jointValues"

available_ports = list_ports.comports()
print(f'available ports: {[x.device for x in available_ports]}')
if len(available_ports) > 0:
    port = available_ports[0].device
    
    device = pydobot.Dobot(port=port, verbose=True)
    
    # init position
    device.move_joint_to(0,0,0,0,False)
    
    def message_handling(client, userdata, msg):
        global prevData
        rawDatas = json.loads(str(msg.payload.decode()))
        # print(str(msg.payload.decode())[:-22] == prevData[:-22])
        data = rawDatas['data']
        moveType = rawDatas['moveType']
        endEffector = rawDatas['data']['endEffector']
        
        
        if str(msg.payload.decode())[:-23] != prevData:
            if moveType == 'joint':
                device.move_joint_to(int(float(data['j1'])),int(float(data['j2'])), int(float(data['j3'])), int(float(data['j4'])), wait=str.lower(data["status"] )== 'true')
            else:
                device.move_to(int(float(data['x'])),int(float(data['y'])), int(float(data['z'])), int(float(data['r'])), wait=str.lower(data["status"] )== 'true')
            
            if endEffector['type'] == "grip":
                device.grip(enable=str.lower(endEffector['enable']) == 'true')
            if endEffector['type'] == "suck":
                device.suck(enable=str.lower(endEffector['enable']) == 'true')
        prevData = str(msg.payload.decode()[:-23])
            
    # mqtt handling
    client = paho.Client(paho.CallbackAPIVersion.VERSION1)
    client.on_message = message_handling

    if client.connect(MQTT_HOST, MQTT_PORT, 60) != 0:
        print("Couldn't connect to the mqtt broker")
        sys.exit(1)
    
    prevData = None
    client.subscribe(MQTT_TOPIC)

    try:
        print("Press CTRL+C to exit...")
        client.loop_forever()
    except Exception as e:
        print(f"Error: \n{e}")
    finally:
        print("Disconnecting from the MQTT broker")
        device.close()
        client.disconnect()

