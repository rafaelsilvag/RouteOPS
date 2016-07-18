#!/usr/bin/env python
#  Author:
#  Muhammad Shahbaz (muhammad.shahbaz@gatech.edu)
#  Arpit Gupta

import sys
from threading import Thread
from multiprocessing.connection import Client
import os
import time
# MongoIPC
import lib.MongoIPC
from lib.defs import *

home_path = os.environ['HOME']
logfile = home_path+'/RouteOPS/logs/client.log'

'''Write output to stdout'''
def _write(stdout,data):
    stdout.write(data + '\n')
    stdout.flush()

''' Sender function '''
def _sender(conn,stdin,log):
    # Warning: when the parent dies we are seeing continual newlines, so we only access so many before stopping
    counter = 0

    while True:
        try:
            line = stdin.readline().strip()

            if line == "":
                counter += 1
                if counter > 100:
                    break
                continue
            counter = 0

            conn.send(AGENT_SERVER_CHANNEL, SERVER_ID, line)

            log.write(line + '\n')
            log.flush()

        except:
            pass

''' Receiver function '''
def _receiver(conn,stdout,log):

    while True:
        try:
            time.sleep(0.05)
            line = conn.recv_msg.pop(0)

            if line == "":
                continue

            _write(stdout, line)
            ''' example: announce route 1.2.3.4 next-hop 5.6.7.8 as-path [ 100 200 ] '''

            log.write(line + '\n')
            log.flush()

        except:
            pass

''' main '''
if __name__ == '__main__':

    log = open(logfile, "w")
    log.write('Open Connection \n')

    conn = lib.MongoIPC.MongoIPCMessageService(MONGO_ADDRESS,MONGO_DB_NAME,AGENT_ID, Thread, time.sleep)
    conn.listen(AGENT_SERVER_CHANNEL, False)

    sender = Thread(target=_sender, args=(conn,sys.stdin,log))
    sender.start()

    receiver = Thread(target=_receiver, args=(conn,sys.stdout,log))
    receiver.start()

    sender.join()
    receiver.join()

    log.close()
