import sys
sys.path.append("../")
from zbus import Broker, Producer, Message
 
broker = Broker('localhost:15555')


p = Producer(broker)

p.declare('MyTopic') 

msg = Message()
msg.topic = 'MyTopic'
msg.body = 'hello world'

res = p.publish(msg)
print(res)
 
broker.close()