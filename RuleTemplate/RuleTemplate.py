import pydot
from IPython.display import Image, display
import io
from PIL import Image
import re
import logging
import matplotlib.pyplot as plt
import treelib
import copy

from RuleTemplate.RuleTree import RuleTree

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


class Branch: #Set of nodes in tree
    def __init__(self, name, parentNode):
        self.name = name
        self.parent = parentNode #parent node branch belongs to
        self.visits = 0
        self.nodes = []

        self.uctScores = [] #list of scores for this branch
        self.matchScores = [] #list of match count scores for this branch in format [percentage, num clients]
        #TODO - make adaptive active client thing here ...

        self.ruleTree = RuleTree()

    def hasChildren(self):
        for n in self.nodes:
            if n.children != []:
                return True

        return False

    def terminalBranch(self):
        for n in self.nodes:
            if n.type not in terminalNodes:
                return False

        return True


class Node: #single STL type
    def __init__(self, name):
        self.name = name
        self.type = re.sub('[0-9]', '', self.name)  # type of node (name stripped of number ID)

        self.branch = None
        self.children = [] #list of branch children


#Full Rule Template
class RuleTemplate():
    def __init__(self, default=True):
        self.root = None #name of root node
        self.nodeIDDict = {}  # tracking current IDs of node
        self._nodes = {} #dict of nodes in template- nodeName: node object
        self._branches = {}
        self.dotGraph = pydot.Dot(graph_type='digraph', forcelabels=True) # Make pydot graph to visualize rule template
        self.logger = logging.getLogger('Rule Template')

        if default: self.makeDefaultTree()

    def makeDefaultTree(self):
        self.addBranch(branch=['eval'], parentName=None)
        self.addBranch(branch=['statementList'], parentName="eval1")
        self.addBranch(branch=['statement'], parentName="statementList1")
        self.addBranch(branch=['boolExpr'], parentName="statement1")

    def getBranch(self, name):
        try:
            return self._branches[name]
        except:
            self.logger.error("Branch name not found")

    def addBranch(self, branch, parentName):
        #get actual parent node from rule template
        if parentName != None:
            parentNode = self._nodes[parentName]
        else:
            parentNode = None

        #get subnode name IDs
        nodeNames = []
        for n in branch:
            nodID = self.generateID(n)
            nodeNames.append(nodID)

        # make branch object and add it to parentNode
        brID = "[" + ' '.join(map(str, nodeNames)) + "]"
        br = Branch(name=brID, parentNode=parentNode)
        self._branches[brID] = br

        if parentNode == None:
            self.root = brID

        else: #add branch to children of parent node
            parentNode.children.append(br)
            br.ruleTree = copy.deepcopy(parentNode.branch.ruleTree)

        #add branch to dot graph
        clusterBranch = pydot.Cluster(brID, label=brID)
        self.dotGraph.add_subgraph(clusterBranch)

        for n in nodeNames:
            nod = Node(n) #make node object
            nod.branch = br #link node to its branch
            br.nodes.append(nod) #add node to branch

            #add nodes to rule temp
            self._nodes[n] = nod

            #add node to dot graph
            clusterBranch.add_node(pydot.Node(n))
            if parentNode != None:
                self.dotGraph.add_edge(pydot.Edge(parentName, n))  # connect edge btw parent and node

        #make rule template
        for n in nodeNames:
            br.ruleTree.create_node(identifier=n, parent=parentName)

        return br #return added branch

    def removeNode(self, nodeName):
        try:
            node = self._nodes[nodeName]
        except:
            self.logger.error("ERROR: cannot find node " +  nodeName)
            return

        if node.children != []:
            self.logger.error("ERROR: cannot remove node, node has children")
            return

        node.branch.nodes.remove(node) #remove node from branch
        del self._nodes[nodeName] #remove node from node list

        #remove node from graph
        self.dotGraph.del_edge(node.branch.parent.name, nodeName) #delete edge
        cluster = self.dotGraph.get_subgraph('"cluster_' + node.branch.name + '"')[0] #delete node from cluster
        cluster.del_node(nodeName)

        #check if all child nodes have been removed from the branch - if so, remove branch
        if node.branch.nodes == []:
            self.logger.info("All nodes removed from branch, removing branch from template")
            self.removeBranch(node.branch.name)


    def removeBranch(self, branchName):
        try:
            branch = self._branches[branchName]
        except:
            self.logger.error("ERROR: cannot find branch " + branchName)
            return

        #make sure no nodes have children
        if branch.hasChildren():
            self.logger.error("ERROR: cannot remove branch, one or more nodes have children")
            return

        #remove nodes
        while len(branch.nodes) != 0:
            n = branch.nodes[0]
            self.removeNode(n.name)

        #remove branch from list
        if branchName in self._branches.keys():
            del self._branches[branchName] #remove node from node list


    # generate unique node ids for tree
    def generateID(self, type):
        if type in self.nodeIDDict:
            val = self.nodeIDDict.get(type) + 1
            self.nodeIDDict[type] = val
        else:
            val = 1
            self.nodeIDDict[type] = val

        return type + str(val)

    #Pydot Graph Functions
    def showGraph(self, title=None):
        plt.figure(figsize=[40,25])
        img = Image.open(io.BytesIO(self.dotGraph.create_png()))  # .show()
        plt.imshow(img)  # to show in pycharm sciview
        if title != None:
            plt.title(title)
        plt.show()

    def saveGraph(self, graphName):
        self.dotGraph.write(graphName, format='png') #to save to file
        # "Graphs/img.png"

    printList = ["G", "F", "U", "[", "]", "(", ")", "atomic"]
    rop = ["GT", "GE", "LT", "LE", "EQ", "NEQ"]
    ropSymbol = [">", ">=", "<", "<=", "=", "!="]

    def getRule(self, branchName, string=None):
        test = treelib.Tree()

        br = self.getBranch(branchName)
        paren = br.parent

        for nod in br.nodes:
            test.create_node(identifier=nod.name, parent=None)

        while paren != None:
            #make parent nodes
            for nod in paren.branch.nodes:
                test.create_node(identifier=nod.name, parent=None)

                #update child nodes
                for n in nod.children:
                    for nn in n.nodes:
                        test.update_node(nn.name, parent=nod.name)

            paren = paren.parent

        test.show()





