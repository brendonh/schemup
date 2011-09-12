import sys, os, os.path, yaml

from schemup.upgraders import registerUpgrader, Upgrader

def find(dirpath):
    for dirname, dirnames, filenames in os.walk(dirpath):
        for filename in filenames:
            loader = fileLoaders.get(os.path.splitext(filename)[1])
            if loader is not None:
                yield dirname, filename, loader


def loadPython(dirname, filename):
    print "Importing", os.path.join(dirname, filename)
    sys.path.insert(0, dirname)
    __import__(filename.rstrip(".py"))
    sys.path.pop(0)


def loadYAML(dirname, filename):
    print "Importing", os.path.join(dirname, filename)
    blocks = []
    for doc in yaml.load_all(
        open(os.path.join(dirname, filename), 'rb')):
        block = _getBlock(doc, blocks)
        registerUpgrader(block)
        blocks.insert(0, block)

        

def _getBlock(doc, blocks):
    block = {
        'tableName': doc['table'],
        'fromVersion': doc['from'] if 'from' in doc else _getFromPrevious(doc, blocks),
        'toVersion': doc['to'],
        'dependencies': [(table, version) for [table, version] in doc.get('depends', [])],
        'upgrader': _getUpgrader(doc),
    }

    return Upgrader(**block)


def _getFromPrevious(doc, blocks):
    for upgrader in blocks:
        if upgrader.tableName == doc['table']:
            return upgrader.toVersion

    raise ValueError("Upgrader has no 'from' and no preceding block", doc)


def _getUpgrader(doc):
    if 'sql' in doc:
        upgrader = lambda db, sql=doc['sql']: db.execute(sql)
        upgrader.__name__ = "YAML_SQL_upgrader"
        return upgrader
    raise ValueError("Couldn't find upgrader", doc)



fileLoaders = {
    '.py': loadPython,
    '.yaml': loadYAML,
}
