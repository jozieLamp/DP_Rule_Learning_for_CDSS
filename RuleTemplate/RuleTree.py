import treelib
import re

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
        printList = ["G", "F", "U","[", "]", "(", ")", "atomic"]
        rop = ["GT", "GE", "LT", "LE", "EQ", "NEQ"]
        ropSymbol = [">", ">=", "<", "<=", "=", "!="]

        gen = self.expand_tree(mode=treelib.Tree.DEPTH, sorting=False)

        g = next(gen)
        while True:
            val = re.sub('[0-9]', '', g)
            if val in printList:
                str = str + val
            elif val == "timeBound":
                str = str + "[?,?]"
            elif val == "AND":
                str += " & "
            elif val == "OR":
                str += " | "
            elif val == "IMPLIES":
                str += " -> "
            elif val == "NOT":
                str += " ! "
            elif val in rop:
                try:
                    at1 = next(gen)
                except:
                    pass
                # at2 = next(gen)
                idx = rop.index(val)

                if varCounter >= len(self.varList):
                    str += " Variable" + " " + ropSymbol[idx] + " " + "?"
                elif re.sub('[0-9]', '', at1) == "Variable":
                    str += self.varList[varCounter] + " " + ropSymbol[idx] + " " + "?"
                    varCounter += 1
                else:
                    str += "?" + " " + ropSymbol[idx] + self.varList[varCounter]
                    varCounter += 1

            else:
                pass

            try:
                g = next(gen)
            except:
                break

        return str

    def toStringWithParams(self):
        str = ""
        varCounter = 0
        printList = ["G", "F", "U", "[", "]", "(", ")", "atomic"]
        rop = ["GT", "GE", "LT", "LE", "EQ", "NEQ"]
        ropSymbol = [">", ">=", "<", "<=", "=", "!="]

        gen = self.expand_tree(mode=treelib.Tree.DEPTH, sorting=False)
        g = next(gen)
        while True:
            val = re.sub('[0-9]', '', g)
            if val in printList:
                str = str + val
            elif val == "timeBound":
                str = str + "[?,?]"
            elif val == "AND":
                str += " & "
            elif val == "OR":
                str += " | "
            elif val == "IMPLIES":
                str += " -> "
            elif val == "NOT":
                str += " ! "
            elif val in rop:
                try:
                    at1 = next(gen)
                except:
                    pass
                #at2 = next(gen)
                idx = rop.index(val)

                if varCounter >= len(self.varList):
                    str += " Variable" + " " + ropSymbol[idx] + " " + "0.0"
                elif re.sub('[0-9]', '', at1) == "Variable":
                    str += self.varList[varCounter] + " " + ropSymbol[idx] + " " + "0.0"
                    varCounter += 1
                else:
                    str += "0.0" + " " + ropSymbol[idx] + self.varList[varCounter]
                    varCounter += 1

            else:
                pass

            try:
                g = next(gen)
            except:
                break

        return str