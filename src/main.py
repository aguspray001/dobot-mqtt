import sys
import paho.mqtt.client as paho
import json

# dobot
from serial.tools import list_ports
import pydobot

MQTT_HOST = "103.106.72.182"
MQTT_PORT = 1887


available_ports = list_ports.comports()
print(f'available ports: {[x.device for x in available_ports]}')
if len(available_ports) > 0:
    port = available_ports[0].device
    
    device = pydobot.Dobot(port=port, verbose=True)
    
    (x, y, z, r, j1, j2, j3, j4) = device.pose()
    print(f'x:{x} y:{y} z:{z} j1:{j1} j2:{j2} j3:{j3} j4:{j4}')
    def message_handling(client, userdata, msg):
        rawDatas = json.loads(str(msg.payload.decode()))
        # print(msg.payload.decode())
        # print(int(float(rawDatas['data']['j1'])))
        # print(len(rawDatas))
        # if len(rawDatas) >= 0:
        #     for rawData in rawDatas:
        #         data = rawData['data']
        #         moveType = rawData['moveType']
        #         endEffector = rawData['data']['endEffector']
        #         print(endEffector)
        #         if moveType == 'joint':
        #             device.move_joint_to(int(float(data['j1'])),int(float(data['j2'])), int(float(data['j3'])), int(float(data['j4'])), wait=str.lower(data["status"] )== 'true')
        #         else:
        #             device.move_to(int(float(data['x'])),int(float(data['y'])), int(float(data['z'])), int(float(data['r'])), wait=str.lower(data["status"] )== 'true')
        #         match endEffector['type']:
        #             case "grip":
        #                 device.grip(enable=str.lower(endEffector['enable']) == 'true')
        #             case "suck":
        #                 device.suck(enable=str.lower(endEffector['enable']) == 'true')
        # else:
        data = rawDatas['data']
        moveType = rawDatas['moveType']
        endEffector = rawDatas['data']['endEffector']
        if moveType == 'joint':
            device.move_joint_to(int(float(data['j1'])),int(float(data['j2'])), int(float(data['j3'])), int(float(data['j4'])), wait=str.lower(data["status"] )== 'true')
        else:
            device.move_to(int(float(data['x'])),int(float(data['y'])), int(float(data['z'])), int(float(data['r'])), wait=str.lower(data["status"] )== 'true')
        match endEffector['type']:
            case "grip":
                device.grip(enable=str.lower(endEffector['enable']) == 'true')
            case "suck":
                device.suck(enable=str.lower(endEffector['enable']) == 'true')
        print(device.isFinish)
            
    # mqtt handling
    client = paho.Client(paho.CallbackAPIVersion.VERSION1)
    client.on_message = message_handling

    if client.connect(MQTT_HOST, MQTT_PORT, 60) != 0:
        print("Couldn't connect to the mqtt broker")
        sys.exit(1)

    # client.subscribe("/robot/mqtt")
    client.subscribe("/robot/Dobot/jointValues")

    try:
        print("Press CTRL+C to exit...")
        client.loop_forever()
    except Exception as e:
        print(f"Error: \n{e}")
    finally:
        print("Disconnecting from the MQTT broker")
        device.close()
        client.disconnect()

