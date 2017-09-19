import playground
from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT32, STRING, BUFFER, BOOL,ListFieldType
from playground.network.common import StackingProtocol,StackingProtocolFactory,StackingTransport
import asyncio
import time

class Answer(PacketType):
    DEFINITION_IDENTIFIER = 'lab1e.student_ZeweiLi.fromserver'
    DEFINITION_VERSION = '1.0'

    FIELDS = [
        ('id', UINT32),
        ('Date',STRING),
        ]
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

class EchoServerProtocol(asyncio.Protocol):
    cont = 0

    def __init__(self):
        self.deserializer = PacketType.Deserializer()
        self.transport = None

    def connection_made(self, transport):
        print("Received a connection from {}".format(transport.get_extra_info("peername")))
        self.transport = transport

    def data_received(self, data):
        EchoServerProtocol.cont = EchoServerProtocol.cont + 1
        print('Data received:' + str(EchoServerProtocol.cont) + 'th packet from client')
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            if isinstance(pkt,RequestProblem):
                print('The question from client is :' + pkt.question)
                packet2 = Answer()
                packet2.id = 2
                packet2.Date = time.asctime(time.localtime(time.time()))
                self.transport.write(packet2.__serialize__())
            elif isinstance(pkt,Receivedinfo):
                print('This ia the packet id :'+ str(pkt.validity))
                print('Communication has finished!')
                self.transport.close()
            else:
                print('Data not received from client')

    def connection_lost(self, exc):
        print("Lost connection to client. Cleaning up.")

class Passthrough1(StackingProtocol):
    def __init__(self):
        super(Passthrough1,self).__init__()
        self.transport = None
    def connection_made(self, transport):
        print('passthrough1')
        self.transport = transport
        higherTransport1 = StackingTransport(self.transport)
        try:
            self.higherProtocol().connection_made(higherTransport1)
        except Exception as e:
            print('failed', e)

    def data_received(self, data):
        self.higherProtocol().data_received(data)

class Passthrough2(StackingProtocol):
    def __init__(self):
        super(Passthrough2,self).__init__()
        self.transport = None

    def connection_made(self, transport):
        print('passthrough2')
        self.transport = transport
        higherTransport2 = StackingTransport(self.transport)
        self.higherProtocol().connection_made(higherTransport2)

    def data_received(self, data):
        self.higherProtocol().data_received(data)

if __name__ == '__main__':

    loop = asyncio.get_event_loop()
    loop.set_debug(enabled = True)

    f = StackingProtocolFactory(lambda :Passthrough1(), lambda : Passthrough2())
    ptConnector = playground.Connector(protocolStack=f)
    playground.setConnector('passthrough',ptConnector)

    coro = playground.getConnector('passthrough').create_playground_server(lambda : EchoServerProtocol(), 8080)
    server = loop.run_until_complete(coro)
    print("Echo Server Started at {}".format(server.sockets[0].gethostname()))

    loop.run_forever()
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()

