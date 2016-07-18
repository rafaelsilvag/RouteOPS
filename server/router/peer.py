#!/usr/bin/env python
#  coding=utf-8
#  Author:
#  Muhammad Shahbaz (muhammad.shahbaz@gatech.edu)
#  Rudiger Birkner (Networked Systems Group ETH Zurich)
#  Modified by:
#         Rafael S. Guimarães <rafaelg@ifes.edu.br>
#
#  NERDS - Núcleo de Estudo em Redes Definidas por Software
#
import json
from lib.defs import *
from rib import Rib

class Peer(object):

    def __init__(self):
        self.ribs = {
                '172.0.0.1': Rib(ip='172.0.0.1'),
                '172.0.0.2': Rib(ip='172.0.0.2'),
                '172.0.0.3': Rib(ip='172.0.0.3'),
                '172.0.0.4': Rib(ip='172.0.0.4'),
        }
        self.main_rib = Rib(ip=MAIN_BGP)

    def configs():
        """Return config all routers"""
        pass

    def update(self, ip, route):
        updates = []
        key = {}

        origin = None
        as_path = None
        med = None
        atomic_aggregate = None
        community = None

        route_list = []

        if ('state' in route['neighbor'] and route['neighbor']['state']=='down'):
            # Delete all routes on RIB
            print "STATE: Peer %(ip)s is Down" % (route['neighbor'])
            self.rib.delete_all()


        if ('update' in route['neighbor']['message']):
            if ('attribute' in route['neighbor']['message']['update']):
                attribute = route['neighbor']['message']['update']['attribute']

                origin = attribute['origin'] if 'origin' in attribute else ''

                temp_as_path = attribute['as-path'] if 'as-path' in attribute else ''
                as_path = ' '.join(map(str,temp_as_path)).replace('[','').replace(']','').replace(',','')

                med = attribute['med'] if 'med' in attribute else ''

                community = attribute['community'] if 'community' in attribute else ''
                communities = ''
                for c in community:
                    communities += ':'.join(map(str,c)) + " "

                atomic_aggregate = attribute['atomic-aggregate'] if 'atomic-aggregate' in attribute else ''

            if ('announce' in route['neighbor']['message']['update']):
                announce = route['neighbor']['message']['update']['announce']
                if ('ipv4 unicast' in announce):
                    for next_hop in announce['ipv4 unicast'].keys():
                        for prefix in announce['ipv4 unicast'][next_hop].keys():
                            aux = {}
                            aux['prefix'] = prefix
                            aux['next_hop'] = next_hop
                            aux['med'] = med
                            if as_path:
                                aux['as_path'] = str(as_path)
                            if communities:
                                aux['communities'] = communities

                            if LOG:
                                print "=> NEIGHBOR: %(ip)s" % route['neighbor']
                                print "=> ANNOUNCE: %(prefix)s" % (aux)
                                print "=> NEXT_HOP: %(next_hop)s" % (aux)
                                print "=> AS_PATH: %s" % (aux.get('as_path', None))
                                print "=> MED: %(med)s" % (aux)
                                print "=> COMMUNITIES: %s" % (aux.get('communities', None))

                            # Add or Update Announce on Rib
                            self.ribs[ip][prefix] = aux
                            # Add Main RIB
                            self.main_rib.update_neighbor(prefix, aux)

                            # Read policy and announce route to others routers using VIP
                            command = 'neighbor %s announce route %s next-hop %s' % ('172.0.0.2', aux['prefix'], aux['next_hop'])

                            if len(as_path) > 1:
                                command += ' as-path [ %s ]' % (as_path)

                            if LOG:
                                print "SENDING ANNOUNCE TO: %s" % ('172.0.0.2')
                                print "ROUTE %(prefix)s NEXT_HOP %(next_hop)s" % (aux)
                                print "COMMAND: %s" % (command)

                            # Send rule to controller OpenFlow

                            """
                            announced_peers = self.sdnrouter.db_peers.find()

                            for a_peer in announced_peers:
                                if a_peer['IP'] == route['neighbor']['ip']:
                                    break;
                                else:
                                    for item in a_peer['prefix']:
                                        if(item['prefix'] == aux['prefix']):
                                            continue
                                        else:
                                            command = "neighbor %s announce route %(prefix)s next-hop %(next_hop)s" % (a_peer['IP'], aux)
                                            if as_path != "":
                                                command += " as-path [ %s ]" % (as_path)
                                            if LOG:
                                                print "SENDING ANNOUNCE TO: %s" % (a_peer['IP'])
                                                print "ROUTE %(prefix)s NEXT_HOP %(next_hop)s" % (aux)
                                                print "COMMAND: %s" % command

                                            #self.sdnrouter.server_ipc.send(AGENT_SERVER_CHANNEL, AGENT_ID, command)
                            """
            elif ('withdraw' in route['neighbor']['message']['update']):
                withdraw = route['neighbor']['message']['update']['withdraw']
                if ('ipv4 unicast' in withdraw):
                    for prefix in withdraw['ipv4 unicast'].keys():
                        self.rib.delete(prefix)
                        #self.main_rib.delete_neighbor(prefix, route['neighbor']['ip'])
                        #deleted_route = self.rib["input"][prefix]
                        #self.rib["input"].delete(prefix)
                        #self.rib["input"].commit()
                        #route_list.append({'withdraw': deleted_route})

        return route_list

    def process_notification(self,route):
        if ('shutdown' == route['notification']):
            pass

    def add_route(self, rib_name, prefix, attributes):
        pass

    def add_many_routes(self, rib_name, routes):
        pass

    def get_route(self, rib_name, prefix):
        pass

    def get_routes(self, rib_name, prefix):
        self.ribs[rib_name].get(prefix)

    def get_all_routes(self, rib_name):
        self.ribs[rib_name].get_all()

    def delete_route(self,rib_name,prefix):
        self.ribs[rib_name].delete(prefix)

    def delete_all_routes(self):
        for rib in self.ribs:
            self.ribs[rib].delete_all()
        self.main_rib.delete_all()

    def filter_route(self,rib_name,item,value):
        pass

''' main '''
if __name__ == '__main__':

    mypeer = Peer('172.0.0.1')
    print mypeer
    route = {u'counter': 1, u'pid': u'10494', u'exabgp': u'3.4.8', u'host': u'routeops', u'neighbor': {u'ip': u'172.0.0.1', u'message': {u'update': {u'attribute': {u'origin': u'igp', u'med': 0, u'local-preference': 100}, u'announce': {u'ipv4 unicast': {u'172.0.0.1': {u'110.0.0.0/24': {}, u'100.0.0.0/24': {}, u'172.0.0.0/23': {}}}}}}, u'asn': {u'peer': u'65000', u'local': u'65000'}, u'address': {u'peer': u'172.0.0.1', u'local': u'172.0.255.254'}}, u'time': 1456167437, u'ppid': u'10449', u'type': u'update'}
    mypeer.update(route)
    #print mypeer.filter_route('input', 'as_path', '300')
