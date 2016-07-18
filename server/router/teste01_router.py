#!/usr/bin/env python
#  Author:
#	Rafael S. Guimaraes <rafaelg@ifes.edu.br>
#
import lib.MongoIPC
import threading
import time
import sys
try:
    res = lib.MongoIPC.MongoIPCMessageService('127.0.0.1','sdnrouter','server',threading.Thread, time.sleep)
    res.listen("agent<->server", False)

    print "# INITIALIZING TESTING..."
    time.sleep(5)

    print "## BEGNING ANNOUNCES"
    print "### ANNOUNCE: 200.0.0.0/23 as-path [ 200 150 ] to 172.0.0.3"
    aux = res.send("agent<->server", 'agent', 'neighbor 172.0.0.3 announce route 200.0.0.0/23 next-hop 172.0.0.2 as-path [ 200 150 ]')
    print "### ANNOUNCE: 140.0.0.0/24 to 172.0.0.2"
    aux = res.send("agent<->server", 'agent', 'neighbor 172.0.0.2 announce route 140.0.0.0/24 next-hop 172.0.0.3')
    print "## ANNOUNCES DONE"

    time.sleep(50)
    for i in range(1,6):
      print i
      time.sleep(1)

    print "## STARTING IPERF"
    time.sleep(200)

    print "## CONVERGING "
    print "### ANNOUNCE: 140.0.0.0/25 to 172.0.0.1"
    aux = res.send("agent<->server", 'agent', 'neighbor 172.0.0.1 announce route 140.0.0.0/25 next-hop 172.0.0.3')
    aux = res.send("agent<->server", 'agent', 'neighbor 172.0.0.2 announce route 140.0.0.128/25 next-hop 172.0.0.3')

    print "### ANNOUNCE: 200.0.0.0/23 as-path [ 100 150 ] to 172.0.0.3"
    aux = res.send("agent<->server", 'agent', 'neighbor 172.0.0.3 announce route 200.0.0.0/24 next-hop 172.0.0.1 as-path [ 100 150 ]')
    aux = res.send("agent<->server", 'agent', 'neighbor 172.0.0.3 announce route 200.0.1.0/24 next-hop 172.0.0.1 as-path [ 100 150 ]')

    #print "### WITHDRAW: 200.0.0.0/23 to 172.0.0.3"
    #aux = res.send("agent<->server", 'agent', 'neighbor 172.0.0.3 withdraw xroute 200.0.0.0/23 next-hop 172.0.0.2')


    #print "### WITHDRAW: 140.0.0.0/24 to 172.0.0.2"
    #aux = res.send("agent<->server", 'agent', 'neighbor 172.0.0.2 withdraw route 140.0.0.0/24 next-hop 172.0.0.3')

    time.sleep(200)

    print "## CLEANING ROUTES"
    print "### WITHDRAW: 200.0.0.0/23 to 172.0.0.3"
    aux = res.send("agent<->server", 'agent', 'neighbor 172.0.0.3 withdraw route 200.0.0.0/24 next-hop 172.0.0.1')
    aux = res.send("agent<->server", 'agent', 'neighbor 172.0.0.3 withdraw route 200.0.1.0/24 next-hop 172.0.0.1')
    aux = res.send("agent<->server", 'agent', 'neighbor 172.0.0.3 withdraw route 200.0.0.0/23 next-hop 172.0.0.2')
    print "### WITHDRAW: 140.0.0.0/24 to 172.0.0.1"
    aux = res.send("agent<->server", 'agent', 'neighbor 172.0.0.1 withdraw route 140.0.0.0/25 next-hop 172.0.0.3')
    aux = res.send("agent<->server", 'agent', 'neighbor 172.0.0.2 withdraw route 140.0.0.128/25 next-hop 172.0.0.3')
    aux = res.send("agent<->server", 'agent', 'neighbor 172.0.0.2 withdraw route 140.0.0.0/24 next-hop 172.0.0.3')
except KeyboardInterrupt, ex:
    pass
