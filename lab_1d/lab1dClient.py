import playground
from playground.network.common import StackingProtocol,StackingProtocolFactory,StackingTransport
from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT32, STRING, BUFFER, BOOL,ListFieldType
import asyncio

class RequestProblem(PacketType):
    DEFINITION_IDENTIFIER = 'lab1e.student_ZeweiLi.fromclient1'
    DEFINITION_VERSION = '1.0'

    FIELDS = [
        ('id', UINT32),
        ('question', STRING)
    ]
class Receivedinfo(PacketType):
    DEFINITION_IDENTIFIER = 'lab1e.student_ZeweiLi.fromclient2'
    DEFINITION_VERSION = '1.0'

    FIELDS = [
        ('id',UINT32),
        ('validity',STRING)
    ]

class Answer(PacketType):
    DEFINITION_IDENTIFIER = 'lab1e.student_ZeweiLi.fromserver'
    DEFINITION_VERSION = '1.0'

    FIELDS = [
        ('id', UINT32),
        ('Date',STRING),
    ]

class EchoClient(asyncio.Protocol):

    def __init__(self,loop):
        self.loop = loop
        self.transport = None
        self.deserializer = PacketType.Deserializer()

    def connection_made(self, transport):
        self.transport = transport
        packet1 = RequestProblem()
        packet1.id = 1
        packet1.question = 'What is the current date'
        packet1Bytes = packet1.__serialize__()
        print("Connected to {}".format(transport.get_extra_info("peername")))
        self.transport.write(packet1Bytes)
        print('Data sending packet1 to server.........')

    def data_received(self, data):
        self.deserializer.update(data)
        while self.deserializer.nextPackets():
            for pkt in self.deserializer.nextPackets():
                if isinstance(pkt,Answer):
                    print('This is the answer from server:'+ pkt.Date)
                    packet3 = Receivedinfo()
                    packet3.id = 3
                    packet3.validity = 'I have already known the date from server'
                    packet3Bytes = packet3.__serialize__()
                    self.transport.write(packet3Bytes)
                    print('Data sending packet3 to server.........')
                else:
                    print('Data not received from server!')
    def connection_lost(self, exc):
        print('The server closed the connection')
        print('Stop the event loop')
        self.transport = None
        self.loop.stop()

if __name__ == '__main__':

    loop = asyncio.get_event_loop()
    loop.set_debug(enabled = True)
    print("Echo Client Connected. Starting........")

    coro = playground.getConnector().create_playground_connection(lambda :EchoClient(loop),'20174.1.1.3',8080)
    loop.run_until_complete(coro)

    loop.run_forever()
    loop.close()


