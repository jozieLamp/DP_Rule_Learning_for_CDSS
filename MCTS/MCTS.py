import logging, math, random, statistics, re
import treelib
from RuleTemplate.RuleTemplate import RuleTemplate, Node, stlGrammarDict, terminalNodes

class MCTS:
    def __init__(self, method, server, verbose):
        self.method = method
        self.server = server
        self.verbose = verbose
        self.mcLogger = logging.getLogger('MCTS')

    def runMCTSRound(self, branchName):

        # SELECTION
        currBranch = self.server.templateTree._branches[branchName]

        selectedBranch = self.selection(currBranch)
        # if self.verbose:
        #     clus = self.server.templateTree.dotGraph.get_subgraph('"cluster_' + selectedBranch.name + '"')[0]
        #     clus.set('color', 'red')
        #     self.mcLogger.info("**Saved Graph " + str(self.server.templateTree.graphNum) + "_" + 'Selection Step\n')
        #     self.server.templateTree.saveGraph(graphName='Selection Step')
        #     clus.set('color', 'black')

        # EXPANSION
        expandedBranch = self.expansion(selectedBranch)

        # QUERYING, BACKPROPAGATION
        if expandedBranch != None:
            matchCount, activeClients = self.getQuery(expandedBranch)

            if matchCount == "BUDGET USED":
                self.mcLogger.info("BUDGET USED\n")
                return
            else:
                self.backpropagation(expandedBranch, matchCount, activeClients)

        else:
            matchCount, activeClients = self.getQuery(selectedBranch)
            if matchCount == "BUDGET USED":
                self.mcLogger.info("BUDGET USED\n")
                return
            else:
                self.backpropagation(selectedBranch, matchCount, activeClients)


        # Perform pruning step --> prune any branches who have a query result < cutoff threshold
        if self.verbose:
            self.mcLogger.info("----PRUNING PHASE----")

        self.server.templateTree.pruneTree(self.server.cutoffThresh)


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

        if branch.terminalBranch():  # if branch is a leaf
            if self.verbose:
                self.mcLogger.info("Branch terminal, returning")
            return branch

        for node in branch.nodes:
            for child in node.children:
                if child.visits == 0.0:  # univisited child branch
                    if self.verbose:
                        self.mcLogger.info("Found univisited child branch " + child.name)
                    return child  # child = child branch from node

        if self.verbose:
            self.mcLogger.info("All children visited, selecting node with highest score value")

        # Select branch with highest score (UTC) value
        maxScore = -1
        bestChild = None

        for node in branch.nodes:
            for child in node.children:

                # add check to only look at child nodes that aren't completely explored
                if not child.completelyExplored:
                    # Note, changed selection policy to be using UCT as well ...
                    # score = child.getCurrentScore()
                    score = self.utcScore(child, child.getCurrentScore())

                    if self.verbose:
                        self.mcLogger.info("Score for " + child.name + " : " + str(score))

                    if score > maxScore:
                        maxScore = score
                        bestChild = child
                else:
                    self.mcLogger.info(child.name + " completely explored, so not adding to check ")

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

        if selectedBranch.terminalBranch():  # fully expanded --> at leaf node
            if self.verbose:
                self.mcLogger.info("Terminal node reached, expansion completed " + selectedBranch.name + "\n")

            return None

        elif selectedBranch.visits == 0:  # branch unvisited
            if self.verbose:
                self.mcLogger.info("Branch unvisited, returning selected branch " + selectedBranch.name + "\n")
            return selectedBranch

        else:
            if not selectedBranch.hasChildren():  # no children added to node yet
                branchChildren = self.evaluateChildren(selectedBranch)  # get possible child branches and add to branch

                if self.verbose:
                    self.mcLogger.info("Updated Template Tree")
                #     clus = self.server.templateTree.dotGraph.get_subgraph('"cluster_' + selectedBranch.name + '"')[0]
                #     clus.set('color', 'red')
                #     self.mcLogger.info("**Saved Graph " + str(self.server.templateTree.graphNum) + "_" + 'Expansion Step')
                #     self.server.templateTree.saveGraph(graphName='Expansion Step')
                #     clus.set('color', 'black')
            else:  # branch has children already
                branchChildren = []
                for nod in selectedBranch.nodes:
                    branchChildren.extend(nod.children)

            # select from the (potentially added) child branches according to a policy
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
            if node.type in stlGrammarDict.keys():  # node is expandable
                childChoices = stlGrammarDict[node.type]  # get possible child branches

                if "Variable" in childChoices[0]:  # Get variable combo level
                    childChoices = []
                    for v in self.server.variables:
                        childChoices.append([v, "Parameter"])

                    if self.verbose:
                        self.mcLogger.info("For node " + node.name + " found Possible Child Branches: {}".format(
                            ' '.join(map(str, childChoices))))

                    for choice in childChoices:
                        br = self.server.templateTree.addBranch(choice, node.name,
                                                         varBranch=True)  # add all children to branch
                        branchChildren.append(br)


                else:  # non variable terminal nodes
                    if self.verbose:
                        self.mcLogger.info("For node " + node.name + " found Possible Child Branches: {}".format(
                            ' '.join(map(str, childChoices))))

                    for choice in childChoices:
                        # Check depth condition
                        if choice not in terminalNodes and branch.depth + 1 > self.server.maxTreeDepth:
                            if self.verbose:
                                self.mcLogger.info(
                                    "Reached max depth of " + str(branch.depth) + " - no children to expand")
                            pass
                        else:
                            br = self.server.templateTree.addBranch(choice, node.name)  # add all children to branch
                            branchChildren.append(br)

        return branchChildren


    def selectionPolicy(self, branchOptions):
        '''
        Select branch according to policy - random
        :param branchOptions: List of branches to choose from
        :return:
        '''

        if branchOptions == [] or branchOptions == None:
            return None
        else:

            if self.method == 'baseline': #Baseline method selects branch randomly
                sel = random.choice(branchOptions)
    
                if self.verbose:
                    self.mcLogger.info("Selected branch to explore " + sel.name + " according to default policy: random\n")

            else: #run coverage version
                scores = []
                for b in branchOptions:
                    scores.append(self.getCoverageScore(self.server.templateTree, b))

                # if all distances same, select randomly
                if all(element == scores[0] for element in scores):
                    sel = random.choice(branchOptions)
                else:
                    # print("branch opts", [x.name for x in branchOptions])
                    # print("Cov scores", scores)
                    idx = scores.index(max(scores))  # select branch with max (highest) edit dist
                    # print("SELECTED:", branchOptions[idx].name)

                    sel = branchOptions[idx]

                if self.verbose:
                    self.mcLogger.info(
                        "Selected branch to explore " + sel.name + " according to coverage selection policy\n")

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

        # Note - this part could be where the p budgets are tested / evaluated ...
        matchCount, activeClients = self.server.queryClientRuleMatch(selectedBranch)

        if matchCount != "BUDGET USED":
            # Fix negative estimates
            if matchCount < 0:
                matchCount = 0.0

            # Fix over estimates
            if matchCount > len(selectedBranch.activeClients):
                matchCount = len(selectedBranch.activeClients)

            percentCount = matchCount / len(selectedBranch.activeClients)

            if self.verbose:
                self.mcLogger.info("Rule Match Count: " + str(matchCount) + ", Rule Match Percentage: " + str(percentCount) + "\n")

            #If terminal node, preserve budget needed for the param estimation and final rule query (add two queries)
            if selectedBranch.terminalBranch():
                self.server.numQueries += 2

                #Preserve privacy budget for querying of params and final rule query
                #for each active client, add param budget amount FOR EACH param in term node
                numParams = len(selectedBranch.ruleTree.getMissingParams())
                for c in selectedBranch.activeClients:
                    xtraBudg = self.server.allocateQueryBudget(strategy=self.server.budgetAllocStrategy)
                    self.server.clientList[c].budgetUsed += xtraBudg #Preserve budget for final query of rule
                    self.server.clientList[c].budgetUsed += (self.server.clientList[c].paramNoise * numParams)
                    self.server.clientList[c].numQueries += numParams  # add count to queries

        return matchCount, activeClients

    #### BACKPROPAGATION
    def backpropagation(self, startingBranch, matchCount, activeClients):
        '''
        Backpropagate UCT score up tree
        :param startingBranch: branch to start backpropagation from
        :param score: score to propagate up
        :return:
        '''
        if self.verbose:
            self.mcLogger.info("----BACKPROPAGATION PHASE----")

        # Update current branch
        startingBranch.matchScores.append([matchCount, startingBranch.activeClients])  # update score list
        startingBranch.visits += 1  # add visit to this node
        startingBranch.utc = self.utcScore(startingBranch, startingBranch.getCurrentScore())  # calc utc for this branch

        #Added check to see if branch terminal or all child branches completely explored, set branch to be compl explored
        if startingBranch.terminalBranch():
            startingBranch.completelyExplored = True
        if startingBranch.allChildrenCompletelyExplored():
            startingBranch.completelyExplored = True

        if self.verbose:
            self.mcLogger.info("Backpropogating Score: " + str(matchCount))
            self.mcLogger.info("Calculated UTC for node " + startingBranch.name + ": " + str(startingBranch.utc))
            self.mcLogger.info(startingBranch.name + "node completely explored " + str(startingBranch.completelyExplored))

        # prop scores
        br = startingBranch
        while br.parent != None:
            br = br.parent.branch
            br.matchScores.append([matchCount, startingBranch.activeClients])  # add score to parent node
            br.visits += 1  # add visit to this node
            br.utc = self.utcScore(br, br.getCurrentScore())  # calc utc for this branch

            #propagate if child branches completely explored
            if br.allChildrenCompletelyExplored():
                br.completelyExplored = True

            if self.verbose:
                self.mcLogger.info("Calculated UTC for node " + br.name + ": " + str(br.utc))
                self.mcLogger.info(br.name + " node completely explored " + str(br.completelyExplored))

        if self.verbose:
            self.mcLogger.info("Backprop completed\n")

        # Update active clients at this branch
        startingBranch.updatedActiveClients = activeClients #updated active clients
        # startingBranch.activeClients = activeClients #updated active clients


    def utcScore(self, branch, score):
        if branch.parent == None:
            parenVisits = branch.visits
        else:
            parenVisits = branch.parent.branch.visits

        if self.method == 'baseline': #do traditional UCT scoring method
            uct = score + self.server.cp * math.sqrt(math.log(parenVisits) / branch.visits)
        else: #Do coverage scoring for UCT
            # Get Coverage metric - average tree edit distance (want largest edit dist)
            editDist = self.getCoverageScore(self.server.templateTree, branch)

            # Normalize edit distance to be btw 0 and 1
            if self.verbose:
                self.mcLogger.info("SCORE " + str(score) + " EDIT DISTANCE " + str(editDist))

            # was score * 2
            uct = score + editDist + self.server.cp * math.sqrt(math.log(parenVisits) / branch.visits)

        return uct

    def getCoverageScore(self, temp, branch):
        '''
        Get coverage score (Tree edit distance) of current branch compared to current trees
        Calculates ordered edit distance btw two templates and returns average score

        :param temp: Full template
        :param branch: current branch to compare
        :return:
        '''

        #Get all current rule templates at "leaf" branches - branches with no children
        treeDB = temp.getBranchesNoChildren()

        #get rule trees from the tree db
        ruleTreeDB = [x.ruleTree for x in treeDB]

        #calc edit distances between branch and all rule trees
        brNodes = self.getTemplateNodes(branch.ruleTree)
        distances = []
        for r in ruleTreeDB:
            rNodes = self.getTemplateNodes(r)

            i = 0 #iterator for brNodes
            j = 0 #iterator for rNodes
            dist = 0
            while i < len(brNodes):
                if j >= len(rNodes): #completely iterated through rNodes, count difs in brNodes
                    dist += len(brNodes) - i
                    i += len(brNodes)
                elif brNodes[i] == rNodes[j]: #match
                    i+=1
                    j+=1
                else: #not match, add edit distance
                    dist += 1
                    j += 1

                # if i >= len(brNodes): #final check for any remaining nodes in rNodes
                #     dist += len(rNodes) - j

            distances.append(dist)

        #Get maximum of the min of tree distances
        editDist = statistics.median(distances)
        # editDist = min(distances)
        #sum(distances) / len(distances) #to do average

        # print("Getting Coverage Score for branch " + branch.name)
        # print("distances:", distances)
        # print("edit distance", editDist)

        return editDist

    # Get list of nodes from template - note temp here is a rule template
    def getTemplateNodes(self, temp):
        nodes = []
        ignoreList = ["(", ")"]

        for n in temp.expand_tree(mode=treelib.Tree.DEPTH, sorting=True):
            nd = temp.get_node(n)
            id = re.sub(r'\#.*', '', nd.identifier)

            # if id in self.variables:
            #     nodes.append("Variable")

            if id not in ignoreList:
                nodes.append(id)

        return nodes