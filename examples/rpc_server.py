#encoding=utf8   
import sys
sys.path.append("../") 

from zbus import RpcProcessor, RpcServer, Message, RequestMapping


class MyService: 
    
    def echo(self, ping):
        return str(ping)
     
    def plus(self, a, b):  
        return int(a) + int(b) 
    
    def testEncoding(self, msg): #msg获取当前上下文的请求消息
        print(msg)
        return u'中文'
    
    def noReturn(self):
        pass
    
    @RequestMapping(path='/')
    def home(self):
        res = Message()
        res.status = 200
        res.headers['content-type'] = 'text/html; charset=utf8'
        res.body = '<h1> from Python </h1>'
        return res
    
    def getBin(self):
        b = bytearray(10)
        import base64
        return base64.b64encode(b).decode('utf8')
    
    def throwException(self):
        raise Exception("runtime exception from server")
    
    
    def map(self): 
        return {
            'key1': 'mykey',
            'key2': 'value2',
            'key3': 2.5
        }
    
    @RequestMapping(path='/post', method='POST')
    def post(self): 
        return {
            'key1': 'post required',
            'key2': 'post me',
            'key3': 122.3
        }
        
    def testTimeout(self):
        import time
        time.sleep(20) 


'''
侵入代码部分，从zbus上取消息处理返回
'''

p = RpcProcessor()
p.url_prefix = ''  #Global URL prefix
p.mount('/example', MyService()) #relative mount url

    
server = RpcServer(p) 
#需要认证的时候打开
#server.enable_auth('2ba912a8-4a8d-49d2-1a22-198fd285cb06', '461277322-943d-4b2f-b9b6-3f860d746ffd') #apiKey + secretKey
server.mq_server_address = 'localhost:15555'
#server.mq_server_address = '111.230.136.74:15555'
server.mq = 'MyRpc'   
server.start()