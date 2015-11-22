from protocol import RxP
import logging

class Server:
    def __init__(self, loglevel=logging.DEBUG):
        self.logger = logging.getLogger("RxPConnection")
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
    
    def start(self):
        socket = RxP()
        socket.listen("127.0.0.1", 52001)
        while True:
            connection = socket.accept()
            # send the connection of to a process handler here
    



server = Server()
server.start()