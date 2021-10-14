import pydot
from IPython.display import Image, display
import io
from PIL import Image

import re
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

import graphviz

class Branch: #Set of nodes in tree
    def __init__(self, name, parentNode):
        self.name = name #name should be in [stl AND stl]1 format
        self.visits = 0

        self.nodes = []

        self.parent = parentNode #parent node branch belongs to

class Node: #single STL type
    def __init__(self, name):
        self.name = name
        self.type = re.sub('[0-9]', '', self.name)  # type of node (name stripped of number ID)
        self.visits = 0

        self.children = [] #list of branch children



class RuleTemplate():
    def __init__(self, default=True):

        #Make pydot graph to visualize rule template
        self.dotGraph = pydot.Dot(graph_type='digraph')

        self.nodeIDDict = {}  # tracking current IDs of node

        self._nodes = {} #dict of nodes in template- nodeName: node object
        self._branches = {}

    #     if default: self.makeDefaultTree()
    #
    #
    # def makeDefaultTree(self):


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
            self.root = br
        else: #add branch to children of parent node
            parentNode.children.append(br)

        #add branch to dot graph
        clusterBranch = pydot.Cluster(brID, label=brID)
        self.dotGraph.add_subgraph(clusterBranch)

        for n in nodeNames:
            nod = Node(n) #make node object
            br.nodes.append(nod) #add node to branch

            #add nodes to rule temp
            self._nodes[n] = nod

            #add node to dot graph
            clusterBranch.add_node(pydot.Node(n))
            if parentNode != None:
                self.dotGraph.add_edge(pydot.Edge(parentName, n))  # connect edge btw parent and node


    def removeNode(self, nodeName):
        pass

    def removeBranch(self, branchName):
        pass

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
    def showGraph(self):
        img = Image.open(io.BytesIO(self.dotGraph.create_png()))  # .show()
        plt.imshow(img)  # to show in pycharm sciview
        plt.show()

    def saveGraph(self, graphName):
        self.dotGraph.write(graphName, format='png') #to save to file
        # "Graphs/img.png"


if __name__ == "__main__":

    rt = RuleTemplate()
    rt.addBranch(branch=["eval"], parentName=None)
    rt.addBranch(branch=["stl", "&", "stl"], parentName="eval1")
    rt.addBranch(branch=["stl", "|", "stl"], parentName="eval1")
    rt.addBranch(branch=["F", "BO"], parentName="stl1")

    print(rt._nodes)
    print(rt.root.nodes)

    rt.showGraph()
    # #test graph
    #
    # #Make graph
    # graph = pydot.Dot(graph_type='digraph')
    #
    # #make nodes
    # # pydot.Node("a", label="BoolExpr") #make node
    # # graph.add_node(pydot.Node("a", label="BoolExpr")) #add node to graph
    # # graph.add_node(pydot.Node("p", label="Parent"))  # add node to graph
    # # graph.add_edge(pydot.Edge("p", "a")) #connect edge btw parent and node
    #
    # graph.add_node(pydot.Node("a"))  # add node to graph
    # graph.add_node(pydot.Node("p"))  # add node to graph
    # graph.add_edge(pydot.Edge("p", "a", color='red'))  # connect edge btw parent and node
    #
    # # node_a = pydot.Node("STL1")
    # # node_b = pydot.Node("AND")
    # # node_c = pydot.Node("STL2")
    # #
    # # #add nodes to graph
    # # graph.add_node(node1)
    # # graph.add_node(node_a)
    # # graph.add_node(node_b)
    # # graph.add_node(node_c)
    # #
    # # #add edges
    # # graph.add_edge(pydot.Edge(node1, node_a))
    # # graph.add_edge(pydot.Edge(node1, node_b))
    # # graph.add_edge(pydot.Edge(node1, node_c))
    #
    # # graph.write("Graphs/img.png", format='png') #to save to file
    # img = Image.open(io.BytesIO(graph.create_png()))#.show()
    # plt.imshow(img) #to show in pycharm sciview
    # plt.show()
    #
    # #GRAPHVIZ
    # # # Make graph
    # # graph = graphviz.Digraph("NameGraph", format='png')
    # #
    # # # make nodes
    # # graph.node('1', 'BoolExpr')
    # # graph.node('2', "STL1")
    # # graph.edge('1', '2')
    # #
    # # graph.render(view=True)
