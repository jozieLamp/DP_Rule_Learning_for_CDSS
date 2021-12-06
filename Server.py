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
from MCTS.MCTS import MCTS

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
        else:
            mcts = MCTS(server=self, verbose=self.verbose)

        totalIters = 1 #to track the number of iterations that are completed
        while not self.globalBudgetUsed() and self.numQueries < self.maxQueries:
            if (self.verbose):
                self.logger.info("BEGIN SEARCH ROUND, ITERATION: " + str(totalIters) + "\n")

            mcts.runMCTSRound(branchName=branchName)

            totalIters += 1

            if self.globalBudgetUsed():
                self.logger.info("GLOBAL BUDGET USED")

        if self.verbose:
            self.logger.info("----MCTS SEARCH COMPLETED----\n")

        #GET FINAL RULESET BY TRAVERSING TEMPLATE TREE
        ruleTrees = self.templateTree.generateRuleSet() #returns a set of rule templates

        #### ESTIMATE PARAMETERS FOR EACH RULE IN THE RULESET
        if self.verbose:
            self.logger.info("----PARAMETER ESTIMATION PHASE----\n")

        stlFac = STLFactory()
        rules = []
        finalTrees = []
        #query params and make final STL Rule Structures (STL Trees)
        for t in ruleTrees:
            #Query missing params for tree
            tempParams = self.queryParameters(t)

            #Only get correctly formatted rules
            ft = stlFac.constructFormulaTree(t.toStringWithParams() + "\n") # Check if structure correct

            if ft != None:  # Formula is not improper
                #TODO - might have to do something where if rule is improper, remove it from the RuleTree list so the other functions are not messed up
                if tempParams != None:
                    ft.updateParams(tempParams)# Update params in structure
                rules.append(ft)
                finalTrees.append(t)

        #Make Rule Set Object to store output rule set
        self.finalRuleSet = RuleSet(finalTrees, rules)

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

        updatedActiveClients = []

        #Non private model
        if self.epsilon == 'inf':
            yesCount = 0
            for c in branch.activeClients:
                resp = self.clientList[c].queryStructuralRuleMatch(tempNodes, template.varList)
                yesCount += resp

                #Remove client if has no match
                if resp == 1:
                    updatedActiveClients.append(c)

            return yesCount, updatedActiveClients

        #Private model
        else:
            # get count from clients of who have template
            yesCount = 0
            trueYesses = 0
            p = None

            for c in branch.activeClients:
                resp, truResp, p = self.clientList[c].randResponseQueryStruct(tempNodes, template.varList)

                if resp == "BUDGET USED":
                    self.clientsWithUsedBudgets.append(c)
                else:
                    yesCount += resp
                    trueYesses += truResp

                    #check if client still active
                    if branch.parent != None:
                        priorProb = branch.parent.branch.getCurrentScore() #prior prob is % match count from parent
                    else:
                        priorProb = 0.5 #50% chance return true

                    if self.checkClientActive(response=resp, p=p, priorProbTrue=priorProb): #if true, still active, add to updated active clients
                        updatedActiveClients.append(c)

            if not self.globalBudgetUsed():
                q = 1-p
                estTrueCount = float((yesCount - (len(self.clientList) * q)) / (p-q))

                percentCount = float(estTrueCount / len(branch.activeClients))
                truePerCount = float(trueYesses / len(branch.activeClients)) #Real percent

                if self.verbose:
                    # print("yes cnt", yesCount, "p", p, "q", q, "est true count", estTrueCount)
                    self.logger.info("True Count " + str(trueYesses) +  ", Est Count " + str(estTrueCount))
                    self.logger.info("True Percent " + str(truePerCount) +  ", Est Percent " + str(percentCount))


                return estTrueCount, updatedActiveClients

            # else:
            return "BUDGET USED", updatedActiveClients

    # Check if the client is still active - client can still have true queries
    def checkClientActive(self, response, p, priorProbTrue):
        p = float(p)
        priorProbTrue = float(priorProbTrue)

        # Calculate prob true answer was yes using Bayes Theorem
        if response == 1:
            # print("\nresp, 1")
            PT1 = priorProbTrue
            PT0 = 1 - priorProbTrue
            # print("PT1", PT1, "PT0", PT0)
            R1gT1 = (p * PT1) / PT1  # if PT1 else 0
            R1gT0 = ((1 - p) * PT0 * p) / PT0 if PT0 else 0
            bayes = (R1gT1 * PT1) / ((R1gT1 * PT1) + (R1gT0 * PT0))  # PT1gR1
            # print("r1g1", R1gT1, "r1gt0", R1gT0, "bayes", bayes)


        else:  # resp == 0
            # print("\nresp, 0")
            PT1 = priorProbTrue
            PT0 = 1 - priorProbTrue
            # print("PT1", PT1, "PT0", PT0)
            R0gT0 = (p * PT0) / PT0 if PT0 else 0
            R0gT1 = ((1 - p) * PT1 * p) / PT1  # if PT1 else 0
            bayes = (R0gT1 * PT1) / ((R0gT1 * PT1) + (R0gT0 * PT0))  # PT1gR0

        # print("BAYES", bayes)

        # Multiply by previous values
        # print("Prior Prob", priorProbTrue)
        cUpdatedProb = priorProbTrue * bayes
        # print("Updated Prob", cUpdatedProb)

        # If probability of returning a true answer is below the defined threshold, don't query this client any more
        if cUpdatedProb < self.cutoffThresh:
            # print("******************************client", idx, " not active anymore")
            return False
        else:
            return True

    # Get list of nodes from template
    def getTemplateNodes(self, temp):
        nodes = []
        relops = ['GT', 'GE', 'LT', 'LE', "EQ", 'NEQ']
        ignoreList = ["(", ")"]
        parent = None
        subNodes = []
        level = 0

        for n in temp.expand_tree(mode=treelib.Tree.WIDTH, sorting=True):
            if temp.parent(n) != parent:
                parent = temp.parent(n)
                subNodes.append(level)  # add level at end
                nodes.append(subNodes)
                subNodes = []

            nd = temp.get_node(n)
            id = re.sub(r'\#.*', '', nd.identifier)
            level = temp.level(n)

            # if id in self.variables and id != 'timeBound':
            #     subNodes.append("Variable")

            if id in relops:
                if temp.parent(n) != parent:
                    parent = temp.parent(n)
                    subNodes.append(level)
                    nodes.append(subNodes)
                    subNodes = []

                subNodes.append(id)

                #append children of node
                for x in temp.children(n):
                    if x.identifier in self.variables:
                        subNodes.append(id)
                    else:
                        subNodes.append(re.sub(r'\#.*', '', x.identifier))

            elif id in self.variables or id == 'Parameter':
                pass
            elif id not in ignoreList:
                subNodes.append(id)

        if subNodes != []:
            subNodes.append(level)
            nodes.append(subNodes)
        return nodes

    #receives a rule tree template
    def queryParameters(self, template):

        # get template node list
        tempNodes = self.getTemplateNodes(template)
        tempParams = template.getMissingParams()
        # print("template params", tempParams)
        # print("template var list", template.varList)

        #Get param values from clients
        for c in template.activeClients:
            params = self.clientList[c].queryParams(tempNodes, template, tempParams, template.varList, self.varDict)

            if params != None:
                for k in tempParams.keys():
                    if k in params:
                        tempParams[k].append(params[k])

        # print("CLIENT PARAMS", tempParams)

        finalParams = {}
        #Get Protocol Param Values
        for k in tempParams.keys():
            vals = sorted([float(x) for x in tempParams[k]])

            # print("vals", vals)

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
