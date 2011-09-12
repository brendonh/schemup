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

        print "Upgrading %s (%s => %s)" % (self.tableName, self.fromVersion, self.toVersion)
        self.upgrader(dbSchema)

    def __repr__(self):
        return "<%s: %s => %s (%s)>" % (
            self.tableName, self.fromVersion, self.toVersion, self.upgrader)


def registerUpgrader(upgrader):

    if upgrader.tableName not in registeredUpgraders:
        registeredUpgraders[upgrader.tableName] = {}

    tableUpgraders = registeredUpgraders[upgrader.tableName]

    if upgrader.fromVersion not in tableUpgraders:
        tableUpgraders[upgrader.fromVersion] = {}

    versionUpgraders = tableUpgraders[upgrader.fromVersion]

    if upgrader.toVersion in versionUpgraders:
        raise ValueError("Upgrader already exists for %s (%s => %s)" % (
                upgrader.tableName, upgrader.fromVersion, upgrader.toVersion))

    versionUpgraders[upgrader.toVersion] = upgrader


def upgrader(tableName, fromVersion, toVersion, dependencies=()):
    """
    Decorator shortcut for registerUpgrader
    """
    def decorate(function):
        upgrader = Upgrader(tableName, fromVersion, toVersion, function, dependencies)
        registerUpgrader(upgrader)
        return function

    return decorate


# ------------------------------------------------------------

def pathToCurrent(tableName, currentVersion):
    path = UpgradePath([])
    for upgrader in findUpgradePath(tableName, None, currentVersion).steps:
        stubUpgrader = upgrader.copy()
        stubUpgrader.upgrader = None
        path.push(stubUpgrader)
    return path


def findUpgradePath(tableName, fromVersion, toVersion):
    upgraders = registeredUpgraders.get(tableName, {})

    stubUpgrader = Upgrader(tableName, None, fromVersion, None)
    initialPath = UpgradePath([ stubUpgrader ])

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
