#encoding=utf8
import sys
sys.path.append("../../")
from zbus import Broker, Consumer, RpcProcessor, Protocol, Message

'''
MyService is just a simple Python object
'''
class MyService(object):
    def getString(self, ping):
        return ping
     
    def echo(self, ping):
        return ping
     
    def save(self, user): 
        return 'OK'
          
    def plus(self, a, b): 
        return int(a) + int(b) 
    
    def testEncoding(self):
        return u'中文'


p = RpcProcessor()
p.add_module(MyService) #could be class or object


broker = Broker('localhost:15555;localhost:15556')
ctrl = Message()
ctrl.topic = 'MyRpc'
ctrl.topic_mask = Protocol.MASK_MEMORY|Protocol.MASK_RPC

c = Consumer(broker, ctrl)
c.connection_count = 1
c.message_handler = p #RpcProcessor is callable
c.start()
