#!/usr/bin/env python
#  Author:
#	Rafael S. Guimaraes <rafaelg@ifes.edu.br>
#
import lib.MongoIPC
import threading
import time
import sys
import os
try:
    res = lib.MongoIPC.MongoIPCMessageService('127.0.0.1','sdnrouter','server',threading.Thread, time.sleep)
    res.listen("agent<->server", False)

    print "# INITIALIZING TESTING..."
    time.sleep(2)

    print "## ANNOUNCES INITIALIZING"

    for i in range(0,16):
        for j in range(0,256):
            msg = 'neighbor 172.0.0.3 announce route 100.%s.%s.0/24 next-hop 172.0.0.2 as-path [ 200 150 ]' % (i,j)
            aux = res.send("agent<->server", 'agent', msg)

    print "### ANNOUNCE: 200.0.0.0/23 as-path [ 100 150 ] to 172.0.0.3"
    aux = res.send("agent<->server", 'agent', 'neighbor 172.0.0.3 announce route 200.0.0.0/23 next-hop 172.0.0.2 as-path [ 200 150 ]')

    for i in range(1,6):
        print i
        time.sleep(1)
    print "### ANNOUNCES DONE ###"

except KeyboardInterrupt, ex:
    print "\nKilling ROUTEOPS Server..."
    time.sleep(1)
    os.kill(os.getpid(), signal.SIGTERM)
