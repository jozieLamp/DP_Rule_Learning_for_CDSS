import logging
import copy
import treelib
import re
import math
import random
import pandas as pd
from RuleTemplate.RuleTemplate import RuleTemplate, Node, stlGrammarDict, terminalNodes
from MCTS.MCTS_Baseline import MCTS_Baseline


class Server :
    def __init__(self, clientList, varDict, params):
        self.clientList = clientList  # dict of clients
        self.varDict = varDict  # variable dictionary to store vars + ranges
        self.variables = list(self.varDict.keys())

        # Output params
        self.verbose = params.verbose
        self.logger = logging.getLogger('SERVER')

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
    def runProtocol(self, branchName):

        #Make MCTS Baseline
        mcts = MCTS_Baseline(server=self, verbose=self.verbose)


        totalIters = 1 #to track the number of iterations that are completed
        while not self.globalBudgetUsed() and self.numQueries < self.maxQueries:
            if (self.verbose):
                self.logger.info("BEGIN SEARCH ROUND, ITERATION: " + str(totalIters) + "\n")

            mcts.runMCTSRound(branchName=branchName)

            totalIters += 1


        if self.verbose:
            self.logger.info("----SEARCH COMPLETED----\n")

        #TODO - maybe do final query on each rule to ensure enough client matches
        #Get final rule set
        self.ruleSet = self.templateTree.generateRuleSet()

        if self.verbose:
            self.logRuleSet()

        self.logger.info("Returned " + str(len(self.ruleSet)) + " rule structures")
        self.logger.info("Completed " + str(self.numQueries) + " queries")




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
        ignoreList = ["(", ")"]

        for n in temp.expand_tree(mode=treelib.Tree.DEPTH, sorting=True):
            nd = temp.get_node(n)
            id = re.sub(r'\#.*', '', nd.identifier)

            if id not in ignoreList:
                nodes.append(id)

        return nodes