import logging
import time
from threading import Timer
from packet import RxPacket
from packet import RxPFlags
from select import select

class RxPCommunicator:
    def __init__(self,socket, loglevel=logging.DEBUG):
        self.logger = logging.getLogger("RxPCommunicator")
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
        # the buffer to read from the 
        self.BUFFER_SIZE = 512
        # set packet retry delay to 5 seconds
        self.RETRY_DELAY = 5.0
        # packets waiting to be acked, we keep this to check for resend
        self.waiting_to_be_acked={}
        # keep track of if the RETRY Thread Running 
        self.RETRY_THREAD = False
        # set socket to the passed in socket
        self.sock = socket
        # packet sequence
        self.packet_sequence_number = 0
        # alive status
        self.ALIVE = True

    
    """
    Send a connection SYN ACK To tell the client that we are here and listening
    We are going to ACKnowledge that we received the packet by sending the sequence number
    we received as the ACK number
    
    And tell the client to initialize by ACK our first packet
    
    This is is a private method
    """
    def sendCONNECTSYNACK(self, sourceip, sourceport, packet):
        flags = [RxPFlags.SYN, RxPFlags.ACK]
        ack = packet.sequence
        seq = self.packet_sequence_number
        synack_packet = RxPacket(
            flags=flags, 
            sequence=seq, 
            ack=ack, 
            sourceip=sourceip, 
            destinationip=packet.sourceip,
            sourceport=sourceport,
            destport=packet.sourceport)
        self.logger.debug("Sending SYNACK packet")
        self.send_packet(synack_packet)
        
        
        
    """Send a SYN packet to initiate a connection with the server"""
    def sendCONNECTSYN(self, sourceip, sourceport, destinationip, destport):
        flags = [RxPFlags.SYN]
        seq = self.__get_next_packet_sequence_number()
        syn_packet = RxPacket(
            flags, 
            seq, 
            sourceip=sourceip, 
            destinationip=destinationip,
            sourceport=sourceport,
            destport=destport)
        self.logger.debug("Sending SYN Packet")
        self.send_packet(syn_packet)
        return seq
    
    '''Send a packet to ACKnowledge a SYNACK or FIN packet'''
    def sendACK(self, sourceport, sourceip, packet):
        flags = [RxPFlags.ACK]
        ack_packet = RxPacket(
            flags=flags, 
            sequence=None,
            ack=packet.sequence,
            sourceip=sourceip, 
            destinationip=packet.sourceip,
            sourceport=sourceport,
            destport=packet.sourceport)
        self.logger.debug("Sending ACK packet")
        self.send_packet(ack_packet)
        
    """Send a SYN packet to initiate a connection with the server"""
    def sendCONNECTFIN(self, sourceip, sourceport, destinationip, destport):
        flags = [RxPFlags.FIN]
        seq = self.__get_next_packet_sequence_number()
        fin_packet = RxPacket(
            flags, 
            seq, 
            sourceip=sourceip, 
            destinationip=destinationip,
            sourceport=sourceport,
            destport=destport)
        self.logger.debug("Sending FIN Packet")
        self.send_packet(fin_packet)
        return seq
        
        
    """Send a SYN packet to initiate a connection with the server"""
    def sendDATA(self, sourceip, sourceport, destinationip, destport, data_in_bytes):
        flags = [RxPFlags.DATA]
        seq = self.__get_next_packet_sequence_number()
        data_packet = RxPacket(
            flags, 
            seq, 
            sourceip=sourceip, 
            destinationip=destinationip,
            sourceport=sourceport,
            destport=destport,
            data=data_in_bytes)
        self.logger.debug("Sending DATA Packet")
        self.send_packet(data_packet)
        return seq
    
    def __get_next_packet_sequence_number(self):
        self.packet_sequence_number += 1
        return self.packet_sequence_number
        
    def add_listener(self, key, listener):
        self.listeners[key] = listener
        
    def remove_listener(self, key):
        del self.listeners[key]
    
    def receive_packet(self):
        data,addr = self.sock.recvfrom(self.BUFFER_SIZE)
        packet = RxPacket.deserialize(data)
        self.logger.debug("Received packet: %s" % str(packet))
        '''Check if we have a non corrupt packet'''
        if packet.checksum != RxPacket.calculate_checksum(packet):
            self.logger.error("Corrupt Packet Detected, dropping packet %s", packet)
            return None
        
        # if packet contains an ACK, remove a waiting to be ACK'ed packet from the unacked list
        if RxPFlags.ACK in packet.flags:
            self.logger.debug("Waiting To be acked going to remove %s, these are the current keys: %s" % (packet.ack, self.waiting_to_be_acked.keys()))
            del self.waiting_to_be_acked[packet.ack]
        
        return packet
    
    '''Send packet to destination'''
    def send_packet(self, packet):
        packet.checksum = RxPacket.calculate_checksum(packet)
        self.logger.debug("Sending packet to %s at port %s: " % (packet.destinationip, packet.destport))
        # set the packet send time
        packet.sent_time = time.time()
        # if the packet needs to be acked then it has to be added to the waiting to be acked list
        if any(flag in [RxPFlags.SYN, RxPFlags.FIN, RxPFlags.DATA] for flag in packet.flags):
            self.waiting_to_be_acked[packet.sequence] = packet
            # if the RETRY Thread is not running, kick it off
            if not self.RETRY_THREAD:
                t = Timer(self.RETRY_DELAY, self.resend_unacked_packets)
                t.setDaemon(True)
                t.start()
                self.RETRY_THREAD = True
        # Send packet over UDP
        self.sock.sendto(RxPacket.serialize(packet), (packet.destinationip, packet.destport))
        self.logger.debug("Sent Packet, returning to calling function")
    
    # Check every time period to see if there are unacked packets to be sent
    def resend_unacked_packets(self):
        if self.waiting_to_be_acked:
            self.logger.debug("This is how many packets are waiting for acks: %s" % len(self.waiting_to_be_acked.keys()))
            # loop through the unacked packets and resend them
            for unacked_packet in self.waiting_to_be_acked:
                self.logger.debug("This is the sequence of the current unacked packet %s" % unacked_packet)
                elapsed_time = time.time() - self.waiting_to_be_acked[unacked_packet].sent_time 
                if elapsed_time > self.RETRY_DELAY:
                    self.send_packet(self.waiting_to_be_acked[unacked_packet])
            # tell the retry thread to try again after delay, we have to keep retrying till the acked packets are done
            t = Timer(self.RETRY_DELAY, self.resend_unacked_packets)
            t.setDaemon(True)
            t.start()
            self.RETRY_THREAD = True
        else:
            self.logger.debug("There are no packets waiting to be acked, killing RETRY THREAD")
            self.RETRY_THREAD = False