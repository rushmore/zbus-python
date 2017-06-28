import sys
sys.path.append("../")
from zbus import MqClientPool, ConsumeThread

pool = MqClientPool('localhost:15555')

def message_handler(msg, client):
    print(msg)

t = ConsumeThread(pool, 'MyTopic')
t.connection_count = 2
t.message_handler = message_handler

t.start()