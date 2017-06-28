import sys
sys.path.append("../")
from zbus import MqClient, Message  

client = MqClient("localhost:15555")

def on_message(msg):
    serverInfo = msg.body 
    print(serverInfo) 

def on_connected():
    msg = Message()
    msg.cmd = 'track_sub'
    client.send(msg) 
    
def on_disconnected():
    print('disconnected')
    
    
client.on_message = on_message
client.on_connected = on_connected
client.on_disconnected = on_disconnected
client.start() 


