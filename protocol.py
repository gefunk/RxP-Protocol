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
        self.initiating_connections = {}
        self.connections = {}
        self.BUFFER_SIZE = 512
    
    '''Start listening for incoming packets'''
    def listen(self, ip, port):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((ip, port))
        self.info("Listening @ IP: %s, Port: %s" % (ip,port))
        
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
            destport=packet.destinationip)
        self.__send_packet(synack_packet)
        
        
    """Send a SYN packet to initiate a connection with the server"""
    def __sendCONNECTSYN(self, sourceip, sourceport, destinationip, destport):
        flags = [RxPFlags.SYN]
        seq = 0
        syn_packet = RxPacket(
            flags=flags, 
            sequence=seq, 
            sourceip=sourceip, 
            destinationip=destport,
            sourceport=sourceport,
            destport=destinationip)
        self.__send_packet(syn_packet)
    
    '''Send a packet to ACKnowledge a SYNACK packet'''
    def __sendCONNECTACK(self, sourceport, sourceip, packet, window_size):
        flags = [RxPFlags.ACK]
        ack_packet = RxPacket(
            flags=flags, 
            sequence=None,
            ack=packet.sequence,
            sourceip=sourceip, 
            destinationip=packet.sourceip,
            sourceport=sourceport,
            destport=packet.destport,
            window_size=window_size)
        self.__send_packet(ack_packet)
        
        
    """Accept listens for new connections and hands off a new connection back to the calling server"""
    def accept(self):
        '''Read all the packets and determine whether a new connection is to be established'''
        while True:
            # wait for a packet to arrive
            self.__receive_packet()
            '''Check if we have a non corrupt packet'''
            if packet.checksum == RxPacket.calculate_checksum(packet):
                ''' Client request to connect '''
                if RxPFlags.SYN in packet.flags:
                    # add client to possible connections list
                    self.initiating_connections[packet.sourceip] = RxPConnection(packet.sourceip, packet.sourceport, 0, None)
                    self.__sendCONNECTSYNACK(packet)
                elif packet.sourceip in initiating_connections and RxPFlags.ACK in packet.flags:
                    """
                    Check if an incoming ACK's is for connection establishment
                    if it is then we will break and return an established connection
                    """
                    self.connections[packet.sourceip] = initiating_connections[packet.sourceip]
                    # set connection status to established
                    self.connections[packet.sourceip].set_state(RxPConnectionState.ESTABLISHED)
                    # remove from the list of connections waiting to be established
                    del self.initiating_connections[packet.sourceip]
                    # break out of loop and return connection
                    return self.connections[packet.sourceip]
    
    """Clients will use this method to connect to a remote destination"""                
    def connect(self, sourceip, sourceport, destinationip, destport, window_size=1):
        '''To initiate a connection we must send a SYN packet'''
        self.__sendSYN(sourceip, sourceport, destinationip, destport)
        while True:
           # wait for a packet to arrive
           self.__receive_packet()
           '''Check if we have a non corrupt packet and its an ACK packet sent to our correct destination'''
           if packet.checksum == RxPacket.calculate_checksum(packet) and packet.destinationip == sourceip and packet.destinationport == sourceport and RxPFlags.ACK in packet.flags:
               # Send acknowledgement to the client
               self.__sendCONNECTACK(sourceport, sourceip, packet)
               # set the connection to established and return
               connection = RxPConnection(packet.sourceip, packet.sourceport, 0, None)
               connection.set_state(RxPConnectionState.ESTABLISHED)
               connection.window_size = window_size
               return connection
               
               
    
    def __receive_packet(self):
        data,addr = self.sock.recvfrom(self.BUFFER_SIZE)
        packet = RxPacket(data)
        self.logger.debug("Received packet: %s" % str(packet))
        return packet
    
    '''Send packet to destination'''
    def __send_packet(self, packet):
        packet.checksum()
        self.logger.debug("Sending packet: %s" % str(packet))
        self.sock.sendto((packet.destinationip, packet.destport))