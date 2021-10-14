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
            # self.rootNode = 'boolExpr1'
            self.rootNode = 'statement1'

        else: #TODO - add option to start from preset template
            pass

        #mcts params
        self.cp = params.cp

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

        while usedBudget < self.epsilon:
            # SELECTION
            if (self.verbose):
                self.mcLogger.info("Begin Search\n")

            currNode = self.templateTree[self.rootNode] #get actual branch node

            X = self.selection(currNode)

            #to del
            self.templateTree['boolExpr1'].data.visits = 1

            Y = self.expansion(X)
            # if (Y):
            #     Result = self.Simulation(Y)
            #     if (self.verbose):
            #         print
            #         "Result: ", Result
            #     self.Backpropagation(Y, Result)
            # else:
            #     Result = game.GetResult(X.state)
            #     if (self.verbose):
            #         print
            #         "Result: ", Result
            #     self.Backpropagation(X, Result)
            # self.PrintResult(Result)

            usedBudget = 1

        if self.verbose:
            self.mcLogger.info("Search Completed")

    #### SELECTION
    def selection(self, currBranch):
        '''
        Perform selection phase of MCTS search
        :param currBranch: branch to start at
        :return: selected branch
        '''
        if self.verbose:
            self.mcLogger.info("--SELECTION PHASE--")
            self.mcLogger.info("Current Branch: " + currBranch.identifier)

        while len(self.templateTree.children(currBranch.identifier)) != 0:
            currBranch = self.selectChildBranch(currBranch)

        if self.verbose:
            self.mcLogger.info("Returned Branch: " + currBranch.identifier + "\n")

        return currBranch

    def selectChildBranch(self, branch):
        '''
        Select 1st unvisited child node, or if all children visited, select node with highest UTC value
        :param branch: branch node to start select from
        :return: selected child branch
        '''

        if self.verbose:
            self.mcLogger.info("Selecting Child Branch from " + branch.identifier)


        if branch.data.type in terminalNodes: #if branch is a leaf node
            if self.verbose:
                self.mcLogger.info("Branch terminal, returning")
            return branch

        for child in self.templateTree.children(branch.identifier):
            if child.data.visits == 0.0: #univisted child node
                if self.verbose:
                    self.mcLogger.info("Found univisited child node " + child.identifier)
                return child

        if self.verbose:
            self.mcLogger.info("All children visited, selecting node with highest UTC value")

        maxUTC = -1
        bestChild = None
        for child in self.templateTree.children(branch.identifier):
            utc = self.utcScore(child)

            if utc > maxUTC:
                maxUTC = utc
                bestChild = child

        return bestChild


    def utcScore(self, branch):

        # get reward for current node --> count of client yes responses
        percentCount = self.queryClientRuleMatch(branch.data.ruleTree)

        uct = percentCount + self.cp * math.sqrt(math.log(branch.parent().data.visits) / branch.data.visits)

        return uct


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

    #### EXPANSION
    def expansion(self, selectedBranch):
        '''
        Expand the previously selected node
        :param selectedBranch:
        :return: ending node of expansion trace
        '''

        if self.verbose:
            self.mcLogger.info("--EXPANSION PHASE--")

        if selectedBranch.data.type in terminalNodes: #fully expanded --> at leaf node
            if self.verbose:
                self.mcLogger.info("Terminal node reached, expansion completed\n")

            return None

        elif selectedBranch.data.visits == 0: #branch unvisited
            if self.verbose:
                self.mcLogger.info("Branch unvisited, returning selected branch\n")
            return selectedBranch

        else:
            if len(self.templateTree.children(selectedBranch.identifier)) == 0: #no children added to node yet
                branchChildren = self.evaluateChildren(selectedBranch) #get possible child branches
                self.templateTree.addChildBranches(parent=selectedBranch, childNodes=branchChildren) #add all children to branch

                if self.verbose:
                    self.mcLogger.info("Updated Template Tree:")
                    self.templateTree.showTree()

            #select child acc to policy

    def evaluateChildren(self, branch):
        '''
        Evaluate all possible children states (branches) and add all those that are feasible / possible to visit
        :param branch: current branch to explore children states of
        :return: child branch options
        '''
        if self.verbose:
            self.mcLogger.info("Evaluating child branches")

        branchChoices = stlGrammarDict[branch.data.type]
        if self.verbose:
            self.mcLogger.info("Found Possible Child Branches: {}".format(' '.join(map(str, branchChoices))))

        return branchChoices