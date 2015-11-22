from enum import Enum, unique
import logging

""" Enum representing the different states a connection can be in"""
@unique
class RxPConnectionState(Enum):
    INITIATED = 1
    ESTABLISHED = 2



"""Represents an active connection - a virtual circuit"""
class RxPConnection:
    def __init__(self, ip, port, sequence, ack, loglevel=logging.DEBUG):
        # Initialize Logger
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
        
        
    
    