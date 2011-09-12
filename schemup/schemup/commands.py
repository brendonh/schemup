from schemup import loaders, validator, upgraders, errors


def load(dirpath):
    """
    Load upgraders from Python or YAML files in the given
    directory.
    """
    for dirname, filename, loader in loaders.find(dirpath):
        loader(dirname, filename)

    

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

    for tableName, currentVersion in dbSchema.getTableVersions():
        paths.append((tableName, upgraders.pathToCurrent(tableName, currentVersion)))

    stepGraph = upgraders.UpgradeStepGraph()

    for tableName, path in paths:
        path.addToGraph(stepGraph)

    stepGraph.calculateEdges()

    dbSchema.begin()

    modifiedTables = []

    for upgrader in stepGraph.topologicalSort():
        upgrader.run(dbSchema)
        if upgrader.upgrader is not None:
            modifiedTables.append((upgrader.tableName, upgrader.toVersion))

    dbSchema.commit()

    for tableName, version in modifiedTables:
        dbSchema.setSchema(tableName, version)

    dbSchema.commit()

    return dbSchema.flushLog()


def snapshot(dbSchema, ormSchema):
    """
    Write current versions to DB schema table.
    Used only to initialize schemup on an existing DB
    """
    
    dbSchema.clearSchemaTable()

    for tableName, version in ormSchema.getExpectedTableVersions():
        dbSchema.setSchema(tableName, version)

    dbSchema.commit()
