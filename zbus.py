#encoding=utf8
import uuid
import time
import json
import random
import inspect
import logging.config
import os
import sys
import importlib
import threading
import socket
import ssl

class Protocol:
    VERSION_VALUE = "0.8.0"  # start from 0.8.0
    #############Command Values############
    # MQ Produce/Consume
    PRODUCE = "produce"
    CONSUME = "consume"
    RPC = "rpc"
    ROUTE = "route"  # route back message to sender, designed for RPC

    # Topic/ConsumeGroup control
    DECLARE = "declare"
    QUERY = "query"
    REMOVE = "remove"
    EMPTY = "empty"

    # Tracker
    TRACK_PUB = "track_pub"
    TRACK_SUB = "track_sub"

    COMMAND = "cmd"
    TOPIC = "topic"
    TOPIC_MASK = "topic_mask"
    TAG = "tag"
    OFFSET = "offset"

    CONSUME_GROUP = "consume_group"
    GROUP_START_COPY = "group_start_copy"
    GROUP_START_OFFSET = "group_start_offset"
    GROUP_START_MSGID = "group_start_msgid"
    GROUP_START_TIME = "group_start_time"
    GROUP_FILTER = "group_filter"
    GROUP_MASK = "group_mask"
    CONSUME_WINDOW = "consume_window"

    SENDER = "sender"
    RECVER = "recver"
    ID = "id"
    
    ACK = "ack"
    ENCODING = "encoding"

    ORIGIN_ID = "origin_id"
    ORIGIN_URL = "origin_url"
    ORIGIN_STATUS = "origin_status"

    # Security
    TOKEN = "token"

    MASK_PAUSE = 1 << 0
    MASK_RPC = 1 << 1
    MASK_EXCLUSIVE = 1 << 2
    MASK_DELETE_ON_EXIT = 1 << 3


##########################################################################
# support both python2 and python3
if sys.version_info[0] < 3:
    Queue = importlib.import_module('Queue')
    def _bytes(buf, encoding='utf8'):
        return buf.encode(encoding)
else:
    Queue = importlib.import_module('queue')
    def _bytes(buf, encoding='utf8'):
        return bytes(buf, encoding)

try:
    log_file = 'log.conf'
    if os.path.exists(log_file):
        logging.config.fileConfig(log_file)
    else:
        import os.path
        log_dir = os.path.dirname(os.path.realpath(__file__))
        log_file = os.path.join(log_dir, 'log.conf')
        logging.config.fileConfig(log_file)
except:
    logging.basicConfig(
        format='%(asctime)s - %(filename)s-%(lineno)s - %(levelname)s - %(message)s')


class Message(dict):
    http_status = {
        200: "OK",
        201: "Created",
        202: "Accepted",
        204: "No Content",
        206: "Partial Content",
        301: "Moved Permanently",
        304: "Not Modified",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        416: "Requested Range Not Satisfiable",
        500: "Internal Server Error",
    }
    reserved_keys = set(['status', 'method', 'url', 'body'])

    def __init__(self, opt=None):
        self.body = None
        if opt and isinstance(opt, dict):
            for k in opt:
                self[k] = opt[k]

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            return None

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        self.pop(name, None)

    def __getitem__(self, key):
        if key not in self:
            return None
        return dict.__getitem__(self, key)


def msg_encode(msg):
    if not isinstance(msg, dict):
        raise ValueError('%s must be dict type' % msg)
    if not isinstance(msg, Message):
        msg = Message(msg)

    res = bytearray()
    if msg.status is not None:
        desc = Message.http_status.get('%s' % msg.status)
        if desc is None:
            desc = b"Unknown Status"
        res += _bytes("HTTP/1.1 %s %s\r\n" % (msg.status, desc), 'utf8')
    else:
        m = msg.method
        if not m:
            m = 'GET'
        url = msg.url
        if not url:
            url = '/'
        res += _bytes("%s %s HTTP/1.1\r\n" % (m, url), 'utf8')

    body_len = 0
    if msg.body:
        if not isinstance(msg.body, (bytes, bytearray)) and not msg['content-type']:
            msg['content-type'] = 'text/plain'

        if not isinstance(msg.body, (bytes, bytearray, str)):
            msg.body = json.dumps(msg.body).encode(msg.encoding or 'utf8')
            msg['content-type'] = 'application/json'

        body_len = len(msg.body)

    for k in msg:
        if k.lower() in Message.reserved_keys:
            continue
        if msg[k] is None:
            continue
        res += _bytes('%s: %s\r\n' % (k, msg[k]), 'utf8')
    len_key = 'content-length'
    if len_key not in msg:
        res += _bytes('%s: %s\r\n' % (len_key, body_len), 'utf8')

    res += _bytes('\r\n', 'utf8')

    if msg.body:
        if isinstance(msg.body, (bytes, bytearray)):
            res += msg.body
        else:
            res += _bytes(str(msg.body), msg.encoding or 'utf8')
    return res


def find_header_end(buf, start=0):
    i = start
    end = len(buf)
    while i + 3 < end:
        if buf[i] == 13 and buf[i + 1] == 10 and buf[i + 2] == 13 and buf[i + 3] == 10:
            return i + 3
        i += 1
    return -1


def decode_headers(buf):
    msg = Message()
    buf = buf.decode('utf8')
    lines = buf.splitlines()
    meta = lines[0]
    blocks = meta.split()
    if meta.upper().startswith('HTTP'):
        msg.status = int(blocks[1])
    else:
        msg.method = blocks[0].upper()
        if len(blocks) > 1:
            msg.url = blocks[1]

    for i in range(1, len(lines)):
        line = lines[i]
        if len(line) == 0:
            continue
        try:
            p = line.index(':')
            key = str(line[0:p]).strip()
            val = str(line[p + 1:]).strip()
            msg[key] = val
        except Exception as e:
            logging.error(e)

    return msg


def msg_decode(buf, start=0):
    p = find_header_end(buf, start)
    if p < 0:
        return (None, start)
    head = buf[start: p]
    msg = decode_headers(head)
    if msg is None:
        return (None, start)
    p += 1  # new start

    body_len = msg['content-length']
    if body_len is None:
        return (msg, p)
    body_len = int(body_len)
    if len(buf) - p < body_len:
        return (None, start)

    msg.body = buf[p: p + body_len]
    content_type = msg['content-type']
    if content_type:
        if str(content_type).startswith('text') or str(content_type) == 'application/json':
            msg.body = str(msg.body.decode(msg.ecoding or 'utf8'))
        if str(content_type) == 'application/json':
            try:
                msg.body = json.loads(msg.body, encoding=msg.ecoding or 'utf8')
            except:
                pass
    return (msg, p + body_len)


class ServerAddress:
    def __init__(self, address, ssl_enabled=False):
        if isinstance(address, str):
            self.address = address
            self.ssl_enabled = ssl_enabled
        elif isinstance(address, dict):
            if 'address' not in address:
                raise TypeError('missing address in dictionary')
            if 'sslEnabled' not in address:  # camel style from java/js
                raise TypeError('missing sslEnabled in dictionary')

            self.address = address['address']
            self.ssl_enabled = address['sslEnabled']
        elif isinstance(address, ServerAddress):
            self.address = address.address
            self.ssl_enabled = address.ssl_enabled
        else:
            raise TypeError(address + " address not support")

    def __key(self):
        if self.ssl_enabled:
            return '[SSL]%s' % self.address
        return self.address

    def __hash__(self):
        return hash(self.address)

    def __eq__(self, other):
        return self.address == other.address and self.ssl_enabled == other.ssl_enabled

    def __str__(self):
        return self.__key()

    def __repr__(self):
        return self.__str__()


class MessageClient(object):
    log = logging.getLogger(__name__)

    def __init__(self, address='localhost:15555', ssl_cert_file=None):
        self.server_address = ServerAddress(address)
        self.ssl_cert_file = ssl_cert_file

        bb = self.server_address.address.split(':')
        self.host = bb[0]
        self.port = 80
        if len(bb) > 1:
            self.port = int(bb[1])

        self.read_buf = bytearray()
        self.sock = None
        self.pid = os.getpid()
        self.auto_reconnect = True
        self.reconnect_interval = 3  # 3 seconds

        self.result_table = {}

        self.lock = threading.Lock()
        self.on_connected = None
        self.on_disconnected = None
        self.on_message = None
        self.manually_closed = False

    def close(self):
        self.manually_closed = True
        self.auto_reconnect = False
        self.on_disconnected = None
        self.sock.close()
        self.read_buf = bytearray()

    def invoke(self, msg, timeout=3):
        with self.lock:
            msgid = self._send(msg, timeout)
            return self._recv(msgid, timeout)

    def send(self, msg, timeout=3):
        with self.lock:
            return self._send(msg, timeout)

    def heartbeat(self):
        msg = Message()
        msg.cmd = 'heartbeat'
        self.send(msg)

    def recv(self, msgid=None, timeout=3):
        with self.lock:
            return self._recv(msgid, timeout)

    def connect(self):
        with self.lock:
            self.manually_closed = False
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.server_address.ssl_enabled:
                self.sock = ssl.wrap_socket(
                    self.sock,  ca_certs=self.ssl_cert_file, cert_reqs=ssl.CERT_REQUIRED)

            self.log.info('Trying connect to (%s)' % self.server_address)
            self.sock.connect((self.host, self.port))
            self.log.info('Connected to (%s)' % self.server_address)

        if self.on_connected:
            self.on_connected()

        self.read_buf = bytearray()

    def _send(self, msg, timeout=10):
        msgid = msg.id
        if not msgid:
            msgid = msg.id = str(uuid.uuid4())

        self.log.debug('Request: %s' % msg)
        self.sock.sendall(msg_encode(msg))
        return msgid

    def _recv(self, msgid=None, timeout=3):
        if not msgid and len(self.result_table) > 0:
            try:
                self.result_table.popitem()[1]
            except:
                pass

        if msgid in self.result_table:
            return self.result_table[msgid]

        self.sock.settimeout(timeout)
        while True:
            buf = self.sock.recv(1024)
            #!!! when remote socket idle closed, could return empty, fixed by raising exception!!!
            if buf == None or len(buf) == 0:
                raise socket.error(
                    'remote server socket status error, possible idle closed')
            self.read_buf += buf
            idx = 0
            while True:
                msg, idx = msg_decode(self.read_buf, idx)
                if msg is None:
                    if idx != 0:
                        self.read_buf = self.read_buf[idx:]
                    break

                self.read_buf = self.read_buf[idx:]

                if msgid:
                    if msg.id != msgid:
                        self.result_table[msg.id] = msg
                        continue

                self.log.debug('Result: %s' % msg)
                return msg

    def start(self, recv_timeout=3):
        def serve():
            while True:
                try:
                    self.connect()
                    break
                except socket.error as e:
                    self.log.warn(e)
                    time.sleep(self.reconnect_interval)

            while True:
                try:
                    msg = self.recv(None, recv_timeout)
                    if msg and self.on_message:
                        self.on_message(msg)
                except socket.timeout as e:
                    try:
                        self.heartbeat()  # TODO use another thread to heartbeat
                    except Exception as e:
                        pass
                    continue
                except socket.error as e:
                    if self.manually_closed:
                        break

                    self.log.warn(e)
                    if self.on_disconnected:
                        self.on_disconnected()
                    if not self.auto_reconnect:
                        break
                    while self.auto_reconnect:
                        try:
                            self.sock.close()
                            self.connect()
                            break
                        except socket.error as e:
                            self.log.warn(e)
                            time.sleep(self.reconnect_interval)

        self._thread = threading.Thread(target=serve)
        self._thread.start()


def build_msg(cmd, topic_or_msg, group=None):
    if isinstance(topic_or_msg, Message):
        msg = topic_or_msg  
    else:
        msg = Message()
        msg.topic = topic_or_msg
    
    msg.cmd = cmd  
    if not msg.consume_group:
        msg.consume_group = group 
    
    return msg


class MqClient(MessageClient):
    def __init__(self, address='localhost:15555', ssl_cert_file=None):
        MessageClient.__init__(self, address, ssl_cert_file)
        self.token = None

    def invoke_cmd(self, cmd, topic_or_msg, group=None,timeout=3):
        msg = build_msg(cmd, topic_or_msg, group=group)
        if not msg.token:
            msg.token = self.token
        
        return self.invoke(msg, timeout=timeout)

    def invoke_object(self, cmd, topic, group=None, timeout=3):
        res = self.invoke_cmd(cmd, topic, group=group, timeout=timeout)
        if res.status != 200:  # not throw exception, for batch operations' convenience
            return {'error': res.body.decode(res.encoding or 'utf8')}
        return res.body

    def produce(self, msg, timeout=3): 
        return self.invoke_cmd(Protocol.PRODUCE, msg, group=None, timeout=timeout)

    def consume(self, topic_or_msg, group=None, timeout=3):
        return self.invoke_cmd(Protocol.CONSUME, topic_or_msg, group=group, timeout=timeout)

    def query(self, topic_or_msg=None, group=None, options=None, timeout=3):
        return self.invoke_object(Protocol.QUERY, topic_or_msg, group=group, timeout=timeout)

    def declare(self, topic_or_msg, group=None, options=None, timeout=3):
        return self.invoke_object(Protocol.DECLARE, topic_or_msg, group=group, timeout=timeout)

    def remove(self, topic_or_msg, group=None, options=None, timeout=3):
        return self.invoke_object(Protocol.REMOVE, topic_or_msg, group=group, timeout=timeout)

    def empty(self, topic_or_msg, group=None, options=None, timeout=3):
        return self.invoke_object(Protocol.EMPTY, topic_or_msg, group=group, timeout=timeout)

    def route(self, msg, timeout=3):
        msg.cmd = Protocol.ROUTE
        if not msg.token:
            msg.token = self.token
        if msg.status:
            msg.origin_status = msg.status
            msg.status = None

        self.send(msg, timeout)


class MqClientPool:
    log = logging.getLogger(__name__)

    def __init__(self, server_address='localhost:15555', ssl_cert_file=None, maxsize=50, timeout=3):
        self.server_address = ServerAddress(server_address)

        self.maxsize = maxsize
        self.timeout = timeout
        self.ssl_cert_file = ssl_cert_file
        self.reset() 
  

    def make_client(self):
        client = MqClient(self.server_address, self.ssl_cert_file)
        client.connect()
        self.log.debug('New client created %s', client)
        return client

    def _check_pid(self):
        if self.pid != os.getpid():
            with self._check_lock:
                if self.pid == os.getpid():
                    return
                self.log.debug('new process, pid changed')
                self.destroy()
                self.reset()

    def reset(self):
        self.pid = os.getpid()
        self._check_lock = threading.Lock()

        self.client_pool = Queue.LifoQueue(self.maxsize)
        while True:
            try:
                self.client_pool.put_nowait(None)
            except Queue.Full:
                break
        self.clients = []

    def borrow_client(self):
        self._check_pid()
        client = None
        try:
            client = self.client_pool.get(block=True, timeout=self.timeout)
        except Queue.Empty:
            raise Exception('No client available')
        if client is None:
            client = self.make_client()
            self.clients.append(client)
        return client

    def return_client(self, client):
        self._check_pid()
        if client.pid != self.pid:
            return
        if not isinstance(client, (tuple, list)):
            client = [client]
        for c in client:
            try:
                self.client_pool.put_nowait(c)
            except Queue.Full:
                pass

    def close(self): 
        for client in self.clients:
            client.close()




class BrokerRouteTable:
    class Vote:
        def __init__(self, version):
            self.version = version
            self.server_list = []
            
    def __init__(self):
        self.topic_table = {}     #{ TopicName=>[TopicInfo] }
        self.server_table = {}    #{ ServerAddress=>ServerInfo }
        self.votes_table = {}     #{ TrackerAddress=>Vote }
        self.vote_factor = 0.5
        
    def update_tracker(self, tracker_info):
        #1) Update votes
        tracker_address = ServerAddress(tracker_info['serverAddress']) 
        vote = self.votes_table.get(tracker_address) 
        new_server_table = tracker_info['serverTable'] 
        tracker_version = tracker_info['infoVersion']
        if vote and vote.version >= tracker_version:
            return []
        server_list = []
        for server_info in new_server_table.values(): 
            server_list.append(ServerAddress(server_info['serverAddress']))

        if not vote:
            vote = BrokerRouteTable.Vote(tracker_version)
            self.votes_table[tracker_address] = vote
            
        vote.version = tracker_version
        vote.server_list = server_list            
        
        #2) Merge ServerTable
        for server_info in new_server_table.values(): 
            server_address = ServerAddress(server_info['serverAddress'])
            old_server_info = self.server_table.get(server_address) 
            if old_server_info and old_server_info['infoVersion']>=server_info['infoVersion']:
                continue
            self.server_table[server_address] = server_info
        
        #3) Purge  
        return self._purge()

    def remove_tracker(self, tracker_address):
        tracker_address = ServerAddress(tracker_address)
        vote = self.votes_table.pop(tracker_address)
        if vote:
            return self._purge() 

    def _purge(self):
        to_remove = []
        for server_address in self.server_table:
            server_info = self.server_table[server_address]
            count = 0
            for tracker_address in self.votes_table:
                vote = self.votes_table[tracker_address]
                if server_address in vote.server_list:
                    count += 1
            total_count = len(self.votes_table)
            if count < total_count*self.vote_factor:
                to_remove.append(server_address)
        
        for server_address in to_remove:
            self.server_table.pop(server_address)
         
        topic_table = {}
        for key in self.server_table:
            server_info = self.server_table[key]
            server_topic_table = server_info['topicTable']
            for topic_name in server_topic_table:
                topic = server_topic_table[topic_name]
                if topic_name not in topic_table:
                    topic_table[topic_name] = [topic]
                else:
                    topic_table[topic_name].append(topic)

        self.topic_table = topic_table 
        return to_remove


class _CountDownLatch(object):
    def __init__(self, count=1):
        self.count = count
        self.lock = threading.Condition()

    def count_down(self):
        self.lock.acquire()
        self.count -= 1
        if self.count <= 0:
            self.lock.notifyAll()
        self.lock.release()

    def wait(self, timeout=3):
        self.lock.acquire()
        while self.count > 0:
            self.lock.wait(timeout)
        self.lock.release()

class Broker: 
    log = logging.getLogger(__name__) 
    def __init__(self, tracker_list=None):
        self.pool_table = {}
        self.route_table = BrokerRouteTable()
        self.ssl_cert_file_table = {}
        self.tracker_subscribers = {}
    
        self.on_server_join = None
        self.on_server_leave = None
        self.on_server_updated = None
        
        if tracker_list:
            trackers = tracker_list.split(';')
            for tracker in trackers:
                self.add_tracker(tracker)
            

    def add_tracker(self, tracker_address, cert_file=None):
        tracker_address = ServerAddress(tracker_address)
        if tracker_address in self.tracker_subscribers:
            return
        if cert_file:
            self.ssl_cert_file_table[tracker_address.address] = cert_file

        notify = _CountDownLatch(1)

        client = MqClient(tracker_address, cert_file)
        self.tracker_subscribers[tracker_address] = client

        def tracker_connected():
            msg = Message()
            msg.cmd = Protocol.TRACK_SUB
            client.send(msg)

        def on_message(msg):
            if msg.status != 200:
                self.log.error(msg)
                return 
            tracker_info = msg.body
            to_remove = self.route_table.update_tracker(tracker_info)
            for server_address in self.route_table.server_table:
                server_info = self.route_table.server_table[server_address]
                self._add_server(server_info)
            
            for server_address in to_remove:
                self._remove_server(server_address) 
                
            notify.count_down()
            

        client.on_connected = tracker_connected
        client.on_message = on_message
        client.start()

        notify.wait() 

    def _add_server(self, server_info):
        server_address = ServerAddress(server_info['serverAddress'])
        if server_address in self.pool_table:
            return 
        
        self.log.info('%s joined' % server_address)
        pool = MqClientPool(server_address, self.ssl_cert_file_table.get(server_address.address))
        self.pool_table[server_address] = pool
        
        if self.on_server_join:
            self.on_server_join(pool) 
            
    def _remove_server(self, server_address): 
        self.log.info('%s left' % server_address)
        pool = self.pool_table.pop(server_address)
        if pool:
            if self.on_server_leave:
                self.on_server_leave(server_address)
            pool.close()

    def select(self, selector, msg):
        keys = selector(self.route_table, msg)
        if not keys or len(keys) < 1:
            raise Exception("Missing MqServer for: %s"%msg)
        res = []
        for key in keys:
            if key in self.pool_table:
                res.append(self.pool_table[key])
        return res

    def close(self):
        for address in self.tracker_subscribers:
            client = self.tracker_subscribers[address]
            client.close()
        self.tracker_subscribers.clear()

        for key in self.pool_table:
            pool = self.pool_table[key]
            pool.close()
        self.pool_table.clear()


class MqAdmin:
    def __init__(self, broker):
        self.broker = broker

        def admin_selector(route_table, msg):
            return list(route_table.server_table.keys())
        self.admin_selector = admin_selector
        self.token = None

    def invoke_object(self, cmd, topic, group=None, timeout=3, selector=None):
        msg = build_msg(cmd, topic, group=group)
        pools = self.broker.select(selector or self.admin_selector, msg)
        res = []
        for pool in pools:
            client = None
            try:
                client = pool.borrow_client()
                res_i = client.invoke_object(cmd, topic, group=group,timeout=timeout)
                res.append(res_i)
            finally:
                if client:
                    pool.return_client(client)
        return res

    def declare(self, topic, group=None, timeout=3, selector=None):
        return self.invoke_object(Protocol.DECLARE, topic, group=group,timeout=timeout, selector=selector)

    def query(self, topic, group=None, timeout=3, selector=None):
        return self.invoke_object(Protocol.QUERY, topic, group=group, timeout=timeout, selector=selector)

    def remove(self, topic, group=None, timeout=3, selector=None):
        return self.invoke_object(Protocol.REMOVE, topic, group=group, timeout=timeout, selector=selector)

    def empty(self, topic, group=None, timeout=3, selector=None):
        return self.invoke_object(Protocol.EMPTY, topic, group=group, timeout=timeout, selector=selector)


class Producer(MqAdmin):
    def __init__(self, broker):
        MqAdmin.__init__(self, broker)
        random.seed(int(time.time()))

        def produce_selecotr(route_table, msg):
            server_table = route_table.server_table
            topic_table = route_table.topic_table
            if len(server_table) < 1:
                return []

            if msg.topic not in topic_table:
                return []
            topic_server_list = topic_table[msg.topic]
            target = topic_server_list[0]
            for server_topic in topic_server_list:
                if target['consumerCount'] < server_topic['consumerCount']:
                    target = server_topic
            return [ServerAddress(target['serverAddress'])]

        self.produce_selector = produce_selecotr

    def publish(self, msg, timeout=3, selector=None):
        msg.cmd = Protocol.PRODUCE
        if not msg.token:
            msg.token = self.token
        pools = self.broker.select(selector or self.produce_selector, msg)
        res = []
        for pool in pools:
            client = None
            try:
                client = pool.borrow_client()
                res_i = client.invoke(msg, timeout=timeout)
                res.append(res_i)
            finally:
                if client:
                    pool.return_client(client)
        if len(res) == 1:
            return res[0]
        return res


class ConsumeThread:
    log = logging.getLogger(__name__)

    def __init__(self, pool, msg_ctrl, message_handler=None, connection_count=1, timeout=3): 
        self.pool = pool
        self.msg_ctrl = msg_ctrl
        if isinstance(msg_ctrl, str):
            msg = Message()
            msg.topic = msg_ctrl
            self.msg_ctrl = msg

        self.consume_timeout = timeout
        self.connection_count = connection_count
        self.message_handler = message_handler
        
        self.client_threads = []
        

    def take(self, client):
        res = client.consume(self.msg_ctrl, timeout=self.consume_timeout)
        if res.status == 404:
            client.declare(self.msg_ctrl, timeout=self.consume_timeout)
            return self.take()
        if res.status == 200:
            res.id = res.origin_id
            del res.origin_id
            if res.origin_url:
                res.url = res.origin_url
                res.status = None
                del res.origin_url

            return res
        raise Exception(res.body) 
    
    def _run_client(self, client):
        if not self.message_handler:
            raise Exception("missing message_handler")
        while True:
            try:
                msg = self.take(client)
                if not msg: continue
                self.message_handler(msg, client)
            except socket.timeout:
                continue
            except Exception as e:
                self.log.error(e)
                break
    
    def start(self):
        for _ in range(self.connection_count):
            client = self.pool.make_client()
            thread = threading.Thread(target=self._run_client, args=(client,))
            thread.client = client 
            thread.start()
            
            self.client_threads.append(thread)

    def close(self):
        for thread in self.client_threads:
            thread.client.close() 



class Consumer(MqAdmin):
    log = logging.getLogger(__name__)

    def __init__(self, broker, msg_ctrl, message_handler=None, connection_count=1, selector=None, timeout=3):
        MqAdmin.__init__(self, broker)

        def consume_selecotr(route_table, msg):
            return list(route_table.server_table.keys())
        self.consume_selector = selector or consume_selecotr

        self.connection_count = connection_count
        self.msg_ctrl = msg_ctrl
        if isinstance(msg_ctrl, str):
            msg = Message()
            msg.topic = msg_ctrl
            self.msg_ctrl = msg

        self.consume_timeout = timeout
        self.message_handler = message_handler

        self.consume_thread_groups = {}

    def start_consume_thread(self, pool):
        if pool.server_address in self.consume_thread_groups:
            return

        consume_thread = ConsumeThread(pool, self.msg_ctrl, message_handler=self.message_handler, 
            connection_count=self.connection_count, timeout=self.consume_timeout)

        self.consume_thread_groups[pool.server_address] = consume_thread
        consume_thread.start()


    def start(self):
        def on_server_join(pool):
            self.start_consume_thread(pool)

        def on_server_leave(server_address):
            consume_thread = self.consume_thread_groups.pop(server_address, None)
            if consume_thread:
                consume_thread.close()

        self.broker.on_server_join = on_server_join
        self.broker.on_server_leave = on_server_leave

        pools = self.broker.select(self.consume_selector, self.msg_ctrl)
        for pool in pools:
            self.start_consume_thread(pool)


class RpcInvoker:
    log = logging.getLogger(__name__)

    def __init__(self, broker=None, topic=None, module=None, method=None, timeout=3, selector=None, token=None, producer=None):
        self.producer = producer or Producer(broker)
        self.producer.token = token

        self.topic = topic
        self.timeout = timeout
        self.server_selector = selector

        self.method = method
        self.module = module

    def __getattr__(self, name):
        return RpcInvoker(method=name, topic=self.topic, module=self.module,
                          producer=self.producer, timeout=self.timeout, selector=self.server_selector)

    def invoke(self, method=None, params=None, module='', topic=None, selector=None):
        topic = topic or self.topic
        if not topic:
            raise Exception("missing topic")

        selector = selector or self.server_selector
        req = {
            'method': method or self.method,
            'params': params,
            'module': module,
        }

        msg = Message()
        msg.topic = topic
        msg.ack = False  # RPC ack must set to False to wait return
        msg.body = req

        msg_res = self.producer.publish(msg, timeout=self.timeout, selector=selector)

        if isinstance(msg_res.body, bytearray):
            msg_res.body = msg_res.body.decode(msg_res.encoding or 'utf8') 
            msg_res.body = json.loads(str(msg_res.body))  
        
        elif isinstance(msg_res.body, (str,bytes)) and msg_res['content-type'] == 'application/json':
            msg_res.body = json.loads(str(msg_res.body))  

        if msg_res.status != 200: 
            raise Exception(msg_res.body)

        res = msg_res.body
        if res and 'error' in res and res['error']:
            raise Exception(res['error'])
        if res and 'result' in res:
            return res['result']  
        
    def __call__(self, *args, **kv_args):
        return self.invoke(params=args, **kv_args)


def Remote(_id=None):
    def func(fn):
        fn.remote_id = _id or fn.__name__
        return fn
    return func


class RpcProcessor:
    log = logging.getLogger(__name__)

    def __init__(self, *args):
        self.methods = {}
        for arg in args:
            self.add_module(arg)

    def add_module(self, service, module=''):
        if inspect.isclass(service):
            service = service()

        methods = inspect.getmembers(service, predicate=inspect.ismethod)
        for method in methods:
            method_name = method[0]

            if hasattr(method[1], 'remote_id'):
                method_name = getattr(method[1], 'remote_id')

            key = '%s:%s' % (module, method_name)
            if key in self.methods:
                self.log.warn('%s duplicated' % key)
            self.methods[key] = (method[1], inspect.getargspec(method[1]))

    def _get_value(self, req, name, default=None):
        if name not in req:
            return default
        return req[name] or default

    def handle_request(self, msg, client):   
        msg_res = Message()
        msg_res.status = 200
        msg_res.encoding = msg.encoding 
        msg_res.recver = msg.sender
        msg_res.id = msg.id 
         
        error = None
        result = None
        try:
            if isinstance(msg.body, (bytes, bytearray)):
                msg.body = str(msg.body.decode(msg.encoding or 'utf8'))

            if isinstance(msg.body, str):
                msg.body = json.loads(msg.body) 
            req = msg.body

        except Exception as e: 
            error = e

        if not error:
            try:
                method = req['method']
                module = self._get_value(req, 'module', '')
                params = self._get_value(req, 'params', []) 
            except Exception as e: 
                error = e

        if not error:
            key = '%s:%s' % (module, method)
            if key not in self.methods: 
                error = Exception('%s method not found' % key)
            else:
                method_info = self.methods[key]
                method = method_info[0]

        if not error:
            try:
                result = method(*params)
            except Exception as e:
                error = e 
                
        msg_res.body = {'error': error, 'result': result} 
        
        try:  client.route(msg_res) 
        except e: pass

    def __call__(self, *args, **kv_args):
        return self.handle_request(*args)


__all__ = [
    Message, MessageClient, MqClient, MqClientPool, ServerAddress,
    Broker, MqAdmin, Producer, Consumer, RpcInvoker, RpcProcessor, Remote,
    ConsumeThread
]
