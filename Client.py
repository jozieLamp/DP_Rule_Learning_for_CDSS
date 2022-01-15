from SignalTemporalLogic.STLFactory import STLFactory
from STLTree.STLTree import STLTree
from STLTree.Atomic import AtomicEnum
import treelib
import logging
import decimal
import math
import random
from statistics import median
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
        # print("Temp vars", varList)
        # print("templt nodes", tempNodes)

        for r in self.ruleSet:
            # print("rule vars", r.getAllVars())
            # check if variables in rule
            self.varsFull = False
            if varList != []:
                self.varsFull = True

            hasVars = True
            for v in varList:
                if v not in r.getAllVars():
                    hasVars = False

            if hasVars:
                # print("HAS VARS")
                clientNodes = self.getClientNodes(r, varList)

                # print("client nodes", clientNodes)
                # print(r.toString())
                if self.nodeListMatch(tempNodes, clientNodes):
                    # print("MATCH")
                    # print("temp", tempNodes)
                    # print("clnt", clientNodes)
                    return 1  # found match

        return 0

    def getClientNodes(self, r, tempVars):
        relops = ['GT', 'GE', 'LT', 'LE', "EQ", 'NEQ']

        # check for structural match
        clientNodes = []
        subNodes = []
        parent = None
        level = 0
        varList = r.getAllVars()
        vCounter = 0

        for node in r.expand_tree(mode=treelib.Tree.WIDTH, sorting=True):
            n = re.sub(r'\#.*', '', node)
            # level = r.level(node)

            if n in relops:
                if r.parent(node) != parent:
                    parent = r.parent(node)
                    subNodes.append(level)
                    clientNodes.append(subNodes)
                    subNodes = []

                level = r.level(node)
                subNodes.append(n)

                if tempVars != []: #only append vars if at var level
                    # append children of node
                    for x in r.children(node):
                        obj = r[x.identifier].data
                        if obj.type == AtomicEnum.Variable:
                            subNodes.append(varList[vCounter])
                            vCounter += 1
                        else:
                            subNodes.append(re.sub(r'\#.*', '', x.identifier))

            elif n == 'Variable' or n == 'Parameter' or n == 'timeBound':
                pass
            else:
                if r.parent(node) != parent:
                    parent = r.parent(node)
                    subNodes.append(level)
                    clientNodes.append(subNodes)
                    subNodes = []

                level = r.level(node)
                subNodes.append(n)

        if subNodes != []:
            subNodes.append(level)
            clientNodes.append(subNodes)

        return clientNodes

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
                clientNodes = self.getClientNodes(r, varList)

                # print("clnt", clientNodes)
                # print("temp", tempNodes)
                if self.nodeListMatch(tempNodes, clientNodes):
                    # print("clnt", clientNodes)
                    # print("match")
                    return r  # found match

        # print("No match")
        return None

    # check for match  between two lists of template nodes + client nodes
    def nodeListMatch(self, tempList, cList):
        relops = ['GT', 'GE', 'LT', 'LE', "EQ"]  # , 'NEQ']

        i = 0
        while i < len(tempList):
            # get current branch of nodes
            if tempList[i] in cList:
                if 'Parameter' not in tempList[i]:  # found a var match
                    #                 idx = cList.index(tempList[i])  # get idx of element of cList
                    #                 cList = cList[idx + 1:]
                    cList.remove(tempList[i])

            elif any(item in tempList[i] for item in relops):
                # Try all match options
                if 'GT' in tempList[i]:
                    test = [x if x != "GT" else "GE" for x in tempList[i]]

                    if test in cList:
                        cList.remove(test)
                    else:
                        return False
                elif 'GE' in tempList[i]:
                    test1 = [x if x != "GE" else "GT" for x in tempList[i]]
                    test2 = [x if x != "GE" else "EQ" for x in tempList[i]]

                    try:
                        idx1 = cList.index(test1)
                    except:
                        idx1 = 999999999
                    try:
                        idx2 = cList.index(test2)
                    except:
                        idx2 = 999999999

                    if test1 in cList and (idx1 < idx2):
                        cList.remove(test1)
                    elif test2 in cList and (idx2 < idx1):
                        cList.remove(test2)
                    else:
                        return False
                elif 'LT' in tempList[i]:
                    test = [x if x != "LT" else "LE" for x in tempList[i]]
                    if test in cList:
                        cList.remove(test)
                    else:
                        return False
                elif 'LE' in tempList[i]:
                    test1 = [x if x != "LE" else "LT" for x in tempList[i]]
                    test2 = [x if x != "LE" else "EQ" for x in tempList[i]]
                    try:
                        idx1 = cList.index(test1)
                    except:
                        idx1 = 999999999
                    try:
                        idx2 = cList.index(test2)
                    except:
                        idx2 = 999999999

                    if test1 in cList and (idx1 < idx2):
                        cList.remove(test1)
                    elif test2 in cList and (idx2 < idx1):
                        cList.remove(test2)
                    else:
                        return False
                elif 'EQ' in tempList[i]:
                    test1 = [x if x != "EQ" else "GE" for x in tempList[i]]
                    test2 = [x if x != "EQ" else "LE" for x in tempList[i]]

                    try:
                        idx1 = cList.index(test1)
                    except:
                        idx1 = 999999999
                    try:
                        idx2 = cList.index(test2)
                    except:
                        idx2 = 999999999

                    if test1 in cList and (idx1 < idx2):
                        cList.remove(test1)
                    elif test2 in cList and (idx2 < idx1):
                        cList.remove(test2)
                    else:
                        return False

            else:
                return False

            i = i + 1

        return True


    def queryParams(self, tempNodes, template, tempParams, varList, varDict):

        #First find possible rule match
        rule = self.queryStructuralRuleMatchReturn(tempNodes, varList)

        if rule != None: #found complete rule
            # print("FOUND COMPLETE RULE IN QUERY PARAMS")
            pList = rule.getAllParams()

        else: #Try partial rule match
            pList = self.queryPartialStructureParamReturn(template, tempParams, varList)

        # print("\nclient plist", pList)

        #No match found, return random params
        missing = list(set(tempParams.keys()) - set(pList.keys()))
        # print("Missing params in plist", missing)
        for m in missing:
            v = m[:-1]

            if v =='timeBoundLower' or v == 'timeBoundUpper':
                pList[m] = random.uniform(varDict['timeBound'][0], varDict['timeBound'][1])
            else:
                pList[m] = random.uniform(varDict[v][0], varDict[v][1])

            #Draw from median value
            # if v == "timeBoundLower":
            #     middle = int((varDict['timeBound'][1] - varDict['timeBound'][0]) / 2)  # get median / mean params
            #     lower = median([varDict['timeBound'][0], middle])
            #     pList[m] = lower
            # elif v == "timeBoundUpper":
            #     middle = int((varDict['timeBound'][1] - varDict['timeBound'][0]) / 2)  # get median / mean params
            #     upper = median([middle, varDict['timeBound'][1]])
            #     pList[m] = upper
            # else:
            #     lower = varDict[v][0]
            #     upper = varDict[v][1]
            #     pList[m] = (upper - lower) / 2  # get median / mean params

        # print("UPDATED client plist", pList)

        #Add noise to found params
        if self.epsilon != 'inf':  # private model, need to noise params
            for key, value in pList.items():
                if 'timeBound' in key:
                    newVal = self.addNoiseToParams(param=float(value), lower=varDict['timeBound'][0],
                                                   upper=varDict['timeBound'][1])
                else:
                    newVal = self.addNoiseToParams(param=float(value), lower=varDict[key][0], upper=varDict[key][1])

                pList[key] = newVal

        return pList

    # check for structural match and return rule
    def queryPartialStructureParamReturn(self, template, tempParams, varList):

        pList = {}
        tempOps = template.getOperators()
        # print("temp ops", tempOps)
        # print(template.toString())

        for r in self.ruleSet:
            #first check for overall order of operators correct
            clientOps = r.getOperators()

            if any(item in varList for item in r.getAllVars()) and self.operatorMatch(tempOps, clientOps): #found operator match
                #get params contained in the rule
                rParams = r.getAllParams()

                #For each variable found, add param value to pList
                for v in tempParams.keys():
                    if v in rParams:
                        pList[v] = rParams[v]

            if pList != {}:
                return pList

        return pList #was none

    def operatorMatch(self, tempList, cList):
        relops = ['GT', 'GE', 'LT', 'LE', "EQ"]#, 'NEQ']

        # print("tlist", tempList)
        # print("clist", cList)

        foundVar = False

        i = 0
        while i < len(tempList):
            # get current branch of nodes
            if tempList[i] in cList:
                if 'Parameter' in tempList[i]: #found a var match
                    foundVar = True
                else:
                    # idx = cList.index(tempList[i])  # get idx of element of cList
                    # cList = cList[idx + 1:]
                    cList.remove(tempList[i])

            elif any(item in tempList[i] for item in relops):
                # Try all match options
                if 'GT' in tempList[i]:
                    test = [x if x != "GT" else "GE" for x in tempList[i]]

                    if test in cList:
                        cList.remove(test)
                    else:
                        return False

                elif 'GE' in tempList[i]:
                    test1 = [x if x != "GE" else "GT" for x in tempList[i]]
                    test2 = [x if x != "GE" else "EQ" for x in tempList[i]]

                    try:
                        idx1 = cList.index(test1)
                    except:
                        idx1 = 999999999
                    try:
                        idx2 = cList.index(test2)
                    except:
                        idx2 = 999999999

                    if test1 in cList and (idx1 < idx2):
                        cList.remove(test1)

                    elif test2 in cList and (idx2 < idx1):
                        cList.remove(test2)
                    else:
                        return False

                elif 'LT' in tempList[i]:
                    test = [x if x != "LT" else "LE" for x in tempList[i]]
                    if test in cList:
                        cList.remove(test)
                    else:
                        return False

                elif 'LE' in tempList[i]:
                    test1 = [x if x != "LE" else "LT" for x in tempList[i]]
                    test2 = [x if x != "LE" else "EQ" for x in tempList[i]]

                    try:
                        idx1 = cList.index(test1)
                    except:
                        idx1 = 999999999
                    try:
                        idx2 = cList.index(test2)
                    except:
                        idx2 = 999999999

                    if test1 in cList and (idx1 < idx2):
                        cList.remove(test1)
                    elif test2 in cList and (idx2 < idx1):
                        cList.remove(test2)
                    else:
                        return False

                elif 'EQ' in tempList[i]:
                    test1 = [x if x != "EQ" else "GE" for x in tempList[i]]
                    test2 = [x if x != "EQ" else "LE" for x in tempList[i]]

                    try:
                        idx1 = cList.index(test1)
                    except:
                        idx1 = 999999999

                    try:
                        idx2 = cList.index(test2)
                    except:
                        idx2 = 999999999

                    if test1 in cList and (idx1 < idx2):
                        cList.remove(test1)
                    elif test2 in cList and (idx2 < idx1):
                        cList.remove(test2)
                    else:
                        return False

            elif 'Parameter' not in tempList[i]: #non var match
                return False

            else:
                pass

            i = i + 1

        if foundVar:
            return True
        else:
            return False


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

