
import pymysql
class PnetMacDB(object):
    def __init__(self,dbhost='localhost',dbuser='root',
                 schema='ovsDB',pwd='root'):
        self.dbhost = dbhost
        self.dbuser = dbuser
        self.schema = schema
        self.pwd=pwd
        self.conn = None
    def dbOpen(self,):
        self.conn = pymysql.connect(self.dbhost, self.dbuser, 
                     self.pwd, self.schema)
  
        print self.conn
        return self.conn
    def dbClose(self,conn=None):
        if conn:
            conn.close()
        else:
            if self.conn:
                self.conn.close()
        
    def getVersion(self):
        return "PnetMacDB 0.9"
            
    def dbTest(self):
        try:
            db = pymysql.connect(self.dbhost, self.dbuser, 
                     self.pwd, self.schema)
            cursor = db.cursor() 
            cursor.execute("SELECT VERSION()")
            results = cursor.fetchone()
            # Check if anything at all is returned
            if results:
                print "True"
            else:
                print "False"               
        except pymysql.Error, e:
            print "ERROR %d IN CONNECTION: %s" % (e.args[0], e.args[1])
