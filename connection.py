from enum import Enum, unique
import logging
from packet import RxPacket,RxPFlags
from threading import Timer, Thread
import traceback
from select import select

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

class RxPConnectionSendException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

"""Represents an active connection - a virtual circuit"""
class RxPConnection(Thread):
    def __init__(self, name, sourceip, sourceport, destinationip, destinationport, sequence, ack, communicator, loglevel=logging.DEBUG, window_size=1):
        # Initialize Super class
        super().__init__()
        # set the name of this process
        self.name = name
        # Initialize Logger
        self.logger = logging.getLogger("RxPConnection: %s" % self.name)
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
        '''Set Window Size'''
        self.set_window_size(window_size)
        self.logger.debug("Initialzied Send Window to Window Size: %s" % self.send_window)
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
        self.logger.debug("Started Connection Process: %s" % self.name)
        self.state = (RxPConnectionState.ESTABLISHED)
        while self.state is not RxPConnectionState.CLOSED and self.communicator is not None:
            self.logger.debug("Running Connection")
            packet = self.communicator.receive_packet()
            self.logger.debug("Run Method received packet %s, handing off to packet handler thread" % packet)
            t = Thread(target=self.__handle_incoming_packets, args=(packet,))
            t.setDaemon(True)
            t.start()
        self.logger.info("Ended Connection Run: %s" % self.name)
    
    
    def __handle_incoming_packets(self, packet):
        self.logger.debug("Handling incoming packet: %s" % packet)
        # If it is an ACK packet then remove the acknowledged packet from the send window
        if RxPFlags.ACK in packet.flags:
            self.__handle_ack_packet(packet)
        elif RxPFlags.FIN in packet.flags:
            self.__handle_fin_received(packet)
        elif RxPFlags.DATA in packet.flags:
            self.logger.debug("Received DATA in connection %s" % packet.sequence)
            # append received 
            self.receive_buffer.extend(packet.data)
            self.logger.debug("Receive Buffer Size : %s" % len(self.receive_buffer))
            # send ACKnowledgement
            self.communicator.sendACK(self.sourceport, self.sourceip, packet)
    

    def __handle_ack_packet(self, packet):
        if self.state == RxPConnectionState.ESTABLISHED:
            self.__remove_acked_from_send_window(packet.ack)
        elif self.state == RxPConnectionState.FIN_WAIT_1:
            self.state == RxPConnectionState.FIN_WAIT_2
            t = Timer(self.FIN_WAIT_2_TIMEOUT, self.__handle_close_timeouts, [self.state])
            t.start()
        elif self.state == RxPConnectionState.CLOSING:
            self.destroy()
            

    def __handle_fin_received(self, packet):
        self.logger.debug("Recieved FIN")
        # Check if we are in the Active close flow in FIN_WAIT_1
        if self.state == RxPConnectionState.FIN_WAIT_1:
            self.communicator.sendACK(self.sourceport, self.sourceip, packet)
            self.state == RxPConnectionState.CLOSING
            t = Timer(self.CLOSING_TIMEOUT, self.__handle_close_timeouts, [self.state])
            t.start()
        elif self.state == RxPConnectionState.FIN_WAIT_2:
            self.communicator.sendACK(self.sourceport, self.sourceip, packet)
            self.state == RxPConnectionState.CLOSED
            self.destroy()
        elif self.state == RxPConnectionState.ESTABLISHED:
            self.communicator.sendACK(self.sourceport, self.sourceip, packet)
            # we are going to the passive close flow
            self.state = RxPConnectionState.CLOSE_WAIT
            self.close()

    """
    Read data from the connection buffer
    """            
    def receive(self, buffer_size):
        data_to_return = None
        while data_to_return is None and self.state is RxPConnectionState.ESTABLISHED:
            if len(self.receive_buffer) > 0:
                self.logger.debug("Should be sending back to user data: %s" % self.receive_buffer)
                data_to_return = self.receive_buffer[0:buffer_size]
                if len(self.receive_buffer) > buffer_size:
                    self.receive_buffer = self.receive_buffer[buffer_size:]
                else:
                    self.receive_buffer = bytearray()
        return data_to_return
    
    """Send data to the other side"""
    def send(self, command, data=None):
        try:
            if self.state is not RxPConnectionState.ESTABLISHED:
                raise RxPConnectionSendException("Connection state is not established it is: %s" % self.state)
            command_bytes = bytearray(command+"|SEPARATOR|", 'utf-8')
            self.data_to_be_sent = command_bytes
            self.data_to_be_sent_last_pointer = 0
            # append data to command if not null
            self.logger.debug("File Data: "+str(data))
            if data:
                self.data_to_be_sent.extend(data)
            self.__fill_send_window()
        except RxPConnectionSendException as e: 
            self.logger.error("Connection Send exception: %s" % e)
            
        
    """Remove ack'ed packets from send window"""    
    def __remove_acked_from_send_window(self, sequence):
        self.logger.debug("Removing ACK'ed from Send window: %s " % self.send_window)
        for index, packet_sequence in enumerate(self.send_window):
            if packet_sequence == sequence:
                self.logger.debug("Removing from Send Window Packet with Sequence: %s" % packet_sequence)
                self.send_window[index] = None
        # fill the window with additional packets
        self.__fill_send_window()
        
           
    """Fill empty slots in the send window with additional packets"""
    def __fill_send_window(self):
        for window_slot, value in enumerate(self.send_window):
            if self.send_window[window_slot] == None:
                data_in_bytes = self.__get_next_datagram()
                if data_in_bytes:
                    # send the packet, and record the sequence number in the send window
                    packet_sequence = self.communicator.sendDATA(self.sourceip, self.sourceport, self.destinationip, self.destinationport, data_in_bytes)
                    self.logger.debug("Fill Send Window Slot: %s Sent Packet with Sequence: %s and data: %s" % (window_slot,packet_sequence, data_in_bytes))
                    self.send_window[window_slot] = packet_sequence
                else:
                    self.logger.debug("No More data to send")
        self.logger.debug("Filled Send Window to: %s" % str(self.send_window))
    
    """Split data to send into buffer size byte data grams"""
    def __get_next_datagram(self):
        data_in_bytes = None
        self.logger.debug("Data To be Sent Last Pointer: %s, Length of Data: %s" % (self.data_to_be_sent_last_pointer, len(self.data_to_be_sent)))
        if self.data_to_be_sent_last_pointer < len(self.data_to_be_sent):
            end_index = self.data_to_be_sent_last_pointer+self.send_buffer_size
            self.logger.debug("End Index: %s " % end_index)
            data_in_bytes = self.data_to_be_sent[self.data_to_be_sent_last_pointer : end_index]
            self.logger.debug("Data in bytes: %s, Data Indices: [%s : %s]" % (data_in_bytes, self.data_to_be_sent_last_pointer, end_index))
            # advance data pointer to next point in data stream
            self.data_to_be_sent_last_pointer = end_index
        return data_in_bytes
    
        
    """Close the connection"""
    def close(self):
        # Check if we are in established, if we are send FIN
        if self.state == RxPConnectionState.ESTABLISHED:
            self.logger.debug("Sending FIN packet to close connection")
            sequence_number = self.communicator.sendCONNECTFIN(self.sourceip, self.sourceport, self.destinationip, self.destinationport)
            self.state = RxPConnectionState.FIN_WAIT_1
            t = Timer(self.FIN_WAIT_1_TIMEOUT, self.__handle_close_timeouts, [self.state, sequence_number])
            t.start()
        # First check if we are in the passive close flow
        elif self.state == RxPConnectionState.CLOSE_WAIT:
            self.logger.debug("Sending FIN packet to close connection")
            sequence_number = self.communicator.sendCONNECTFIN(self.sourceip, self.sourceport, self.destinationip, self.destinationport)
            self.state = RxPConnectionState.LAST_ACK
            t = Timer(self.LAST_ACK_TIMEOUT, self.__handle_close_timeouts, [self.state, sequence_number])
            t.start()
        

        
    # destroy any resources with this connection    
    def destroy(self):
        self.logger.debug("Destroying Connection")
        self.state = RxPConnectionState.CLOSED
        self.receive_buffer = None
        self.send_window = None
        self.communicator = None
        return None
            
    
    """Function to handle any close state timeouts"""
    def __handle_close_timeouts(self, state, sequence=None):
        # If the state has changed since we were waiting for an ACK
        # ANd we are still not waiting for the FIN packet to be ACk'ed
        if sequence and sequence not in self.communicator.waiting_to_be_acked and self.state is not state:
            return None
        else:
            self.logger.debug("Close timeout in State: %s for Packet Sequence: %s" % (state, sequence))
            self.destroy()
            
    """Set the Send Window Size"""
    def set_window_size(self, window_size):
        self.window_size = window_size
        self.send_window = []
        for i in range(0, self.window_size):
            self.send_window.append(None)
    