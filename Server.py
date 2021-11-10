import logging
import copy
import treelib
import re
import math
import random
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from RuleTemplate.RuleTemplate import RuleTemplate, Node, stlGrammarDict, terminalNodes
from SignalTemporalLogic.STLFactory import STLFactory
from MCTS.MCTS_Baseline import MCTS_Baseline

#Make Ruleset Object to store all pieces of final ruleset
class RuleSet:
    def __init__(self, ruleTrees, rules):
        self.ruleTrees = ruleTrees #Rule templates
        self.rules = rules #Actual rule structures (STL Grammar Trees)
        self.logger = logging.getLogger('SERVER')

        #Make ruleset df
        self.getRulesetDF()


    def getRulesetDF(self):
        # make dataframe of rules and their client counts
        if len(self.ruleTrees) != len(self.rules):
            self.logger.error("ERROR- Rule Trees and Rules are not same length, cannot complete RuleSet DF generation.")
            return

        lst = []
        for i in range(len(self.ruleTrees)):
            lst.append([self.rules[i].toString(), self.ruleTrees[i].percentCount])

        self.ruleSetDF = pd.DataFrame(lst, columns=["Rule", "Percent Count"])


    def logRuleSet(self):
        self.logger.info("Retrieved Rules:")
        self.logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        for r in self.rules:
            self.logger.info(r.toString())
        self.logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")


class Server :
    def __init__(self, clientList, varDict, params):
        self.clientList = clientList  # dict of clients
        self.varDict = varDict  # variable dictionary to store vars + ranges
        self.variables = list(self.varDict.keys())

        # Output params
        self.verbose = params.verbose
        self.logger = logging.getLogger('SERVER')

        # make default rule template tree to start
        self.templateTree = RuleTemplate(varDict=self.varDict, default=True, clientList=clientList, verbose=self.verbose)

        #mcts params
        self.mctsType = params.mctsType
        self.maxQueries = params.maxQueries
        self.cp = params.cp
        self.maxTreeDepth = params.maxTreeDepth
        self.cutoffThresh = params.cutoffThresh
        self.paramPercentile = params.paramPercentile

        #Privacy budget params
        self.epsilon = params.epsilon
        self.clientsWithUsedBudgets = []  # list of clients who have used budget
        self.numQueries = 0

        self.logger.info("Setting privacy budget to: " + str(self.epsilon))


    def globalBudgetUsed(self):
        if list(self.clientList.keys()) == set(self.clientsWithUsedBudgets):
            return True
        elif len(set(self.clientsWithUsedBudgets)) > len(self.clientList)-3: #only a few clients without used budgets so end
            return True
        else:
            return False


    # RUN Monte Carlo Tree Search
    def runProtocol(self, branchName):

        #### RUN MONTE CARLO TREE SEARCH TO FIND RULE STRUCTURES
        if self.mctsType == 'baseline':
            #Make MCTS Baseline
            mcts = MCTS_Baseline(server=self, verbose=self.verbose)

        totalIters = 1 #to track the number of iterations that are completed
        while not self.globalBudgetUsed() and self.numQueries < self.maxQueries:
            if (self.verbose):
                self.logger.info("BEGIN SEARCH ROUND, ITERATION: " + str(totalIters) + "\n")

            mcts.runMCTSRound(branchName=branchName)

            totalIters += 1

        if self.verbose:
            self.logger.info("----MCTS SEARCH COMPLETED----\n")

        #TODO - maybe do final query on each rule to ensure enough client matches


        #GET FINAL RULESET BY TRAVERSING TEMPLATE TREE
        ruleTrees = self.templateTree.generateRuleSet() #returns a set of rule templates

        #### ESTIMATE PARAMETERS FOR EACH RULE IN THE RULESET
        if self.verbose:
            self.logger.info("----PARAMETER ESTIMATION PHASE----\n")

        stlFac = STLFactory()
        rules = []
        #query params and make final STL Rule Structures (STL Trees)
        for t in ruleTrees:
            #Query params for tree
            tempParams = self.queryParameters(t)

            #Only get correctly formatted rules
            ft = stlFac.constructFormulaTree(t.toStringWithParams() + "\n") # Check if structure correct

            if ft != None:  # Formula is not improper
                #TODO - might have to do something where if rule is improper, remove it from the RuleTree list so the other functions are not messed up
                ft.updateParams(tempParams)# Update params in structure
                rules.append(ft)


        #Make Rule Set Object to store output rule set
        self.finalRuleSet = RuleSet(ruleTrees, rules)

        # OUTPUT FINAL RETURNED RULE STRUCTURES
        if self.verbose:
            self.finalRuleSet.logRuleSet()

        self.logger.info("Produced " + str(len(self.finalRuleSet.ruleTrees)) + " Rule Tree Structures")
        self.logger.info("Generated " + str(len(self.finalRuleSet.rules)) + " Formatted Rules")
        self.logger.info("Completed " + str(self.numQueries) + " server queries")





    # Get a % of how many clients have a match to the template
    # Return a COUNT with the total num clients
    def queryClientRuleMatch(self, branch):
        template = branch.ruleTree

        #add to num queries sent out by server
        self.numQueries += 1

        # get template node list
        tempNodes = self.getTemplateNodes(template)
        # print("temp nodes", tempNodes)

        updatedActiveClients = {}
        #Non private model
        if self.epsilon == 'inf':
            yesCount = 0
            for c in branch.activeClients:
                resp = branch.activeClients[c].queryStructuralRuleMatch(tempNodes, template.varList)
                yesCount += resp

                #Remove client if has no match
                if resp == 1:
                    updatedActiveClients[c] = branch.activeClients[c]


            return yesCount, updatedActiveClients

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

            if id in self.variables:
                nodes.append("Variable")

            elif id not in ignoreList:
                nodes.append(id)

        return nodes

    #receives a rule tree template
    def queryParameters(self, template):

        activeClients = self.clientList  # TODO fix this part ...

        # get template node list
        tempNodes = self.getTemplateNodes(template)
        # print("temp nodes", tempNodes)
        tempParams = template.getMissingParams()

        #Get param values from clients
        for c in self.clientList:
            params = self.clientList[c].queryParams(tempNodes, tempParams, template.varList, self.varDict)

            if params != None:
                for k in tempParams.keys():
                    tempParams[k].append(params[k])

        #Get Protocol Param Values
        finalParams = {}
        for k in tempParams.keys():
            vals = sorted([float(x) for x in tempParams[k]])

            # #plot distributions of params
            # if self.verbose:
            #     plt.figure(figsize=(10, 5))
            #     plt.title('Distribution of Param ' + str(k))
            #     plt.xlabel('Param Value')
            #     plt.ylabel('Client Count')
            #     plt.hist(vals)
            #     plt.show()

            # score at or below which (inclusive) 50% of the scores in the distribution may be found
            p = np.percentile(vals, self.paramPercentile)

            finalParams[k] = p

        # return param set
        return finalParams

    def getClientQueryCount(self):
        lst = []
        for c in self.clientList:
            lst.append([self.clientList[c].clientNum, self.clientList[c].numQueries])

        #Make dataframe of client nums and their queries
        df = pd.DataFrame(lst, columns=['Client', 'Num Queries']).set_index('Client')

        return df
