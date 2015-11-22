from enum import Enum

@unique
class RxPFlags(Enum):
    SYN = 'SYN'
    ACK = 'ACK'



class RxPacket:
    def __init__(self, flags, sequence, ack=None, data=None, sourceip=None, destintationip=None, sourceport=None, destport=None, checksum=None):
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
        
    '''Convert udp datagram to rxp packet'''
    @classmethod
    def from_udp_to_packet(cls, udppacket):
        return cls(
            udppacket.flags,
            udppacket.sequence, 
            udppacket.ack, 
            udppacket.data, 
            udppacket.sourceip, 
            updpacket.destinationip,
            udppacket.sourceport,
            udppacket.destport,
            udppacket.checksum)
    
    # Calculate checksum
    @staticmethod
    def calculate_checksum(packet):
        pass
        
        
