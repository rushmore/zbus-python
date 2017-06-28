import sys
sys.path.append("../")
from zbus import MqClient, Message
import time, threading
client = MqClient("localhost:15555")
client.connect()

def test():
    while True:
        msg = Message()
        msg.topic = 'hong'
        msg.body = 'from zbus.py %.3f'%time.time()  
        client.produce(msg)  
        res = client.consume('hong')  
        print('%s-%s'%(threading.get_ident(), res)) 

threads = []
for i in range(10):
    t = threading.Thread(target=test)
    threads.append(t)
    t.start()

for t in threads:
    t.join()