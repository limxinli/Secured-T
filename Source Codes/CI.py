#!/usr/bin/env python
#
import MySQLdb, socket, threading, Queue, sys, os, select, datetime, string, random
from time import sleep

def DBconnect():
        db = MySQLdb.connect(host="localhost",    # your host, usually localhost
                                user="sectest",         # your username
                                passwd="1qwer$#@!",  # your password
                                db="sectestDB")        # name of the database
        return db

def processQueue(comq):
        db = DBconnect()
        cur = db.cursor()

        # here we will check if comq contains anything.
        # each queue item is a tuple which contains  ( adm No, ip address, isDisconnected)
        while not comq.empty():
                admNo,address,con_stat,cheat_stat = comq.get()
                #This is when client is detected to be disconnected
                if con_stat:
                        print " (" + address[0] + ")  has been DISCONNECTED"
                        cur.execute("UPDATE T_STUDENT_INFO SET C_DISCONNECTED=%s WHERE C_IP=%s AND C_PORT=%s", (1, address[0], address[1]))
                        db.commit()
                #each other subsequent reporting from the client comes here saying its ok, no disconnect or cheat.
                #update timestamp
                elif admNo == "OK":
                        print " Reporting from " + address[0]
                        cur.execute("UPDATE T_STUDENT_INFO SET C_TIMESTAMP=NOW() WHERE C_IP=%s AND C_PORT=%s", (address[0], address[1]))
                        db.commit()

                #Enter initial student data into the db
                if "OK" not in admNo and admNo != "cheat" and len(admNo) != 0: #if admin length is 8
                        print admNo, len(admNo)
                        cur.execute("INSERT INTO T_STUDENT_INFO (C_ADMISSION_NO, C_IP, C_PORT, C_TIMESTAMP, C_UNIQUE_CODE, C_CHEATING, C_DISCONNECTED, C_SS_KL, C_LOGIN) VALUES (%s, %s, %s, NOW(), %s, %s, %s, %s, %s)" , (admNo, address[0], address[1], ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6)), 0, 0, 0, 0))
                        db.commit()
                        print "inserted initial student info in db"

                #This is when client is detected to be cheating
                #since not disconnected, update timestamp as well
                if cheat_stat:
                        print address[0] + " is CHEATING!"
                        #When sees cheat, if cheating col has a '1', dont need do anything.
                        #else, set to '1'
                        cur.execute("SELECT C_CHEATING FROM T_STUDENT_INFO WHERE C_IP=%s AND C_PORT=%s", (address[0], address[1]))
                        db.commit()
                        cheat_value =  [int(record[0]) for record in cur.fetchall()]
                        print cheat_value
                        if cheat_value == [0]:
                                print "cheat value was 0. Setting to 1."
                                cur.execute("UPDATE T_STUDENT_INFO SET C_CHEATING=%s, C_TIMESTAMP=NOW(), C_SS_KL=%s WHERE C_IP=%s AND C_PORT=%s", (1, 1, address[0], address[1]))
                                db.commit()
                        else:
                                cur.execute("UPDATE T_STUDENT_INFO SET C_TIMESTAMP=NOW() WHERE C_IP=%s AND C_PORT=%s", (address[0], address[1]))
                                db.commit()

        db.close()

def ServerCmd(address):
        db = DBconnect()
        cursor = db.cursor()
        #Reads db and tries to check if there is any demand to log student
##        while True:
        print "try to read db"
        cursor.execute("SELECT C_SS_KL, C_DISCONNECTED FROM T_STUDENT_INFO WHERE C_IP=%s AND C_PORT=%s", (address[0], address[1])) #get with IP and port
        db.commit()
##        discon_stat = [int(record[1]) for record in cursor.fetchall()]
        demand = [int(record[0]) for record in cursor.fetchall()]
        #print demand
        if demand == [1]: #demand ss and kl
                #print "Logging started"
                response = "demand"
        elif demand == [0]:
                #print "No demand / Stops"
                response = "nodemand"
##        elif discon_stat == [1]:
##                response = "terminate"
        else:
                print "nothing"
                response = "nothing"
        sleep(2)
        db.close()
        return response
        

def handler(con,q,address):
        buf = address[0] #initialization
        print address[0] + " is CONNECTED"
        con.settimeout(12.0) #assume disconnected after 12s of not receiving anything
        while True:
                try:
                        # keep receiving new update from the targeted client.
                        # will send a mesg to the queue for database update.
                        buf = con.recv(255)  #receive adminNo from client
                        if len(buf) > 0:
                                print buf
                                if buf == "cheat":
                                        #SPAI detected cheating case!
                                        mesg=(buf,address,False, True)

                                else:
                                        #normal reporting from the SPAI
                                        #print buf
                                        mesg=(buf, address, False, False)
                                q.put(mesg)

                                demand_resp = ServerCmd(address)
                                # ServerCmd(demand)
                                if demand_resp == "demand": #demand ss and kl
                                        print "Sending Logging command"
                                        con.send("demand"+os.linesep)
                                elif demand_resp == "nodemand":
                                        print "No demand"
                                        con.send("nodemand"+os.linesep)
                                elif demand_resp == "terminate":
                                        print "Terminating connection"
                                        con.send("terminate"+os.linesep)
                        else:
                                #if len(buf) is zero 
                                #This is a case that the client has disconnected.
                                print buf + " (" + str(address[0]) + ") in " + str(address[1]) +" has closed the connection"
                                mesg=(buf,address,True,False)
                                q.put(mesg)
                                break
                                
                except Exception as inst:
                        print inst
                        if str(inst) != "timed out": # timed out exception is okay, else must quit.
                                print buf + " (" + address[0] + ") is DISCONNECTED or HUNG"
                                mesg=(buf,address,False,True)
                                q.put(mesg)
                                break
                        # cannot send anymore 
                        #con.send("disconnected"+os.linesep)

        con.close()
        return

commonq = Queue.Queue(10)
serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.bind(('0.0.0.0', 8808))
serversocket.listen(5) # become a server socket, maximum 5 connections
print "Server starts listening ..."
serversocket.settimeout(2.0) # setup a 2 seconds timeout to exit the blocking state
while True:
        try:
                connection, address = serversocket.accept()
                #connection.setblocking(1)
                # setup and start a new thread to run an instance of handler()
                t = threading.Thread(target=handler, args=(connection,commonq,address))
                t.start()
        except Exception as inst:
                if str(inst) != "timed out": # timed out exception is okay, else must quit.
                        break
        # I have just break from the accept call
        #print "Ready to check Queue"
        processQueue(commonq)
print "Server stops"
