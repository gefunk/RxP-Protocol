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
        socket = RxP(self.loglevel)
        conn = socket.connect("127.0.0.1", 52000, "127.0.0.1", 52001)
        self.logger.debug("Connection Established, %s" % conn)
        return conn



client = Client(logging.INFO)

conn = client.connect()
client.window_size = 2
conn.send("hello, whats up guy?")


while True:
    data = conn.receive(512)
    print ("Data from Server: "+str(data))
    

