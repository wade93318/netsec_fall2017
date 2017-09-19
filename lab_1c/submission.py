from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT32, STRING, BUFFER, BOOL,ListFieldType
from playground.asyncio_lib.testing import TestLoopEx
from playground.network.testing import MockTransportToStorageStream
from playground.network.testing import MockTransportToProtocol
import asyncio
import time

class RequestProblem(PacketType):

    DEFINITION_IDENTIFIER = 'lab1b.student_ZeweiLi_packet1.fromclient'
    DEFINITION_VERSION = '1.0'

    FIELDS = [
        ('id', UINT32),
        ('info',STRING)
    ]
class Receivedinfo(PacketType):
    DEFINITION_IDENTIFIER = 'lab1b.student_ZeweiLi_packet3.fromclient'
    DEFINITION_VERSION = '1.0'

    FIELDS = [
        ('id',UINT32),
        ('validity',STRING)
    ]

class Answer(PacketType):
    DEFINITION_IDENTIFIER = 'lab1b.student_ZeweiLi.fromserver'
    DEFINITION_VERSION = '1.0'

    FIELDS = [
            ('id', UINT32),
            ('Date',STRING),
        ]

class EchoServerProtocol(asyncio.Protocol):

    def __init__(self):
        self.packet2 = Answer()
        self.transport = None
        self._deserializer = None

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('Connection from {}'.format('client'))
        self.transport = transport
        self._deserializer = PacketType.Deserializer()

    def data_received(self, data):
        self._deserializer.update(data)
        for pkt in self._deserializer.nextPackets():
            if isinstance(pkt,RequestProblem):
                print('Packet:{}----->Msg:{} from client'.format(pkt.id,pkt.info))
                self.packet2.id = 2
                self.packet2.Date = time.asctime(time.localtime(time.time()))
                self.packet2 = self.packet2.__serialize__()
                self.transport.write(self.packet2)
            elif isinstance(pkt,Receivedinfo):
                print('Packet:{}----->Msg:{} from client'.format(pkt.id,pkt.validity))
                print('Service Finished')

    def connection_lost(self, exc):
        self.transport = None

class EchoClientProtocol(asyncio.Protocol):
    def __init__(self, packet):
        self.packet = packet
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        self.packet = self.packet.__serialize__()
        self._deserializer = PacketType.Deserializer()
        self.transport.write(self.packet)

    def data_received(self, data):
        print('Data received from Server!')
        self._deserializer.update(data)
        for pkt in self._deserializer.nextPackets():
            if isinstance(pkt,Answer):
                print(pkt.Date)
                self.packet3 = Receivedinfo()
                self.packet3.id = 3
                self.packet3.validity = 'Client has known current date!'
                self.packet3 = self.packet3.__serialize__()
                self.transport.write(self.packet3)
            else:
                print('Not Data received from server!')

    def connection_lost(self, exc):
        print('The server closed the connection')
        print('Stop the event loop')
        self.transport.close()

def basicUnitTest():
    asyncio.set_event_loop(TestLoopEx())
    packet1 = RequestProblem()
    packet1.id = 1
    packet1.info = 'Request Current Date'

    server = EchoServerProtocol()
    client = EchoClientProtocol(packet1)

    transportToServer = MockTransportToProtocol(server)
    transportToClient = MockTransportToProtocol(client)


    server.connection_made(transportToClient)
    client.connection_made(transportToServer)

if __name__ == '__main__':
    basicUnitTest()
