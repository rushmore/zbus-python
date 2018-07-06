#encoding=utf8   
from __future__ import print_function

import sys
sys.path.append("../")  

from zbus import RpcClient  
    
client = RpcClient('localhost:15555', mq='MyRpc') #invoke will internally trigger connect 


#module.method(x,y) 
res = client.example.plus(1,2)
print(res) 



m = client.module('example')
print(m.plus(1,2))

res = client.invoke('plus', [1,2], module='example')
print(res)  

res = client.module('example', 'MyRpc').plus(1,2)
print(res)

#close client
client.close()

