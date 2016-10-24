import sys
import getopt

import Checksum
import BasicSender
from random import randint
import time

'''
This is a skeleton sender class. Create a fantastic transport protocol here.
'''
class Sender(BasicSender.BasicSender):
    def __init__(self, dest, port, filename, debug=False, sackMode=False):
        super(Sender, self).__init__(dest, port, filename, debug)
        self.sackMode = sackMode
        self.debug = debug
        self.initial_seqnum = randint(3578,5437)
        self.next_seqnum_to_receiver = 0
        self.running_index = 0
        self.recv_buffer = []
        self.msg_buffer = []
        self.seqno_buffer = []
        self.list_of_expected_seqno = []
        self.validated_packts = []

    # Main sending loop.
    def start(self):
        # hand shake
        try:
            self.initate_con()
        except Exception as error_msg:
            print error_msg.args[0]
            exit()

        # break file into 
        self.msg_buffer = self.make_msg(filename)

        # buffer seqno
        start = self.initial_seqnum + 1
        stop = len(self.msg_buffer) + self.initial_seqnum + 1
        self.seqno_buffer = [x for x in range(start, stop)]

        # reset variables 
        self.validated_packts = []
        self.recv_buffer = []   
        # sending packets
        while self.msg_buffer[self.running_index:] != []:

            self.list_of_expected_seqno = []
            # slicing already ack'd data off msg_buffer
            self.send_packets(self.msg_buffer[self.running_index:], self.seqno_buffer[self.running_index:])
            # check timeout
            self.recv_buffer = filter(None, self.recv_buffer)
            if self.recv_buffer != [] and self.validate_packet(self.recv_buffer, self.sackMode):                
                self.update_running_index()

    # Initate connection
    def initate_con(self):
        i = 0
        while i < 30:
            self.list_of_expected_seqno = []
            # send initial patch to receiver
            packet = self.make_packet('syn', self.initial_seqnum,'')
            self.send(packet,(dest, port))
            # set timer
            self.recv_buffer.append(self.receive(0.5))
            self.list_of_expected_seqno.append(self.initial_seqnum + 1)
            self.recv_buffer = filter(None, self.recv_buffer)
            # validate data
            if self.recv_buffer != [] and self.validate_packet(self.recv_buffer, self.sackMode):
                return None
            # increment counter for attempts to reach receiver
            i+=1
        raise Exception ('Unable to reach Receiver')

    # Validate packet is not corrupt and update next_seqnum_to_receiver
    def validate_packet(self, packets_recv, sackMode):
        packets_recv = filter(None, packets_recv)

        if sackMode:
            seqno = 0
            buffd_at_receiver = []

            self.list_of_expected_seqno = [int(x) for x in self.list_of_expected_seqno]

            # import pdb; pdb.set_trace()
            
            # search for largest ack'd and most buffer at receiver to remedy packets arriving out of order
            for x in packets_recv:
                recv_msg_type, recv_seqno, recv_data, recv_checksum = self.split_packet(x)
                if recv_msg_type == 'sack' and Checksum.validate_checksum(x) and recv_checksum != None:
                    # seperating proper ack from buffered at receiver 
                    recv_seqno = recv_seqno.split(';', 1)
                    recv_seqno = filter(None, recv_seqno)

                if int(recv_seqno[0]) not in self.list_of_expected_seqno and int(recv_seqno[0]) != self.initial_seqnum + 1:
                    continue

                if int(recv_seqno[0]) > seqno:
                    seqno = int(recv_seqno[0])
                    try:
                        buffd_at_receiver = [int(x) + 1 for x in recv_seqno[1].split(',')]
                    except:
                        buffd_at_receiver = []
                elif int(recv_seqno[0]) == seqno:                      
                    if len(recv_seqno) >  1:
                        for x in [int(x) + 1 for x in recv_seqno[1].split(',')]:
                            if x not in buffd_at_receiver:
                                buffd_at_receiver.append(x)
                else:
                    seqno = self.initial_seqnum + 1

            self.validated_packts.append(seqno)

            if buffd_at_receiver != []:  
                # quick resend                
                for x in self.list_of_expected_seqno:
                    if x not in buffd_at_receiver:
                        num = self.running_index + self.list_of_expected_seqno.index(x) 
                        packet = self.make_packet('dat', self.seqno_buffer[num], self.msg_buffer[num])
                        self.send(packet,(dest, port)) 
                        self.recv_buffer.append(self.receive(0.5))
        else:
            # check for ack and exsitence of a valid checksum
            for x in packets_recv:

                recv_msg_type, recv_seqno, recv_data, recv_checksum = self.split_packet(x)
                if not(recv_msg_type == 'ack' and Checksum.validate_checksum(x) and recv_checksum != None):
                    return False
                # checks if recv sequence number is expected
                if int(recv_seqno) not in self.list_of_expected_seqno:
                    return False

                self.validated_packts.append(recv_seqno)

                #fast retransmit
                if packets_recv.count(x) >= 4:
                    i = self.running_index + self.list_of_expected_seqno.index(recv_seqno)
                    send_packets(self.msg_buffer[i], self.seqno_buffer[i])

        return True

    # Read and Break up file into messages
    def make_msg(self, filename):
        msgs = []
        f = open(filename, "r")
        while True:
            msg = f.read(1470)
            if msg == '':
                break
            msgs.append(msg)
        return msgs

    # Send MAX packets (windows size)
    def send_packets(self, msgs, seqnos):
        i = 0

        self.recv_buffer = []
        
        while i < min(7, len(msgs)):
            msg_type = 'dat'

            # check if final message         
            if self.seqno_buffer[-1:][0] == seqnos[i]:
                msg_type = 'fin'

            # send packets
            packet = self.make_packet(msg_type, seqnos[i], msgs[i])
            self.send(packet,(dest, port))
            self.list_of_expected_seqno.append(seqnos[i] + 1)
            self.recv_buffer.append(self.receive(0.5))
            i += 1

        self.recv_buffer = filter(None, self.recv_buffer)

    # update index
    def update_running_index(self):
        # if not in list running index remains same
        try:
            self.running_index += self.list_of_expected_seqno.index(int(max(self.validated_packts))) + 1
        except:
            pass


'''
This will be run if you run this script from the command line. You should not
change any of this; the grader may rely on the behavior here to test your
submission.
'''
if __name__ == "__main__":
    def usage():
        print "BEARS-TP Sender"
        print "-f FILE | --file=FILE The file to transfer; if empty reads from STDIN"
        print "-p PORT | --port=PORT The destination port, defaults to 33122"
        print "-a ADDRESS | --address=ADDRESS The receiver address or hostname, defaults to localhost"
        print "-d | --debug Print debug messages"
        print "-h | --help Print this usage message"
        print "-k | --sack Enable selective acknowledgement mode"

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                               "f:p:a:dk", ["file=", "port=", "address=", "debug=", "sack="])
    except:
        usage()
        exit()

    port = 33122
    dest = "localhost"
    filename = None
    debug = False
    sackMode = False

    for o,a in opts:
        if o in ("-f", "--file="):
            filename = a
        elif o in ("-p", "--port="):
            port = int(a)
        elif o in ("-a", "--address="):
            dest = a
        elif o in ("-d", "--debug="):
            debug = True
        elif o in ("-k", "--sack="):
            sackMode = True

    s = Sender(dest,port,filename,debug, sackMode)
    try:
        s.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
