class ValidationMismatch(object):
    def __init__(self, (tableName, actual, expected)):
        self.tableName = tableName
        self.actual = actual
        self.expected = expected

class ORMValidationMismatch(ValidationMismatch):
    def __repr__(self):
        return "<%s: expected %s, found %s>" % (
            self.tableName, self.expected, self.actual)

class SchemaValidationMismatch(ValidationMismatch):
    def __repr__(self):
        return "\n%s:\n----------\nExpected:\n%s\n----------\nActual:\n%s\n----------\n" % (
            self.tableName, self.expected, self.actual)


class ValidationError(Exception):
    pass

class ORMValidationError(Exception):
    """
    There's a mismatch between the table versions
    specified by the code and the versions in the
    schemup cache table.
    """
    pass

class SchemaValidationError(Exception):
    """
    There's a mismatch between the table schemas cached
    by schemup and the actual DB table structures.
    """
