import socket
import multiprocessing
import logging
from packet import RxPacket
from connection import RxPConnection
from packet import RxPFlags
from connection import RxPConnectionState

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
        # Initialize underlying implementation socket to UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # all the connections that are still waiting to establish
        self.initiating_connections = {}
        # established connections
        self.connections = {}
        self.BUFFER_SIZE = 512
    
    '''Start listening for incoming packets'''
    def listen(self, ip, port):
        self.ip = ip
        self.port = port
        self.logger.info("Listening @ IP: %s, Port: %s" % (ip,port))
        self.sock.bind((ip, port))
        
        
    """
    Send a connection SYN ACK To tell the client that we are here and listening
    We are going to ACKnowledge that we received the packet by sending the sequence number
    we received as the ACK number
    
    And tell the client to initialize by ACK our first packet
    
    This is is a private method
    """
    def __sendCONNECTSYNACK(self, packet):
        flags = [RxPFlags.SYN, RxPFlags.ACK]
        ack = packet.sequence
        seq = 0
        synack_packet = RxPacket(
            flags=flags, 
            sequence=seq, 
            ack=ack, 
            sourceip=self.ip, 
            destinationip=packet.sourceip,
            sourceport=self.port,
            destport=packet.sourceport)
        self.logger.debug("Sending SYNACK packet")
        self.__send_packet(synack_packet)
        
        
    """Send a SYN packet to initiate a connection with the server"""
    def __sendCONNECTSYN(self, sourceip, sourceport, destinationip, destport):
        flags = [RxPFlags.SYN]
        seq = 0
        syn_packet = RxPacket(
            flags, 
            seq, 
            sourceip=sourceip, 
            destinationip=destinationip,
            sourceport=sourceport,
            destport=destport)
        self.logger.debug("Sending SYN Packet")
        self.__send_packet(syn_packet)
    
    '''Send a packet to ACKnowledge a SYNACK packet'''
    def __sendCONNECTACK(self, sourceport, sourceip, packet):
        flags = [RxPFlags.ACK]
        ack_packet = RxPacket(
            flags=flags, 
            sequence=None,
            ack=packet.sequence,
            sourceip=sourceip, 
            destinationip=packet.sourceip,
            sourceport=sourceport,
            destport=packet.sourceport)
        self.logger.debug("Sending CONNECT ACK packet")
        self.__send_packet(ack_packet)
        
        
    """Accept listens for new connections and hands off a new connection back to the calling server"""
    def accept(self):
        '''Read all the packets and determine whether a new connection is to be established'''
        while True:
            self.logger.debug("Accept - waiting for packet to arrive")
            # wait for a packet to arrive
            packet = self.__receive_packet()
            if packet:
                connection_key = packet.sourceip+":"+str(packet.sourceport)
                ''' Client request to connect '''
                self.logger.debug("Initiating Connections: %s" % (self.initiating_connections.keys()))
                if RxPFlags.SYN in packet.flags:
                    # add client to possible connections list
                    self.initiating_connections[connection_key] = RxPConnection(packet.sourceip, packet.sourceport, 0, None)
                    self.__sendCONNECTSYNACK(packet)
                elif connection_key in self.initiating_connections and RxPFlags.ACK in packet.flags:
                    """
                    Check if an incoming ACK's is for connection establishment
                    if it is then we will break and return an established connection
                    """
                    self.connections[connection_key] = self.initiating_connections[packet.sourceip+":"+str(packet.sourceport)]
                    # set connection status to established
                    self.connections[connection_key].set_state(RxPConnectionState.ESTABLISHED)
                    # remove from the list of connections waiting to be established
                    del self.initiating_connections[connection_key]
                    # break out of loop and return connection
                    self.logger.debug("End Accept Returning Connection to Server")
                    return self.connections[connection_key]
    
    """Clients will use this method to connect to a remote destination"""                
    def connect(self, sourceip, sourceport, destinationip, destport, window_size=1):
        self.listen(sourceip, sourceport)
        '''To initiate a connection we must send a SYN packet'''
        self.__sendCONNECTSYN(sourceip, sourceport, destinationip, destport)
        
        while True:
           self.logger.debug("Connection Init Starting to recieve packet")
           # wait for a packet to arrive
           packet = self.__receive_packet()
           '''Check if we have a non corrupt packet and its an ACK packet sent to our correct destination'''
           if packet.checksum == RxPacket.calculate_checksum(packet) and packet.destinationip == sourceip and packet.destport == sourceport and RxPFlags.ACK in packet.flags:
               # Send acknowledgement to the client
               self.__sendCONNECTACK(sourceport, sourceip, packet)
               # set the connection to established and return
               connection = RxPConnection(packet.sourceip, packet.sourceport, 0, None)
               connection.set_state(RxPConnectionState.ESTABLISHED)
               connection.window_size = window_size
               return connection
               
               
    
    def __receive_packet(self):
        data,addr = self.sock.recvfrom(self.BUFFER_SIZE)
        self.logger.debug("Data in bytes: %s" % RxPacket.deserialize(data))
        packet = RxPacket.deserialize(data)
        self.logger.debug("Received packet: %s" % str(packet))
        '''Check if we have a non corrupt packet'''
        if packet.checksum != RxPacket.calculate_checksum(packet):
            self.logger.error("Corrupt Packet Detected, dropping packet %s", packet)
            return None
        return packet
    
    '''Send packet to destination'''
    def __send_packet(self, packet):
        packet.checksum = RxPacket.calculate_checksum(packet)
        self.logger.debug("Sending packet to %s at port %s: " % (packet.destinationip, packet.destport))
        # Send packet over UDP
        self.sock.sendto(RxPacket.serialize(packet), (packet.destinationip, packet.destport))