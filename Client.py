from SignalTemporalLogic.STLFactory import STLFactory
from STLTree.STLTree import STLTree
import treelib
import logging
import decimal
import math
import numpy as np
import re


class Client:
    def __init__(self, clientNum, epsilon, ruleSet):
        self.clientNum = clientNum
        self.epsilon = epsilon
        self.ruleSet = ruleSet

        self.logger = logging.getLogger('CLIENT')
        self.budgetUsed = 0


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

    def randResponseQueryStruct(self, tempNodes, varList=None, pLossBudg=0.05):

        if not self.privacyBudgetUsed():  # first check privacy budget not used

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
            hasVars = True

            #TODO- will need to adjust variable checking at some point
            # for v in varList:
            #     if v not in r.getAllVars():
            #         hasVars = False

            if hasVars:
                # print(self.clientNum, "has vars")
                # check for structural match
                clientNodes = []
                parent = None
                for node in r.expand_tree(mode=treelib.Tree.WIDTH, sorting=True):
                    if r.parent(node) != parent:
                        parent = r.parent(node)
                        clientNodes.append("newLevel")

                    n = re.sub('[0-9]', '', node)
                    clientNodes.append(n)

                # print("client nodes", clientNodes)
                if self.nodeListMatch(tempNodes, clientNodes):
                    return 1  # found match

        return 0

    # check for match  between two lists of template nodes + client nodes
    def nodeListMatch(self, tempList, cList):
        lMatches = ["LE", "LT"]
        gMatches = ["GE", "GT"]

        for i in range(len(tempList)):
            if tempList[i] != cList[i] and tempList[i] != "?":
                if (tempList[i] in lMatches and cList[i] in lMatches) or (
                        tempList[i] in gMatches and cList[i] in gMatches):  # allow match btw < and <= / > and >=
                    pass
                else:
                    return False

        if len(tempList) != len(cList) and cList[i + 1] != "newLevel":
            return False

        return True