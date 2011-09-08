from collections import deque

# table -> {(from, to) -> function}
registeredUpgraders = {}

def registerUpgrader(tableName, fromVersion, toVersion, upgrader):
    if tableName not in registeredUpgraders:
        registeredUpgraders[tableName] = {}

    tableUpgraders = registeredUpgraders[tableName]

    if fromVersion not in tableUpgraders:
        tableUpgraders[fromVersion] = {}

    versionUpgraders = tableUpgraders[fromVersion]

    if toVersion in versionUpgraders:
        raise ValueError("Upgrader already exists for %s (%s => %s)" % (
                tableName, fromVersion, toVersion))

    versionUpgraders[toVersion] = upgrader


def upgrader(tableName, fromVersion, toVersion):
    """
    Decorator shortcut for registerUpgrader
    """
    def decorate(function):
        registerUpgrader(tableName, fromVersion, toVersion, function)
        return function

    return decorate


class UpgradePath(object):
    def __init__(self, steps=None, seen=None):
        self.steps = steps or []
        self.seen = seen or set()

    def copy(self):
        return UpgradePath(self.steps[:], self.seen.copy())

    def push(self, version, upgrader):
        if version in self.seen:
            raise ValueError("Upgrader cycle", self.steps, version)
        self.seen.add(version)
        self.steps.append((version, upgrader))

    def pushNew(self, version, upgrader):
        copy = self.copy()
        copy.push(version, upgrader)
        return copy

    def firstVersion(self):
        return self.steps[0][0]

    def lastVersion(self):
        return self.steps[-1][0]

    def apply(self, dbSchema):
        for _version, upgrader in self.steps:
            if upgrader is not None:
                upgrader(dbSchema)

    def __str__(self):
        return "\n".join("-> %s: %s" % (v, u) for (v, u) in self.steps)
        

def findUpgradePath(tableName, fromVersion, toVersion):
    upgraders = registeredUpgraders.get(tableName, {})

    paths = deque([ UpgradePath([(fromVersion, None)]) ])
    
    while paths:
        path = paths.popleft()

        lastVersion = path.lastVersion()
        if lastVersion == toVersion:
            return path

        for (nextVersion, upgrader) in upgraders.get(lastVersion, {}).iteritems():
            paths.append( path.pushNew(nextVersion, upgrader) )

    raise ValueError("No upgrade path for %s (%s -> %s)" % (tableName, fromVersion, toVersion))
