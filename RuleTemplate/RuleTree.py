import treelib
import re

printDict = {"G": "G", "F": "F", "U": "U", "timeBound": "[?,?]", "GT": ">", "GE": ">=", "LT": "<", "LE": "<=",
             "EQ": "=", "NEQ": "!=", "AND": "&", "OR": "|", "IMPLIES": "->", "(":"(", ")":")", "Variable": "Variable"}


#Single Rule Tree
class RuleTree(treelib.Tree):
    def __init__(self,  *args, **kw):
        super().__init__(*args, **kw)
        self.varList = []
        self.percentCount = None

    # def __init__(self, tree=None, deep=False, node_class=None):
    #     # super().__init__(self)
    #     self.varList = []
    #     super().__init__(tree, deep, node_class)
    #     # super(RuleTree, self).__init__()
    
    #Make rule trees hashable ..
    def __eq__(self, other):
        return self.toString() == other.toString()

    def __hash__(self):
        return hash(('string', self.toString()))


    def toString(self):
        str = ""
        varCounter = 0

        btwNode = ['AND', 'OR', 'IMPLIES', 'U']
        btwNodePrecursor = ['BooleanAtomic', 'boolExpr']
        frontPart = False
        btw = None

        gen = self.expand_tree(mode=treelib.Tree.DEPTH, sorting=False)

        g = next(gen)
        while True:
            val = re.sub('[0-9]', '', g)

            if val in btwNode:
                #get sibling nodes of btw node
                sibNames = [x.identifier for x in self.siblings(g) if re.sub('[0-9]', '', x.identifier) != 'timeBound']

                if val == "U":
                    btw = " " + printDict[val]
                    btw += "[?,?] "
                    g = next(gen)
                    g = next(gen)
                else:
                    btw = " " + printDict[val] + " "

                try:
                    g = next(gen)
                except:
                    pass

                test = ""
                while True:
                    val = re.sub('[0-9]', '', g)
                    newStr, varCounter = self.getSymbol(val, gen, varCounter)
                    test += newStr

                    if g == sibNames[1]: #reached second sibname
                        str += test
                        str += btw
                        break

                    try:
                        g = next(gen)
                    except:
                        break

            newStr, varCounter = self.getSymbol(val, gen, varCounter)
            str += newStr

            try:
                g = next(gen)
            except:
                break

        str = self.checkString(str)
        return str

    def getSymbol(self, val, gen, varCounter):
        rop = ["GT", "GE", "LT", "LE", "EQ", "NEQ"]
        str = ""

        if val in printDict.keys() or val in self.varList:

            if val in rop:  # format leaf parts
                try:
                    atomic = re.sub('[0-9]', '', next(gen))
                except:
                    pass

                str += atomic + " " + printDict[val] + " " + "?"

            else:
                str += printDict[val]

        return str, varCounter

    def toStringWithParams(self):
        str = ""
        varCounter = 0

        btwNode = ['AND', 'OR', 'IMPLIES', 'U']
        btwNodePrecursor = ['BooleanAtomic', 'boolExpr']
        frontPart = False
        btw = None

        gen = self.expand_tree(mode=treelib.Tree.DEPTH, sorting=False)

        g = next(gen)
        while True:
            val = re.sub('[0-9]', '', g)

            if val in btwNode:
                #get sibling nodes of btw node
                sibNames = [x.identifier for x in self.siblings(g) if re.sub('[0-9]', '', x.identifier) != 'timeBound']

                if val == "U":
                    btw = " " + printDict[val]
                    btw += "[?,?] "
                    g = next(gen)
                    g = next(gen)
                else:
                    btw = " " + printDict[val] + " "

                try:
                    g = next(gen)
                except:
                    pass

                test = ""
                while True:
                    val = re.sub('[0-9]', '', g)
                    newStr, varCounter = self.getSymbolParams(val, gen, varCounter)
                    test += newStr

                    if g == sibNames[1]: #reached second sibname
                        str += test
                        str += btw
                        break

                    try:
                        g = next(gen)
                    except:
                        break

            newStr, varCounter = self.getSymbolParams(val, gen, varCounter)
            str += newStr

            try:
                g = next(gen)
            except:
                break

        str = self.checkString(str)
        return str

    def getSymbolParams(self, val, gen, varCounter):
        rop = ["GT", "GE", "LT", "LE", "EQ", "NEQ"]
        str = ""

        if val in printDict.keys() or val in self.varList:

            if val in rop:  # format leaf parts
                try:
                    atomic = re.sub('[0-9]', '', next(gen))
                except:
                    pass

                str += atomic + " " + printDict[val] + " " + "0.000"

            else:
                str += printDict[val]

        return str, varCounter


    #Check string for any inconsistencies
    def checkString(self, str):
        paren1 = str.count("(")
        paren2 = str.count(")")

        dif = paren1 - paren2

        if dif > 0:
            for i in range(dif):
                str += ")"

        return str