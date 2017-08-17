import sys
sys.path.append("../../")
from zbus import Broker, RpcInvoker

try: 
    broker = Broker('localhost:15555;localhost:15556')
    
    rpc = RpcInvoker(broker, 'MyRpc')
    
    
    res = rpc.invoke(method='plus', params=[1,2])
    print(res)
     
    res = rpc.plus(1,22)
    print(res)
    
    res = rpc.getString('hong')
    print(res)
    
finally:    
    broker.close()