#encoding=utf8   
from __future__ import print_function

import sys
sys.path.append("../")  

from zbus import RpcClient
    
rpc = RpcClient('localhost',mq='MyRpc')

rpc.enable_auth('2ba912a8-4a8d-49d2-1a22-198fd285cb06', '461277322-943d-4b2f-b9b6-3f860d746ffd') 
 
res = rpc.example.plus(1,2) 
print(res)


#close client
rpc.close()
