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
internalNodes = ["eval", "statementList", "statement", "boolExpr", "stlTerm", "BooleanAtomic", "GT", "GE", "LE", "LT", "EQ", "NEQ"]

class Branch: #Set of nodes in tree
    def __init__(self, name, parentNode, activeClients):
        self.name = name
        self.parent = parentNode #parent node branch belongs to
        self.activeClients = activeClients #list of active client numbers at this branch
        self.updatedActiveClients = [] #updated list of what clients are active after the query completed at this branch, used for child node query
        self.visits = 0.0
        self.depth = 0
        self.nodes = []
        self.completelyExplored = False #Check if branch has been completely explored and should not be selected anymore

        self.matchScores = [] #list of match count scores + number of clients queried in format [percentage, num clients]
        self.uct = 0.0 #UCT score of branch

        self.ruleTree = RuleTree()

    def getCurrentScore(self): #return sum of percent match score
        counts = [item[0] for item in self.matchScores]
        numClients = [len(item[1]) for item in self.matchScores]

        perCount = sum(counts) / sum(numClients)

        # print("\n", self.name)
        # print(self.ruleTree.show())
        # print("counts:", counts)
        # print("num clients", numClients)
        # print("per count", perCount)
        return perCount

    def allChildrenCompletelyExplored(self):
        if self.hasChildren():
            for n in self.nodes:
                for childBranch in n.children:
                    if not childBranch.completelyExplored:
                        return False

            return True
        else: #Node is not completely expanded, so return False
            return False


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
        # print("\ntesting term branch for ", self.name)
        # print([n.type for n in self.nodes])
        # print([n.name for n in self.nodes])

        #Check for empty node list
        if self.nodes == []:
            return False

        for n in self.nodes:
            if n.type not in terminalNodes:
                # print("n type not in term nodes", n.type)
                return False

        return True



class Node: #single STL type
    def __init__(self, name):
        self.name = name
        self.type = re.sub(r'\#.*', '', self.name)  # type of node (name stripped of number ID)
        self.branch = None
        self.children = [] #list of branch children


#Full Rule Template
class RuleTemplate():
    def __init__(self, varDict, default=True, clientList=None, verbose=True):
        self.root = None #name of root node
        self.clientList = clientList #dict of clients
        self.verbose = verbose
        self.nodeIDDict = {}  # tracking current IDs of node
        self._nodes = {} #dict of nodes in template- nodeName: node object
        self._branches = {}
        self._varDict= varDict
        # self.dotGraph = pydot.Dot(graph_type='digraph', forcelabels=True) # Make pydot graph to visualize rule template

        self.logger = logging.getLogger('Rule Template')

        self.graphNum = 1

        if default: self.makeDefaultTree()

    def makeDefaultTree(self):
        self.addBranch(branch=['eval'], parentName=None)


    def getBranch(self, name):
        try:
            return self._branches[name]
        except:
            self.logger.error("Branch name not found")

    def addBranch(self, branch, parentName, varBranch=False):
        #get actual parent node from rule template
        if parentName != None:
            parentNode = self._nodes[parentName]
            # ac = parentNode.branch.activeClients #TODO HERE
            ac = parentNode.branch.updatedActiveClients
        else:
            parentNode = None
            ac = list(self.clientList.keys())

        #get subnode name IDs
        nodeNames = []
        for n in branch:
            nodID = self.generateID(n)
            nodeNames.append(nodID)

        # make branch object and add it to parentNode
        brID = "[" + ' '.join(map(str, nodeNames)) + "]"
        br = Branch(name=brID, parentNode=parentNode, activeClients=ac)
        self._branches[brID] = br

        if parentNode == None:
            self.root = brID

        else: #add branch to children of parent node
            parentNode.children.append(br)
            br.ruleTree = copy.deepcopy(parentNode.branch.ruleTree)
            br.depth = parentNode.branch.depth + 1 #increment depth for branch

        # #add branch to dot graph
        # clusterBranch = pydot.Cluster(brID, label=brID)
        # self.dotGraph.add_subgraph(clusterBranch)


        for n in nodeNames:
            nod = Node(n) #make node object
            nod.branch = br #link node to its branch

            if varBranch: #fix type of node not to var name but to be variable
                vars = []
                if re.sub(r'\#.*', '', n) != "Parameter":
                    nod.type = "Variable"
                    vars.append(re.sub(r'\#.*', '', n))

                br.ruleTree.varList.extend(vars) #add vars to varList

            br.nodes.append(nod) #add node to branch

            #add nodes to rule temp
            self._nodes[n] = nod

            # #add node to dot graph
            # clusterBranch.add_node(pydot.Node(n))
            # if parentNode != None:
            #     self.dotGraph.add_edge(pydot.Edge(parentName, n))  # connect edge btw parent and node

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

        # #remove node from graph
        # # print("del edge", node.branch.parent.name, nodeName)
        # self.dotGraph.del_edge('"' + node.branch.parent.name + '"', '"' + nodeName + '"') #delete edge
        # # print("edge list", [x.__str__() for x in self.dotGraph.get_edge_list()])
        #
        # cluster = self.dotGraph.get_subgraph('"cluster_' + node.branch.name + '"')[0] #delete node from cluster
        # cluster.del_node('"' + nodeName + '"')


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

        #remove branch from parent node
        branch.parent.children.remove(branch)

        #remove nodes
        while len(branch.nodes) != 0:
            n = branch.nodes[0]
            self.removeNode(n.name)

        #remove branch from list
        if branchName in self._branches.keys():
            del self._branches[branchName] #remove node from node list

    #Prune any branches who have a match score < cutoff
    def pruneTree(self, cutoff):
        delNames = []
        for key, br in self._branches.items():
            # if has been visited and score < cutoff or no more active clients, prune branch
            # if (br.visits > 0 and br.getCurrentScore() < cutoff) or len(br.activeClients) == 0:
            if br.visits > 0 and br.getCurrentScore() < cutoff :

                if self.verbose:
                    self.logger.info("PRUNING BRANCH " +  key)
                    self.logger.info("Got score " + str(br.getCurrentScore()) + " < cutoff thresh " + str(cutoff) + "\n")
                delNames.append(key)

        for n in delNames:
            self.removeBranch(n)

        if delNames != []:
            # if self.verbose:
            #     self.logger.info("**Saved Graph " + str(self.graphNum) + "_" + 'Pruning Step\n')
            # self.saveGraph(graphName='PRUNED TREE')
            pass
        else:
            if self.verbose:
                self.logger.info("Nothing to prune\n")


    # generate unique node ids for tree
    def generateID(self, type):
        if type in self.nodeIDDict:
            val = self.nodeIDDict.get(type) + 1
            self.nodeIDDict[type] = val
        else:
            val = 1
            self.nodeIDDict[type] = val

        return type + "#" + str(val)

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

    #Get number of terminal branches
    def getNumTerminalBranches(self):
        num = 0
        for key, br in self._branches.items():
            if br.terminalBranch():
                num += 1

        return num

    def getLeafBranches(self):
        brList = []
        for key, br in self._branches.items():
            if not br.hasChildren():
                brList.append(br)

        return brList

    def generateRuleSet(self):
        '''
        Code to generate fule rule set from template
        :return: Rule Set
        '''
        branch = self._branches[self.root]
        trees = self.traverseLeaf(branch)

        #Remove duplicate rules
        trees = list(set(trees))

        return trees


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
                    # print("Multi child tree gen")
                    # rt.show()
                    # print(rt.toString())

                #add combined trees to real tree list
                trueLeaf = True
                leaves = rt.leaves()
                # print("full leaves", leaves)

                #Make sure all leaf nodes actually leaves --> var or param
                for l in leaves:
                    # print("leaf", l, "named", re.sub(r'\#.*', '', l.identifier))

                    if re.sub(r'\#.*', '', l.identifier) in internalNodes: #Rule not complete - there are internal nodes that are not complete
                        # print("not true leaf", l.identifier)
                        trueLeaf = False

                if trueLeaf:
                    # print("true leaves", leaves)
                    realTrees.append(rt)

            # print("real trees", [r.toString() for r in realTrees])
            return realTrees

        if not branch.hasChildren(): #reached leaf nodes
            if branch.terminalBranch() and branch.visits > 0: #only append rule if is true leaf node that has been visited--> var or param
                # print("BRANCH in child part", branch.name)
                # print("trees", [t.toString() for t in trees])

                if branch.ruleTree.activeClients == []:
                    branch.ruleTree.activeClients = copy.deepcopy(branch.activeClients) #add active clients to rule tree
                    branch.ruleTree.percentCount = branch.getCurrentScore()  # add percent count to rule tree

                trees.append(branch.ruleTree)
                # print("trees after appending", [t.toString() for t in trees])
            return trees
        else:
            for opt in branch.getChildBranches():
                trees = self.traverseLeaf(opt, trees)

        # print("final return trees", [t.toString() for t in trees])
        # print("length of final trees", len(trees))
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
        parentTree.remove_node(nodeName)  # remove duplicate nodes to be added in main tree
        parentTree.paste(parentNode, subtree)  # paste subtree onto parent

        #add active clients and percent counts to parent tree
        ac = copy.deepcopy(parentTree.activeClients)
        ac.extend(childTree.activeClients)
        parentTree.activeClients = list(set(ac))
        parentTree.varList.extend(childTree.varList) #add var list

        if parentTree.percentCount == None or childTree.percentCount > parentTree.percentCount:
            parentTree.percentCount = childTree.percentCount

        return parentTree

    def getBranchesNoChildren(self):
        lst = []
        for b, br in self._branches.items():
            if not br.hasChildren():
                lst.append(br)

        return lst
