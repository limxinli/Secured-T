#!/usr/bin/env python
from dnslib import *
#from IPy import IP
import threading, operator, time
import SocketServer, socket, sys, os
import imp
my_db = imp.load_source('my_db', '/home/securedt/my_db.py')
import binascii
import pymysql
import re
import MySQLdb
import Queue, dpkt
import requests, json

allowed_domains = {}
ipqueue = Queue.Queue(100) #max size of 100 should be big enough
ipmap  = {}

class DNSHandler():
    def fakeResponse(self, data, dominio, ip):
        packet=''
        if dominio:
            packet+=data[:2] + "\x81\x80"
            packet+=data[4:6] + data[4:6] + '\x00\x00\x00\x00'   # Questions and Answers Counts
            packet+=data[12:]                                         # Original Domain Name Question
            packet+='\xc0\x0c'                                             # Pointer to domain name
            packet+='\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'             # Response type, ttl and resource data length -> 4 bytes
            packet+=str.join('',map(lambda x: chr(int(x)), ip.split('.'))) # 4bytes of IP
        return packet

    def parse(self,data,client_address):
        ip_src = ""
        if client_address:
            if client_address[0]:
                ip_src = client_address[0]

        response = ""
        qname=""

        try:
            # Parse data as DNS
            d = DNSRecord.parse(data)
            qname = str(d.q.qname)
            print '[',qname,']'
        except Exception, e:
            print "[%s] %s: ERROR: %s" % (time.strftime("%H:%M:%S"), self.client_address[0], "Invalid DNS request")

        else:
            for p in allowed_domains:
                if re.search(p,qname):
                    response = self.proxyrequest(data)
                    if response:
                        dnsresp = dpkt.dns.DNS(response)
                        #print "%d bytes received, id is %d" % (len(response), dnsresp.id)
                        if dnsresp and dnsresp.an:
                            for rr in dnsresp.an:
                                #print "AN: class is %d, type is %d, name is %s" % (rr.cls, rr.type, rr.name)
                                if hasattr(rr, 'ip'):
                                    #try to resolve the resp to IP address and put in ipqueue
                                    ip=socket.inet_ntoa(rr.ip)
                                    if ip not in ipmap:
                                        ipqueue.put(ip)
                     	return response
    
       #reach here, means must block.
	print "Faking"
	response =self.fakeResponse(data,qname, "192.168.237.138")
    #response = self.proxyrequest(data)
    #add code here
        return response

# Obtain a response from a real DNS server.
    def proxyrequest(self, request, port="53"):
        print "proxyreq"
        reply = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3.0)
            # Send the proxy request to a randomly chosen DNS server
            sock.sendto(request, ('192.168.137.2', int(port)))
            reply = sock.recv(1024)
            sock.close()

        except Exception, e:
            print "[!] Could not proxy request: %s" % e
        else:
            return reply


# UDP DNS Handler for incoming requests
class UDPHandler(DNSHandler, SocketServer.BaseRequestHandler):
    #def setup(self):
    #    print "starting a new UDPHandler"
    #    print self.server.mydb.getVersion()
         
    def handle(self):
        #print self.client_address
        (data,socket) = self.request
        response = self.parse(data,self.client_address)

        if response:
            socket.sendto(response, self.client_address)
    def finish(self):
        print "Terminating an UDPHandler"
         

class ThreadedUDPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):

    # Override SocketServer.UDPServer to add extra parameters
    def __init__(self, server_address, RequestHandlerClass):
      
        self.address_family =  socket.AF_INET
        SocketServer.UDPServer.__init__(self,server_address,RequestHandlerClass)            

modid = raw_input("Please enter assessment ID: ")

try:
        
    server = ThreadedUDPServer(("0.0.0.0", 53), UDPHandler)
    #open database
    dbobj = my_db.PnetMacDB('localhost', 'sectest', 'sectestDB' , '1qwer$#@!')
        

    def DNdata():
        #open SQL connection
        conn = dbobj.dbOpen()
        #prepare cursor obj using cursor() method
        cur = dbobj.conn.cursor()
        #SQL command
        sql="""SELECT C_DOMAIN_NAME FROM sectestDB.T_WHITELIST_DOMAIN WHERE C_ASSESSMENT_ID = ('%s')""" % modid
        #execute query
        cur.execute(sql)
        #fetch all rows in query
        data = cur.fetchall()
        #print the rows
        for x in data:
            allowed_domains[x[0]]=1
        #close connection
        dbobj.dbClose(conn)
        return allowed_domains

    DNdata()

    # Start a thread with the server -- that thread will then start one
    # more threads for each request
    print "Starting server"
    server_thread = threading.Thread(target=server.serve_forever)
    # Exit the server thread when the main thread terminates
    server_thread.daemon = True
    server_thread.start()

    # Loop in the main thread
    while True:
        time.sleep(3)
        while not ipqueue.empty():
            ip = ipqueue.get()
            print "try to add {}".format(ip)
            if ip not in ipmap:
                ipmap[ip]=1
                #expect to send the new valid ip address to the ryu controller
                url = 'http://127.0.0.1:8080/myswitch/cmd/2'
                payload = {'cmd': '2'}
                payload["whiteip"]= ip
                print payload
                # Create your header as required
                headers = {"content-type": "application/json", "Authorization": "<auth-key>" }
                r = requests.put(url, data=json.dumps(payload), headers=headers)

except (KeyboardInterrupt, SystemExit):
    server.shutdown()
    print "[*] DNS Proxy is shutting down."
    sys.exit()
