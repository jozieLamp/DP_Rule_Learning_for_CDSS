import treelib
import re

printDict = {"G": "G", "F": "F", "U": "U", "timeBound": "[?,?]", "GT": ">", "GE": ">=", "LT": "<", "LE": "<=",
             "EQ": "=", "NEQ": "!=", "AND": "&", "OR": "|", "IMPLIES": "->", "(":"(", ")":")", "Variable": "Variable"}


#Single Rule Tree
class RuleTree(treelib.Tree):
    def __init__(self,  *args, **kw):
        super().__init__(*args, **kw)
        self.varList = []

    # def __init__(self, tree=None, deep=False, node_class=None):
    #     # super().__init__(self)
    #     self.varList = []
    #     super().__init__(tree, deep, node_class)
    #     # super(RuleTree, self).__init__()


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

                g = next(gen)

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

        if val in printDict.keys():

            if val in rop:  # format leaf parts
                try:
                    atomic = re.sub('[0-9]', '', next(gen))
                except:
                    pass

                if varCounter >= len(self.varList):
                    str += "Variable" + " " + printDict[val] + " " + "?"
                elif re.sub('[0-9]', '', atomic) == "Variable":
                    str += self.varList[varCounter] + " " + printDict[val] + " " + "?"
                    varCounter += 1
                else:
                    str += "?" + " " + printDict[val] + self.varList[varCounter]
                    varCounter += 1


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

                g = next(gen)

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

        if val in printDict.keys():

            if val in rop:  # format leaf parts
                try:
                    atomic = re.sub('[0-9]', '', next(gen))
                except:
                    pass

                if varCounter >= len(self.varList):
                    str += "Variable" + " " + printDict[val] + " " + "0.0"
                elif re.sub('[0-9]', '', atomic) == "Variable":
                    str += self.varList[varCounter] + " " + printDict[val] + " " + "0.0"
                    varCounter += 1
                else:
                    str += "0.0" + " " + printDict[val] + self.varList[varCounter]
                    varCounter += 1


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