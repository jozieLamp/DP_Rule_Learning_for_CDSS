import logging
import copy
import treelib
import re
import math
import random
import pandas as pd
from RuleTemplate.RuleTemplate import RuleTemplate, Node, stlGrammarDict, terminalNodes



class Server :
    def __init__(self, clientList, varDict, params):
        self.clientList = clientList  # dict of clients
        self.varDict = varDict  # variable dictionary to store vars + ranges
        self.variables = list(self.varDict.keys())

        # Output params
        self.verbose = params.verbose
        self.logger = logging.getLogger('SERVER')
        self.mcLogger = logging.getLogger('MCTS')

        #template params
        if params.template == None:
            # make default rule template tree to start
            self.templateTree = RuleTemplate(varDict=self.varDict, default=True, verbose=self.verbose)


        else: #TODO - add option to start from preset template
            pass

        #mcts params
        self.maxQueries = params.maxQueries
        self.cp = params.cp
        self.maxTreeDepth = params.maxTreeDepth
        self.cutoffThresh = params.cutoffThresh

        #Privacy budget params
        self.epsilon = params.epsilon
        self.clientsWithUsedBudgets = []  # list of clients who have used budget
        self.numQueries = 0

        self.logger.info("Setting privacy budget to: " + str(self.epsilon))

        #Ruleset
        self.ruleSet = [] #set of rule trees



    def logRuleSet(self):
        self.logger.info("Retrieved Rules:")
        self.logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        for r in self.ruleSet:
            self.logger.info(r.toString())
        self.logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")

    def getRulesetDF(self):
        # make dataframe of rules and their client counts
        lst = []
        for r in self.ruleSet:
            lst.append([r.toStringWithParams(), r.percentCount])

        df = pd.DataFrame(lst, columns=["Rule", "Percent Count"])
        return df

    def globalBudgetUsed(self):
        if list(self.clientList.keys()) == set(self.clientsWithUsedBudgets):
            return True
        elif len(set(self.clientsWithUsedBudgets)) > len(self.clientList)-3: #only a few clients without used budgets so end
            return True
        else:
            return False


    # RUN Monte Carlo Tree Search
    def runMCTS(self, branchName):

        totalIters = 1 #to track the number of iterations that are completed
        while not self.globalBudgetUsed() and self.numQueries < self.maxQueries:
            # SELECTION
            if (self.verbose):
                self.mcLogger.info("BEGIN SEARCH ROUND, ITERATION: " + str(totalIters) + "\n")

            currBranch = self.templateTree._branches[branchName]

            #query here in utc score part ...
            selectedBranch = self.selection(currBranch)
            if self.verbose:
                clus = self.templateTree.dotGraph.get_subgraph('"cluster_' + selectedBranch.name + '"')[0]
                clus.set('color', 'red')
                self.templateTree.saveGraph(graphName='Selection Step')
                self.mcLogger.info("**Saved Graph " + str(self.templateTree.graphNum) + "_" + 'Selection Step\n')
                clus.set('color', 'black')

            #EXPANSION
            expandedBranch = self.expansion(selectedBranch)

            #QUERYING AND BACKPROPAGATION
            if expandedBranch != None:
                result = self.getQuery(expandedBranch) #result is in form [matchCount, activeClients]

                if result[0] == "BUDGET USED":
                    self.logger.info("BUDGET USED\n")
                    break
                else:
                    self.backpropagation(expandedBranch, result)

            else:
                result = self.getQuery(selectedBranch) #result is in form [matchCount, activeClients]
                if result[0] == "BUDGET USED":
                    self.logger.info("BUDGET USED\n")
                    break
                else:
                    self.backpropagation(selectedBranch, result)


            # Perform pruning step --> prune any branches who have a query result < cutoff threshold
            if self.verbose:
                self.mcLogger.info("----PRUNING PHASE----")

            self.templateTree.pruneTree(self.cutoffThresh)

            totalIters += 1



        if self.verbose:
            self.mcLogger.info("----SEARCH COMPLETED----\n")

        #TODO - maybe do final query on each rule to ensure enough client matches
        #Get final rule set
        self.ruleSet = self.templateTree.generateRuleSet()

        if self.verbose:
            self.logRuleSet()

        self.logger.info("Completed " + str(self.numQueries) + " queries")



###################################################################################################################################################################

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
            self.mcLogger.info("Returned Branch: " + currBranch.name)

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
                    if self.verbose:
                        self.mcLogger.info("Found univisited child branch " + child.name)
                    return child #child = child branch from node

        if self.verbose:
            self.mcLogger.info("All children visited, selecting node with highest score value")


        #Select branch with highest score (UTC) value
        maxScore = -1
        bestChild = None

        for node in branch.nodes:
            for child in node.children:
                #Note, changed selection policy to be using UCT as well ...
                # score = child.getCurrentScore()
                score = self.utcScore(child, child.getCurrentScore())

                if self.verbose:
                    self.logger.info("Score for " + child.name + " : " + str(score))

                if score > maxScore:
                    maxScore = score
                    bestChild = child

        return bestChild


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
                    clus = self.templateTree.dotGraph.get_subgraph('"cluster_' + selectedBranch.name + '"')[0]
                    clus.set('color', 'red')
                    self.templateTree.saveGraph(graphName='Expansion Step')
                    self.mcLogger.info("**Saved Graph " + str(self.templateTree.graphNum) + "_" + 'Selection Step')
                    clus.set('color', 'black')
            else: #branch has children already
                branchChildren = []
                for nod in selectedBranch.nodes:
                    branchChildren.extend(nod.children)

            #select from the (potentially added) child branches according to a policy
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
            if node.type in stlGrammarDict.keys(): #node is expandable
                childChoices = stlGrammarDict[node.type] #get possible child branches

                if "Variable" in childChoices[0]: #Get variable combo level
                    childChoices = []
                    for v in self.variables:
                        childChoices.append([v, "Parameter"])

                    if self.verbose:
                        self.mcLogger.info("For node " + node.name + " found Possible Child Branches: {}".format(
                            ' '.join(map(str, childChoices))))

                    for choice in childChoices:
                        br = self.templateTree.addBranch(choice, node.name, varBranch=True)  # add all children to branch
                        branchChildren.append(br)


                else: #non variable terminal nodes
                    if self.verbose:
                        self.mcLogger.info("For node " + node.name + " found Possible Child Branches: {}".format(' '.join(map(str, childChoices))))

                    for choice in childChoices:
                        #Check depth condition
                        if choice not in terminalNodes and branch.depth + 1 > self.maxTreeDepth:
                            if self.verbose:
                                self.mcLogger.info("Reached max depth of " + str(branch.depth) + " - no children to expand")
                            pass
                        else:
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

        if branchOptions == [] or branchOptions == None:
            return None
        else:
            sel = random.choice(branchOptions)

            if self.verbose:
                self.mcLogger.info("Selected branch to explore " +  sel.name + " according to default policy: random\n")

            return sel

    #### QUERY (this part is normally called simulation in traditional MCTS)
    def getQuery(self, selectedBranch):
        '''
        Get some type of query result for entire rule at this node --> query of number of client matches
        Note: this is the only place in the search where an actual query is conducted

        :param selectedBranch: branch to simulate results for
        :return: query result (right now match count to rule)
        '''
        if self.verbose:
            self.mcLogger.info("----QUERY PHASE----")
            self.mcLogger.info("Querying Branch: " + selectedBranch.name)
            selectedBranch.ruleTree.show()
            print("Variables for rule tree:", selectedBranch.ruleTree.varList)

        #Note - this part could be where the p budgets are tested / evaluated ...
        matchCount, activeClients = self.queryClientRuleMatch(selectedBranch.ruleTree)

        percentCount = matchCount / len(activeClients)

        if self.verbose:
            self.mcLogger.info("Rule Match Percentage: " + str(percentCount) + "\n")

        return matchCount, activeClients

    #TODO HERE --> update UCT scores to be sum of child nodes in back prop!!!
    def backpropagation(self, startingBranch, score):
        '''
        Backpropagate UCT score up tree
        :param startingBranch: branch to start backpropagation from
        :param score: score to propagate up
        :return:
        '''
        if self.verbose:
            self.mcLogger.info("----BACKPROPAGATION PHASE----")

        #Update current branch
        startingBranch.matchScores.append(score) #update score list
        startingBranch.visits += 1 #add visit to this node
        startingBranch.utc = self.utcScore(startingBranch, startingBranch.getCurrentScore()) #calc utc for this branch

        if self.verbose:
            self.mcLogger.info("Backpropogating Score: " + str(score[0]))
            self.mcLogger.info("Calculated UTC for node " + startingBranch.name + ": "+ str(startingBranch.utc))

        #prop scores
        br = startingBranch
        while br.parent != None:
            br = br.parent.branch
            br.matchScores.append(score) #add score to parent node
            br.visits += 1  # add visit to this node
            br.utc = self.utcScore(br, br.getCurrentScore())  # calc utc for this branch


            if self.verbose:
                self.mcLogger.info("Calculated UTC for node " + br.name + ": " + str(br.utc))

        if self.verbose:
            self.mcLogger.info("Backprop completed\n")

    def utcScore(self, branch, score):
        if branch.parent == None:
            parenVisits = branch.visits
        else:
            parenVisits = branch.parent.branch.visits

        uct = score + self.cp * math.sqrt(math.log(parenVisits) / branch.visits)

        # uct = score * (1/(parenVisits + branch.visits))
        # #Add discount factor for terminal branches so they don't get searched
        # if branch.terminalBranch():
        #     uct = uct * 0.4

        return uct


    # Get a % of how many clients have a match to the template
    # Return a COUNT with the total num clients
    def queryClientRuleMatch(self, template):
        #add to num queries sent out by server
        self.numQueries += 1

        # get template node list
        tempNodes = self.getTemplateNodes(template)
        # print("temp nodes", tempNodes)

        activeClients = self.clientList#TODO fix this part ...

        #Non private model
        if self.epsilon == 'inf':
            yesCount = 0
            for c in self.clientList:
                yesCount += self.clientList[c].queryStructuralRuleMatch(tempNodes, template.varList)


            return yesCount, activeClients

        #Private model
        else:
            # get count from clients of who have template
            yesCount = 0
            trueYesses = 0
            p = None

            for c in self.clientList:
                resp, truResp, p = self.clientList[c].randResponseQueryStruct(tempNodes, template.varList)

                if resp == "BUDGET USED":
                    self.clientsWithUsedBudgets.append(c)
                else:
                    yesCount += resp
                    trueYesses += truResp

            if not self.globalBudgetUsed():
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

                return estTrueCount, activeClients #percentCount, activeClients

            # else:
            return "BUDGET USED", activeClients

    # Get list of nodes from template
    def getTemplateNodes(self, temp):
        nodes = []
        parent = None
        ignoreList = ["(", ")"]
        # for n in temp.expand_tree(mode=treelib.Tree.WIDTH, sorting=True):
        #     if temp.parent(n) != parent:
        #         parent = temp.parent(n)
        #         nodes.append("newLevel")
        #
        #     nd = temp.get_node(n)
        #     id = re.sub('[0-9]', '', nd.identifier)
        #
        #     if id not in ignoreList:
        #         nodes.append(id)  # remove numbers, append name


        for n in temp.expand_tree(mode=treelib.Tree.DEPTH, sorting=True):
            # if temp.parent(n) != parent:
            #     parent = temp.parent(n)
            #     nodes.append("newLevel")

            nd = temp.get_node(n)
            id = re.sub('[0-9]', '', nd.identifier)

            if id not in ignoreList:
                nodes.append(id)

        return nodes