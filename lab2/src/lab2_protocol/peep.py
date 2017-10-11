import asyncio, enum, functools, heapq, os, struct, zlib
from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT8, UINT16, UINT32, BUFFER
from playground.network.packet.fieldtypes.attributes import Optional
from playground.network.common import StackingProtocol, StackingTransport

class PEEPPacketType(enum.Enum):
    SYN = 0
    SYNACK = 1
    ACK = 2
    RIP = 3
    RIPACK = 4

def uint32OverflowAdd(lhs, rhs):
    return (lhs + rhs) % (1<<32)

def uint32CircularLessThan(lhs, rhs):
    if lhs >= (1<<32) - (1<<30) and rhs < 1<<30:
        return True
    return lhs < rhs

@functools.total_ordering
class PEEPPacket(PacketType):
    DEFINITION_IDENTIFIER = "PEEP.Packet"
    DEFINITION_VERSION = "1.0"
    
    FIELDS = [
        ("Type", UINT8),
        ("SequenceNumber", UINT32({Optional: True})),
        ("Checksum", UINT16),
        ("Acknowledgement", UINT32({Optional: True})),
        ("Data", BUFFER({Optional: True}))
    ]
    
    MAXIMUM_DATA_SIZE = 1024
    
    def calculateChecksum(self):
        oldChecksum = self.Checksum
        self.Checksum = 0
        bytes = self.__serialize__()
        self.Checksum = oldChecksum
        return zlib.adler32(bytes) & 0xffff
    
    def updateChecksum(self):
        self.Checksum = self.calculateChecksum()
    
    def verify(self):
        return self.Checksum == self.calculateChecksum() and isinstance(self.SequenceNumber, int)
    
    def __eq__(self, other):
        if not isinstance(other, PEEPPacket): return False
        return self.SequenceNumber == other.SequenceNumber
    
    def __lt__(self, other):
        return uint32CircularLessThan(self.SequenceNumber, other.SequenceNumber)

class PEEPTransport(StackingTransport):
    def __init__(self, protocol):
        super().__init__(protocol.transport)
        self.protocol = protocol

    def write(self, data):
        self.protocol.send_packet(payload=data)
    
    def close(self):
        self.protocol.close()

class PEEPProtocol(StackingProtocol):
    WINDOW_SIZE = 4096
    TIMEOUT = 1
    RETRY = 3
    
    def connection_made(self, transport):
        self.transport = transport
        self._deserializer = PEEPPacket.Deserializer()
        randBytes = os.urandom(4)
        self.seq = struct.unpack("I", randBytes)[0]
        self.unackedData = b""
        self.unsentData = b""
        self.incomingPackets = []
        self.remainingRetries = self.RETRY
        self.timer = None
        self.state = 0
    
    def data_received(self, data):
        self._deserializer.update(data)
        for pkt in self._deserializer.nextPackets():
            if not pkt.verify():
                continue
            if pkt.Type == PEEPPacketType.SYN.value or pkt.Type == PEEPPacketType.SYNACK.value:
                self.handle_handshake(pkt)
            elif pkt.Type == PEEPPacketType.ACK.value:
                self.handle_data(pkt)
            else:
                self.handle_rip(pkt)
    
    def connection_lost(self, exc):
        self.transport = None
        self.higherProtocol().connection_lost(exc)
    
    async def timeout(self):
        await asyncio.sleep(self.TIMEOUT)
        if self.remainingRetries == 0:
            self.connection_lost(TimeoutError())
            self.state = 0
        else:
            self.remainingRetries -= 1
            self.send_packet(retry=True)
    
    def send_packet(self, payload=b"", retry=False):
        if self.state == 0:
            self.send_handeshake()
        elif retry:
            # Timeout, resend unacked data
            ack = PEEPPacket(Type=PEEPPacketType.ACK.value, SequenceNumber=self.seq, Acknowledgement=self.ack)
            ack.Data = self.unackedData[:PEEPPacket.MAXIMUM_DATA_SIZE]
            ack.updateChecksum()
            self.transport.write(ack.__serialize__())
        else:
            payload += self.unsentData
            if len(payload) == 0 or len(self.unackedData) >= self.WINDOW_SIZE:
                # Separate ACK
                ack = PEEPPacket(Type=PEEPPacketType.ACK.value, SequenceNumber=self.seq, Acknowledgement=self.ack)
                ack.updateChecksum()
                self.transport.write(ack.__serialize__())
                self.packetSent = True
                return
            
            while len(payload) > 0:
                if len(self.unackedData) >= self.WINDOW_SIZE:
                    self.unsentData = payload
                    break
                #Send data
                length = self.WINDOW_SIZE - len(self.unackedData)
                if length > PEEPPacket.MAXIMUM_DATA_SIZE:
                    length = PEEPPacket.MAXIMUM_DATA_SIZE
                data = payload[:length]
                ack = PEEPPacket(Type=PEEPPacketType.ACK.value, SequenceNumber=uint32OverflowAdd(self.seq, len(self.unackedData)), Acknowledgement=self.ack)
                ack.Data = data
                ack.updateChecksum()
                self.transport.write(ack.__serialize__())
                self.packetSent = True
                self.unackedData += data
                payload = payload[length:]
        
        if not self.timer or self.timer.cancelled():
            self.timer = asyncio.ensure_future(self.timeout())
    
    def send_handeshake(self):
        raise NotImplementedError()
    
    def send_rip(self):
        pass
    
    def handle_handshake(self, pkt):
        raise NotImplementedError()
    
    def handle_data(self, pkt):
        if self.state == 0: return
        print(" ~ ACK {} {} {}".format(pkt.SequenceNumber, pkt.Acknowledgement, len(pkt.Data) if pkt.Data else "0"))
        if isinstance(pkt.Acknowledgement, int) and uint32CircularLessThan(self.seq, pkt.Acknowledgement) and not uint32CircularLessThan(uint32OverflowAdd(self.seq, len(self.unackedData)), pkt.Acknowledgement):
            # Handle ACK
            length = pkt.Acknowledgement - self.seq
            if length < 0: length += 1<<32
            self.unackedData = self.unackedData[length:]
            if len(self.unackedData) == 0:
                self.reset_timeout()
            self.seq = pkt.Acknowledgement
            if len(self.unsentData) > 0: self.send_packet()
            if self.state == 3 and len(self.unackedData) == 0:
                self.send_rip()
        
        if not pkt.Data or uint32CircularLessThan(uint32OverflowAdd(pkt.SequenceNumber, len(pkt.Data)), self.ack) or uint32CircularLessThan(uint32OverflowAdd(self.ack, self.WINDOW_SIZE), pkt.SequenceNumber):
            return
        # Handle payload
        heapq.heappush(self.incomingPackets, pkt)
        self.packetSent = False
        while len(self.incomingPackets) > 0 and not uint32CircularLessThan(self.ack, self.incomingPackets[0].SequenceNumber):
            pkt = heapq.heappop(self.incomingPackets)
            length = self.ack - pkt.SequenceNumber
            if length < 0: length += 1<<32
            data = pkt.Data[length:]
            if len(data) > 0:
                self.ack = uint32OverflowAdd(pkt.SequenceNumber, len(pkt.Data))
                if self.state == 1:
                    self.seq = uint32OverflowAdd(self.seq, 1)
                    self.state = 2
                    higherTransport = PEEPTransport(self)
                    self.higherProtocol().connection_made(higherTransport)
                self.higherProtocol().data_received(data)
        if not self.packetSent: self.send_packet()
    
    def handle_rip(self, pkt):
        pass
    
    def reset_timeout(self):
        self.timer.cancel()
        self.remainingRetries = self.RETRY
    
    def close(self):
        self.state = 3
        if len(self.unackedData) == 0:
            self.send_rip()

class PEEPClient(PEEPProtocol):
    def connection_made(self, transport):
        super().connection_made(transport)
        self.send_packet()
        self.state = 1
    
    def send_handeshake(self):
        syn = PEEPPacket(Type=PEEPPacketType.SYN.value, SequenceNumber=self.seq)
        syn.updateChecksum()
        self.transport.write(syn.__serialize__())
    
    def handle_handshake(self, pkt):
        if self.state == 1 and pkt.Type == PEEPPacketType.SYNACK.value and pkt.Acknowledgement == uint32OverflowAdd(self.seq, 1):
            self.reset_timeout()
            print(" ~ SYNACK {} {}".format(pkt.SequenceNumber, pkt.Acknowledgement))
            self.state = 2
            self.seq = uint32OverflowAdd(self.seq, 1)
            self.ack = uint32OverflowAdd(pkt.SequenceNumber, 1)
            self.packetSent = False
            higherTransport = PEEPTransport(self)
            self.higherProtocol().connection_made(higherTransport)
            if not self.packetSent: self.send_packet()

class PEEPServer(PEEPProtocol):
    def send_handeshake(self):
        ack = PEEPPacket(Type=PEEPPacketType.SYNACK.value, SequenceNumber=self.seq, Acknowledgement=self.ack)
        ack.updateChecksum()
        self.transport.write(ack.__serialize__())
    
    def handle_handshake(self, pkt):
        if self.state == 0 and pkt.Type == PEEPPacketType.SYN.value:
            print(" ~ SYN {}".format(pkt.SequenceNumber))
            self.ack = uint32OverflowAdd(pkt.SequenceNumber, 1)
            self.send_packet()
            self.state = 1
