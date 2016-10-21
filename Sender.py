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
        self.msg_buffer = []
        self.running_index = 0
        self.recv_buffer = []


    # Main sending loop.
    def start(self):
        # add things here
        try:
            self.initate_con()
            # print 'connection established'
            # exit()
        except Exception as error_msg:
            print error_msg.args[0]
            exit()
        # break file into 
        self.msg_buffer = self.make_msg(filename)
        # print len(self.msg_buffer)
        # sending packets
        while self.msg_buffer[self.running_index:] != []:
            start = int(self.next_seqnum_to_receiver)
            stop = len(self.msg_buffer[self.running_index:]) + self.initial_seqnum + 1
            list_of_seqno = [x for x in range(start, stop)]
            self.send_packets(self.msg_buffer[self.running_index:], list_of_seqno)

    # Initate connection
    def initate_con(self):
        i = 0
        while i < 5:
            # send initial patch to receiver
            packet = self.make_packet('syn',self.initial_seqnum,'')
            self.next_seqnum_to_receiver = self.initial_seqnum + 1
            self.send(packet,(dest, port))
            # set timer
            recv = self.receive(0.5)
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
        if packet_recv is not None:
            recv_msg_type, recv_seqno, recv_data, recv_checksum = self.split_packet(packet_recv)
            if recv_msg_type == 'ack' and Checksum.validate_checksum(packet_recv) and recv_checksum != None:
                self.next_seqnum_to_receiver = recv_seqno
                return True
        return False

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
            # print seqnos[i],
            self.send(packet,(dest, port))
            self.running_index += 1
            self.recv_buffer.append(self.receive(0.5))
            i += 1
            # print recv
        print self.recv_buffer
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
