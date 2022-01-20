import logging
import copy
import treelib
import re
import math
import decimal
import random
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from RuleTemplate.RuleTemplate import RuleTemplate, Node, stlGrammarDict, terminalNodes
from SignalTemporalLogic.STLFactory import STLFactory
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

        self.logger = logging.getLogger('SERVER')
        self.params = params

        if params != None:
            # Output params
            self.verbose = params.verbose

            # make default rule template tree to start
            self.templateTree = RuleTemplate(varDict=self.varDict, default=True, clientList=clientList, verbose=self.verbose)
            self.timeBounds = params.timeBounds

            #mcts params
            self.mctsType = params.mctsType
            self.maxQueries = params.maxQueries
            self.cp = params.cp
            self.maxTreeDepth = params.maxTreeDepth
            self.cutoffThresh = params.cutoffThresh
            self.paramPercentile = params.paramPercentile

            #Privacy budget params
            self.epsilon = params.epsilon
            self.budgetAllocStrategy = params.budgetAllocMethod
            self.clientsWithUsedBudgets = []  # list of clients who have used budget
            self.numQueries = 0

            self.logger.info("Setting privacy budget to: " + str(self.epsilon))


    def globalBudgetUsed(self):
        # print("Clients with used budgets:", self.clientsWithUsedBudgets)

        if list(self.clientList.keys()) == set(self.clientsWithUsedBudgets):
            return True
        elif len(set(self.clientsWithUsedBudgets)) > len(self.clientList)-3: #only a few clients without used budgets so end
            return True
        else:
            return False


    # RUN Monte Carlo Tree Search
    def runProtocol(self, branchName):

        # RUN MONTE CARLO TREE SEARCH TO FIND RULE STRUCTURES
        mcts = MCTS(method=self.mctsType, server=self, verbose=self.verbose)

        totalIters = 1 #to track the number of iterations that are completed
        while not self.globalBudgetUsed() and self.numQueries < self.maxQueries and not self.templateTree._branches[branchName].completelyExplored:
            if (self.verbose):
                self.logger.info("BEGIN SEARCH ROUND, ITERATION: " + str(totalIters) + "\n")

            mcts.runMCTSRound(branchName=branchName)

            #TODO here - add something to check and print or save # queries and total rules generated ...

            totalIters += 1

            if self.globalBudgetUsed():
                self.logger.info("GLOBAL BUDGET USED")

            if self.numQueries >= self.maxQueries:
                self.logger.info("TOTAL QUERIES USED UP")

            if self.templateTree._branches[branchName].completelyExplored:
                self.logger.info("TREE COMPLETELY EXPLORED")


        if self.verbose:
            self.logger.info("----MCTS SEARCH COMPLETED----\n")

        if self.verbose:
            self.logger.info("----GENERATE FULL RULESET FROM TEMPLATE TREE----")

        # GET FINAL RULESET BY TRAVERSING TEMPLATE TREE
        initialRuleTrees = self.templateTree.generateRuleSet() #returns a set of rule templates

        #Save initial rule trees
        irtDF = pd.DataFrame([x.toString() for x in initialRuleTrees], columns=['Initial Rule Trees'])
        # irtDF.to_csv(self.params.resultsFilename + "InitialRules.csv")
        #TODO - del this
        if self.verbose:
            self.logger.info("Initial Rules")
            for x in initialRuleTrees:
                self.logger.info(x.toString())

        if self.verbose:
            self.logger.info("Generated " + str(len(initialRuleTrees)) + " initial rules\n")
            self.logger.info("----PERFORM FINAL QUERY FOR EACH FULL RULE----")

        # do one final query for each rule to make sure full rule has a match
        ruleTrees = []
        for r in initialRuleTrees:
            # print(r.toString())
            # r.show()

            origAC = r.activeClients
            matchCount, activeClients = self.queryFullRuleMatch(r)

            # Fix negative estimates
            if matchCount < 0:
                matchCount = 0.0
            # Fix over estimates
            if matchCount > len(origAC):
                matchCount = len(origAC)

            percentCount = matchCount / len(origAC) if len(origAC) > 0 else 0

            # if self.verbose:
            #     self.logger.info(r.toString())
            #     self.logger.info("Rule Match Count: " + str(matchCount) + ", Rule Match Percentage: " + str(percentCount))

            if percentCount >= self.cutoffThresh:
                #update active clients to be only clients who said yes
                r.activeClients = activeClients  # add active clients to rule tree
                r.percentCount = percentCount  # add percent count to rule tree
                ruleTrees.append(r)

        if self.verbose:
            self.logger.info("Generated " + str(len(ruleTrees)) + " full rules\n")

        #TODO del this
        if self.verbose:
            self.logger.info("Generated Full Rules:")
            for x in ruleTrees:
                self.logger.info(x.toString())

        # ESTIMATE PARAMETERS FOR EACH RULE IN THE RULESET
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

                #TODO - OPTION might have to do something where if rule is improper, remove it from the RuleTree list so the other functions are not messed up
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

        # #TODO del this part
        # if self.globalBudgetUsed():
        #     self.logger.info("GLOBAL BUDGET USED")
        # if self.numQueries >= self.maxQueries:
        #     self.logger.info("TOTAL QUERIES USED UP")
        # if self.templateTree._branches[branchName].completelyExplored:
        #     self.logger.info("TREE COMPLETELY EXPLORED")



    #Final query once have completed final rules generated from rule template
    def queryFullRuleMatch(self, template):
        # get template node list
        tempNodes = self.getTemplateNodes(template)
        updatedActiveClients = []

        # Non private model
        if self.epsilon == 'inf':
            yesCount = 0
            for c in template.activeClients: #TODO - OPTION potentially query all clients, not just the active ones in the final step (?)
                resp = self.clientList[c].queryStructuralRuleMatch(tempNodes, template.varList)
                yesCount += resp

                # Remove client if has no match
                if resp == 1:
                    updatedActiveClients.append(c)

            return yesCount, updatedActiveClients

        # Private model
        else:
            # get count from clients of who have template
            yesCount = 0
            trueYesses = 0

            # Get PLoss budget for this query
            pLossBudg = self.allocateQueryBudget(strategy=self.budgetAllocStrategy)
            p = decimal.Decimal(math.e) ** decimal.Decimal(pLossBudg) / (1 + decimal.Decimal(math.e) ** decimal.Decimal(pLossBudg))

            for c in template.activeClients: #TODO - OPTION potentially query all clients, not just the active ones in the final step (?)
                resp, truResp = self.clientList[c].finalRandResponseQuery(tempNodes, template.varList, pLossBudg)

                yesCount += resp
                trueYesses += truResp

                if resp == 1:
                    updatedActiveClients.append(c) #make active clients only the ones who said yes

            #Calculate final match count for this rule
            q = 1 - p
            estTrueCount = float((yesCount - (len(template.activeClients) * q)) / (p - q))
            percentCount = float(estTrueCount / len(template.activeClients))
            truePerCount = float(trueYesses / len(template.activeClients))  # Real percent

            # if self.verbose:
            #     self.logger.info("Template: " + template.toString())
            #     self.logger.info(str(("Active clients ", template.activeClients)))
            #     # print("yes cnt", yesCount, "p", p, "q", q, "est true count", estTrueCount)
            #     self.logger.info("True Yesses " + str(trueYesses) + ", Yes Responses " + str(yesCount) + ", Estimated True yesses " + str(estTrueCount))
            #     self.logger.info("True Percent " + str(truePerCount) + ", Est Percent " + str(percentCount) + "\n")

            return estTrueCount, updatedActiveClients



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

            #Get PLoss budget for this query
            pLossBudg = self.allocateQueryBudget(strategy=self.budgetAllocStrategy)
            p = decimal.Decimal(math.e) ** decimal.Decimal(pLossBudg) / (1 + decimal.Decimal(math.e) ** decimal.Decimal(pLossBudg))

            # print("\nActive clients at CURRENT BRANCH", branch.name, ":", branch.activeClients)
            for c in branch.activeClients:
                resp, truResp = self.clientList[c].randResponseQueryStruct(tempNodes, template.varList, pLossBudg)

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

                    # print("\nClient", c, "resp", resp)
                    if self.checkClientActive(response=resp, p=p, priorProbTrue=priorProb): #if true, still active, add to updated active clients
                        updatedActiveClients.append(c)

            # print("Updated active clients", updatedActiveClients)

            if not self.globalBudgetUsed():
                q = 1-p
                # estTrueCount = float((yesCount - (len(self.clientList) * q)) / (p-q))
                estTrueCount = float((yesCount - (len(branch.activeClients) * q)) / (p-q))
                percentCount = float(estTrueCount / len(branch.activeClients))
                truePerCount = float(trueYesses / len(branch.activeClients)) #Real percent

                if self.verbose:
                    # print("yes cnt", yesCount, "p", p, "q", q, "est true count", estTrueCount)
                    self.logger.info("True Yesses " + str(trueYesses) + ", Yes Responses " + str(yesCount) +", Estimated True yesses " + str(estTrueCount))
                    self.logger.info("True Percent " + str(truePerCount) + ", Est Percent " + str(percentCount) + "\n")
                    # self.logger.info("True Count " + str(trueYesses) +  ", Est Count " + str(estTrueCount))
                    # self.logger.info("True Percent " + str(truePerCount) +  ", Est Percent " + str(percentCount))


                return estTrueCount, updatedActiveClients

            # else:
            return "BUDGET USED", updatedActiveClients

    #Allocate budget for this query
    def allocateQueryBudget(self, strategy):

        if strategy == 'fixed':  #Fixed budget
            pLossBudg = self.epsilon / self.maxQueries

        return pLossBudg

    # Check if the client is still active - client can still have true queries
    def checkClientActive(self, response, p, priorProbTrue):
        p = float(p)
        priorProbTrue = float(priorProbTrue)
        # print("Prior prob:", priorProbTrue)

        # Calculate prob true answer was yes using Bayes Theorem
        if response == 1:
            # print("resp, 1")
            PT1 = priorProbTrue
            PT0 = 1 - priorProbTrue
            # print("PT1", PT1, "PT0", PT0)
            R1gT1 = (p * PT1) / PT1  # if PT1 else 0
            R1gT0 = ((1 - p) * PT0 * p) / PT0 if PT0 else 0
            bayes = (R1gT1 * PT1) / ((R1gT1 * PT1) + (R1gT0 * PT0))  # PT1gR1
            # print("r1g1", R1gT1, "r1gt0", R1gT0, "bayes", bayes)

        else:  # resp == 0
            # print("resp, 0")
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
            # print("******************************client not active anymore")
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

        varList = temp.getAllVars()
        vCounter = 0

        for n in temp.expand_tree(mode=treelib.Tree.WIDTH, sorting=True):
            nd = temp.get_node(n)
            id = re.sub(r'\#.*', '', nd.identifier)

            # if id in self.variables and id != 'timeBound':
            #     subNodes.append("Variable")

            if id in relops:
                if temp.parent(n) != parent:
                    parent = temp.parent(n)
                    subNodes.append(level)
                    nodes.append(subNodes)
                    subNodes = []

                level = temp.level(n)
                subNodes.append(id)

                #append children of node
                for x in temp.children(n):
                    xid = re.sub(r'\#.*', '', x.identifier)

                    if xid in self.variables:
                        subNodes.append(xid)
                    elif xid == 'Variable':
                        # print("VAR LIST ADDition")
                        # print(varList)
                        # print("var list at vcounter", varList[vCounter])

                        subNodes.append(varList[vCounter])
                        vCounter += 1
                        # subNodes.append(id)
                    else:
                        subNodes.append(re.sub(r'\#.*', '', x.identifier))

            elif id in self.variables or id == 'Parameter' or id =='Variable' or id == 'timeBound':
                pass
            elif id not in ignoreList:
                if temp.parent(n) != parent:
                    parent = temp.parent(n)
                    subNodes.append(level)  # add level at end
                    nodes.append(subNodes)
                    subNodes = []

                level = temp.level(n)
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
        # print("template", template.toString())
        # print("template params", tempParams)
        # print("template var list", template.varList)

        if self.epsilon != 'inf':
            pLossBudg = self.allocateQueryBudget(strategy=self.budgetAllocStrategy)
        else:
            pLossBudg = None

        #Get param values from clients
        for c in template.activeClients:
            # print("Client", c)
            params = self.clientList[c].queryParams(tempNodes, template, tempParams, template.varList, self.varDict, self.timeBounds, pLossBudg)

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

            # score at or below which (inclusive) param percentile% of the scores in the distribution may be found
            p = np.percentile(vals, self.paramPercentile)

            finalParams[k] = p

        # return param set
        # print("final params", finalParams, "\n")
        return finalParams

    def getClientQueryCount(self):
        lst = []
        for c in self.clientList:
            lst.append([self.clientList[c].clientNum, self.clientList[c].numQueries])

        #Make dataframe of client nums and their queries
        df = pd.DataFrame(lst, columns=['Client', 'Num Queries']).set_index('Client')

        return df
