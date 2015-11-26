from protocol import RxP
import logging
from threading import Thread




class Server(Thread):
    def __init__(self, port, loglevel=logging.DEBUG):
        super(Server, self).__init__()
        self.logger = logging.getLogger("RxPServer")
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
        self.SHOULD_I_RUN = True
        self.port = port
        
        self.connection_threads = []
        
    def handle_client(self,connection):
        while True:
            data = connection.receive(512)
            self.logger.info("Data Recieved from Client: %s " % data)
            connection.send("I got you, SON!")
    
    def run(self):
        socket = RxP(self.loglevel)
        socket.listen("127.0.0.1", self.port)
        while self.SHOULD_I_RUN:
            connection = socket.accept()
            # send the connection of to a process handler here
            t = Thread(target=self.handle_client, args=(connection,))
            self.connection_threads.append(t)
            t.start()
            

            
    def stop(self):
        self.SHOULD_I_RUN = False


if __name__ == '__main__':
    server = Server(52001, logging.DEBUG)
    server.start()


