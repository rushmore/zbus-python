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

Start zbus, please refer to [https://gitee.com/rushmore/zbus](https://gitee.com/rushmore/zbus) 


## Getting started

    pip install zbuspy

- zbus.py has no dependency 
- zbus.py works for both python2.x and python3.x


## API Demo

Only demos the gist of API, more configurable usage calls for your further interest.

### Produce message

    broker = Broker('localhost:15555') 
    
    p = Producer(broker) 
    p.declare('MyTopic') 

    msg = Message()
    msg.topic = 'MyTopic'
    msg.body = 'hello world'

    res = p.publish(msg)



### Consume message

    broker = Broker('localhost:15555')  

    def message_handler(msg, client):
        print(msg)

    c = Consumer(broker, 'MyTopic')
    c.message_handler = message_handler 
    c.start()

### RPC client

    broker = Broker('localhost:15555')

    rpc = RpcInvoker(broker, 'MyRpc') 

    res = rpc.invoke(method='plus', params=[1,2])
    print(res)
    
    res = rpc.plus(1,22)
    print(res)

    res = rpc.getString('hong')
    print(res)
    
    broker.close()

### RPC service

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


    broker = Broker('localhost:15555') 

    c = Consumer(broker, 'MyRpc')
    c.connection_count = 1
    c.message_handler = p #RpcProcessor is callable
    c.start()