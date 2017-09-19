from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT32, STRING, BUFFER, BOOL,ListFieldType
import time

class RequestProblem(PacketType):
    DEFINITION_IDENTIFIER = 'lab1b.student_ZeweiLi.fromclient1'
    DEFINITION_VERSION = '1.0'

    FIELDS = [
        ('id', UINT32)
    ]

class Answer(PacketType):
    DEFINITION_IDENTIFIER = 'lab1b.student_ZeweiLi.fromserver'
    DEFINITION_VERSION = '1.0'

    FIELDS = [
        ('id', UINT32),
        ('Date',STRING),
    ]

class Receivedinfo(PacketType):
    DEFINITION_IDENTIFIER = 'lab1b.student_ZeweiLi.fromclient2'
    DEFINITION_VERSION = '1.0'

    FIELDS = [
        ('id',UINT32),
        ('validity',BOOL)
    ]
def BasicUnitTest():
    packet1 = RequestProblem()
    packet1.id = 1

    packet2 = Answer()
    packet2.id = 1
    packet2.Date = time.asctime(time.localtime(time.time()))

    packet3 = Receivedinfo()
    packet3.id = 1
    packet3.validity = True

    packet1Bytes = packet1.__serialize__()
    packet1a = RequestProblem.Deserialize(packet1Bytes)
    if packet1 == packet1a:
        print('two packets are same!')


    packet2Bytes = packet2.__serialize__()
    packet2a = Answer.Deserialize(packet2Bytes)
    if packet2 == packet2a:
        print('two packets are same!')

    packet3Bytes = packet3.__serialize__()
    packet3a = Receivedinfo.Deserialize(packet3Bytes)

    if packet3 == packet3a:
        print('two packets are same!')

def BasicUnitTest2():
    packet1 = RequestProblem()
    packet1.id = 1

    packet2 = Answer()
    packet2.id = 1
    packet2.Date = time.asctime(time.localtime(time.time()))

    packet3 = Receivedinfo()
    packet3.id = 1
    packet3.validity = True


    pktBytes = packet1.__serialize__() + packet2.__serialize__() + packet3.__serialize__()
    deserializer = PacketType.Deserializer()
    print('Starting with {} bytes of data'.format(len(pktBytes)))


    while len(pktBytes):
        chunk, pktBytes = pktBytes[:10], pktBytes[10:]
        deserializer.update(chunk)
        print('Another 10 bytes loaded into deserializer.left = {}'.format(len(pktBytes)))

        for packet in deserializer.nextPackets():
            print('got a packet!')
            if packet == packet1:
                print('It is packet1!')
            if packet == packet2:
                print('It is packet2!')
            if packet == packet3:
                print('It is packet3!')
def BasicWrongTest():

    packet1 = RequestProblem()
    packet1.id = 1

    packet2 = Answer()
    packet2.id = 1
    packet2.Date = time.asctime(time.localtime(time.time()))

    packet3 = Receivedinfo()
    packet3.id = 1
    packet3.validity = True

    packetFake2 = Answer()
    packetFake2.id = 2
    packetFake2.Date ='2017/09/03'


    packet1Bytes = packet1.__serialize__()
    packet1a = RequestProblem.Deserialize(packet1Bytes)
    if packet1 == packet1a:
        print('two packets are same!')


    packetfake2Bytes = packetFake2.__serialize__()
    packetfake2a = Answer.Deserialize(packetfake2Bytes)
    if packet2 == packetfake2a:
        print('two packets are same!')
    else:
        print('two packets are not same!failure!')

    packet3Bytes = packet3.__serialize__()
    packet3a = Receivedinfo.Deserialize(packet3Bytes)

    if packet3 == packet3a:
        print('two packets are same!')
class AnswerListType(PacketType):
    DEFINITION_IDENTIFIER = 'lab1b.student_ZeweiLi.fromserver2'
    DEFINITION_VERSION = '1.0'

    FIELDS = [
        ('id', UINT32),
        ('Date',ListFieldType(STRING)),
    ]



def BasicListTest():
    packet1 = RequestProblem()
    packet1.id = 1

    packet2 = AnswerListType()
    packet2.id = 1
    packet2.Date = []
    packet2.Date.append(time.localtime(time.time()))

    packet3 = Receivedinfo()
    packet3.id = 1
    packet3.validity = True

    packet1Bytes = packet1.__serialize__()
    packet1a = RequestProblem.Deserialize(packet1Bytes)
    if packet1 == packet1a:
        print('two packets are same!')

    packet2Bytes = packet2.__serialize__()
    packet2a = AnswerListType.Deserialize(packet2Bytes)

    if packet2 == packet2a:
        print('two packets are same!')

    if packet2a.Date[0] == list(packet2.Date)[0]:
        print('the list test is successful!')


    packet3Bytes = packet3.__serialize__()
    packet3a = Receivedinfo.Deserialize(packet3Bytes)

    if packet3 == packet3a:
        print('two packets are same!')


if __name__ == '__main__':
    BasicUnitTest()
    BasicUnitTest2()
    BasicWrongTest()
    BasicListTest()
