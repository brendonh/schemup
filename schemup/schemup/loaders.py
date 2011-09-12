import sys, os, os.path

def find(dirpath):
    for dirname, dirnames, filenames in os.walk(dirpath):
        for filename in filenames:
            loader = fileLoaders.get(os.path.splitext(filename)[1])
            if loader is not None:
                yield dirname, filename, loader


def loadPython(dirname, filename):
    print "Importing", dirname, filename
    sys.path.insert(0, dirname)
    __import__(filename.rstrip(".py"))
    sys.path.pop(0)



fileLoaders = {
    '.py': loadPython,
    '.yaml': lambda x, y: None
}
