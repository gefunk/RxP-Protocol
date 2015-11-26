from protocol import RxP
import logging
import sys
import threading
from connection import RxPConnectionState

class Client:
    def __init__(self, bindport, destip, destport, loglevel=logging.DEBUG):
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
        self.bindport = int(bindport)
        self.destip = destip
        self.destport = int(destport)
        self.connection = None
        
        self.receive_state = None
        self.separator_text = b'|SEPARATOR|'
        
    
    def connect(self):
        socket = RxP(self.loglevel)
        conn = socket.connect("127.0.0.1", self.bindport, self.destip, self.destport, self.connect_listener)
        self.logger.debug("Connection process started")
        return conn


    def connect_listener(self, connection):
        self.connection = connection

    def handle_receive_data(self, conn):
        self.logger.debug("Handling Receiving of Data")
        data = bytearray()
        filename = None
        while conn.state is RxPConnectionState.ESTABLISHED:
            self.logger.debug("Client Receiving Data")
            data.extend(conn.receive(512))
            
            separator = data.find(self.separator_text)
            
            self.logger.debug("Client Separator Found : "+str(separator))
            if separator is not -1:
                server_command = data[0:separator].decode("utf-8") 
                self.logger.debug("Client command: "+server_command)
                command = server_command.split(' ')[0]
                filename = server_command.split(' ')[1]
                contents = data[separator+1+len(self.separator_text):]
                if 'file' in command:
                    self.logger.debug("Client WRiting bytes to file")
                    self.receive_state = 'file'
                    self.__write_bytes_to_file(filename, contents)
                    data = bytearray()
            elif self.receive_state == 'file':
                end_file = data.find(b'|END')
                if end_file is -1:
                    self.logger.debug("Client WRiting bytes to file")
                    self.__write_bytes_to_file(filename, data)
                    data = bytearray()
                else:
                    contents = data[:end_file]
                    self.__write_bytes_to_file(filename, contents)
                    self.logger.debug("Ending File Write")
                    self.receive_state = None
                    data = bytearray()

            self.logger.debug("Data from Server: "+str(data))
        self.logger.debug("Ended Client Recieve Data")

    def __write_bytes_to_file(self, filename, data):
        file = open(filename, "ab")
        file.write(data)
        file.close()


if len(sys.argv) != 4:
    print ("""Please provide the following 3 arguments: X A P\n
X: the port number at which the FxA-client’s UDP socket should bind to (even number). Please remember that this port number should be equal to the server’s port number minus 1. 
A: the IP address of NetEmu
P: the UDP port number of NetEmu 
            """)
else:
    print ("Starting client")
    client = Client( sys.argv[1], sys.argv[2], sys.argv[3], logging.DEBUG)
    ALIVE = True
    while ALIVE:
        user_input = input("What is your wish (command) ?")
        user_input = user_input.lower()
        if user_input == 'disconnect':
            conn.close()
            ALIVE = False
            print ("Client End - Goodbye")
        elif 'window' in user_input:
            window_size = user_input.split(' ',2)[1]
            try:
                window_size = int(window_size)
                conn.set_window_size(window_size)
            except ValueError:
                print ("ERROR window size is not an integer")
        elif 'connect' in user_input:
            conn = client.connect()
            t = threading.Thread(target=client.handle_receive_data, args=(conn,))
            t.setDaemon(True)
            t.start()
        elif 'get' in user_input:
            file_name = user_input.split(' ',2)[1]
            conn.send("get "+file_name)
        elif 'post' in user_input:
            file_name = user_input.split(' ',2)[1]
            file_contents = open(file_name, "rb").read()
            print("Sending following file contents: %s" % file_contents)
            conn.send("file %s" % (file_name+"_client"), file_contents+b'|END')
            
            
    
    print ("Client Should be ended")
    

