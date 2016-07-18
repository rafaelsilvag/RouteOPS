#!/usr/bin/env python
# coding: utf-8
'''
Created on Jul 25, 2014

@author: Gilmar Luiz Vassoler
@modified: Rafael S. Guimarães e Dione Sousa Albuquerque
'''

import logging
from ryu.ofproto import nx_match
from ryu.lib.mac import haddr_to_bin
import networkx as nx
import time

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
# LOG.setLevel(logging.INFO)
logging.basicConfig()


class Node(object):

	def __init__(self, dpid, dp):
		self.dpid = dpid
		self.dp = dp
		self.ip = dp.socket.getpeername()[0] # get MGMT IP from connection
		self.binaddr = None
		self.host = None
		self.mac = None
		self.neighbors = {}     # neighbors[neighboraddr]  --> port object
		self.mac_to_port = {}   # mac_to_port[mac] --> port_no
		self.host_port = {}     # host_port[port] --> port_name
		self._binAddr(self.dpid)

	def __str__(self):
		return "(%s)" % (self.binaddr)

	def _binAddr(self, dpid):
		#~ host = int(ip.split('.')[3]) - ]) - 1
		host = dpid -1
		self.binaddr = "{0:b}".format(host)
		self.host = host
		self.mac = "00:00:00:%02x:00:01" % (self.host)

	def set_binAddr(self, binaddr):
		if self.binaddr is None:
			self.binaddr = binaddr
			self.host = int(binaddr, base=2)
			self.mac = "00:00:00:%02x:00:01" % (self.host)

class Topology(object):

	def __init__(self, nodes, allnodes=True):
		self.networtcontrollerport=None
		self.rootnode = None
		self.nodes = {}   # self.nodes[dpid] --> node
		self.visitednodes = []  # list of nodes visited and with binaddr
		self.graph = nx.Graph() # From NetworkX framework
		#~ self.gray
		self.generateTopology(nodes, allnodes) # Retorna um grafo em formato de hypercube

	def _distanceToDestination(self, n1, n2):
		path = n1 ^ n2
		distance=0;
		base = 2;
		while (path != 0):
			if ((path % base) == 1):
				distance = distance + 1
			path = path / base
		return distance;

	def _isNeighbors(self, n1, n2):
		if (self._distanceToDestination(n1, n2) == 1):
			return True
		else:
			return False

	def _freeNeighborAddr(self, node):
		for h in self.nodesaddr:
			if (self._isNeighbors(h, node.host)):
				self.nodesaddr.remove(h)
				return h
		return None

	def _neighborsBinAddr(self, src, dst):
		if (src.binaddr is not None) and (dst.binaddr is None):
			binaddr = self._binTostr(self._freeNeighborAddr(src))
			if binaddr is None:
				return
			dst.set_binAddr(binaddr)

		if (src.binaddr is None) and (dst.binaddr is not None):
			binaddr = self._binTostr(self._freeNeighborAddr(dst))
			if binaddr is None:
				return
			src.set_binAddr(binaddr)

	def _hostPorts(self, dp, port_type=None):
		for port in dp.ports.values():
			LOG.debug("Dpid %s, port (%s, %s)" % (dp.id, port.port_no, port.name))
			self.add_hostPort(dp.id, port, port_type)
		LOG.debug(sorted(self.nodes[dp.id].host_port.values()))

	def _rootNode(self):
		# Try find a node with all neighbors and put the address 0000
		maxneighbors = self.degree
		while (maxneighbors > 0):
			for node in self.nodes.values():
				if len(node.neighbors) == maxneighbors:
					LOG.debug("root is %s" % node.dpid)
					binaddr = self._binTostr(self.nodesaddr.pop(0))
					print "Root: addr %s" % binaddr
					node.set_binAddr(binaddr)
					return node
			maxneighbors -= 1
		return None

	def _visiteNodes(self, node):
		if len(self.visitednodes) == len(self.nodes):
			return
		if node in self.visitednodes:
			return
		# add node to visitednodes list
		self.visitednodes.append(node)
		LOG.debug("Visiting node %s " % node.host)
		#~ for n in node.neighbors.iterkeys():
		    #~ neighbor = self.nodes[n]
		    #~ self._neighborsBinAddr(node, neighbor)
		    #~ LOG.debug("Visinho %s " % neighbor.host)
		for n in node.neighbors.iterkeys():
			neighbor = self.nodes[n]
			self._neighborsBinAddr(node, neighbor)
			self._visiteNodes(neighbor)

	def add_link(self, link):
		# Se nao existir representa um erro.
		if link.src.dpid not in self.nodes:
			return
		if link.dst.dpid not in self.nodes:
			return

		src = self.nodes[link.src.dpid]
		dst = self.nodes[link.dst.dpid]

		# Adicionar os vizinhos
		if dst.dpid not in src.neighbors:
			src.neighbors[dst.dpid] = link.src  # Port object
		if src.dpid not in dst.neighbors:
			dst.neighbors[src.dpid] = link.dst  # Port object

		# Adiciona ao graph para rotas
		self.graph.add_edge(src.dpid,dst.dpid)

	def del_link(self, link):
		# Se nao existir representa um erro.
		if link.src.dpid not in self.nodes:
			return
		if link.dst.dpid not in self.nodes:
			return

		src = self.nodes[link.src.dpid]
		dst = self.nodes[link.dst.dpid]

		# remove os vizinhos
		if dst.dpid in src.neighbors:
			del src.neighbors[dst.dpid]

		if src.dpid in dst.neighbors:
			del dst.neighbors[src.dpid]
		# Remove do graph para rotas

		if self.graph.has_edge(src.dpid,dst.dpid):
			try:
				self.graph.remove_edge(src.dpid,dst.dpid)
			except:
				LOG.info("Exception: NetworkXError")

	def fail_nodes(self, s_dpid, d_dpid):
		# Notifica nós em falha
		src = self.nodes[s_dpid]
		dst = self.nodes[d_dpid]

		if self.graph.has_edge(src.dpid,dst.dpid):
			try:
				self.graph.remove_edge(src.dpid,dst.dpid)
			except:
				LOG.info("Exception: NetworkXError")

	def restore_nodes(self, s_dpid, d_dpid):
		# Restaura na topologia os nós que
		# estavam em falha
		src = self.nodes[s_dpid]
		dst = self.nodes[d_dpid]
		# Adiciona ao graph para rotas
		try:
			self.graph.add_edge(src.dpid,dst.dpid)
		except Exception, ex:
			print ex.message

	def add_node(self, dp):
		# Adiciona os nos ao cubo
		if dp.id not in self.nodes:
			for port in dp.ports.values():
				#~ if port.name.find(self.host_port_type) == 0:
				self.nodes[dp.id] = Node(dp.id, dp)

	def printroute(self):
		for src in self.nodes.iterkeys():
			print "[Neighors List] neighbor = %s" % (src)
			print nx.neighbors(self.graph, src)
			print "[Shortest Paths] - %s " % (src)
			for dst in self.nodes.iterkeys():
				if src != dst:
					print nx.shortest_path(self.graph, src, dst)

	def get_route(self, src, dst):
		# Get Route to destination DPID
		return nx.shortest_path(self.graph, src, dst)

	def get_neighbors(self, src):
		# Return neighbors to source DPID
		return nx.neighbors(self.graph, src)

	def generateTopology(self, swiches, allnodes=False):
		# Adiciona os nos ao cubo
		if allnodes == True: # only mount a complet hypercube
			wait = True
			while wait:
				for dp in swiches.dps.values():
					self.add_node(dp)
				#if len(self.nodes) == self.max:
				#	wait = False
				#print "[Join Nodes] Waiting all nodes..."
				time.sleep(2)

		# Adiciona os vizinhos aos nos
		for link in swiches.links:
			self.add_link(link)

	def add_macToPort(self, dpid, mac, port_no):
		# Manipulacao da lista de Mac --> numero da porta
		if dpid in self.nodes:
			node = self.nodes[dpid]
			node.mac_to_port[mac] = port_no

	def get_macToPort(self, dpid, mac):
		# return None if mac not in dict
		if dpid in self.nodes:
			node = self.nodes[dpid]
			return node.mac_to_port.get(mac)
		return None

	def del_macToPort(self, dpid, mac):
		if dpid in self.nodes:
			node = self.nodes[dpid]
			if mac in node.mac_to_port:
				del node.mac_to_port[mac]

	def getall_macToPort(self, dpid, port):
		if dpid in self.nodes:
			node = self.nodes[dpid]
			return [mac for (mac, port_) in node.mac_to_port.items() if port_ == port]

	def add_hostPort(self, dpid, port, port_type=None):
		# Manipulacao da lista portas para hosts
		if dpid in self.nodes:
			node = self.nodes[dpid]
			if port not in node.neighbors.values(): # se nao for uma porta para outro switch
				if port.port_no == 65534: # port to controller
					return
				if port.name.find("eth4") == 0: #Porta para o network controller
					self.networtcontrollerport = port.port_no
				if port_type is None:
					node.host_port[port.name] = port.port_no
				elif port.name.find(port_type) != -1:
					node.host_port[port.name] = port.port_no

	def get_hostPort(self, dpid, port_name):
		# return None if mac not in dict
		if dpid in self.nodes:
			node = self.nodes[dpid]
			return node.host_port.get(port_name)
		return None

	def del_hostPort(self, dpid, port_name):
		if dpid in self.nodes:
			node = self.nodes[dpid]
			if port_name in node.host_port:
				del node.host_port[port_name]

	def getall_hostPort(self, dpid):
		if dpid in self.nodes:
			node = self.nodes[dpid]
			return node.host_port.values()
		return
