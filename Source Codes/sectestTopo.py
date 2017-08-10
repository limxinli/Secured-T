#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, UserSwitch, OVSSwitch
from mininet.node import IVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, Intf
from subprocess import call

def myNetwork():

    net = Mininet( topo=None,
                   build=False,
                   switch=OVSSwitch)

    info( '*** Adding controller\n' )
    ryu_ctl=net.addController(name='c0',
                      controller=RemoteController)

    info( '*** Add switches\n')
    s1 = net.addSwitch('s1', dpid='00000002', protocols='OpenFlow13')
    Intf( 'eth0', node=s1 )
    s2 = net.addSwitch('s2',  dpid='0000000A', protocols='OpenFlow13')
    Intf( 'eth1', node=s2 )

    info( '*** Add hosts\n')
    h1 = net.addHost('h1')

    info( '*** Add links\n')
    net.addLink(h1,s1)
    net.addLink(h1,s2)

    info( '*** Starting network\n')
    net.build()

    info( '*** Starting switches\n')
    net.get('s1').start([ryu_ctl])
    net.get('s2').start([ryu_ctl])

    info( '*** Post configure switches and hosts\n')
    s1.cmd("sudo ifconfig eth0 0")
    s1.cmd("sudo ifconfig eth1 0")
    s1.cmd("sudo ifconfig s1 192.168.137.128/24")
    s1.cmd("sudo route add -net 192.168.137.0/24 dev s1")
    s2.cmd("sudo ifconfig s2 192.168.237.138/24")
    s2.cmd("sudo route add -net 192.168.237.0/24 dev s2")
    s2.cmd("sudo route add default gw 192.168.137.2")
    h1.cmd("sudo ifconfig h1-eth0 192.168.137.150/24")
    h1.cmd("sudo ifconfig h1-eth1 192.168.237.150/24")
    h1.cmd("sudo route add default gw 192.168.137.2")
    h1.cmd("sudo sysctl -w net.ipv4.ip_forward=1")
    h1.cmd("sudo iptables -t nat -A POSTROUTING -o h1-eth0 -j MASQUERADE")
    h1.cmd("sudo iptables -A FORWARD -i h1-eth1 -o h1-eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT")
    h1.cmd("sudo iptables -A FORWARD -i h1-eth0 -o h1-eth1 -j ACCEPT")
    CLI(net)
    # the user has exited the mininet prompt.
    # need to stop the net and restore the host IP configurations
    s2.cmd('sudo ip addr add 192.168.237.138/24 dev eth1')
    s1.cmd('sudo ifconfig  eth0 down')
    s1.cmd('sudo ifconfig  eth0 up')
    #s1.cmd('sudo dhclient eth0')
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    myNetwork()

