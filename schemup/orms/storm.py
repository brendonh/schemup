
class StormSchema(object):

    def __init__(self):
        self.modelCache = []

    def versioned(self, cls):
        self.modelCache.append((cls.__storm_table__, unicode(cls.__version__)))
        return cls

    def getExpectedTableVersions(self):
        return sorted(self.modelCache)
