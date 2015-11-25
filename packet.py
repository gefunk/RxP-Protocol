from enum import Enum, unique
import pickle
import hashlib

'''
Class representing the different FLAGS that can be set on a FLAG
'''
@unique
class RxPFlags(Enum):
    SYN = 'SYN'
    ACK = 'ACK'
    NACK = 'NACK'
    FIN = 'FIN'
    DATA = 'DATA'

'''
Class representing the different states that the packet can be in
'''
@unique
class RxPPacketState(Enum):
    NOT_SENT = 1
    SENT_WAITING_FOR_ACK = 2
    RECEIVED_ACK = 3


class RxPacket:
    def __init__(self, flags, sequence, ack=None, data=None, sourceip=None, destinationip=None, sourceport=None, destport=None, checksum=None):
        '''List of packet flags, describing the type of packet'''
        self.flags = flags
        '''Sequence Numbers'''
        self.sequence = sequence
        '''Acknowledgement Number'''
        self.ack = ack
        '''The data being sent if any in this packet'''
        self.data = data
        '''The source IP of this packet'''
        self.sourceip = sourceip
        '''The destination IP of this packet'''
        self.destinationip = destinationip
        '''The source port of this packet'''
        self.sourceport = sourceport
        '''The destination port of this packet'''
        self.destport = destport
        '''Checksum'''
        self.checksum = checksum
        '''Current state packet is in'''
        self.state = RxPPacketState.NOT_SENT
        '''The time this packet was sent'''
        self.sent_time = None
        
    
    """String representation of this packet"""
    def __str__(self):
        return "flags: %s, sequence %s, ack %s, sourceip:port: %s:%s, destinationip:port: %s:%s" % (self.flags,self.sequence, self.ack, self.sourceip, self.sourceport, self.destinationip, self.destport)
            
    '''Serialize packet to bytes'''
    @staticmethod
    def serialize(packet):
        return pickle.dumps(packet)
    
    '''deserialize from bytes to object'''
    @staticmethod
    def deserialize(packet):
        return pickle.loads(packet)
    
    # Calculate checksum
    @staticmethod
    def calculate_checksum(packet):
        m = hashlib.md5()
        # add all the flags to the checksum
        for flag in packet.flags:
            m.update(flag.name.encode('utf-8'))
        if packet.sequence:
            m.update(str(packet.sequence).encode('utf-8'))
        if packet.ack:
            m.update(str(packet.ack).encode('utf-8'))
        if packet.data:
            m.update(packet.data)
        if packet.sourceip:
            m.update(packet.sourceip.encode('utf-8'))
        if packet.sourceport:
            m.update(str(packet.sourceport).encode('utf-8'))
        if packet.destinationip:
            m.update(packet.destinationip.encode('utf-8'))
        if packet.destport:
            m.update(str(packet.destport).encode('utf-8'))
        return m.digest()
        
        
        
