from schemup import validator, upgraders, errors

def snapshot(dbSchema, ormSchema):
    """
    Write current versions to DB schema table.
    Used only to initialize schemup on an existing DB
    """
    
    dbSchema.clearSchemaTable()

    for tableName, version in ormSchema.getExpectedTableVersions():
        dbSchema.setSchema(tableName, version)

    dbSchema.commit()



def validate(dbSchema, ormSchema):
    """
    Check DB versions against ORM versions, returning mismatches.
    If there are version mismatches, check DB schemas against cache,
    returning mismatches there.
    """

    mismatches = validator.findMismatches(dbSchema, ormSchema)

    if mismatches:
        raise errors.ORMValidationError(
            map(errors.ORMValidationMismatch, mismatches))

    schemaMismatches = list(validator.findSchemaMismatches(dbSchema))
    
    if schemaMismatches:
        raise errors.SchemaValidationError(
            map(errors.SchemaValidationMismatch, schemaMismatches))



def upgrade(dbSchema, ormSchema):
    """
    Attempt to find upgrade paths for all out-of-sync tables,
     and run them.
    """

    paths = [(tableName, upgraders.findUpgradePath(tableName, fromVersion, toVersion))
             for (tableName, fromVersion, toVersion)
             in validator.findMismatches(dbSchema, ormSchema)]

    if not paths:
        return

    for tableName, path in paths:
        print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
        print "Upgrading %s" % tableName
        print "%s => %s" % (path.firstVersion(), path.lastVersion())
        print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
        path.apply(dbSchema)
        dbSchema.setSchema(tableName, path.lastVersion(), log=False)
        dbSchema.printLog()

    dbSchema.commit()
