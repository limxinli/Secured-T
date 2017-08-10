#!/usr/bin/env python
# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, arp, ipv4, icmp, tcp
from ryu.lib.packet import ether_types
from ryu.utils import binary_str


class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    whitelist = {}
##    whitelist["192.168.237.138"]=1
    ip_pat = r"192.168.237.(1[7-9][0-9]|2[0-3][0-9])"
    spec_pat = r"244.0.0"
    
    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        
        
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
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        # experiment of drop actons.
        #match2=parser.OFPMatch(ipv4_dst="164.78.252.49")
        #dropAction = [ parser.OFPInstructionActions(ofproto.OFPIT_CLEAR_ACTIONS, [])]
        #self.add_flow(datapath, 3, match2, dropAction)
        #match3=parser.OFPMatch(ipv4_dst="164.78.248.110")
        #self.add_flow(datapath, 3, match3, dropAction)
        
        #instruction = [ parser.OFPInstructionActions(ofproto.OFPIT_CLEAR_ACTIONS, []) ]

        #req = datapath.ofproto_parser.OFPFlowMod(datapath, 0, 0, table_id,ofp.OFPFC_DELETE,0,0,1,ofp.OFPCML_NO_BUFFER,ofp.OFPP_ANY,ofp.OFPG_ANY,0, match2,instructions)
        #req = parser.OFPFlowMod(datapath,
        #                    table_id = 0,
        #                    priority = 3,
        #                    command = ofproto.OFPFC_ADD,
        #                    match = match2,
        #                    instructions = instruction
        #                    )
        #datapath.send_msg(req)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)
        
    def checkTarget(self,in_port,dpid,pkt,datapath,parser,msg):
        data = msg.data
        ofproto = datapath.ofproto
        retval=False    # assume no need to block
        match = None
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        #self.logger.info("Packets in dpID: %s, SRC_MAC: %s, DST_MAC: %s, IN_PORT: %s", dpid, src, dst, in_port)
        #The following protocols can be used for debugging
        arp_pkt = pkt.get_protocol(arp.arp)
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
        icmp_pkt = pkt.get_protocol(icmp.icmp)
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        if ipv4_pkt:
            #if ipv4_pkt.dst in ["164.78.248.110","164.78.252.49"]:
            if ipv4_pkt.dst in self.whitelist:
                #match= parser.OFPMatch(in_port=in_port, eth_dst=dst, ipv4_dst=ipv4_pkt.dst)
                match=ipv4_pkt.dst
                #print("Got a new match ! from inport {}".format(in_port))
                payload = pkt.protocols[-1]
                #if isinstance(payload,str):
                #    print "<"
                #    print payload
                #    print type(payload)
                #    print ">"
                retval = False
            elif ipv4_pkt.dst.startswith( '192.168.137' ) or ipv4_pkt.dst.startswith('192.168.237'):
                # also allow packets to go to internal hosts.
                retval = False
            else:
               #self.logger.info("Blocking, ipv4 pkt. dst_ip : %s",ipv4_pkt.dst)
               # print self.whitelist.keys()
                retval=True
        return (retval,match)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})
        newmatch = None
        #self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)
        p_level = 2
        if ipv4_pkt and ipv4_pkt.dst=="192.168.237.138":
            #print "trouble {}".format(ipv4_pkt.src)
        if dpid == 10: # dpid = 10, SW2 dpid is 10
            # need to check if need the target ip is valid.
            blocked,newmatch = self.checkTarget(in_port,dpid,pkt,datapath,parser,msg)
            if blocked:
                # drop the current packet
                return
            #print("return from checkTarget and newmatch is {}".format(newmatch))
        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
            #print "out_port is {}".format(out_port)
        else:
            out_port = ofproto.OFPP_FLOOD
        #define the send to out_port action
        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid triggering the packet_in next time
        # we also never add any flow for dpid 10 unless it has a ipv4 header.
        if out_port != ofproto.OFPP_FLOOD:
            if dpid == 10:
                if ipv4_pkt:
                    print "bingo {}".format(ipv4_pkt.dst)
                    match = parser.OFPMatch(in_port=in_port, eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=ipv4_pkt.dst)
                    if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                        # in this case, the actual packet payload has been buffered at the ovswitch.
                        # add the flowing flow (with buffer_id) to send out the data.
                        self.add_flow(datapath, 3, match, actions, msg.buffer_id)
                        return
                    else:
                        self.add_flow(datapath, 3, match, actions)
            else:
                # This is the case of dpid != 10
                match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
                # verify if we have a valid buffer_id, if yes avoid to send both
                # flow_mod & packet_out
                if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                    # in this case, the actual packet payload has been buffered at the ovswitch.
                    # add the flowing flow (with buffer_id) to send out the data.
                    self.add_flow(datapath, p_level, match, actions, msg.buffer_id)
                    return
                else:
                    self.add_flow(datapath, p_level, match, actions)
        #else:
        #    out_port = ofproto.OFPP_FLOOD
         
        data = None # assume the packet payload has been buffered at the ovswitch.
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
