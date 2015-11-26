from protocol import RxP
from connection import RxPConnectionState
import logging
from threading import Thread
import sys




class Server(Thread):
    def __init__(self, sourceport, destinationip, destinationport, loglevel=logging.DEBUG):
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
        self.port = int(sourceport)
        self.destionationip = destinationip
        self.destinationport = int(destinationport)
        self.connected_client = None
        self.receive_state = None
        self.separator_text = b'|SEPARATOR|'
        
        
    def handle_client(self,connection):
        data = bytearray()
        while self.SHOULD_I_RUN and connection.state is RxPConnectionState.ESTABLISHED:
            data.extend(connection.receive(512))
            self.logger.info("Data Recieved from Client: %s " % data)
            
            separator = data.find(self.separator_text)
            print ("Separator Found : "+str(separator))
            if separator is not -1:
                server_command = data[0:separator].decode("utf-8") 
                print ("Server command: "+server_command)
                command = server_command.split(' ')[0]
                filename = server_command.split(' ')[1]
                if 'get' in command:
                    file_contents = open(filename, "rb").read()
                    self.logger.debug("Sending following file contents: %s" % file_contents)
                    connection.send("file %s" % (filename+"_server"), file_contents+b'|END')
                    data = bytearray()
                elif 'file' in command:
                    self.logger.debug("Server Start WRiting bytes to file")
                    self.receive_state = 'file'
                    self.__write_bytes_to_file(filename, data[separator+(len(self.separator_text)):])
                    data = bytearray()
            elif self.receive_state == 'file':
                end_file = data.find(b'|END')
                if end_file is -1:
                    self.logger.debug("Server WRiting bytes to file")
                    self.__write_bytes_to_file(filename, data)
                    data = bytearray()
                else:
                    contents = data[:end_file]
                    self.__write_bytes_to_file(filename, contents)
                    self.logger.debug("Ending File Write")
                    self.receive_state = None
                    data = bytearray()
        self.logger.debug("Ended Handle Client")
        
    def __write_bytes_to_file(self, filename, data):
        file = open(filename, "ab")
        file.write(data)
        file.close()

    
    def start(self):
        socket = RxP(self.loglevel)
        socket.listen("127.0.0.1", self.port)
        connection = socket.accept()
        t = Thread(target=self.handle_client, args=(connection,))
        self.connected_client = (connection)
        t.start()
            

            
    def stop(self):
        self.SHOULD_I_RUN = False
        for connection in self.connected_clients:
            connection.close()


if len(sys.argv) != 4:
    print ("""Please provide the following 3 arguments: X A P\n
""")
else:
    print ("Starting server")
    server = Server( sys.argv[1], sys.argv[2], sys.argv[3], logging.INFO)
    server.start()
    ALIVE = True
    while ALIVE:
        user_input = input("What is your wish (command) ?")
        user_input = user_input.lower()
        if user_input == 'terminate':
            server.stop()
            ALIVE = False
            print ("Server End - Goodbye")
        elif 'window' in user_input:
            window_size = user_input.split(' ',2)[1]
            try:
                window_size = int(window_size)
                #conn.set_window_size(window_size)
            except ValueError:
                print ("ERROR window size is not an integer")
    
    print ("Server ended")


