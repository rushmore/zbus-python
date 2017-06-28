import sys
sys.path.append("../")
from zbus import Broker, Consumer
 
broker = Broker('localhost:15555') 

def message_handler(msg, client):
    print(msg)

c = Consumer(broker, 'MyTopic')
c.message_handler = message_handler 
c.start()
