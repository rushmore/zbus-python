                /\\\                                                                             
                \/\\\                                                                            
                 \/\\\                                           /\\\\\\\\\     /\\\  /\\\       
     /\\\\\\\\\\\ \/\\\         /\\\    /\\\  /\\\\\\\\\\        /\\\/////\\\   \//\\\/\\\       
     \///////\\\/  \/\\\\\\\\\  \/\\\   \/\\\ \/\\\//////        \/\\\\\\\\\\     \//\\\\\       
           /\\\/    \/\\\////\\\ \/\\\   \/\\\ \/\\\\\\\\\\       \/\\\//////       \//\\\       
          /\\\/      \/\\\  \/\\\ \/\\\   \/\\\ \////////\\\       \/\\\          /\\ /\\\       
         /\\\\\\\\\\\ \/\\\\\\\\\  \//\\\\\\\\\   /\\\\\\\\\\  /\\\ \/\\\         \//\\\\/       
         \///////////  \/////////    \/////////   \//////////  \///  \///           \////      
         
# zbus-python-client

zbus strives to make Message Queue and Remote Procedure Call fast, light-weighted and easy to build your own service-oriented architecture for many different platforms. Simply put, zbus = mq + rpc.

zbus carefully designed on its protocol and components to embrace KISS(Keep It Simple and Stupid) principle, but in all it delivers power and elasticity. 

Start zbus, please refer to [https://github.com/rushmore/zbus](https://github.com/rushmore/zbus) 


## Getting started

    pip install zbuspy

- zbus.py works for both python2.x and python3.x


## API Demo

Only demos the gist of API, more configurable usage calls for your further interest.

### Produce message

    from zbus import MqClient, Message

    def onopen(client):
        msg = Message()
        msg.headers.cmd = 'pub'
        msg.headers.mq = 'MyMQ'
        msg.body = 'hello from python'

        client.invoke(msg, lambda res: print(res) )

    client = MqClient('localhost:15555')
    client.onopen = onopen
    client.connect()



### Consume message

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
        msg.headers.cmd = 'sub' #sub on channel of mq
        msg.headers.mq = mq
        msg.headers.channel = channel 
        
        def cb(res):
            print(res)
        
        client.invoke(msg, cb)

    def message_handler(msg):
        print(msg)

    client = MqClient('localhost:15555')
    client.onopen = onopen
    client.add_mq_handler(mq, channel, message_handler)
    client.connect() 

### RPC client

    from zbus import RpcClient   
    rpc = RpcClient('localhost:15555', mq='MyRpc')

    res = rpc.example.plus(1,2) 
    print(res)

    rpc.close()

### RPC service

    from zbus import RpcServer, Message, RequestMapping


    class MyService: 
        
        def echo(self, ping):
            return str(ping)
        
        def getString(self, s):
            return str(s)
            
        def plus(self, a, b):  
            return int(a) + int(b) 
        
        def testEncoding(self, msg): #msg -- request message context
            print(msg)
            return u'中文'
        
        def noReturn(self):
            pass
        
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
        
        @RequestMapping(path='/m', method='POST') #change path
        def map(self): 
            return {
                'key1': 'mykey',
                'key2': 'value2',
                'key3': 2.5
            }
            
        def testTimeout(self):
            import time
            time.sleep(20) 


    p = RpcProcessor()
    p.url_prefix = ''  #Global URL prefix
    p.mount('/example', MyService()) #relative mount url 

    server = RpcServer(p) 
    #When auth required
    #server.enable_auth('2ba912a8-4a8d-49d2-1a22-198fd285cb06', '461277322-943d-4b2f-b9b6-3f860d746ffd') #apiKey + secretKey
    server.mq_server_address = 'localhost:15555' 
    server.mq = 'MyRpc'   
    server.start()