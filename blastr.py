import json
import numpy as np
import os

getClassStr = lambda x:str(type(x))[8:-2] # removes <class thing from str(type(instance))
isSpecialList = lambda x: (
    type(x) is list and
    len(x) == 2 and
    type(x[1]) is list and
    isinstance(x[0],str) and
    x[0].startswith("__") and
    x[0].endswith("__") and
    x[0] # return type
    )
joinName = lambda parentName, attr: "-".join(
    [i for i in [parentName, str(attr)] if i]) 

def directoryCheck(path):
    if not os.path.exists(os.path.abspath(path)):
        os.makedirs(os.path.abspath(path))
    if not os.path.isdir(path):
        raise OSError("Path exists as a file.")

class ObjectJsonWrapper():
    terminal = [str, int, float, bool]
    astype = dict([
        (type(dict([]).keys()), list),
        (type(dict([]).values()), list),
        (type(dict([]).items()), list),
        (set, list),
        (frozenset, list),
        (tuple, list),
        (complex, lambda x: ["__complex__", [x.real, x.imag]]),
        (type, getClassStr)
        ])
    getters = dict([])
    saveExternDict = dict([
        # type:(subdirectory_name, internal value, saving external func, extension)
        (np.ndarray, 
            ('ndarray', 
             lambda x: {"len":len(x), "dtype": x.dtype}, 
             lambda file, x: np.savetxt(file, x),
             ".npy",
        ))])
    def __init__(self):
        self.value = None
        self.objInstance = None
        self.objType = None
        self.children = []
        self.name = ""
    def walkChildren(self):
        if len(self.children) == 0:
            return [self]
        return [self]+sum([child.walkChildren() for child in self.children],[])
    def getRoot(self):
        if self.parent is None:
            return self
        return self.parent.getRoot()
    @classmethod
    def ignoreAttr(cls, type_, attrStr):
        if attrStr.startswith('__'):
            return True
        return False
    def internalValue(self):
        return dict([])
    def saveFolder(self, foldername = "untitled", metatype=None):
        pass #TODO
    def saveFile(self, file = "meta.json", ftype=None):
        # determine file name and set file as None if it is not a file object
        if type(file) == str:
            fname = file
            file = None
        elif hasattr(file, "write") and hasattr(file, "name"):
            fname = file.name
        else:
            fname = "meta.json"
            file = None

        # if not given, determine file type
        # might cause file.name != fname
        if ftype is None:
            *front, ftype = fname.split(".")
            if front == []: # no extensions
                fname += ".json"
                ftype = "json"
            elif ftype not in ["json",]: # only supported ones
                fname = ".".join([*front, "json"])
                ftype = "json"

        # determine saving func
        saveFunc = {"json": self._save_json}[ftype]

        # save meta.
        # use if file object is given, open if not
        if file:
            saveFunc(file, fname)
        else:
            directoryCheck(os.path.dirname(fname))            
            with open(fname, 'wt') as file:
                saveFunc(file, fname)
        
        # save externals
        for child in self.walkChildren():
            doExternSave = isSpecialList(child.value) and child.value[0] == "__extern__"
            if not doExternSave:
                continue
            saveFunc, extension, *_ = child.saveExtern
            _, (relDirPath, *_) = child.value
            externFname = os.path.join(os.path.dirname(fname),relDirPath, child.name+extension)
            directoryCheck(os.path.dirname(externFname))
            with open(externFname, 'wt') as externFile:
                saveFunc(externFile, child.objInstance)
                # pass
    def _save_json(self, file, fname):
        content = json.dumps({**self.value, **self.internalValue()})
        file.write(content)
    @classmethod
    def fromInstance(cls, instance, name = "", parent=None):
        '''This will convert an object instance so that it will be json serializable, usually to a dict'''
        self = cls()
        self.objInstance = instance
        self.objType = type(instance)
        self.name = name
        self.parent = parent
        instance_ = self.objInstance
        type_ = self.objType
        
        if parent is None:
            parent = cls()
            parent.name = name
            self.existExternFiles = dict([])

        # convert type for simple objects
        if type(instance) in cls.astype.keys():
            instance_ = cls.astype[type(instance)](instance)
            type_ = type(instance_)

        # save some data not on json but on external file
        if type_ in cls.saveExternDict.keys():
            directory, self.internalValue, *self.saveExtern = cls.saveExternDict[type_]
            self.value = ["__extern__", [directory]]
            root = self.getRoot()
            if directory not in root.existExternFiles.keys():
                root.existExternFiles[directory] = []
            while self.name in root.existExternFiles[directory]:
                self.name += "_"
            
            return self

        # handle terminals
        if type_ in cls.terminal or isSpecialList(instance_):
            self.value = instance_
            return self
        if type_ is list:
            self.children = [cls.fromInstance(v, joinName(self.name, i), self) for i, v in enumerate(instance_)]
            self.value = [child.value for child in self.children]
            return self
        if type_ is dict:
            self.value = dict([])
            for k, v in instance_.items():
                if not isinstance(k, str):
                    # k = '{0}({1})'.format(getClassStr(k),str(k))
                    raise TypeError("keys must be a string")
                if "name" in instance_.keys():
                    self.name = instance_["name"]
                name = joinName(self.name, k)
                child = cls.fromInstance(v, name, self)
                self.children.append(child)
                self.value[k] = child.value
            return self


        # access attrs via dir
        self.value = dict([])
        for attrStr in dir(instance_):
            if cls.ignoreAttr(type_, attrStr):
                continue
            attr = getattr(instance_,attrStr)
            name = joinName(self.name, attr)
            # ignore methods unless it is listed in getters
            if callable(attr):
                if not (type_ in cls.getters.keys() and attrStr in cls.getters[type_]):
                    continue
                attr = attr()
            child = cls.fromInstance(attr, name, self)
            self.value[attrStr] = child.value
            self.children.append(child)
        return self
    def save(self, fname):
        pass

if __name__ == '__main__':
    c = ObjectJsonWrapper.fromInstance({"name":"aaa", "array":[1,np.array([2,3])] })
    c.saveFile("aa/meta.json")
