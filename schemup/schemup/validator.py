def findMismatches(dbSchema, ormSchema):
    actual = dict(dbSchema.getKnownTableVersions())
    expected = dict(ormSchema.getExpectedTableVersions())

    tables = set(actual.keys()) | set(expected.keys())

    mismatches = []

    for table in tables:
        exTable = expected.get(table)
        acTable = actual.get(table)

        if exTable == acTable:
            continue

        mismatches.append((table, acTable, exTable))

    return mismatches


def findSchemaMismatches(dbSchema):
    errors = []
    for tableName, expectedSchema in dbSchema.getVersionedTableSchemas():
        actualSchema = dbSchema.getSchema(tableName)
        if expectedSchema != actualSchema:
            errors.append((tableName, actualSchema, expectedSchema))
    return errors
            
            
