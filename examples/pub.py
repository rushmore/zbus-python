#encoding=utf8   
from __future__ import print_function

import sys
sys.path.append("../")  

from zbus import MqClient, Message

def onopen(client):
    msg = Message()
    msg.headers.cmd = 'pub'
    msg.headers.mq = 'MyMQ'  
    #msg.headers.tag = 'abc'
    msg.body = 'pub from python'

    for _ in range(100):
        client.invoke(msg, lambda res: print(res)) 

client = MqClient('zbus.io:15555')
client.onopen = onopen
client.connect()

