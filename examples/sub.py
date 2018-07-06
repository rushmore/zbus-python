#encoding=utf8   
from __future__ import print_function

import sys
sys.path.append("../")  

from zbus import MqClient, Message

mq = 'MyMQ'
channel = 'MyChannel'

def create_mq(client):
    msg = Message()
    msg.headers.cmd = 'create'
    msg.headers.mq = mq
    msg.headers.channel = channel 
      
    client.invoke(msg, lambda res: print(res)) #lambda

def onopen(client):
    
    create_mq(client)
    
    msg = Message()
    msg.headers.cmd = 'sub'
    msg.headers.mq = mq
    #msg.headers.filter = 'abc'
    msg.headers.channel = channel 
    msg.headers.window = 1 #set in-flight message count
    
    def cb(res):
        print(res)
     
    client.invoke(msg, cb)

def message_handler(msg):
    print(msg)

client = MqClient('zbus.io:15555')
client.onopen = onopen
client.add_mq_handler(mq=mq, channel=channel, handler=message_handler)
client.connect() 

