import socket
import multiprocessing
import logging
from connection import RxPConnection
from connection import RxPConnectionState
from communicator import RxPCommunicator
from packet import RxPFlags

class RxP:
    def __init__(self, loglevel=logging.DEBUG):
        self.logger = logging.getLogger("RxP")
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
        # all the connections that are still waiting to establish
        self.initiating_connections = {}
        # established connections
        self.connections = {}
        # Initialize underlying implementation socket to UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Initialize RxP communication class
        self.communicator = RxPCommunicator(self.sock, loglevel)
        
    
    '''Start listening for incoming packets'''
    def listen(self, ip, port):
        self.ip = ip
        self.port = port
        self.logger.info("Listening @ IP: %s, Port: %s" % (ip,port))
        self.sock.bind((ip, port))
        
        
        
    """Accept listens for new connections and hands off a new connection back to the calling server"""
    def accept(self):
        '''Read all the packets and determine whether a new connection is to be established'''
        while True:
            self.logger.debug("Accept - waiting for packet to arrive")
            # wait for a packet to arrive
            packet = self.communicator.receive_packet()
            if packet:
                connection_key = packet.sourceip+":"+str(packet.sourceport)
                ''' Client request to connect '''
                self.logger.debug("Initiating Connections: %s" % (self.initiating_connections.keys()))
                if RxPFlags.SYN in packet.flags:
                    # add client to possible connections list
                    self.initiating_connections[connection_key] = RxPConnection("Connection to: "+connection_key,self.ip, self.port, packet.sourceip, packet.sourceport, 0, None, self.communicator, self.loglevel)
                    self.communicator.sendCONNECTSYNACK(self.ip, self.port, packet)
                elif connection_key in self.initiating_connections and RxPFlags.ACK in packet.flags:
                    """
                    Check if an incoming ACK's is for connection establishment
                    if it is then we will break and return an established connection
                    """
                    self.connections[connection_key] = self.initiating_connections[packet.sourceip+":"+str(packet.sourceport)]
                    # start the connection process
                    self.connections[connection_key].start()
                    # remove from the list of connections waiting to be established
                    del self.initiating_connections[connection_key]
                    # break out of loop and return connection
                    self.logger.debug("End Accept Returning Connection to Server")
                    return self.connections[connection_key]
    
    
    
    """Clients will use this method to connect to a remote destination"""                
    def connect(self, sourceip, sourceport, destinationip, destport, window_size=1):
        self.listen(sourceip, sourceport)
        '''To initiate a connection we must send a SYN packet'''
        self.communicator.sendCONNECTSYN(sourceip, sourceport, destinationip, destport)
        while True:
           self.logger.debug("Connection Init Starting to recieve packet")
           # wait for a packet to arrive
           packet = self.communicator.receive_packet()
           '''Check if its an ACK packet sent to our correct destination'''
           if packet.destinationip == sourceip and packet.destport == sourceport and RxPFlags.ACK in packet.flags:
               # Send acknowledgement to the client
               self.communicator.sendACK(sourceport, sourceip, packet)
               connection_key = packet.sourceip+":"+str(packet.sourceport)
               # set the connection to established and return
               connection = RxPConnection("Connection to: "+connection_key,sourceip, sourceport, packet.sourceip, packet.sourceport, 0, None, self.communicator, self.loglevel)
               # start the connection process
               connection.start()
               connection.window_size = window_size
               return connection
               
               
    

                
        