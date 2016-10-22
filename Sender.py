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
        
        # sending packets
        while self.msg_buffer[self.running_index:] != []:
            self.list_of_expected_seqno = []
            # slicing already ack'd data off msg_buffer
            self.send_packets(self.msg_buffer[self.running_index:], self.seqno_buffer[self.running_index:])
            # validate recv packets
            for x in self.recv_buffer:
                self.validate_packet(x)
            # update running_index to last successfully ack'd
            self.running_index += self.list_of_expected_seqno.index(int(self.next_seqnum_to_receiver)) + 1



    # Initate connection
    def initate_con(self):
        i = 0
        while i < 5:
            # send initial patch to receiver
            packet = self.make_packet('syn',self.initial_seqnum,'')
            self.send(packet,(dest, port))
            # set timer
            recv = self.receive(0.5)
            self.list_of_expected_seqno.append(self.initial_seqnum + 1)
            # validate data
            if self.validate_packet(recv):
                return None
            # increment counter for attempts to reach receiver
            i+=1
            # waits 5 seconds before trying again
            time.sleep(2)
        raise Exception ('Unable to reach Receiver')

    # Validate packet is not corrupt and update next_seqnum_to_receiver
    def validate_packet(self, packet_recv):
        # checks connection time out
        if packet_recv is None:
            return False
        # check for ack and exsitence of a valid checksum
        recv_msg_type, recv_seqno, recv_data, recv_checksum = self.split_packet(packet_recv)
        if not(recv_msg_type == 'ack' and Checksum.validate_checksum(packet_recv) and recv_checksum != None):
            return False
        # checks if recv sequence number is expected
        if int(recv_seqno) not in self.list_of_expected_seqno:
            return False
        # update next_seqnum_to_receiver with largest ack seqno
        if recv_seqno > self.next_seqnum_to_receiver:
            self.next_seqnum_to_receiver = recv_seqno
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
        while i < 7 and i < len(msgs):
            packet = self.make_packet('dat', seqnos[i], msgs[i])
            self.send(packet,(dest, port))
            self.list_of_expected_seqno.append(seqnos[i] + 1)
            self.recv_buffer.append(self.receive(0.5))
            i += 1
        # print self.recv_buffer

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
