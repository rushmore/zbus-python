#encoding=utf8   
from __future__ import print_function

import sys
sys.path.append("../")  

from zbus import RpcClient  
    
rpc = RpcClient('localhost:15555') 

res = rpc.example.plus(1,2) 
print(res)


#close client
rpc.close()

