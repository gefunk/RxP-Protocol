from protocol import RxP
import logging

class Client:
    def __init__(self, loglevel=logging.DEBUG):
        self.logger = logging.getLogger("Client")
        self.loglevel = loglevel
        # create console handler and set level to debug
        self.logger.setLevel(loglevel)
        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(loglevel)
        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # add formatter to ch
        ch.setFormatter(formatter)
        # add ch to logger
        self.logger.addHandler(ch)
    
    def connect(self):
        socket = RxP()
        conn = socket.connect("127.0.0.1", 52000, "127.0.0.1", 52001)
        self.logger.debug("Connection Established, %s" % conn)
        return conn



client = Client()

conn = client.connect()
print ("Sending Data through client")
conn.send("hello, whats up guy?")


data = conn.receive(512)
print ("Data from Server: "+data)
    

