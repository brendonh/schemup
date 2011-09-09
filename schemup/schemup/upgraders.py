from collections import deque

# table -> {(from, to) -> function}
registeredUpgraders = {}


class Upgrader(object):
    def __init__(self, tableName, fromVersion, toVersion, upgrader, dependencies=()):
        self.tableName = tableName
        self.fromVersion = fromVersion
        self.toVersion = toVersion
        self.upgrader = upgrader
        self.dependencies = list(dependencies)

    def copy(self):
        return Upgrader(self.tableName, self.fromVersion, self.toVersion,
                        self.upgrader, self.dependencies)

    def run(self, dbSchema):
        if self.upgrader is None:
            return

        print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
        print "Upgrading %s" % self.tableName
        print "%s => %s" % (self.fromVersion, self.toVersion)
        self.upgrader(dbSchema)
        dbSchema.setSchema(self.tableName, self.toVersion, log=False)
        dbSchema.printLog()


    def __repr__(self):
        return "<%s: %s => %s (%s)>" % (
            self.tableName, self.fromVersion, self.toVersion, self.upgrader)


def registerUpgrader(tableName, fromVersion, toVersion, upgrader, dependencies=()):
    if tableName not in registeredUpgraders:
        registeredUpgraders[tableName] = {}

    tableUpgraders = registeredUpgraders[tableName]

    if fromVersion not in tableUpgraders:
        tableUpgraders[fromVersion] = {}

    versionUpgraders = tableUpgraders[fromVersion]

    if toVersion in versionUpgraders:
        raise ValueError("Upgrader already exists for %s (%s => %s)" % (
                tableName, fromVersion, toVersion))

    versionUpgraders[toVersion] = Upgrader(
        tableName, fromVersion, toVersion, upgrader, dependencies)


def upgrader(tableName, fromVersion, toVersion, dependencies=()):
    """
    Decorator shortcut for registerUpgrader
    """
    def decorate(function):
        registerUpgrader(tableName, fromVersion, toVersion, function, dependencies)
        return function

    return decorate


# ------------------------------------------------------------

def findUpgradePath(tableName, fromVersion, toVersion):
    upgraders = registeredUpgraders.get(tableName, {})

    initialPath = UpgradePath([])

    if fromVersion is None:
        initialPath.push(Upgrader(tableName, None, fromVersion, None))
    else:
        for upgrader in findUpgradePath(tableName, None, fromVersion).steps:
            stubUpgrader = upgrader.copy()
            stubUpgrader.upgrader = None
            initialPath.push(stubUpgrader)

    paths = deque([ initialPath ])
    
    while paths:
        path = paths.popleft()

        lastVersion = path.lastVersion()
        if lastVersion == toVersion:
            return path

        for (nextVersion, upgrader) in upgraders.get(lastVersion, {}).iteritems():
            paths.append( path.pushNew(upgrader) )

    raise ValueError("No upgrade path for %s (%s -> %s)" % (tableName, fromVersion, toVersion))


class UpgradePath(object):
    def __init__(self, steps=None, seen=None):
        self.steps = steps or []
        self.seen = seen or set()

    def copy(self):
        return UpgradePath(self.steps[:], self.seen.copy())

    def push(self, upgrader):
        if upgrader.toVersion in self.seen:
            raise ValueError("Upgrader cycle", self.steps, version)
        self.seen.add(upgrader.toVersion)
        self.steps.append(upgrader)

    def pushNew(self, upgrader):
        copy = self.copy()
        copy.push(upgrader)
        return copy

    def firstVersion(self):
        return self.steps[0].toVersion

    def lastVersion(self):
        return self.steps[-1].toVersion

    def addToGraph(self, graph):
        prev = None
        for origUpgrader in self.steps:
            upgrader = origUpgrader.copy()
            if prev is not None:
                upgrader.dependencies.append((prev.tableName, prev.toVersion))
            graph.addUpgrader(upgrader)
            prev = upgrader

    def __str__(self):
        return "\n".join("-> %s: %s" % (u.toVersion, u.upgrader) for u in self.steps)
        


class UpgradeStepGraph(object):
    def __init__(self):
        self.nodes = {}
        self.edges = {}

    def addUpgrader(self, upgrader):
        self.nodes[(upgrader.tableName, upgrader.toVersion)] = upgrader
        
    def calculateEdges(self):
        for fromKey, upgrader in self.nodes.iteritems():
            if fromKey not in self.edges:
                self.edges[fromKey] = set()

            for toKey in upgrader.dependencies:
                if toKey not in self.nodes:
                    raise ValueError(
                        "Upgrader %s has unmet dependency on %s"
                        % (upgrader, toKey))

                self.edges[fromKey].add(toKey)
        
    def topologicalSort(self):
        edges = self.edges.copy()
        path = []
        while True:
            freeKeys = set(key for (key, deps) in edges.iteritems() if not deps)
            if not freeKeys:
                break
            path.extend(freeKeys)
            edges = dict((key, deps - freeKeys) for (key, deps) in edges.iteritems()
                         if key not in freeKeys)

        if edges:
            raise ValueError(
                "Cyclic upgrader dependencies", self.edges)
        
        return [self.nodes[key] for key in path]
