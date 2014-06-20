class DictSchema(object):
    
    def __init__(self, versions):
        self.versions = versions

    def getExpectedTableVersions(self):
        return self.versions.items()

