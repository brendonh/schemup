class SpannerSchema(object):

    def __init__(self, database, types, dryRun=False):
        self.database = database
        self.types = types
        self.dryRun = dryRun
        self.runLog = []

        
    def execute(self, query, args=None, log=True):
        if log:
            self.runLog.append("%s <- %s" % (query, args))
        
        if not self.dryRun:
            verb = query.split(None, 1)[0]
            print "Verb:", verb
            if verb.upper() in ("CREATE", "ALTER", "DROP"):
                print "Running DDL:", query
                if args:
                    raise Exception("Can't pass args to DDL")
                return self.database.update_ddl([query])
            else:
                print "Running DML:", query
                with self.database.snapshot() as snapshot:
                    return list(
                        snapshot.execute_sql(query, args,
                                             {k: self.types.STRING_PARAM_TYPE
                                              for k in args}))


    def flushLog(self):
        log, self.runLog = self.runLog, []
        return log

    def printLog(self):
        for line in self.flushLog():
            print line

    def begin(self):
        pass
    
    def commit(self):
        pass
    
    def ensureSchemaTable(self):
        with self.database.snapshot() as snapshot:
            [[count]] = snapshot.execute_sql(
                "SELECT COUNT(*)"
                " FROM information_schema.tables"
                " WHERE table_name = 'schemup_tables'")

        if count:
            return

        print "Creating schema table..."
        self.database.update_ddl([
            "CREATE TABLE schemup_tables ("
            " table_name STRING(64) NOT NULL,"
            " version STRING(8) NOT NULL,"
            " is_current BOOL NOT NULL,"
            " schema STRING(MAX))"
            " PRIMARY KEY (table_name, version)"])

        

    def clearSchemaTable(self):
        with self.database.snapshot() as snapshot:
            snapshot.execute_sql("DELETE FROM schemup_tables")

        
    def getSchema(self, tableName):
        with self.database.snapshot() as snapshot:
            result = list(snapshot.execute_sql(
                "SELECT column_name, spanner_type, is_nullable"
                " FROM information_schema.columns"
                " WHERE table_name = @table"
                " ORDER BY column_name",
                {"table": tableName},
                {"table": self.types.STRING_PARAM_TYPE}))
            print "!!!", result
        
        return u"\n".join(u"|".join(unicode(c) for c in row) for row in result)

    def getTableVersions(self):
        with self.database.snapshot() as snapshot:
            return snapshot.execute_sql(
                "SELECT table_name, version"
                " FROM schemup_tables"
                " WHERE is_current = true")

    def getVersionedTableSchemas(self):
        with self.database.snapshot() as snapshot:
            result = list(snapshot.execute_sql(
                "SELECT table_name, schema"
                " FROM schemup_tables"
                " WHERE is_current = true"))
            print ">>> Schemas:", result
            return result

    
    def setSchema(self, tableName, version, log=True):
        schema = self.getSchema(tableName)
        print self.execute(
            "UPDATE schemup_tables"
            " SET is_current = false"
            " WHERE table_name = @table",
            {"table": tableName},
            log)
        print self.execute(
            "INSERT INTO schemup_tables"
            " (table_name, version, is_current, schema)"
            " VALUES (@table, @version, true, @schema)",
            {"table": tableName, "version": version, "schema": schema},
            log)


    def getKnownTableVersions(self):
        with self.database.snapshot() as snapshot:
            results = snapshot.execute_sql(
                "SELECT table_name, version"
                " FROM schemup_tables"
                " WHERE is_current = true")
            
            return sorted(list(results))
