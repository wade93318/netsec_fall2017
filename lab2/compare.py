import sys, asyncio, playground
from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT, BUFFER, BOOL
from playground.network.packet.fieldtypes.attributes import Optional

class DataPacket(PacketType):
    DEFINITION_IDENTIFIER = "lab1b.gzhang21.DataPacket"
    DEFINITION_VERSION = "1.0"
    
    FIELDS = [
        ("id", UINT({Optional:True})),
        ("data", BUFFER)
    ]

class TokenPacket(PacketType):
    DEFINITION_IDENTIFIER = "lab1b.gzhang21.TokenPacket"
    DEFINITION_VERSION = "1.0"
    
    FIELDS = [("id", UINT)]

class ResultPacket(PacketType):
    DEFINITION_IDENTIFIER = "lab1b.gzhang21.ResultPacket"
    DEFINITION_VERSION = "1.0"
    
    FIELDS = [
        ("id", UINT),
        ("result", BOOL)
    ]

class ServerProtocol(asyncio.Protocol):
    dataDict = {}
    counter = 0
    
    def __init__(self):
        self.transport = None
    
    def connection_made(self, transport):
        self.transport = transport
        self._deserializer = PacketType.Deserializer()
    
    def data_received(self, data):
        self._deserializer.update(data)
        for pkt in self._deserializer.nextPackets():
            if not isinstance(pkt, DataPacket):
                continue
            if isinstance(pkt.id, int):
                same = pkt.data == ServerProtocol.dataDict.pop(pkt.id, None)
                result = ResultPacket(id=pkt.id, result=same)
                self.transport.write(result.__serialize__())
            else:
                ServerProtocol.dataDict[ServerProtocol.counter] = pkt.data
                token = TokenPacket(id=ServerProtocol.counter)
                self.transport.write(token.__serialize__())
                ServerProtocol.counter += 1
                if ServerProtocol.counter == 2**32: ServerProtocol.counter = 0
    
    def connection_lost(self, exc):
        self.transport = None

class ClientProtocol(asyncio.Protocol):
    def __init__(self, packet, callback):
        self.transport = None
        self.packet = packet
        self.callback = callback
    
    def connection_made(self, transport):
        self.transport = transport
        self._deserializer = PacketType.Deserializer()
        transport.write(self.packet.__serialize__())
    
    def data_received(self, data):
        self._deserializer.update(data)
        for pkt in self._deserializer.nextPackets():
            self.callback(pkt.id, getattr(pkt, "result", None))
            self.transport.close()
            break
    
    def connection_lost(self, exc):
        self.transport = None
        if isinstance(exc, TimeoutError):
            print("Connection Timed Out")
            sys.exit(1)

usage = """compare.py is a client/server tool that let two party check if they hold the
same data.

compare server
 - launches server

compare [address] [string]
 > address: server address
 > string: data to compare
 - server will respond with a one-time token

compare [address] [string] [token]
 > address: server address
 > string: data to compare
 > token: one-time token from server
 - server will respond same or not
"""

def main(argv):
    if len(argv) < 2: sys.exit(usage)
    loop = asyncio.get_event_loop()
    
    if argv[1] == "server":
        coro = playground.getConnector("lab2_protocol").create_playground_server(ServerProtocol, 8000)
    else:
        if len(argv) < 3: sys.exit(usage)
        packet = DataPacket(data=argv[2].encode("utf8"))
        if len(argv) > 3: packet.id = int(argv[3])
        
        def callback(token, result):
            if result is None:
                print("Token is {}".format(token))
            else:
                print("Same" if result else "Not same / Not found")
            loop.stop()

        coro = playground.getConnector("lab2_protocol").create_playground_connection(lambda: ClientProtocol(packet, callback), argv[1], 8000)
    
    asyncio.ensure_future(coro)
    loop.run_forever()
    loop.close()

if __name__=="__main__":
    main(sys.argv)
