#!/usr/bin/env python
# coding: utf-8
# Author:
#         Rafael S. Guimarães <rafaelg@ifes.edu.br>
#
# NERDS - Núcleo de Estudo em Redes Definidas por Software
#

import time
from operator import attrgetter
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import arp, ipv4, ipv6, tcp, udp
from ryu.lib import dpid as dpid_lib
from ryu.lib import hub
from ryu.lib.packet import vlan
from ryu.topology import switches, event
from ryu.controller import network, dpset
import netaddr
# from controller.topology import Topology
from colorama import Fore
# MongoDB
from threading import Thread, Event
import lib.MongoIPC
from lib.defs import *
import json

ETHERNET = ethernet.ethernet.__name__
ARP = arp.arp.__name__


class ApplicationOF(app_manager.RyuApp):
    _CONTEXTS = {
        'switches': switches.Switches,
        'network': network.Network,
    }

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ApplicationOF, self).__init__(*args, **kwargs)
        self.switches = kwargs['switches']
        self.network = kwargs['network']
        self.wait = True
        self.newnodefound = False
        self.topology = None
        self.mac_to_port = {}
        self.nodes_restore = []
        self.datapaths = {}
        self.conn = None
        self.server_ipc = None
        self.start_time = time.time()
        self.traffic_port = {}
        self.traffic_flow = {}
        # Conection with MongoDB
        try:
            self.server_ipc = lib.MongoIPC.MongoIPCMessageService(MONGO_ADDRESS,MONGO_DB_NAME, PROXY_ID, Thread, time.sleep)
            self.server_ipc.listen(SERVER_PROXY_CHANNEL, False)
            self.logger.info('[Mongo Connection]: %s', "Success")
        except Exception, ex:
            self.logger.info('[Mongo ConnectionError]: %s', ex.message)

        #self.generatetopology_thread = hub.spawn(self._generateTopology)
        self.monitor_thread = hub.spawn(self._monitor)
        self.mongo_ipc_thread = hub.spawn(self._mongo_ipc)

    def _generateTopology(self):
        time.sleep(5)
        self.topology = Topology(self.switches, allnodes=True)

        self.wait = False
        for n in self.topology.nodes.itervalues():
            self.logger.info("[Generate Topology] dpid=[%s], host=[%s], name=[%s], mac=[%s]" %
                             (n.dpid, n.host, n.binaddr, n.mac))
            for (dpid, port) in n.neighbors.items():
                self.logger.info("[Generate Topology] neighbors=[%s] --> (%d  %s)" %
                                 (dpid, port.port_no, port.name))
        self.topology.printroute()
        self.logger.info('##################################')

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(10)

    def _request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

    def _mongo_ipc(self):
        while True:
            try:
                time.sleep(0.05)
                message = self.server_ipc.recv_msg.pop(0)
                of_message = json.loads(message)
                dp_id=1
                if ("IP" in of_message):
                    self.logger.info("=====> Configuration")
                    self.logger.info("=====> MAC: %(MAC)s Port: %(Port)s", of_message['Ports'][0])
                    ofproto = self.datapaths[dp_id].ofproto
                    parser = self.datapaths[dp_id].ofproto_parser
                    match = parser.OFPMatch(eth_dst=of_message['Ports'][0]["MAC"])
                    actions = [parser.OFPActionOutput(of_message['Ports'][0]["Port"])]
                    self.logger.info(
                        Fore.YELLOW + "[Add-Flow] " + Fore.WHITE +
                        "dpid=[%s]: dst=[%s] => port[%s]",
                        str(self.datapaths[dp_id].id), str(of_message['Ports'][0]["MAC"]),
                        Fore.WHITE+str(of_message['Ports'][0]["Port"])+Fore.WHITE)
                    self.add_flow(self.datapaths[dp_id], 1, match, actions)

                elif ("ADD" in of_message):
                    pass
                elif ("REMOVE" in of_message):
                    pass
                elif ("UPDATE" in of_message):
                    pass

            except IndexError, ex:
                pass
            except AttributeError, ex:
                self.logger.info("ERROR: %s", ex)
            except Exception, ex:
                self.logger.info("ERROR: %s", ex)

    def _get_mac_from_database(self, ip):
        # Retorna o MAC do host especificado
        pass

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """
		 Adiciona a regra de fluxo no plano de dados associado
		"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    def delete_flow(self, datapath):
        """
		 Deleta uma regra de fluxo no plano de dados associado
		"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        for dst in self.mac_to_port[datapath.id].keys():
            match = parser.OFPMatch(eth_dst=dst)
            mod = parser.OFPFlowMod(
                datapath, command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY,
                priority=1, match=match)
            datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        # Abrir o protocolo OpenFlow
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)

        # Abrir o header Ethernet
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        # Define o DPID do switch
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})
        # Get ARP Protocol
        # p_arp  = self._find_protocol(pkt, "arp")
        # Get VLAN Protocol
        # p_vlan = self._find_protocol(pkt, "vlan")

        # Get IPv4 or IPv6 headers
        # p_ipv4 = pkt.get_protocols(ipv4.ipv4)
        # p_ipv6 = pkt.get_protocols(ipv6.ipv6)

        # Get TCP or UDP headers
        # p_tcp = pkt.get_protocols(tcp.tcp)
        # p_udp = pkt.get_protocols(udp.udp)

        self.logger.info(
            Fore.CYAN + "[Packet-In] " + Fore.WHITE +
            "in_port=[%s] dpid=[%s] src=[%s] dst=[%s]", in_port,
            Fore.WHITE + src + Fore.WHITE,
            Fore.WHITE + dst + Fore.WHITE, dpid )

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            self.logger.info(
                Fore.YELLOW + "[Add-Flow] " + Fore.WHITE +
                "dpid=[%s]: in_port=[%s] => dst=[%s]",
                dpid, in_port, Fore.WHITE + dst + Fore.WHITE)
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        self.logger.info(
            Fore.GREEN+"[Packet-Out] "+Fore.WHITE+
            "dpid=[%s]: in_port=[%s] => dst=[%s] -> out_port[FLOOD]",
            dpid, in_port, Fore.WHITE+dst+Fore.WHITE)

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        # Convert DPID to String
        dpid_str = dpid_lib.dpid_to_str(dp.id)

        if msg.reason == ofp.OFPPR_ADD:
            reason = Fore.YELLOW + 'ADD' + Fore.WHITE
        elif msg.reason == ofp.OFPPR_DELETE:
            reason = Fore.YELLOW + 'DELETE' + Fore.WHITE
        elif msg.reason == ofp.OFPPR_MODIFY:
            reason = Fore.YELLOW + 'MODIFY' + Fore.WHITE
        else:
            reason = Fore.YELLOW + 'UNKNOWN' + Fore.WHITE

        if msg.desc.state == 1:
            state = Fore.RED + 'DOWN' + Fore.WHITE
        elif msg.desc.state == 0:
            state = Fore.GREEN + 'UP' + Fore.WHITE
            self.nodes_restore.append(dp.id)
        else:
            state = Fore.ORANGE + 'UNKNOWN' + Fore.WHITE

        self.logger.info(Fore.MAGENTA + "[Port State Change]" + Fore.WHITE +
                         "dpid=[%s] msg=[%s] port=[%s] state=[%s]",
                         int(dpid_str), reason, msg.desc.port_no, state)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]

        self.add_flow(datapath, 0, match, actions)

    @set_ev_cls(event.EventLinkAdd, MAIN_DISPATCHER)
    def link_add_handler(self, ev):
        self.logger.info(Fore.MAGENTA + "[Change Topology]" + Fore.WHITE + "Link: SRC=[%s] DST=[%s] ["
                         + Fore.GREEN + "UP" + Fore.WHITE + "]",
                         ev.link.src.dpid,
                         ev.link.dst.dpid)

    @set_ev_cls(event.EventLinkDelete, MAIN_DISPATCHER)
    def link_delete_handler(self, ev):
        self.logger.info(Fore.MAGENTA + "[Change Topology] " + Fore.WHITE + "Link: SRC=[%s] DST=[%s] ["
                         + Fore.RED + "DOWN" + Fore.WHITE + "]",
                         ev.link.src.dpid,
                         ev.link.dst.dpid)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if not datapath.id in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body
        self.logger.info('datapath         '
                         'in-port  eth-dst           '
                         'out-port packets  bytes')
        self.logger.info('---------------- '
                         '-------- ----------------- '
                         '-------- -------- -------- --------')
        dp_id = str(ev.msg.datapath.id)
        if len(self.traffic_flow) == 0:
            self.traffic_flow[dp_id] = {}
            self.traffic_flow[dp_id]['time'] = time.time()

        for stat in sorted([flow for flow in body if flow.priority >= 1],
                            key=lambda flow: (flow.match['eth_dst'])):
                            #key=lambda flow: (flow.match['in_port'],
                                             #flow.match['eth_dst'])):
            self.logger.info('%016x %8x %17s %8x %8d %8d %8d %s',
                             ev.msg.datapath.id,
                             stat.match.get('in_port', 65535), stat.match['eth_dst'],
                             stat.instructions[0].actions[0].port,
                             stat.packet_count, stat.byte_count, stat.priority, str(stat.match))
            # Send Statistics for Router Server
            # JSON pack
            traffic_msg = {}
            traffic_msg['stats'] = {}
            traffic_msg['stats']['switch'] = ev.msg.datapath.id
            # Match
            traffic_msg['stats']['match'] = {}
            traffic_msg['stats']['match']['in_port'] = stat.match.get('in_port', 65535)

            if 'tcp_src' in stat.match:
                traffic_msg['stats']['match']['tcp_src'] = stat.match['tcp_src']
            if 'tcp_dst' in stat.match:
                traffic_msg['stats']['match']['tcp_dst'] = stat.match['tcp_dst']
            if 'udp_src' in stat.match:
                traffic_msg['stats']['match']['udp_src'] = stat.match['udp_src']
            if 'udp_dst' in stat.match:
                traffic_msg['stats']['match']['udp_dst'] = stat.match['udp_dst']

            if 'eth_src' in stat.match:
                traffic_msg['stats']['match']['eth_src'] = stat.match['eth_src']
            if 'eth_dst' in stat.match:
                traffic_msg['stats']['match']['eth_dst'] = stat.match['eth_dst']
            if 'ipv4_dst' in stat.match and 'ipv4_src' in stat.match:
                traffic_msg['stats']['match']['ipv4_src'] = "/".join(stat.match['ipv4_src'])
                traffic_msg['stats']['match']['ipv4_dst'] = "/".join(stat.match['ipv4_dst'])
                traffic_msg['stats']['byte_count'] = stat.byte_count
                traffic_json = json.dumps(traffic_msg)
                self.server_ipc.send(SERVER_PROXY_CHANNEL, SERVER_ID, traffic_json)
            elif 'ipv4_src' in stat.match:
                traffic_msg['stats']['match']['ipv4_src'] = "/".join(stat.match['ipv4_src'])
                traffic_msg['stats']['byte_count'] = stat.byte_count
                traffic_json = json.dumps(traffic_msg)
                self.server_ipc.send(SERVER_PROXY_CHANNEL, SERVER_ID, traffic_json)
            elif 'ipv4_dst' in stat.match:
                traffic_msg['stats']['match']['ipv4_dst'] = "/".join(stat.match['ipv4_dst'])
                traffic_msg['stats']['byte_count'] = stat.byte_count
                traffic_json = json.dumps(traffic_msg)
                self.server_ipc.send(SERVER_PROXY_CHANNEL, SERVER_ID, traffic_json)

        self.traffic_flow[dp_id]['time'] = time.time()

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body

        self.logger.info('datapath         port     '
                         'rx-pkts  rx-bytes rx-error '
                         'tx-pkts  tx-bytes tx-error')
        self.logger.info('---------------- -------- '
                         '-------- -------- -------- '
                         '-------- -------- --------')
        dp_id = str(ev.msg.datapath.id)
        if len(self.traffic_port) == 0:
            self.traffic_port[dp_id] = {}
            self.traffic_port[dp_id]['time'] = time.time()

        for stat in sorted(body, key=attrgetter('port_no')):
            self.logger.info('%016x %8x %8d %8d %8d %8d %8d %8d',
                             ev.msg.datapath.id, stat.port_no,
                             stat.rx_packets, stat.rx_bytes, stat.rx_errors,
                             stat.tx_packets, stat.tx_bytes, stat.tx_errors)
            # Send Statistics for Router Server
            # JSON pack
            traffic_msg = {}
            traffic_msg['stats'] = {}
            traffic_msg['stats']['switch'] = ev.msg.datapath.id
            traffic_msg['stats']['port_no'] = stat.port_no
            traffic_msg['stats']['rx'] = 0.0
            traffic_msg['stats']['tx'] = 0.0

            port_no = str(stat.port_no)
            rx_bytes = float(stat.rx_bytes)
            tx_bytes = float(stat.tx_bytes)

            if port_no not in self.traffic_port[dp_id]:
                self.traffic_port[dp_id][port_no] = {}
                self.traffic_port[dp_id][port_no]['rx'] = rx_bytes
                self.traffic_port[dp_id][port_no]['tx'] = tx_bytes

            old_rx_bytes = float(self.traffic_port[dp_id][port_no]['rx'])
            old_tx_bytes = float(self.traffic_port[dp_id][port_no]['tx'])
            new_time = time.time()
            diff_time = new_time - self.traffic_port[dp_id]['time']
            try:
                new_rx = (((rx_bytes - old_rx_bytes)*8)/diff_time)
                new_tx = (((tx_bytes - old_tx_bytes)*8)/diff_time)
                traffic_msg['stats']['rx'] = round(new_rx, 1)
                traffic_msg['stats']['tx'] = round(new_tx, 1)
            except ZeroDivisionError:
                pass
            self.traffic_port[dp_id][port_no]['rx'] = rx_bytes
            self.traffic_port[dp_id][port_no]['tx'] = tx_bytes

            traffic_json = json.dumps(traffic_msg)

            if (stat.port_no > 65535):
                break;

            #self.server_ipc.send(SERVER_PROXY_CHANNEL, SERVER_ID, traffic_json)

        self.traffic_port[dp_id]['time'] = time.time()
