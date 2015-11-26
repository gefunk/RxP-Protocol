import unittest
import logging
from packet import RxPacket, RxPFlags
from communicator import RxPCommunicator

class TestPacket(RxPacket):
    def __init__(self, flags, sequence, ack=None, data=None, sourceip=None, destinationip=None, sourceport=None, destport=None, checksum=None):
        super().__init__(flags, sequence, ack, data, sourceip, destinationip, sourceport, destport, checksum)

"""dummy socket object to emulate udp socket"""
class DummySocket:

    def __init__(self, test_packet):
        self.test_packet = test_packet

    def recvfrom(self,buffer_size):
        return (self.test_packet, "127.0.0.1")

    def sendto(self, data, tuple):
        print ("Send To: "+data)



class TestCommunicator(unittest.TestCase):

    def setUp(self):
        self.communicator = RxPCommunicator(DummySocket(None))

    def test_corrupt_receive_packet(self):
        test_packet = TestPacket([RxPFlags.DATA], 10, data=bytearray("Hello", 'utf-8'))
        test_packet.checksum = 1233445
        self.communicator.sock.test_packet = RxPacket.serialize(test_packet)
        self.assertIsNone(self.communicator.receive_packet())

    def test_receive_packet(self):
        test_packet = TestPacket([RxPFlags.DATA], 10, data=bytearray("Hello", 'utf-8'))
        test_packet.checksum = RxPacket.calculate_checksum(test_packet)
        self.communicator.sock.test_packet = RxPacket.serialize(test_packet)
        self.assertIsNotNone(self.communicator.receive_packet())



if __name__ == '__main__':
    unittest.main()
