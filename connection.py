from enum import Enum, unique
import logging
from packet import RxPacket,RxPFlags
from threading import Timer
from multiprocessing import Process
import traceback

""" Enum representing the different states a connection can be in"""
@unique
class RxPConnectionState(Enum):
    INITIATED = 1
    ESTABLISHED = 2
    FIN_WAIT_1=3
    FIN_WAIT_2=4
    CLOSING=6
    CLOSE_WAIT=7
    LAST_ACK=8
    CLOSED=5

"""Represents an active connection - a virtual circuit"""
class RxPConnection(Process):
    def __init__(self, sourceip, sourceport, destinationip, destinationport, sequence, ack, communicator, loglevel=logging.DEBUG, window_size=1):
        # Initialize Super class
        super().__init__()
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
        # Source IP and port for the connection
        self.sourceip = sourceip
        self.sourceport = sourceport
        # The destination port where this connection is connected to
        self.destinationip = destinationip
        self.destinationport = destinationport
        
        self.state = RxPConnectionState.INITIATED
        '''The sequence number to use for the next packet'''
        self.last_seq = sequence
        '''Last Acknowledgement number'''
        self.last_ack = ack
        self.window_size = window_size
        self.send_window = []
        for i in range(0, self.window_size):
            self.send_window.append(None)
        self.send_window_data = {}
        self.communicator = communicator
        # Timeouts for the different states during close
        self.CLOSING_TIMEOUT = 10.0
        self.FIN_WAIT_1_TIMEOUT = 10.0
        self.FIN_WAIT_2_TIMEOUT = 10.0
        self.LAST_ACK_TIMEOUT = 10.0
        #
        self.send_buffer_size = 8
        self.data_to_be_sent = None
        self.data_to_be_sent_last_pointer = None
        #
        self.receive_buffer = bytearray()
        
    """
    This method is called to set the connection to an established state
    and to start off the connection in a separate process
    """
    def run(self):
        self.logger.debug("Started Connection Process")
        print (traceback.extract_stack())
        self.state = (RxPConnectionState.ESTABLISHED)
        while True:
            packet = self.communicator.receive_packet()
            # If it is an ACK packet then remove the acknowledged packet from the send window
            if RxPFlags.ACK in packet.flags:
                self.__remove_acked_from_send_window(packet.ack)
            elif RxPFlags.DATA in packet.flags:
                self.logger.debug("Received DATA in connection %s" % packet.sequence)
                # append received 
                self.receive_buffer.extend(packet.data)
                self.logger.debug("Receive Buffer Size : %s" % len(self.receive_buffer))
                # send ACKnowledgement
                self.communicator.sendACK(self.sourceport, self.sourceip, packet)
    
    """
    Read data from the connection buffer
    """            
    def receive(self, buffer_size):
        data_to_return = None
        while data_to_return is None:
            if len(self.receive_buffer) > 0:
                self.logger.debug("Should be sending back to user")
                if len(self.receive_buffer) > buffer_size:
                    self.receive_buffer = self.receive_buffer[buffer_size:]
                else:
                    self.receive_buffer = bytearray()
                data_to_return = self.receive_buffer[0:buffer_size]
        return data_to_return
    
    """Send data to the other side"""
    def send(self, command, data=None):
        command_bytes = bytearray(command, 'utf-8')
        self.data_to_be_sent = command_bytes
        self.data_to_be_sent_last_pointer = 0
        # append data to command if not null
        if data:
            self.data_to_be_sent += data
        self.__fill_send_window()
            
        
    """Remove ack'ed packets from send window"""    
    def __remove_acked_from_send_window(self, sequence):
        for index, packet_sequence in self.send_window:
            if packet_sequence == sequence:
                self.logger.debug("Removing from Send Window Packet with Sequence: %s" % packet_sequence)
                self.send_window[index] = None
        # move the send window to make space for additional packets
        self.__advance_send_window(0)
        # fill the window with additional packets
        self.__fill_send_window()
        
    """Advance the send window"""
    def __advance_send_window(self, index):
        # remove all preceding empty spaces from the send window 
        if index < self.window_size and self.send_window[index] == None:
            del self.send_window[index]
            self.__advance_send_window[index+1]
        self.logger.debug("Advanced Send Window to: %s" % str(self.send_window))
            
    """Fill empty slots in the send window with additional packets"""
    def __fill_send_window(self):
        for window_slot in range(0, self.window_size):
            if self.send_window[window_slot] == None:
                data_in_bytes = self.__get_next_datagram()
                # send the packet, and record the sequence number in the send window
                packet_sequence = self.communicator.sendDATA(self.sourceip, self.sourceport, self.destinationip, self.destinationport, data_in_bytes)
                self.logger.debug("Fill Send Window Slot: %s Sent Packet with Sequence: %s" % (window_slot,packet_sequence))
                self.send_window[window_slot] = packet_sequence
        self.logger.debug("Filled Send Window to: %s" % str(self.send_window))
    
    """Split data to send into buffer size byte data grams"""
    def __get_next_datagram(self):
        data_in_bytes = None
        if self.data_to_be_sent and self.data_to_be_sent_last_pointer <= (len(self.data_to_be_sent)):
            data_buffer_width = self.data_to_be_sent_last_pointer + self.send_buffer_size;
            if data_buffer_width >= (len(self.data_to_be_sent)):
                data_buffer_width = len(self.data_to_be_sent)
            data_in_bytes = self.data_to_be_sent[self.data_to_be_sent_last_pointer+1 : data_buffer_width]
        return data_in_bytes
    
        
    """Close the connection"""
    def close(self):
        self.logger.debug("Sending FIN packet to close connection")
        sequence_number = self.sendCONNECTFIN(self, sourceip, sourceport, destinationip, destport)
        # First check if we are in the passive close flow
        if self.state == RxPConnectionState.CLOSE_WAIT:
            self.state = RxPConnectionState.LAST_ACK
            t = Timer(self.LAST_ACK_TIMEOUT, self.handle_close_timeouts, [self.state, sequence_number])
            t.start()
        else:
            # Otherwise we are going to do the Active Close Flow
            self.state = RxPConnectionState.FIN_WAIT_1
            t = Timer(self.FIN_WAIT_1_TIMEOUT, self.handle_close_timeouts, [self.state, sequence_number])
            t.start()
        
    def fin_received(self, packet):
        self.logger.debug("Recieved FIN")
        # ACK the FIN
        self.communicator.sendCONNECTACK(self.port, self.ip, packet)
        # Check if we are in the Active close flow in FIN_WAIT_1
        if self.state == RxPConnectionState.FIN_WAIT_1:
            self.state == RxPConnectionState.CLOSING
        else:
            # we are going to the passive close flow
            self.state = RxPConnectionState.CLOSE_WAIT
            self.close()
        
    # destroy any resources with this connection    
    def destroy(self):
        self.logger.debug("Destroying Connection")
        return None
            
    
    """Function to handle any close state timeouts"""
    def handle_close_timeouts(self, state, sequence):
        if self.communicator.waiting_to_be_acked[sequence] and self.state == state:
            self.logger.debug("Close timeout in State: %s for Packet Sequence: %s", (state, sequence))
            self.state = RxPConnectionState.CLOSED
            self.destroy()
            
        
    
    