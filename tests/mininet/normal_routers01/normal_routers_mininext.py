#!/usr/bin/python

"Create topology with 4 Quagga edge routers"

import inspect, os, sys, atexit
# Import topo from Mininext
from mininext.topo import Topo
# Import quagga service from examples
from mininext.services.quagga import QuaggaService
# Other Mininext specific imports
from mininext.net import MiniNExT as Mininext
from mininext.cli import CLI
import mininext.util
# Imports from Mininet
import mininet.util
mininet.util.isShellBuiltin = mininext.util.isShellBuiltin
sys.modules['mininet.util'] = mininet.util

from mininet.util import dumpNodeConnections
from mininet.node import RemoteController
from mininet.node import Node
from mininet.link import Link
from mininet.log import setLogLevel, info
from collections import namedtuple
#from mininet.term import makeTerm, cleanUpScreens
QuaggaHost = namedtuple("QuaggaHost", "name ip mac port")
net = None


class QuaggaTopo( Topo ):
    "Quagga topology example."

    def __init__( self ):

        "Initialize topology"
        Topo.__init__( self )

        "Directory where this file / script is located"
        scriptdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # script directory

        "Initialize a service helper for Quagga with default options"
        quaggaSvc = QuaggaService(autoStop=False)

        "Path configurations for mounts"
        quaggaBaseConfigPath=scriptdir + '/configs/'

        "List of Quagga host configs"
        quaggaHosts = []
        quaggaHosts.append(QuaggaHost(
                           name = 'r01',
                           ip = '172.0.0.1/16',
                           mac = '08:00:27:89:3b:9f',
                           port = 1))
        quaggaHosts.append(QuaggaHost(
                           name = 'r02',
                           ip = '172.0.0.2/16',
                           mac ='08:00:27:92:18:1f',
                           port = 2))
        quaggaHosts.append(QuaggaHost(
                           name = 'r03',
                           ip = '172.0.0.3/16',
                           mac = '08:00:27:54:56:ea',
                           port = 3))

        "Add switch"
        s1, s2, s3, s4, s5, s6 = [
            self.addSwitch( s ) for s in 's1', 's2', 's3', 's4', 's5', 's6'
        ]

        "Setup each legacy router, add a link between it and the IXP fabric"
        for host in quaggaHosts:
            "Set Quagga service configuration for this node"
            quaggaSvcConfig = \
            { 'quaggaConfigPath' : scriptdir + '/configs/' + host.name }

            quaggaContainer = self.addHost( name=host.name,
                                            ip=host.ip,
                                            mac=host.mac,
                                            privateLogDir=True,
                                            privateRunDir=True,
                                            inMountNamespace=True,
                                            inPIDNamespace=True)
            self.addNodeService(node=host.name, service=quaggaSvc,
                                nodeConfig=quaggaSvcConfig)
            "Attach the quaggaContainer to the IXP Fabric Switch"
            self.addLink( quaggaContainer, s1 , port2=host.port)

            # Adicionando Roteadores agregados
            a03_config = \
            { 'quaggaConfigPath' : scriptdir + '/configs/' + 'a03' }
            a03 = self.addHost( name='a03',
                                        ip='22.0.0.1/24',
                                        privateLogDir=True,
                                        privateRunDir=True,
                                        inMountNamespace=True,
                                        inPIDNamespace=True)
            self.addNodeService(node='a03', service=quaggaSvc,
                            nodeConfig=a03_config)
            self.addLink(s6, a03)


            if(host.name == 'r02'):
                cli01r02_config = \
                { 'quaggaConfigPath' : scriptdir + '/configs/' + 'cli01r02' }
                # Adicionando Roteadores agregados
                cli01r02 = self.addHost( name='cli01r02',
                                            ip='10.0.0.2/24',
                                            privateLogDir=True,
                                            privateRunDir=True,
                                            inMountNamespace=True,
                                            inPIDNamespace=True)
                self.addNodeService(node='cli01r02', service=quaggaSvc,
                                nodeConfig=cli01r02_config)

                a02_config = \
                { 'quaggaConfigPath' : scriptdir + '/configs/' + 'a02' }
                # Adicionando Roteadores agregados
                a02 = self.addHost( name='a02',
                                            ip='11.0.0.2/24',
                                            mac='00:00:11:00:00:02',
                                            privateLogDir=True,
                                            privateRunDir=True,
                                            inMountNamespace=True,
                                            inPIDNamespace=True)
                self.addNodeService(node='a02', service=quaggaSvc,
                                nodeConfig=a02_config)

                self.addLink(s2, quaggaContainer)
                self.addLink(s3, quaggaContainer)
                self.addLink(s2, cli01r02)
                self.addLink(s3, a02)
                self.addLink(s6, a02)

            elif(host.name == 'r01'):
                a01_config = \
                { 'quaggaConfigPath' : scriptdir + '/configs/' + 'a01' }
                # Adicionando Roteadores agregados
                a01 = self.addHost( name='a01',
                                            ip='12.0.0.2/24',
                                            mac='00:00:12:00:00:02',
                                            privateLogDir=True,
                                            privateRunDir=True,
                                            inMountNamespace=True,
                                            inPIDNamespace=True)
                self.addNodeService(node='a01', service=quaggaSvc,
                                nodeConfig=a01_config)

                self.addLink(s4, quaggaContainer)
                self.addLink(s4, a01)
                self.addLink(s5, a01)
                self.addLink(s5, a03)

def addInterfacesForNetwork( net ):
    hosts=net.hosts
    print "Configuring participating ASs\n\n"
    for host in hosts:
        print "Host name: ", host.name
        host.cmd( 'sysctl net.ipv4.ip_forward=1' )
        if host.name=='r01':
            host.cmd('sudo ifconfig lo:1 100.0.0.1 netmask 255.255.255.0 up')
            host.cmd('sudo ifconfig lo:2 100.0.0.2 netmask 255.255.255.0 up')
            host.cmd('sudo ifconfig lo:110 110.0.0.1 netmask 255.255.255.0 up')
            host.cmd('sudo ifconfig r01-eth1 12.0.0.1 netmask 255.255.255.0 up')
        if host.name=='r02':
            host.cmd('sudo ifconfig lo:110 110.0.0.1 netmask 255.255.255.0 up')
            host.cmd('sudo ifconfig lo:111 110.0.0.2 netmask 255.255.255.0 up')
            host.cmd('sudo ifconfig r02-eth1 10.0.0.1 netmask 255.255.255.0 up')
            host.cmd('sudo ifconfig r02-eth2 11.0.0.1 netmask 255.255.255.0 up')
        if host.name=='r03':
            host.cmd('sudo ifconfig lo:140 140.0.0.1 netmask 255.255.255.0 up')
        if host.name=='cli01r02':
            host.cmd('sudo ifconfig lo:150 150.0.0.1 netmask 255.255.255.0 up')

        if host.name == 'a01':
            host.cmd('sudo ifconfig a01-eth1 22.0.0.2 netmask 255.255.255.0 up')
        if host.name == 'a02':
            host.cmd('sudo ifconfig a02-eth1 21.0.0.2 netmask 255.255.255.0 up')
        if host.name == 'a03':
            host.cmd('sudo ifconfig a03-eth2 21.0.0.1 netmask 255.255.255.0 up')
        #if host.name == "exabgp":
        #    host.cmd( 'route add -net 172.0.0.0/16 dev exabgp-eth0')

def startNetwork():
    info( '** Creating Quagga network topology\n' )
    topo = QuaggaTopo()
    global net
    net = Mininext(topo=topo)

    info( '** Starting the network\n' )
    net.start()

    info( '**Adding Network Interfaces for SDX Setup\n' )
    addInterfacesForNetwork(net)

    info( '** Running CLI\n' )
    CLI( net )

def stopNetwork():
    if net is not None:
        info( '** Tearing down Quagga network\n' )
        net.stop()

if __name__ == '__main__':
    # Force cleanup on exit by registering a cleanup function
    atexit.register(stopNetwork)

    # Tell mininet to print useful information
    setLogLevel('info')
    startNetwork()
