class PostgresSchema(object):

    def __init__(self, conn, dryRun=False):
        self.conn = conn
        self.dryRun = dryRun
        self.runLog = []

        
    def execute(self, query, args=(), cur=None, log=True):
        if cur is None:
            cur = self.conn.cursor()

        if log:
            if args:
                self.runLog.append(cur.mogrify(query, args))
            else:
                self.runLog.append(query)
        
        if not self.dryRun:
            cur.execute(query, args)

    def flushLog(self):
        log, self.runLog = self.runLog, []
        return log

    def printLog(self):
        for line in self.flushLog():
            print line

    def begin(self):
        if self.dryRun:
            self.runLog.append("START TRANSACTION")

    def commit(self):
        if self.dryRun:
            self.runLog.append("COMMIT")
        else:
            self.conn.commit()

    def ensureSchemaTable(self):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT COUNT(*)"
            " FROM information_schema.tables"
            " WHERE table_name = 'schemup_tables'")
        
        if cur.fetchone()[0]:
            return
        
        print "Creating schema table..."
        cur.execute(
            "CREATE TABLE schemup_tables ("
            " table_name VARCHAR NOT NULL,"
            " version VARCHAR NOT NULL,"
            " is_current BOOLEAN NOT NULL DEFAULT 'f',"
            " schema TEXT)")
        
        self.conn.commit()
        

    def clearSchemaTable(self):
        self.execute("DELETE FROM schemup_tables")

        
    def getSchema(self, tableName):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT column_name, data_type, is_nullable, column_default"
            " FROM information_schema.columns"
            " WHERE table_name = %s"
            " ORDER BY column_name",
            (tableName,))
        
        return u"\n".join(u"|".join(unicode(c) for c in row) for row in cur)

    def getTableVersions(self):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT table_name, version"
            " FROM schemup_tables"
            " WHERE is_current = 't'")
        return cur


    def getVersionedTableSchemas(self):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT table_name, schema"
            " FROM schemup_tables"
            " WHERE is_current = 't'")
        return cur

    
    def setSchema(self, tableName, version, log=True):

        schema = self.getSchema(tableName)

        cur = self.conn.cursor()
        self.execute(
            "UPDATE schemup_tables"
            " SET is_current = 'f'"
            " WHERE table_name = %s",
            (tableName,), cur, log)
        self.execute(
            "INSERT INTO schemup_tables"
            " (table_name, version, is_current, schema)"
            " VALUES (%s, %s, 't', %s)",
            (tableName, version, schema), cur, log)


    def getKnownTableVersions(self):
        self.ensureSchemaTable()
        
        cur = self.conn.cursor()
        cur.execute(
            "SELECT table_name, version"
            " FROM schemup_tables"
            " WHERE is_current = 't'")
        
        return sorted(cur.fetchall())
