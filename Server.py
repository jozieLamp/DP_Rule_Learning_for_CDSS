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
from scipy.stats import norm
from scipy.optimize import minimize_scalar, minimize, Bounds
from gekko import GEKKO
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
            # Previous node p and q values
            self.q_paren = 0.5 #initially set to even 50%
            self.p_paren = 0.5
            self.final_saved_budget = []

            self.logger.info("Setting privacy budget to: " + str(self.epsilon))


    def globalBudgetUsed(self):
        # print("Clients with used budgets:", self.clientsWithUsedBudgets)
        self.budgetZero = False

        if list(self.clientList.keys()) == set(self.clientsWithUsedBudgets):
            return True
        elif len(set(self.clientsWithUsedBudgets)) > len(self.clientList)-3: #only a few clients without used budgets so end
            return True
        elif self.budgetZero == True:
            return True
        else:
            return False


    # RUN Monte Carlo Tree Search
    def runProtocol(self, branchName):

        # RUN MONTE CARLO TREE SEARCH TO FIND RULE STRUCTURES
        mcts = MCTS(method=self.mctsType, server=self, verbose=self.verbose)

        totalIters = 1 #to track the number of iterations that are completed
        # while not self.globalBudgetUsed() and self.numQueries < self.maxQueries and not self.templateTree._branches[branchName].completelyExplored:
        while not self.globalBudgetUsed() and not self.templateTree._branches[branchName].completelyExplored:

            if (self.verbose):
                self.logger.info("BEGIN SEARCH ROUND, ITERATION: " + str(totalIters) + "\n")

            mcts.runMCTSRound(branchName=branchName)

            totalIters += 1

            if self.globalBudgetUsed():
                self.logger.info("GLOBAL BUDGET USED")

            # if self.numQueries >= self.maxQueries:
            #     self.logger.info("TOTAL QUERIES USED UP")

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
        irtDF.to_csv(self.params.resultsFilename + "InitialRules.csv")
        #TODO - del this
        # if self.verbose:
        #     self.logger.info("Initial Rules")
        #     for x in initialRuleTrees:
        #         self.logger.info(x.toString())

        if self.verbose:
            self.logger.info("Generated " + str(len(initialRuleTrees)) + " initial rules\n")
            self.logger.info("----PERFORM FINAL QUERY FOR EACH FULL RULE----")

        self.logger.info("Generated " + str(len(initialRuleTrees)) + " initial rules\n")


        # do one final query for each rule to make sure full rule has a match
        ruleTrees = []
        for ri in range(len(initialRuleTrees)):
            r = initialRuleTrees[ri]
            # print(r.toString())
            # r.show()

            origAC = r.activeClients
            percentCount = r.percentCount

            if self.epsilon != 'inf':
                if self.budgetAllocStrategy == 'fixed':
                    finalBudg = self.allocateQueryBudget(self.budgetAllocStrategy, None)
                else:
                    # finalBudg = self.final_saved_budget[ri] #sum(self.final_saved_budget) / len(self.final_saved_budget) #
                    # finalBudg = 5 / len(self.final_saved_budget)
                    finalBudg = sum(self.final_saved_budget) / len(initialRuleTrees) #this is the good one ...
                    # finalBudg = 0.1 #now checking to see if higher budg at end is better
                    print(r.toString(), "count:", r.percentCount)
                print("FINAL BUDG", finalBudg)
            else:
                finalBudg=None

            # TODO here - how to save ploss budget used for query so can do final last query ...
            # finalBudg = r.pLossBudg
            # print(r.toString())
            # print("FINAL BUDG Query from rule Tree", finalBudg)

            matchCount, activeClients = self.queryFullRuleMatch(r, finalBudg)

            # Fix negative estimates
            if matchCount < 0:
                matchCount = 0.0
            # Fix over estimates
            if matchCount > len(origAC):
                matchCount = len(origAC)

            percentCount = matchCount / len(origAC) if len(origAC) > 0 else 0

            if self.verbose:
                self.logger.info(r.toString())
                self.logger.info("Rule Match Count: " + str(matchCount) + ", Rule Match Percentage: " + str(percentCount))

            # if percentCount >= self.cutoffThresh:
            #     #update active clients to be only clients who said yes
            #     # r.activeClients = activeClients  # add active clients to rule tree
            #     r.percentCount = percentCount  # add percent count to rule tree
            #     ruleTrees.append(r)

            # TODO - now trying averages of node percent counts + last query
            # Get aves of percent count at each node
            # print(r.percentCount)
            avePer = (sum(r.percentCount) + percentCount) / (len(r.percentCount) + 1)

            if avePer >= self.cutoffThresh: #TODO - change cutoff thresh here ...? #if avePer > 0.33:
                #update active clients to be only clients who said yes
                # r.activeClients = activeClients  # add active clients to rule tree
                r.percentCount = percentCount  # add percent count to rule tree
                ruleTrees.append(r)

        if self.verbose:
            self.logger.info("Generated " + str(len(ruleTrees)) + " full rules\n")

        #TODO del this
        # if self.verbose:
        #     self.logger.info("Generated Full Rules:")
        #     for x in ruleTrees:
        #         self.logger.info(x.toString())

        # ESTIMATE PARAMETERS FOR EACH RULE IN THE RULESET
        if self.verbose:
            self.logger.info("----PARAMETER ESTIMATION PHASE----\n")

        stlFac = STLFactory()
        rules = []
        finalTrees = []
        #query params and make final STL Rule Structures (STL Trees)
        for ti in range(len(ruleTrees)):
            t = ruleTrees[ti]

            # get budget
            if self.epsilon != 'inf':
                finalBudg = self.final_saved_budget[ti]
            else:
                finalBudg = None

            #Query missing params for tree
            tempParams = self.queryParameters(t, finalBudg)

            #Only get correctly formatted rules
            ft = stlFac.constructFormulaTree(t.toStringWithParams() + "\n") # Check if structure correct

            if ft != None:  # Formula is not improper

                if tempParams != None:
                    ft.updateParams(tempParams)# Update params in structure
                rules.append(ft)
                finalTrees.append(t)

        #Make Rule Set Object to store output rule set
        self.finalRuleSet = RuleSet(finalTrees, rules)

        # OUTPUT FINAL RETURNED RULE STRUCTURES
        if self.verbose:
            self.finalRuleSet.logRuleSet()

        self.logger.info("Generated " + str(len(initialRuleTrees)) + " initial rules")
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
    def queryFullRuleMatch(self, template, pLossBudg):
        # get template node list
        tempNodes = self.getTemplateNodes(template)
        updatedActiveClients = template.activeClients

        # Non private model
        if self.epsilon == 'inf':
            yesCount = 0
            for c in template.activeClients:
                resp = self.clientList[c].queryStructuralRuleMatch(tempNodes, template.varList)
                yesCount += resp

                # # Remove client if has no match
                # if resp == 1:
                #     updatedActiveClients.append(c)

            return yesCount, updatedActiveClients

        # Private model
        else:
            # get count from clients of who have template
            yesCount = 0
            trueYesses = 0

            # Get PLoss budget for this query
            # parentCount = len(self.clientList) / 2 #if no parent node assume 50% prob of match #TODO - might need to set this as something standard...
            # pLossBudg = self.allocateQueryBudget(strategy=self.budgetAllocStrategy, c=parentCount)
            p = math.e ** pLossBudg / (1 + math.e ** pLossBudg)
            #decimal.Decimal(math.e) ** decimal.Decimal(pLossBudg) / (1 + decimal.Decimal(math.e) ** decimal.Decimal(pLossBudg))

            for c in template.activeClients:
                resp, truResp = self.clientList[c].finalRandResponseQuery(tempNodes, template.varList, pLossBudg)

                yesCount += resp
                trueYesses += truResp

                # if resp == 1:
                #     updatedActiveClients.append(c) #make active clients only the ones who said yes

            #Calculate final match count for this rule
            q = 1 - p

            c_hat = float((yesCount - (len(template.activeClients) * q)) / (p - q) if (p-q) else (yesCount - (len(template.activeClients) * q)) ) #unbiased estimate of count
            #Fix/clip over/under estimates
            if c_hat > len(template.activeClients):
                estTrueCount = len(template.activeClients)
            elif c_hat < 0:
                estTrueCount = 0
            else:
                estTrueCount = c_hat

            percentCount = float(estTrueCount / len(template.activeClients))
            truePerCount = float(trueYesses / len(template.activeClients))  # Real percent

            # if self.verbose:
            #     self.logger.info("Template: " + template.toString())
            #     self.logger.info(str(("Active clients ", template.activeClients)))
            #     # print("yes cnt", yesCount, "p", p, "q", q, "est true count", estTrueCount)
            #     self.logger.info("True Yesses " + str(trueYesses) + ", Yes Responses " + str(yesCount) + ", Estimated True yesses " + str(estTrueCount))
            #     self.logger.info("True Percent " + str(truePerCount) + ", Est Percent " + str(percentCount) + "\n")

            print("p " + str(p) + " q " + str(q))
            print("True Yesses " + str(trueYesses) + ", Yes Responses " + str(yesCount) + ", c_hat " + str(
                c_hat) + ", Estimated True yesses " + str(estTrueCount))
            print("\n")

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

                # ***ADDED - Removing active client computation
                # #Remove client if has no match
                # if resp == 1:
                #     updatedActiveClients.append(c)
                updatedActiveClients.append(c)

            return yesCount, updatedActiveClients, None

        #Private model
        else:
            # get count from clients of who have template
            yesCount = 0
            trueYesses = 0

            #Get PLoss budget for this query
            if branch.parent:
                parentCount = branch.parent.branch.getMatchCount()
            else:
                parentCount = len(self.clientList) / 2 #if no parent node assume 50% prob of match
            # print("FOUND MATCH COUNT", parentCount)
            pLossBudg = self.allocateQueryBudget(strategy=self.budgetAllocStrategy, c=parentCount)
            # p = decimal.Decimal(math.e) ** decimal.Decimal(pLossBudg) / (1 + decimal.Decimal(math.e) ** decimal.Decimal(pLossBudg))
            p = math.e ** pLossBudg / (1 + math.e ** pLossBudg)

            if pLossBudg == None or self.clientList[1].privacyBudgetUsed(): #set budget as used
                self.budgetZero = True

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

                    # ***ADDED - Removing active client computation
                    # # print("\nClient", c, "resp", resp)
                    # if self.checkClientActive(response=resp, p=p, priorProbTrue=priorProb): #if true, still active, add to updated active clients
                    #     updatedActiveClients.append(c)
                    updatedActiveClients.append(c)

            # print("Updated active clients", updatedActiveClients)

            if not self.globalBudgetUsed():
                q = 1-p

                c_hat = float((yesCount - (len(self.clientList) * q)) / (p - q) if (p-q) else (yesCount - (len(self.clientList) * q)))  # unbiased estimate of count
                # Fix/clip over/under- estimates
                if c_hat > len(self.clientList):
                    estTrueCount = len(self.clientList)
                elif c_hat < 0:
                    estTrueCount = 0
                else:
                    estTrueCount = c_hat

                percentCount = float(estTrueCount / len(branch.activeClients)) if len(branch.activeClients) else 0
                truePerCount = float(trueYesses / len(branch.activeClients)) if len(branch.activeClients) else 0  # Real percent

                if self.verbose:
                    self.logger.info("p "+ str(p) + " q " + str(q) + " len client list " + str(len(branch.activeClients)))
                    self.logger.info("True Yesses " + str(trueYesses) + ", Yes Responses " + str(yesCount) +", Estimated True yesses " + str(estTrueCount))
                    self.logger.info("True Percent " + str(truePerCount) + ", Est Percent " + str(percentCount) + "\n")
                    # self.logger.info("True Count " + str(trueYesses) +  ", Est Count " + str(estTrueCount))
                    # self.logger.info("True Percent " + str(truePerCount) +  ", Est Percent " + str(percentCount))

                print("p "+ str(p) + " q " + str(q) + " len client list " + str(len(branch.activeClients)))
                print("True Yesses " + str(trueYesses) + ", Yes Responses " + str(yesCount) + ", c_hat " + str(c_hat) +", Estimated True yesses " + str(estTrueCount))
                print("\n")

                return estTrueCount, updatedActiveClients, pLossBudg

            # else:
            return "BUDGET USED", updatedActiveClients, pLossBudg

    # Allocate budget for this query --> method using mystic
    def allocateQueryBudget(self, strategy, c):

        if strategy == 'fixed':  # Fixed budget
            pLossBudg = self.epsilon / self.maxQueries
        elif strategy == 'adaptive':
            # print("In adaptive tree search")

            #check if budget used
            if self.clientList[1].privacyBudgetUsed():
                return 0

            # Constants
            n = len(self.clientList)  # num clients
            theta = 0.05 # acceptable error probability, e.g., 5%
            c = c / n


            # Formulate optimization problem to find minimum budget (beta) to use
            #P[ˆc > λ | c ≤ λ] + P[ˆc ≤ λ | c > λ] ≤ θ
            def obj_func(beta):
                p = math.e ** beta / (1 + math.e ** beta)
                q = 1-p

                # c_hat = p * n
                c_hat = p

                print("\nP", p)
                print("c hat", c_hat)
                print("c", c)

                sigma_c_hat = self.sigma(n, beta, p, q)
                print("sigma c hat", sigma_c_hat)
                sigma_c = self.sigma(n, self.epsilon, self.p_paren, self.q_paren)
                print("sigma c", sigma_c)

                lmda = self.cutoffThresh #* n
                print("lmda", lmda)

                # # Compute CDFs
                # #P[ˆc > λ | c ≤ λ]
                # falseContinue = (1 - norm.cdf(self.Z(n, c_hat, sigma_c_hat))) / norm.cdf(self.Z(n, c, sigma_c))
                # #P[ˆc ≤ λ | c > λ]
                # falseCutoff = norm.cdf(self.Z(n, c_hat, sigma_c_hat)) / (1 - norm.cdf(self.Z(n, c, sigma_c)))

                # # Compute CDFs
                # # P[ˆc > λ | c ≤ λ]
                # falseContinue = ((1 - norm.cdf(self.Z(n, c_hat, sigma_c_hat))) - norm.cdf(self.Z(n, c, sigma_c))) / (1 - norm.cdf(self.Z(n, c, sigma_c)))
                # # P[ˆc ≤ λ | c > λ]
                # falseCutoff = (norm.cdf(self.Z(n, c_hat, sigma_c_hat)) - (1 - norm.cdf(self.Z(n, c, sigma_c)))) / norm.cdf(self.Z(n, c, sigma_c))
                # print("P[c_hat > lambda", 1 - norm.cdf(self.Z(n, c_hat, sigma_c_hat)))
                # print("P[c <= lambda", norm.cdf(self.Z(n, c, sigma_c)))
                # print("Prob false continue", falseContinue)
                # print("P[c_hat <= lambda", norm.cdf(self.Z(n, c_hat, sigma_c_hat)))
                # print("P[c > lambda", 1 - norm.cdf(self.Z(n, c, sigma_c)))
                # print("Prob false cutoff", falseCutoff)

                # TODO - working here ... not sure if probs make sense
                # Compute CDFs
                # # P[ˆc > λ | c ≤ λ]
                # falseContinue = ((1 - norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat)) * norm.cdf(lmda, loc=c, scale=sigma_c)) / (1 - norm.cdf(lmda, loc=c, scale=sigma_c))
                # # P[ˆc ≤ λ | c > λ]
                # falseCutoff = (norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat) * (1 - norm.cdf(lmda, loc=c, scale=sigma_c))) / norm.cdf(lmda, loc=c, scale=sigma_c)
                # P[ˆc > λ | c ≤ λ]
                falseContinue = (1 - norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat)) * norm.cdf(lmda, loc=c,scale=sigma_c)
                # P[ˆc ≤ λ | c > λ]
                falseCutoff = norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat) * (1 - norm.cdf(lmda, loc=c, scale=sigma_c))

                print("P[c_hat > lambda", 1 - norm.cdf(self.Z(n, c_hat, sigma_c_hat) ))
                print("P[c <= lambda", norm.cdf(self.Z(n, c, sigma_c)))
                print("Prob false continue", falseContinue)
                print("P[c_hat <= lambda",norm.cdf(self.Z(n, c_hat, sigma_c_hat)))
                print("P[c > lambda", 1 - norm.cdf(self.Z(n, c, sigma_c)))
                print("Prob false cutoff", falseCutoff)


                # Compute CDFs
                # P[ˆc > λ | c ≤ λ]
                # falseContinue = norm.cdf(lmda, loc=c, scale=sigma_c) * (1 - norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat)) / norm.cdf(lmda, loc=c, scale=sigma_c)
                # # P[ˆc ≤ λ | c > λ]
                # falseCutoff = (1 - norm.cdf(lmda, loc=c, scale=sigma_c)) * norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat) / (1 - norm.cdf(lmda, loc=c, scale=sigma_c))

                # # P[ˆc > λ | c ≤ λ]
                # falseContinue = (1 - norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat)) * norm.pdf(lmda, loc=c, scale=sigma_c) / norm.cdf(lmda, loc=c, scale=sigma_c)
                # # P[ˆc ≤ λ | c > λ]
                # falseCutoff = norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat) * (1 - norm.cdf(lmda, loc=c, scale=sigma_c)) / norm.pdf(lmda, loc=c_hat, scale=sigma_c_hat)
                # # falseCutoff = norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat) * (1 - norm.pdf(lmda, loc=c, scale=sigma_c)) / (1 - norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat))

                # # P[ˆc > λ | c ≤ λ]
                # falseContinue = (1 - norm.cdf(self.Z(n, c_hat, sigma_c_hat))) * norm.pdf(self.Z(n, c,sigma_c)) / norm.cdf(self.Z(n, c, sigma_c))
                # # P[ˆc ≤ λ | c > λ]
                # falseCutoff = norm.cdf(self.Z(n, c_hat, sigma_c_hat)) * (1 - norm.cdf(self.Z(n, c, sigma_c))) / norm.pdf(self.Z(n, c_hat, sigma_c_hat))
                # falseCutoff = norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat) * (1 - norm.pdf(lmda, loc=c, scale=sigma_c)) / (1 - norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat))


                probErrorChoice = falseContinue + falseCutoff
                print("beta", beta)
                # print("c_hat cdf", norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat))
                # print("c cdf", norm.cdf(lmda, loc=c, scale=1))
                # print("c pdf", norm.pdf(lmda, loc=c, scale=1))
                # print("z of c hat", self.Z(n, c_hat, sigma_c_hat))
                # print("cdf of c hat", norm.cdf(self.Z(n, c_hat, sigma_c_hat)))
                # print("z of c", self.Z(n, c, sigma_c))
                # print("cdf of c", norm.cdf(self.Z(n, c, sigma_c)))
                # print("false cont", falseContinue)
                # print("fasle cutoff", falseCutoff)
                print("Prob make incorrect choice", probErrorChoice)
                print("Prob make correct choice, and function return", 1 - probErrorChoice)
                return 1 - probErrorChoice

            # TODO - change all cutoff thresh vars to be lambda and make this prob a hyperparam fed in --> theta
            ineq_constraint = {'type': 'ineq', 'fun': lambda x: obj_func(x) - (1 - theta)}

            lw_bnd = 0.1#1e-5#1e-10 #1e-20
            print("BUDGET USED", self.clientList[1].budgetUsed)
            print("global budget used?", self.globalBudgetUsed())
            up_bnd = self.epsilon - self.clientList[1].budgetUsed
            if lw_bnd > up_bnd:
                up_bnd = lw_bnd
            bnds = Bounds(lb=lw_bnd, ub=up_bnd)
            print("bounds", bnds)

            # SLSQP method
            options = {'maxiter': 1000, 'ftol': 0.1}
            result = minimize(obj_func, x0=np.array(lw_bnd), constraints=ineq_constraint, bounds=bnds, method='SLSQP',options=options)

            # trust-constr method
            # options = {'maxiter': 1000}  # Increase the maximum number of function evaluations
            # result = minimize(obj_func, x0=np.array(lw_bnd), constraints=ineq_constraint, bounds=bnds, method='trust-constr', options=options)

            # # if failed try trust constr method
            # if not result.success:
            #     print("TRYING TRUST CONSTR METHOD*************************************************************************")
            #     options = {'maxiter': 500}  # Increase the maximum number of function evaluations
            #     result = minimize(obj_func, x0=np.array(lw_bnd), constraints=ineq_constraint, bounds=bnds, method='trust-constr', options=options)


            if result.success:
                print("Success, beta = ", result.x)
                print("Estimated Prob of", result.fun)

                pLossBudg = result.x[0]

                #TODO - fix this
                if pLossBudg < 0:
                    pLossBudg = lw_bnd

                # Update global p and q params of parent node
                self.p_paren = math.e ** pLossBudg / (1 + math.e ** pLossBudg)
                    #decimal.Decimal(math.e) ** decimal.Decimal(pLossBudg) / (1 + decimal.Decimal(math.e) ** decimal.Decimal(pLossBudg))
                self.q_paren = 1 - self.p_paren

            else:
                print("FAIL")
                print(result)
                print(result.message)
                pLossBudg = None

        print("Returning budget of:", pLossBudg)
        return pLossBudg

    def sigma(self, n, beta, p ,q):
        bottom =n* ((p - q) ** 2)
        # bottom = (p - q) ** 2
        stdDev = q * (1 - q) / bottom if bottom else (q * (1 - q))
        # print("top", q * (1 - q))
        # stdDev = stdDev / n
        # print("p, q, p-q", p, q, (p - q))
        # print("p-q std dev", math.pow((p - q), 2))
        # print("p-q std dev", ((p - q)**2))
        # stdDev = (q * (1 - q)) / ((p - q)**2)
        # print("sigma, bottom", bottom)
        # print("sigma, top", (n * q * (1 - q)))
        # print("top sigma", (n * (1 - p - q)))
        # bottom = p-q
        # stdDev = (n * (1 - p - q)) / bottom if bottom else 0
        # stdDev = n * ((-1 + beta) / (beta - 1)**2 )
        # if stdDev == 0:
        #     stdDev = 1

        return stdDev

    def Z(self, n, v, sigma_v):
        cutoffCount = self.cutoffThresh #* n
        return (cutoffCount - v) / sigma_v


    # # Allocate budget for this query --> method using mystic
    # def allocateQueryBudget(self, strategy, c):
    #
    #     if strategy == 'fixed':  # Fixed budget
    #         pLossBudg = self.epsilon / self.maxQueries
    #     elif strategy == 'adaptive':
    #         # print("In adaptive tree search")
    #
    #         #check if budget used
    #         if self.clientList[1].privacyBudgetUsed():
    #             return 0
    #
    #         # Constants
    #         n = len(self.clientList)  # num clients
    #         # c is param passed in, true count (mean) from parent node
    #
    #         # Compute Standard Deviation of parent node
    #         # bottom = (self.p_paren - self.q_paren) ** 2
    #         # stdDev = (n * self.q_paren * (1 - self.q_paren)) / bottom if bottom else (
    #         #             n * self.q_paren * (1 - self.q_paren))
    #         # # print("q paren", self.q_paren)
    #         # # print("p paren", self.p_paren)
    #         # # print("std dev", stdDev)
    #         # # print("bottom", bottom)
    #         stdDev = n / 4
    #
    #         d = 2 * stdDev  # Distance of within 2 standard deviations
    #         print("Std Dev", stdDev, "distance", d)
    #
    #         # Formulate optimization problem to find minimum budget (beta) to use
    #         def obj_func(beta):
    #             p = math.e ** beta / (1 + math.e ** beta)
    #             c_hat = p * n
    #
    #             #Compute z scores for distances
    #             z_upper = (c_hat - c + d) / stdDev
    #             z_lower = (c_hat - c - d) / stdDev
    #
    #             # Compute CDF
    #             cdf_upper = norm.cdf(z_upper)
    #             cdf_lower = norm.cdf(z_lower)
    #
    #             # print("beta", beta, "Sub CDFs", (cdf_upper - cdf_lower))
    #
    #             return (cdf_upper - cdf_lower)  # >= 0.95
    #
    #         ineq_constraint = {'type': 'ineq', 'fun': lambda x: obj_func(x) - 0.95} # was 0.95
    #
    #         lw_bnd = 1e-10 #1e-20
    #         print("BUDGET USED", self.clientList[1].budgetUsed)
    #         print("global budget used?", self.globalBudgetUsed())
    #         up_bnd = self.epsilon - self.clientList[1].budgetUsed
    #         if lw_bnd > up_bnd:
    #             up_bnd = lw_bnd
    #         bnds = Bounds(lb=lw_bnd, ub=up_bnd)
    #         print("bounds", bnds)
    #
    #         # SLSQP method
    #         options = {'maxiter': 1000, 'ftol': 0.1}
    #         result = minimize(obj_func, x0=np.array(lw_bnd), constraints=ineq_constraint, bounds=bnds, method='SLSQP',options=options)
    #
    #         # trust-constr method
    #         # options = {'maxiter': 1000}  # Increase the maximum number of function evaluations
    #         # result = minimize(obj_func, x0=np.array(lw_bnd), constraints=ineq_constraint, bounds=bnds, method='trust-constr', options=options)
    #
    #         # if failed try trust constr method
    #         if not result.success:
    #             print("TRYING TRUST CONSTR METHOD*************************************************************************")
    #             options = {'maxiter': 500}  # Increase the maximum number of function evaluations
    #             result = minimize(obj_func, x0=np.array(lw_bnd), constraints=ineq_constraint, bounds=bnds, method='trust-constr', options=options)
    #
    #
    #         if result.success:
    #             print("Success, beta = ", result.x)
    #             print("Estimated Prob of", result.fun)
    #
    #             pLossBudg = result.x[0]
    #
    #             #TODO - fix this
    #             if pLossBudg < 0:
    #                 pLossBudg = lw_bnd
    #
    #             # Update global p and q params of parent node
    #             self.p_paren = math.e ** pLossBudg / (1 + math.e ** pLossBudg)
    #                 #decimal.Decimal(math.e) ** decimal.Decimal(pLossBudg) / (1 + decimal.Decimal(math.e) ** decimal.Decimal(pLossBudg))
    #             self.q_paren = 1 - self.p_paren
    #
    #         else:
    #             print("FAIL")
    #             print(result)
    #             print(result.message)
    #             pLossBudg = None
    #
    #     print("Returning budget of:", pLossBudg)
    #     return pLossBudg



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
            R1gT1 = (p * PT1) / PT1  if PT1 else 0
            R1gT0 = ((1 - p) * PT0 * p) / PT0 if PT0 else 0
            bayes = (R1gT1 * PT1) / ((R1gT1 * PT1) + (R1gT0 * PT0))  # PT1gR1
            # print("r1g1", R1gT1, "r1gt0", R1gT0, "bayes", bayes)

        else:  # resp == 0
            # print("resp, 0")
            PT1 = priorProbTrue
            PT0 = 1 - priorProbTrue
            # print("PT1", PT1, "PT0", PT0)
            R0gT0 = (p * PT0) / PT0 if PT0 else 0
            R0gT1 = ((1 - p) * PT1 * p) / PT1  if PT1 else 0
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
    def queryParameters(self, template, pLossBudg):

        # get template node list
        tempNodes = self.getTemplateNodes(template)
        tempParams = template.getMissingParams()
        # print("template", template.toString())
        # print("template params", tempParams)
        # print("template var list", template.varList)

        # if self.epsilon != 'inf':
        #     pLossBudg = self.allocateQueryBudget(strategy=self.budgetAllocStrategy)
        # else:
        #     pLossBudg = None

        #Get param values from clients
        # print("active clients", template.activeClients)
        if template.activeClients == []:
            params = self.clientList[1].queryParams(tempNodes, template, tempParams, template.varList, self.varDict, self.timeBounds, pLossBudg)

            if params != None:
                for k in tempParams.keys():
                    if k in params:
                        tempParams[k].append(params[k])


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
