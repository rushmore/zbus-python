import sys
sys.path.append("../")
from zbus import Broker, MqAdmin, Message
 
broker = Broker('localhost:15555')

admin = MqAdmin(broker)

msg = Message()
msg.topic = 'hong6'
res = admin.declare(msg)
for res_i in res:
    print(res_i)
 
broker.close()