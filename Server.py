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
    def runMCTS(self, branchName):
        usedBudget = 0


        # while usedBudget < self.epsilon:
        while not self.checkClientBudgetsUsed():
            # SELECTION
            if (self.verbose):
                self.mcLogger.info("Begin Search\n")

            currBranch = self.templateTree._branches[branchName]

            X = self.selection(currBranch) #TODO - may need to fix selection to do multiple paths from branches with multi nodes
            if self.verbose:
                self.templateTree.showGraph(title='Selection Step')

            Y = self.expansion(X)

            if Y != None:
                result = self.simulation(Y)
                self.backpropagation(Y, result)

            else:
                result = self.queryClientRuleMatch(X.ruleTree) #TODO - this was originally game.getResult(X.state) may need to adapt this
                if (self.verbose):
                    self.mcLogger.info("Got result " + str(result))

                self.backpropagation(X, result)


        if self.verbose:
            self.mcLogger.info("Search Completed")

    #### SELECTION
    def selection(self, currBranch):
        '''
        Perform selection phase of MCTS search
        :param currBranch: branch(es) to start at
        :return: selected branch(es)
        '''
        if self.verbose:
            self.mcLogger.info("----SELECTION PHASE----")
            self.mcLogger.info("Current Branch: " + currBranch.name)

        while currBranch.hasChildren():
            currBranch = self.selectChildBranch(currBranch)

        if self.verbose:
            self.mcLogger.info("Returned Branch: " + currBranch.name + "\n")

        return currBranch

    def selectChildBranch(self, branch):
        '''
        Select 1st unvisited child branch, or if all children visited, select branch with highest UTC value
        :param branch: branch node to start select from
        :return: selected child branch(es)
        '''

        if self.verbose:
            self.mcLogger.info("Selecting Child Branch from " + branch.name)

        if branch.terminalBranch(): #if branch is a leaf
            if self.verbose:
                self.mcLogger.info("Branch terminal, returning")
            return branch

        for node in branch.nodes:
            for child in node.children:
                if child.visits == 0.0: #univisited child branch
                    self.mcLogger.info("Found univisited child branch " + child.name)
                    return child #child = child branch from node

        if self.verbose:
            self.mcLogger.info("All children visited, selecting node with highest UTC value")


        #Select branch with highest UTC value

        #Note - currently treats each child as separate (even if parent has combined children options ...)
        # TODO HERE -->
        #get all combinations of child nodes
        #for each child combo, get max UTC, update the UTC of each node in the branch

        maxUTC = -1
        bestChild = None

        for node in branch.nodes:
            for child in node.children:
                utc = self.utcScore(child)

                if self.verbose:
                    self.logger.info("UTC for " + child.name + " : " + str(utc))

                if utc > maxUTC:
                    maxUTC = utc
                    bestChild = child

            return bestChild


    def utcScore(self, branch):
        # get reward for current node --> count of client yes responses
        percentCount = self.queryClientRuleMatch(branch.ruleTree)
        parenVisits = branch.parent.branch.visits
        uct = percentCount + self.cp * math.sqrt(math.log(parenVisits) / branch.visits)

        #update scores in branch
        branch.uctScores.append(uct)
        branch.matchScores.append(percentCount)

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

            if resp == "BUDGET USED":
                self.clientsWithUsedBudgets.append(c)
            else:
                yesCount += resp
                trueYesses += truResp

        if not self.checkClientBudgetsUsed():
            q = 1-p
            estTrueCount = (yesCount - (len(self.clientList) * q)) / (p-q)
            percentCount = float(estTrueCount / len(self.clientList))

            truePerCount = float(trueYesses / len(self.clientList)) #Real percent

            #Fix negative estimates
            if percentCount < 0:
                percentCount = 0.0

            #Fix over estimates
            if percentCount > 1.0:
                percentCount = 1.0

            if self.verbose:
                # print("yes cnt", yesCount, "p", p, "q", q, "est true count", estTrueCount)
                self.logger.info("True Percent " + str(truePerCount) +  ", Est Percent " + str(percentCount))

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
            self.mcLogger.info("----EXPANSION PHASE----")

        if selectedBranch.terminalBranch(): #fully expanded --> at leaf node
            if self.verbose:
                self.mcLogger.info("Terminal node reached, expansion completed " + selectedBranch.name +  "\n")

            return None

        elif selectedBranch.visits == 0: #branch unvisited
            if self.verbose:
                self.mcLogger.info("Branch unvisited, returning selected branch "  + selectedBranch.name +  "\n")
            return selectedBranch

        else:
            if not selectedBranch.hasChildren(): #no children added to node yet
                branchChildren = self.evaluateChildren(selectedBranch) #get possible child branches and add to branch

                if self.verbose:
                    self.mcLogger.info("Updated Template Tree")
                    self.templateTree.showGraph(title='Expansion Step')

            #select from the added child branches according to a policy
            return self.selectionPolicy(branchChildren)

    def evaluateChildren(self, branch):
        '''
        Evaluate all possible children states (branches) and add all those that are feasible / possible to visit
        :param branch: current branch to explore children states of
        :return branch children added
        '''
        if self.verbose:
            self.mcLogger.info("Evaluating possible child branches")

        branchChildren = []

        for node in branch.nodes:
            childChoices = stlGrammarDict[node.type] #get possible child branches
            if self.verbose:
                self.mcLogger.info("For node " + node.name + " found Possible Child Branches: {}".format(' '.join(map(str, childChoices))))

            #TODO - potentially evaluate some type of condition here to add the branches to the node ...
            for choice in childChoices:
                br = self.templateTree.addBranch(choice, node.name) #add all children to branch
                branchChildren.append(br)

        return branchChildren


    #TODO - this is currently random, make an actual policy here eventually
    def selectionPolicy(self, branchOptions):
        '''
        Select branch according to policy
        :param branchOptions: List of branches to choose from
        :return:
        '''
        sel = random.choice(branchOptions)

        if self.verbose:
            self.mcLogger.info("Selected branch to explore " +  sel.name + " according to default policy: random\n")

        return sel

    #### SIMULATION
    def simulation(self, selectedBranch):
        '''
        Get some type of simulation result for entire rule at this node

        :param selectedBranch: branch to simulate results for
        :return: simulation result (right now match count to rule)
        '''
        if self.verbose:
            self.mcLogger.info("----SIMULATION PHASE----")
            self.mcLogger.info("Simulating Branch: " + selectedBranch.name)
            selectedBranch.ruleTree.show()

        #Traditional result here is the number of wins or losses --> for us could be # clients with match ???
        #Note - this part could be where the p budgets are tested / evaluated ...
        percentCount = self.queryClientRuleMatch(selectedBranch.ruleTree)

        if self.verbose:
            self.mcLogger.info("Rule Match Percentage: " + str(percentCount) + "\n")

        return percentCount

    def backpropagation(self, startingBranch, score):
        '''
        Backpropagate score up tree
        :param startingBranch: branch to start backpropagation from
        :param score: score to propagate up
        :return:
        '''
        if self.verbose:
            self.mcLogger.info("----BACKPROPAGATION PHASE----")

        #Update current branch
        startingBranch.matchScores.append(score)
        startingBranch.visits += 1 #add visit to this node
        #normally is a self.utcScore() here ... but need to determine how to do this without doubly querying the clients ...

        #prop scores
        br = startingBranch
        while br.parent != None:
            br = br.parent.branch
            br.matchScores.append(score)
            br.visits += 1  # add visit to this node