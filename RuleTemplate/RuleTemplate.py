import treelib
import re
import copy

#Grammar Dictionary for easier access of child nodes in template tree
stlGrammarDict = {
    "eval": [["statemenList"]],
    "statementList": [["statement"]],
    "statement": [["(","boolExpr",")"]],
    "boolExpr": [["stlTerm"], ["stlTerm", "AND", "stlTerm"], ["stlTerm", "OR", "stlTerm"], ["stlTerm", "IMPLIES", "stlTerm"] ],
    "stlTerm": [["BooleanAtomic", "U", "timeBound",  "BooleanAtomic"], ["F", "timeBound", "BooleanAtomic"], ["G", "timeBound", "BooleanAtomic"], ["BooleanAtomic"]],
    "timeBound": [["[","atomic",",","atomic","]"]],
    "BooleanAtomic": [["GT"], ["GE"], ["LT"], ["LE"], ["EQ"], ["NEQ"], ["(","boolExpr",")"], ["NOT", "BooleanAtomic"]],
    "GT": [["Variable", "Parameter"]],
    "GE": [["Variable", "Parameter"]],
    "LT": [["Variable", "Parameter"]],
    "LE": [["Variable", "Parameter"]],
    "EQ": [["Variable", "Parameter"]],
    "NEQ": [["Variable", "Parameter"]]
}

terminalNodes = ["Variable", "Parameter"]


class Node:
    def __init__(self, name, ruleTree=None):
        self.name = name
        self.type = re.sub('[0-9]', '', self.name) #type of node (name stripped of number ID)
        self.visitNum = 0

        self.ruleTree = ruleTree #current rule structure of this node

class RuleTemplate(treelib.Tree):
    def __init__(self, default=True):
        super(RuleTemplate, self).__init__()

        self.idDict = {}  # tracking current ids

        if default: self.makeDefaultTree()


    def makeDefaultTree(self):
        # Make start  of rule template
        self.create_node(identifier=self.generateID("eval"), parent=None, data=Node(name="evl1"))
        self.create_node(identifier=self.generateID("statementList"), parent="eval1", data=Node(name="statementList1"))
        self.create_node(identifier=self.generateID("statement"), parent="statementList1", data=Node(name="statemen1"))
        self.create_node(identifier=self.generateID("boolExpr"), parent="statement1", data=Node(name="boolExpr1"))
        self['boolExpr1'].data.ruleTree = copy.deepcopy(self)

    # generate unique ids for tree
    def generateID(self, type):
        if type in self.idDict:
            val = self.idDict.get(type) + 1
            self.idDict[type] = val
        else:
            val = 1
            self.idDict[type] = val

        return type + str(val)

    # show tree structure and groups
    def showTree(self):
        self.show(idhidden=False, data_property="name")

