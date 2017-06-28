import sys
sys.path.append("../")
from zbus import MqClient, Message

client = MqClient("localhost:15555")
client.connect()  


client.declare('hong')

msg = Message()
msg.topic = 'hong'
msg.body = 'hello world'

res = client.produce(msg)
print(res)



client.close()
