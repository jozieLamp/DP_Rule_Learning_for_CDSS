from SignalTemporalLogic.STLFactory import STLFactory
from STLTree.STLTree import STLTree
import treelib
import logging
import decimal
import math
import numpy as np
import re


class Client:
    def __init__(self, clientNum, epsilon, ruleSet, paramNoise=1):
        self.clientNum = clientNum
        self.epsilon = epsilon
        self.ruleSet = ruleSet

        self.logger = logging.getLogger('CLIENT')
        self.budgetUsed = 0
        self.paramNoise = paramNoise

        self.numQueries = 0


    def loadRuleSet(self, textfile):
        stlFac = STLFactory()
        try:
            file = open(textfile, "r")
            for line in file:
                if line[0] == "(" and line[-2] == ")":
                    line = line[1:-2] + "\n"

                rule = stlFac.constructFormulaTree(line)
                self.ruleSet.append(rule)

            file.close()
            return True

        except:
            self.logger.error("File not found for Client %d" % (self.clientNum) )
            return False


    def logRuleSet(self):
        self.logger.info("\nRule Set for Client %s" % (str(self.clientNum)))
        for i in range(len(self.ruleSet)):
            self.logger.info(self.ruleSet[i].toString())

    # Return True if p budget used up
    def privacyBudgetUsed(self):
        if self.budgetUsed >= self.epsilon:
            return True
        else:
            return False

    #Get randomized response query to rule template
    def randResponseQueryStruct(self, tempNodes, varList, pLossBudg=0.5):

        if not self.privacyBudgetUsed():  # first check privacy budget not used

            self.numQueries += 1 #update to add another query

            p = decimal.Decimal(math.e) ** decimal.Decimal(pLossBudg) / (1 + decimal.Decimal(math.e) ** decimal.Decimal(pLossBudg))

            response = None

            # prob to respond heads (true value) of p
            coin = np.random.binomial(1, p)
            if coin == 1:  # heads, return true value
                response = self.queryStructuralRuleMatch(tempNodes, varList)

            else:  # tails
                coin2 = np.random.binomial(1, 1 - p) #report any other value with prob q (1-p)
                if coin2 == 1:
                    response = 1
                else:
                    response = 0

            # print("\n", self.clientNum, "real resp", self.queryStructuralRuleMatch(tempNodes, varList))

            # update privacy budget
            # self.budgetUsed += self.pLoss
            self.budgetUsed += pLossBudg

            #Get ground truth for experimental purposes
            trueResp = self.queryStructuralRuleMatch(tempNodes, varList)

            return response, trueResp, p

        else:
            return "BUDGET USED", None, None


    # check for structural match
    def queryStructuralRuleMatch(self, tempNodes, varList):
        for r in self.ruleSet:
            # check if variables in rule
            self.varsFull = False
            if varList != []:
                self.varsFull = True

            hasVars = True
            for v in varList:
                if v not in r.getAllVars():
                    hasVars = False

            if hasVars:
                # check for structural match
                clientNodes = []

                for node in r.expand_tree(mode=treelib.Tree.DEPTH, sorting=True):
                    n = re.sub(r'\#.*', '', node)
                    clientNodes.append(n)

                # print("client nodes", clientNodes)
                if self.nodeListMatch(tempNodes, clientNodes):
                    return 1  # found match

        return 0

    # check for structural match and return rule
    def queryStructuralRuleMatchReturn(self, tempNodes, varList):
        for r in self.ruleSet:
            # check if variables in rule
            self.varsFull = False
            if varList != []:
                self.varsFull = True

            hasVars = True
            for v in varList:
                if v not in r.getAllVars():
                    hasVars = False

            if hasVars:
                # check for structural match
                clientNodes = []

                for node in r.expand_tree(mode=treelib.Tree.DEPTH, sorting=True):
                    n = re.sub(r'\#.*', '', node)
                    clientNodes.append(n)

                # print("client nodes", clientNodes)
                if self.nodeListMatch(tempNodes, clientNodes):
                    return r  # found match

        return None

    # check for match  between two lists of template nodes + client nodes
    def nodeListMatch(self, tempList, cList):

        if self.varsFull:
            # print("tempList", tempList)
            # print("clist", cList)
            self.varsFull = False

        #Fix relop matches
        tempList[:] = [x if x != "LT" else "LE" for x in tempList]
        tempList[:] = [x if x != "GT" else "GE" for x in tempList]
        cList[:] = [x if x != "LT" else "LE" for x in cList]
        cList[:] = [x if x != "GT" else "GE" for x in cList]

        i = 0
        while i < len(tempList):
            if tempList[i] in cList:
                idx = cList.index(tempList[i]) #get idx of element of cList
                cList = cList[idx+1:]
            else:
                return False

            i = i+1

        return True

    def queryParams(self, tempNodes, tempParams, varList, varDict):

        #First find possible rule match
        rule = self.queryStructuralRuleMatchReturn(tempNodes, varList)

        if rule != None: #found rule
            # print("\n")
            # print(rule.toString())
            pList = rule.getAllParams()
            # print("orig plist", pList)

            if self.epsilon != 'inf': #private model, need to noise params
                for key, value in pList.items():
                    if 'timeBound' in key:
                        newVal = self.addNoiseToParams(param=float(value), lower=varDict['timeBound'][0], upper=varDict['timeBound'][1])
                    else:
                        newVal = self.addNoiseToParams(param=float(value), lower=varDict[key][0], upper=varDict[key][1])

                    pList[key] = newVal


            return pList

        else:
            return None

    #TODO here- fix issues with noise addition
    def addNoiseToParams(self, param, lower, upper):
        # add noise
        sensitivity = float(upper) - float(lower)
        # noise = np.random.laplace(0, 1 / self.epsilon)
        # noise = np.random.laplace(0, sensitivity / self.pLoss)
        noise = np.random.laplace(0, sensitivity / self.paramNoise)

        # print("noise to be added", noise)

        # clip values
        if (param + noise < lower):
            x = lower
        elif (param + noise > upper):
            x = upper
        else:
            x = param + noise

        #Note budget should not be updated here because it was already accounted for earlier ...
        # update privacy budget
        # NOTE- currently cut this out since budget management excludes param aggregation
        # self.budgetUsed = float(self.budgetUsed)
        # self.budgetUsed += self.paramNoise #self.pLoss

        return x

