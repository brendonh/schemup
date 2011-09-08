import psycopg2

from schemup.dbs import postgres
from schemup.orms import storm
from schemup.upgraders import upgrader
from schemup import commands

conn = psycopg2.connect("dbname=schemup_test")

stormSchema = storm.StormSchema()
postgresSchema = postgres.PostgresSchema(conn, dryRun=False)

@stormSchema.versioned
class Quick(object):
    __storm_table__ = "quick"
    __version__ = "bgh_3"

@upgrader('quick', 'bgh_1', 'bgh_2')
def quick_bgh1to2(dbSchema):
    dbSchema.execute("ALTER TABLE quick ADD another VARCHAR NOT NULL DEFAULT 'hey'")

@upgrader('quick', 'bgh_2', 'bgh_3')
def quick_bgh2to3(dbSchema):
    dbSchema.execute("ALTER TABLE quick ADD onemore INTEGER")


@stormSchema.versioned
class NewTable(object):
    __storm_table__ = "new_table"
    __version__ = "bgh_1"

@upgrader('new_table', None, 'bgh_1')
def new_table_create(dbSchema):
    dbSchema.execute("CREATE TABLE new_table ("
                     " id SERIAL NOT NULL PRIMARY KEY,"
                     " name VARCHAR)")


commands.upgrade(postgresSchema, stormSchema)

validationError = commands.validate(postgresSchema, stormSchema)
if validationError is not None:
    errorType, errors = validationError
    print "Validation failed (%s)" % errorType
    for (tableName, actual, expected) in errors:
        print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
        print "Table: %s" % tableName
        print "- Actual: %s" % actual
        print "- Expected: %s" % expected
    raise SystemExit
