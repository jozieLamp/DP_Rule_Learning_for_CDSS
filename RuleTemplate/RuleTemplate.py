import pydot
from IPython.display import Image, display
import io
from PIL import Image
import re
import logging
import matplotlib.pyplot as plt
import treelib
import copy
import itertools

from RuleTemplate.RuleTree import RuleTree
from SignalTemporalLogic.STLFactory import STLFactory

#Grammar Dictionary for easier access of child nodes in template tree
stlGrammarDict = {
    "eval": [["statementList"]],
    "statementList": [["statement"]],
    # "statement": [["(","boolExpr",")"]],
    "statement": [["boolExpr"]],
    "boolExpr": [["stlTerm"], ["stlTerm", "AND", "stlTerm"], ["stlTerm", "OR", "stlTerm"], ["stlTerm", "IMPLIES", "stlTerm"] ],
    "stlTerm": [["BooleanAtomic", "U", "timeBound",  "BooleanAtomic"], ["F", "timeBound", "BooleanAtomic"], ["G", "timeBound", "BooleanAtomic"], ["BooleanAtomic"]],
    # "timeBound": [["[","atomic",",","atomic","]"]],
    # "BooleanAtomic": [["GT"], ["GE"], ["LT"], ["LE"], ["EQ"], ["NEQ"], ["(","boolExpr",")"], ["NOT", "BooleanAtomic"]],
    "BooleanAtomic": [["GT"], ["LT"], ["EQ"], ["NEQ"], ["(", "boolExpr", ")"],["NOT", "BooleanAtomic"]],
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
        self.visits = 0.0
        self.depth = 0
        self.nodes = []

        self.matchScores = [] #list of match count scores + number of clients queried in format [percentage, num clients]
        self.uct = 0.0 #UCT score of branch
        #TODO - make adaptive active client thing here ...

        self.ruleTree = RuleTree()

    def getCurrentScore(self): #return sum of percent match score
        counts = [item[0] for item in self.matchScores]
        numClients = [len(item[1]) for item in self.matchScores]
        perCount = sum(counts) / sum(numClients)
        return perCount

    def hasChildren(self):
        for n in self.nodes:
            if n.children != []:
                return True

        return False

    def multiChildBranch(self):
        ccount = 0
        for nod in self.nodes:
            if nod.children != []:
                ccount += 1

        if ccount > 1:
            return True
        else:
            return False

    def getChildBranches(self):
        childs = []
        for nod in self.nodes:
            if nod.children != []:
                childs.extend(nod.children)

        return childs

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

        self.graphNum = 1

        if default: self.makeDefaultTree()

    def makeDefaultTree(self):
        self.addBranch(branch=['eval'], parentName=None)
        # self.getBranch('[eval1]').visits = 1
        # self.addBranch(branch=['statementList'], parentName="eval1")
        # self.addBranch(branch=['statement'], parentName="statementList1")
        # self.addBranch(branch=['boolExpr'], parentName="statement1")

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
            br.depth = parentNode.branch.depth + 1 #increment depth for branch

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

    #Prune any branches who have a match score < cutoff
    def pruneTree(self, cuttoff):

        pass
        #prune branches -- and then do check, if branch has all children pruned, remove parent branch also ...


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
        nme = "RuleTemplate/Graphs/" + str(self.graphNum) + "_" + graphName + ".png"
        self.dotGraph.write(nme, format='png') #to save to file
        self.graphNum += 1
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


    def getLeafBranches(self):
        brList = []
        for key, br in self._branches.items():
            if not br.hasChildren():
                brList.append(br)

        return brList

    def generateRuleSet(self, verbose):
        '''
        Code to generate fule rule set from template
        :return: rule set
        '''
        ruleSet = []
        branch = self._branches[self.root]
        trees = self.traverseLeaf(branch)

        #Remove duplicate rules
        trees = list(set(trees))

        #Only get correctly formatted rules
        for t in trees:
            stlFac = STLFactory()  # Check if structure correct
            ft = stlFac.constructFormulaTree(t.toStringWithParams() + "\n")

            if ft != None:  # Formula is not improper
                ruleSet.append(t)

        # Print first set of rules
        if verbose:
            self.logger.info("Produced Rule Structures: ")
            for t in trees:
                self.logger.info(t.toString())

        self.logger.info("Produced " + str(len(trees)) + " Rule Structures")
        self.logger.info("Generated " + str(len(ruleSet)) + " Formatted Rules\n")

        return ruleSet

    def traverseLeaf(self, branch, trees=[]):
        if branch.multiChildBranch():
            # print("Reached multi branch", branch.name)

            realTrees = copy.deepcopy(trees)

            nodeList = [] #list of nodes with children getting combos for
            options = []
            for n in branch.nodes: #Get all leaf options for this split
                sub = []
                for c in n.children:
                    sub.extend(self.traverseLeaf(c, trees=[]))

                if sub != []:
                    nodeList.append(n)
                    options.append(sub)

            #Get all combinations of the leaf items for each node in split
            combos = list(itertools.product(*options))
            for com in combos:
                rt = copy.deepcopy(branch.ruleTree) #make copy of current branch tree

                for i in range(len(com)): #for each subtree to be added from combos
                    rt = self.addSubtreeToRuleTree(parentTree=rt, childTree=com[i], nodeName=nodeList[i].name)

                    #add combined trees
                    realTrees.append(rt)

            return realTrees

        if not branch.hasChildren(): #reached leaf nodes
            trees.append(branch.ruleTree)
            return trees
        else:
            for opt in branch.getChildBranches():
                trees = self.traverseLeaf(opt, trees)

        return trees

    def addSubtreeToRuleTree(self, parentTree, childTree, nodeName):
        #Node name is where subtree node will be added at in parent tree / cut off from subtree

        # print("Current parent tree")
        # parentTree.show()
        #
        # print("child tree to be added")
        # childTree.show()
        #
        # print("Nodename getting subtree at:", nodeName)
        subtree = childTree.subtree(nodeName)  # make copy of subtree
        # print("subtree")
        # subtree.show()

        # Get parent node name in rule tree
        parentNode = parentTree.parent(nodeName).identifier
        # print("Paren name", parentNode)
        parentTree.remove_node(nodeName)  # remove duplicate nodes to be added in main tree
        parentTree.paste(parentNode, subtree)  # paste subtree onto parent

        return parentTree

