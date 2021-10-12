import logging
import copy
import treelib
import re
import math
import random
from RuleTemplate.RuleTemplate import RuleTemplate, Node, stlGrammarDict, terminalNodes



class Server :
    def __init__(self, clientList, varDict, params):
        self.clientList = clientList  # dict of clients
        self.varDict = varDict  # variable dictionary to store vars + ranges
        self.variables = list(self.varDict.keys())

        #template params
        if params.template == None:
            # make default rule template tree to start
            self.templateTree = RuleTemplate(default=True)
            self.rootNode = 'boolExpr1'

        else: #TODO - add option to start from preset template
            pass

        #mcts params
        self.defaultPolicy = params.defaultPolicy

        #Privacy budget params
        self.epsilon = params.epsilon
        self.clientsWithUsedBudgets = []  # list of clients who have used budget

        #Output params
        self.verbose = params.verbose
        self.logger = logging.getLogger('SERVER')
        self.mcLogger = logging.getLogger('MCTS')

    def checkClientBudgetsUsed(self):
        # print("clients used budgets", self.clientsWithUsedBudgets)
        if list(self.clientList.keys()) == set(self.clientsWithUsedBudgets):
            return True
        # elif len(set(self.clientsWithUsedBudgets)) > len(self.clientList) - 3:  # only a few clients without used budgets so end
        #     return True
        else:
            return False

    # RUN Monte Carlo Tree Search
    def runMCTS(self):
        usedBudget = 0
        states = [self.rootNode]

        while usedBudget < self.epsilon:
            # SELECTION
            branches = []
            branch = self.selectBranch(states[-1])
            print("Branch selected:", branch)

            #TODO - working here - line 89 in robo grammar
            while branch != None:
                pass

            usedBudget = 1


    # state is string name of node
    #Returns the selected branch choice
    def selectBranch(self, state):
        # get actual current node from state name
        currNode = self.templateTree[state]
        if self.verbose:
            print("CurrNode:", currNode.identifier)

        # get available branch choices
        branchChoices = stlGrammarDict[currNode.data.type]
        if self.verbose:
            print("Next Set of Branch Choices", branchChoices)

        if all([x == terminalNodes for x in branchChoices]): #Reached only terminal nodes
            if self.verbose:
                print("Reached terminal nodes")
            return None

        else:
            # If state unvisited
            if currNode.data.visitNum == 0:  # state unvisited --> follow default policy
                # TODO - make alternative default policies
                if self.defaultPolicy == "random": #Randomly select a branch
                    return random.choice(branchChoices)

            else:  # follow tree policy
                # TODO - adapt tree policy potentially

                # get branch choice that has max of uct score
                if self.verbose:
                    print("Tree Policy selected")

                maxScore = 0
                maxBranch = None
                for bc in branchChoices:
                    uct = self.uctScore(currNode, bc)
                    if uct > maxScore:
                        maxScore = uct
                        maxBranch = bc

                return maxBranch

    #branch is string type
    def uctScore(self, currNode, branch): #TODO - Update UCT scoring method
        #Get actual branch in tree to get visit count
        nodeChilds = self.templateTree.children(currNode.identifier)
        idx = [i for i, s in enumerate(nodeChilds) if branch in s][0]
        branchVisitCount = self.templateTree[nodeChilds[idx]].data.visitNum

        if branchVisitCount > 0:
            #get reward for current node --> count of client yes responses
            #Make test template
            testTemp = copy.deepcopy(currNode.data.ruleTree)
            for n in branch:
                id = testTemp.generateID(n)
                testTemp.create_node(identifier=id, parent=currNode.identifier, data=Node(name="boolExpr1"))

            percentCount = self.queryClientRuleMatch(testTemp)

            uct = 2*(1/math.sqrt(2)) * math.sqrt(2.0 * math.log(currNode.data.visitNum)/branchVisitCount)
            score = percentCount + uct

        else:
            return float('inf')

        if self.verbose:
            print("UCT Score for possible branch", branch, ": ", score)

        return score


    # Get a % of how many clients have a match to the template
    def queryClientRuleMatch(self, template):
        # get template node list
        tempNodes = self.getTemplateNodes(template)
        # print("temp nodes", tempNodes)

        # get count from clients of who have template
        yesCount = 0
        trueYesses = 0
        p = None

        for c in self.clientList:
            resp, truResp, p = self.clientList[c].randResponseQueryStruct(tempNodes)
            trueYesses += truResp
            if resp == "BUDGET USED":
                self.clientsWithUsedBudgets.append(c)
            else:
                yesCount += resp

        if not self.checkClientBudgetsUsed():
            q = 1-p
            estTrueCount = (yesCount - (len(self.clientList) * q)) / (p-q)
            percentCount = float(estTrueCount / len(self.clientList))

            truePerCount = float(trueYesses / len(self.clientList)) #Real percent

            #Fix negative estimates
            if percentCount < 0:
                percentCount = 0.0

            if self.verbose:
                # print("yes cnt", yesCount, "p", p, "q", q, "est true count", estTrueCount)
                print("True Percent", truePerCount, "Est Percent", percentCount)

            return percentCount

        # else:
        return "BUDGET USED"

    # Get list of nodes from template
    def getTemplateNodes(self, temp):
        nodes = []
        parent = None
        ignoreList = ["(", ")"]
        for n in temp.expand_tree(mode=treelib.Tree.WIDTH, sorting=True):
            if temp.parent(n) != parent:
                parent = temp.parent(n)
                nodes.append("newLevel")

            nd = temp.get_node(n)
            id = re.sub('[0-9]', '', nd.identifier)

            if id not in ignoreList:
                nodes.append(id)  # remove numbers, append name

        return nodes