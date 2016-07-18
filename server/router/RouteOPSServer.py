#!/usr/bin/env python
# coding=utf-8
# Author:
#         Rafael S. Guimarães <rafaelg@ifes.edu.br>
#
# NERDS - Núcleo de Estudo em Redes Definidas por Software
#
import os
import json
import signal
import argparse
import time

import Queue
import json
from threading import Thread, Event
from core import parse_config
from peer import Peer
#from decision_process import decision_process
import lib.MongoIPC
from lib.defs import *
from ipaddress import ip_address, ip_network

class RouterServer(object):

    def __init__(self, config_file):
        print "Initialize the RouteOPS Server"
        self.relax_announce = True
        # Init the SDNRoute Server
        ## Parse Config
        self.sdnrouter = parse_config(config_file)
        self.peer = Peer()
        # MongoIPC agent<->server
        self.sdnrouter.server_ipc = \
            lib.MongoIPC.MongoIPCMessageService(MONGO_ADDRESS, MONGO_DB_NAME, SERVER_ID, Thread, time.sleep)
        self.sdnrouter.server_ipc.listen(AGENT_SERVER_CHANNEL, False)
        self.sdnrouter.server_ipc.listen(SERVER_PROXY_CHANNEL, False)

        try:
            pass
            #db = mongo.Connection(MONGO_ADDRESS)[MONGO_DB_NAME]
            #self.sdnrouter.db_peers = db[TABLE_PEERS]
            #for participant in self.sdnrouter.participants:
            #    res = None
            #    res = self.sdnrouter.db_peers.find_one({'IP': self.sdnrouter.participants[participant]['IP']})
            #    if res:
            #        pass
            #    else:
            #        self.sdnrouter.db_peers.insert(self.sdnrouter.participants[participant])
        except Queue.Empty:
            pass
        except:
            pass

        self.run = True

    def start(self):
        print "Start Server"
        print "Sending initial rules - Openflow Controller"
        #
        for participant in self.sdnrouter.participants:
            msg = json.dumps(self.sdnrouter.participants[participant])
            self.sdnrouter.server_ipc.send(SERVER_PROXY_CHANNEL, PROXY_ID, msg)
            print msg
        #
        while self.run:
            # get BGP messages from ExaBGP via stdin and Openflow Message from Ryu
            try:
                time.sleep(0.05)
                route = self.sdnrouter.server_ipc.recv_msg.pop(0)
                route = json.loads(route)
                # process route advertisements - add/remove routes to/from rib of respective participant (neighbor)
                updates = None

                if 'neighbor' in route:
                    if 'ip' in route['neighbor']:
                        if LOG:
                            print "NEIGHBOR: %(ip)s" % (route['neighbor'])
                        # update route on neighbor
                        self.peer.update(route['neighbor']['ip'], route)
                        """
                        if (route['neighbor']['ip'] == '172.0.0.1'):
                            # Rotas para cenario 03
                            self.sdnrouter.server_ipc.send(
                                AGENT_SERVER_CHANNEL,
                                AGENT_ID,
                                'neighbor 172.0.0.3 announce route 200.0.0.0/24 next-hop 172.0.0.1 as-path [ 100 150 ]'
                            )
                            self.sdnrouter.server_ipc.send(
                                AGENT_SERVER_CHANNEL,
                                AGENT_ID,
                                'neighbor 172.0.0.3 announce route 200.0.1.0/24 next-hop 172.0.0.1 as-path [ 100 150 ]'
                            )


                            #self.sdnrouter.server_ipc.send(
                            #    AGENT_SERVER_CHANNEL,
                            #    AGENT_ID,
                            #    'neighbor 172.0.0.4 announce route 200.0.0.0/24 next-hop 172.0.0.1 as-path [ 100 150 ]'
                            #)
                            #self.sdnrouter.server_ipc.send(
                            #    AGENT_SERVER_CHANNEL,
                            #    AGENT_ID,
                            #    'neighbor 172.0.0.4 announce route 200.0.1.0/24 next-hop 172.0.0.1 as-path [ 100 150 ]'
                            #)


                            self.sdnrouter.server_ipc.send(
                                AGENT_SERVER_CHANNEL,
                                AGENT_ID,
                                'neighbor 172.0.0.1 announce route 140.0.0.0/25 next-hop 172.0.0.3'
                            )
                            self.sdnrouter.server_ipc.send(
                                AGENT_SERVER_CHANNEL,
                                AGENT_ID,
                                'neighbor 172.0.0.1 announce route 140.0.0.128/25 next-hop 172.0.0.3'
                            )
                            self.sdnrouter.server_ipc.send(
                                AGENT_SERVER_CHANNEL,
                                AGENT_ID,
                                'neighbor 172.0.0.1 announce route 150.0.0.0/24 next-hop 172.0.0.3 as-path [ 300 ]'
                            )
                            #self.sdnrouter.server_ipc.send(
                            #    AGENT_SERVER_CHANNEL,
                            #    AGENT_ID,
                            #    'neighbor 172.0.0.2 announce route 150.0.0.0/24 next-hop 172.0.0.3 as-path [ 300 ]'
                            #)
                            """
                elif 'notification' in route:
                    if LOG:
                        print "NOTIFICATION: %s" % route
                    if route['notification'] == 'shutdown' and 'exabgp' in route:
                        # Controller BGP is Down
                        self.peer.delete_all_routes()

                elif 'stats' in route:
                    if LOG:
                        # Flow Stats
                        eth_dst = None
                        ip_src = None
                        ip_dst = None
                        tcp_src = None
                        tcp_dst = None
                        """
                        asn_prefix = ip_network(u'200.0.1.0/255.255.255.0')
                        if 'match' in route['stats']:
                            stats = "STATS: \n\tSWITCH=%(switch)08x\n" % (route['stats'])
                            stats += "\tMATCH"
                            if 'eth_src' in route['stats']['match']:
                                stats += "\n\t\tETH_SRC=%(eth_src)s" % (route['stats']['match'])
                            if 'eth_dst' in route['stats']['match']:
                                stats += "\n\t\tETH_DST=%(eth_dst)s" % (route['stats']['match'])
                                eth_dst = route['stats']['match']['eth_dst']
                            if 'ipv4_src' in route['stats']['match']:
                                stats += "\n\t\tIPv4_SRC=%(ipv4_src)s" % (route['stats']['match'])
                                ip_src = route['stats']['match']['ipv4_src']
                            if 'ipv4_dst' in route['stats']['match']:
                                stats += "\n\t\tIPv4_DST=%(ipv4_dst)s" % (route['stats']['match'])
                                ip_dst = route['stats']['match']['ipv4_dst']
                            if 'tcp_src' in route['stats']['match']:
                                stats += "\n\t\tTCP_SRC=%(tcp_src)s" % (route['stats']['match'])
                                tcp_src = route['stats']['match']['tcp_src']

                            if ip_dst and ip_src:
                                for rule in self._clientes[eth_dst]:
                                    if rule['ip'] == ip_network(ip_dst) \
                                            and ip_network(ip_src).subnet_of(asn_prefix) \
                                            and not tcp_src:
                                        if rule['counter'] == 0:
                                            rule['counter'] = int(route['stats']['byte_count'])
                                        else:
                                            d_time = int(route['stats']['byte_count']) - rule['counter']
                                            rule['counter'] = int(route['stats']['byte_count'])
                                            if d_time < 1:
                                                flow_rate = 0
                                                if self.relax_announce:
                                                    self.sdnrouter.server_ipc.send(
                                                        AGENT_SERVER_CHANNEL,
                                                        AGENT_ID,
                                                        'neighbor 172.0.0.2 withdraw route 150.0.0.128/25 next-hop 172.0.0.4'
                                                    )
                                                    self.relax_announce = False
                                            else:
                                                flow_rate = ((d_time/10)*8)/1024
                                                if flow_rate > 600000 and not self.relax_announce:
                                                    self.sdnrouter.server_ipc.send(
                                                        AGENT_SERVER_CHANNEL,
                                                        AGENT_ID,
                                                        'neighbor 172.0.0.2 announce route 150.0.0.128/25 next-hop 172.0.0.4 as-path [ 300 ]'
                                                    )
                                                    self.relax_announce = True
                                            print "FLOW RATE: %s" % (str(flow_rate))

                                    #elif rule['ip'] == ip_network(ip_dst):
                                    #    if rule['counter'] == 0:
                                    #        rule['counter'] = int(route['stats']['byte_count'])
                                    #    else:
                                    #        d_time = int(route['stats']['byte_count']) - rule['counter']
                                    #        rule['counter'] = int(route['stats']['byte_count'])
                                    #        print "UDP: %s %s" % (route['stats']['byte_count'], str(d_time))
                                    #        print route['stats']
                            if 'tcp_dst' in route['stats']['match']:
                                stats += "\n\t\tTCP_DST=%(tcp_dst)s" % (route['stats']['match'])
                                tcp_dst = route['stats']['match']['tcp_dst']
                            if 'udp_src' in route['stats']['match']:
                                stats += "\n\t\tUDP_SRC=%(udp_src)s" % (route['stats']['match'])
                            if 'udp_dst' in route['stats']['match']:
                                stats += "\n\t\tUDP_DST=%(udp_dst)s" % (route['stats']['match'])
                            stats += "\n\tBYTE_COUNT=%(byte_count)s " % (route['stats'])

                        # Port Stats
                        if 'port_no' in route['stats']:
                            stats = "STATS: \n\tSWITCH=%(switch)s " % (route['stats'])
                            stats += "\t\tPORT_NO=%(port_no)s\n" % (route['stats'])
                            stats += "\t\tRX=%(rx)s\n" % (route['stats'])
                            stats += "\t\tTX=%(tx)s" % (route['stats'])
                        """

            except IndexError:
                pass
            except AttributeError:
                pass
            except Exception, ex:
                if LOG:
                    print "ERROR: %s" % (ex)

    def stop(self):
        self.run = False


def main(argv):
    # locate config file
    base_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)),"conf"))
    config_file = os.path.join(base_path, "global.cfg")
    policy_file = os.path.join(base_path, "policies.cfg")
    print config_file
    print policy_file
    # start route server
    sdnrouter = RouterServer(config_file)
    rs_thread = Thread(target=sdnrouter.start)
    rs_thread.daemon = True
    rs_thread.start()

    while rs_thread.is_alive():
        try:
            rs_thread.join(1)
        except KeyboardInterrupt:
            print "\nKilling RouteOPS Server..."
            sdnrouter.stop()
            time.sleep(1)
            os.kill(os.getpid(), signal.SIGTERM)

''' main '''
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('dir', help='the directory of the example')
    args = parser.parse_args()

    main(args)
