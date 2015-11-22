from enum import Enum

""" Enum representing the different states a connection can be in"""
@unique
class RxPConnectionState(Enum):
    INITIATED = 1
    ESTABLISHED = 2



"""Represents an active connection - a virtual circuit"""
class RxPConnection:
    def __init__(self, ip, port, sequence, ack, loglevel=logging.DEBUG):
        self.ip = ip
        self.port = port
        self.state = RxPConnectionState.INITIATED
        '''The sequence number to use for the next packet'''
        self.last_seq = sequence
        '''Last Acknowledgement number'''
        self.last_ack = ack
        self.window_size = 1
        
    def set_state(self, state):
        self.state = state
        
    
    
    