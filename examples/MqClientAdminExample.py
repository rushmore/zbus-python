import sys
sys.path.append("../")
from zbus import MqClient

client = MqClient("localhost:15555")
client.connect()


res = client.declare('hong')
print (res)  
 
res = client.query()
print (res) 
 
res = client.query('hong')
print (res) 

res = client.query('hong', 'hong')
print (res) 

res = client.declare('hong')
print (res) 

#client.remove('hong')


client.close()