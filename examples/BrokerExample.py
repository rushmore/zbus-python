import sys
sys.path.append("../")
from zbus import Broker 
 
broker = Broker()
broker.add_tracker('localhost:15555')

 
print(broker.pool_table) 

broker.close()