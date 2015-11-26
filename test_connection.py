import unittest
import logging
from connection import RxPConnection, RxPConnectionState


class DummyCommunicator:
    def __init__(self):
        self.packet_sequence = 0


    def sendDATA(self, sourceip, sourceport, destinationip, destport, data_in_bytes):
        print ("Dummy Communicator: %s" % data_in_bytes)
        self.packet_sequence += 1
        return self.packet_sequence

    def sendACK(self, ip, port, packet):
        print ("Dummy Communicator ACK: %s" % packet['ack'])

    def sendCONNECTFIN(self,sourceip, sourceport, destinationip, destport):
        print ("Dummy Communicator CONNECT FIN")
        self.packet_sequence += 1
        return self.packet_sequence


class TestConnection(unittest.TestCase):
    
    def setUp(self):
        communicator = DummyCommunicator()
        connection_key = "TestConnection"
        sourceip = "127.0.0.1"
        sourceport = 50002
        destinationip = "127.0.0.1"
        destinationport = 50002
        self.connection =  RxPConnection("Connection to: "+connection_key,sourceip, sourceport, destinationip, destinationport, 0, None, communicator, logging.DEBUG, 10)

    """Test splitting data into datagrams"""
    def test__get_next_datagram(self):
        self.connection.data_to_be_sent = bytearray("hello my friend! guy", 'utf-8')
        self.connection.data_to_be_sent_last_pointer = 0
        self.assertEqual(self.connection._RxPConnection__get_next_datagram(), self.connection.data_to_be_sent[0:8])
        self.assertEqual(self.connection._RxPConnection__get_next_datagram(), self.connection.data_to_be_sent[8:16])
        self.assertEqual(self.connection._RxPConnection__get_next_datagram(), self.connection.data_to_be_sent[16:24])
        self.assertEqual(self.connection._RxPConnection__get_next_datagram(), None)


    """Test sending back data to clients"""
    def test_receive_buffer(self):
        test_data = bytearray("hello my friend! guy", 'utf-8')
        self.connection.receive_buffer = test_data
        self.assertEqual(test_data[0:8],self.connection.receive(8))
        self.assertEqual(test_data[8:16],self.connection.receive(8))
        self.assertEqual(test_data[16:24],self.connection.receive(8))
        # this will block till we have data
        #self.assertEqual(None,self.connection.receive(8))

    """Test Send window logic"""
    def test_send_window(self):
        self.assertEqual(self.connection.window_size, 10)
        self.assertEqual(len(self.connection.send_window), 10)
        self.connection.send_buffer_size = 1
        self.connection.data_to_be_sent = bytearray("0123456789", 'utf-8')
        self.connection.data_to_be_sent_last_pointer = 0
        self.connection._RxPConnection__fill_send_window()
        self.assertEqual([1,2,3,4,5,6,7,8,9,10], self.connection.send_window)


    """Test Removing Ack from Send Window Logic"""
    def test_removing_ack_from_send_window(self):
        self.assertEqual(self.connection.window_size, 10)
        self.assertEqual(len(self.connection.send_window), 10)
        self.connection.send_buffer_size = 1
        self.connection.data_to_be_sent = bytearray("0123456789", 'utf-8')
        self.connection.data_to_be_sent_last_pointer = 0
        self.connection._RxPConnection__fill_send_window()
        for sequence in range(1,10):
            self.connection._RxPConnection__remove_acked_from_send_window(sequence)
            self.assertNotIn(sequence,self.connection.send_window)


    def test_active_close(self):
        self.connection.state = RxPConnectionState.ESTABLISHED
        self.connection.close()
        # test active flow
        self.assertEqual(RxPConnectionState.FIN_WAIT_1, self.connection.state)

    def test_passive_close(self):
        self.connection.state = RxPConnectionState.CLOSE_WAIT
        self.connection.close()
        # test active flow
        self.assertEqual(RxPConnectionState.LAST_ACK, self.connection.state)

    def test_fin_received_active(self):
        test_packet = {'ack': 1}
        self.connection.state = RxPConnectionState.FIN_WAIT_1
        self.connection._RxPConnection__handle_fin_received(test_packet)
        self.assertEqual(RxPConnectionState.CLOSING, self.connection.state)


if __name__ == '__main__':
    unittest.main()