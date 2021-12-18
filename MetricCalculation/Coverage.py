#Coverage Metrics

from SignalTemporalLogic.STLFactory import STLFactory
import matplotlib.pyplot as plt
plt.rc('font', size=12)
import copy
import pandas as pd
import seaborn as sns
import numpy as np
from collections import Counter
import operator
import warnings
import treelib
import re
from Client import Client
from Server import Server


def getClientTreesFromCountDF(df):
    stlFac = STLFactory()
    clTrees = []
    for c in df['Client Rule'].tolist():
        c = stlFac.constructFormulaTree(c + "\n")
        clTrees.append(c)

    return clTrees

def countUniqueStructuresNoVars(ldpTrees):
    lst = []
    for lt in ldpTrees:
        l = copy.deepcopy(lt)
        l.getFormulaNoVars()
        lst.append(l.toString())

    # print("total structs to start", len(ldpTrees))
    uniqStrcts = set(lst)
    # print("unique structs", len(uniqStrcts))

    return len(uniqStrcts)

#Get count of coverage
def getCoverageTable(thresh, ldpDF, ldpTrees, clientDF):
    stlFac = STLFactory()

    # Get client rules above the threshold
    df = clientDF[clientDF['Percent of Population'] >= thresh]
    clientRules = df['Rule'].tolist()

    # From client rules, first make client trees
    clientTrees = []
    for c in clientRules:
        c = stlFac.constructFormulaTree(c + "\n")
        clientTrees.append(c)

    # Calculate num true rules, num false rules and precision (true rules / total rules found)
    foundRules = 0
    nonRules = 0
    matchLst = []

    for l in ldpTrees:
        print("\nTemplate", l.toString(), "Per Count", ldpDF[ldpDF["Rule"] == l.toString()]['Percent Count'].item())

        #TODO- figure out why returning partial matches when should only ret full ones ...
        cRule, cCount = findRuleMatch(l, clientTrees, ldpDF, clientDF)

        if cRule != None:  # check structural match --> will count partial matches as a full match
            foundRules += 1
            # print(l.toString())
            # print(ldpDF[ldpDF["Rule"] == l.toString()]['Percent Count'])
            lCount = ldpDF[ldpDF["Rule"] == l.toString()]['Percent Count'].item()
            # cCount = clientDF[clientDF["Rule"] == cRule]['Percent of Population'].item()
            matchLst.append([l.toString(), cRule, lCount, cCount])
        else:
            print("RULE NOT FOUND", l.toString())
            nonRules += 1

    bot = foundRules + nonRules
    prec = foundRules / bot if bot else 0
    lst = [len(clientRules), foundRules, nonRules, prec]
    covDF = pd.DataFrame([lst], columns=["Total Client Rules", "Found Rules", "Non Rules", "Precision"])

    # Make DF that compares the count percentages of the ldp and client rules that were found
    countDF = pd.DataFrame(matchLst, columns=['LDP Rule', 'Client Rule', "LDP Count", "Client Count"])

    return covDF, countDF

def findRuleMatch(template, clientTrees, ldpDF, clientDF):
    rule = queryStructuralFullMatch(template, clientTrees)

    if rule != None:
        print("Full Match Found")
        rule = rule.toString()
        cCount = clientDF[clientDF["Rule"] == rule]['Percent of Population'].item()

    # else: #try partial match
    #     print("full match not found, trying partial match")
    #     partials = queryPartialStructuralMatch(template, clientTrees, clientDF)
    #
    #     if partials != None:
    #         key = list(partials.keys())[0]
    #         for k in partials.keys():
    #             if partials[k][1] > partials[key][1]:
    #                 key = k
    #
    #         rule, cCount = partials[key]
    #         rule = rule.toString()
    #     else:
    #         rule = None
    #         cCount = None

    else:
        rule = None
        cCount = None


    return rule, cCount

def queryPartialStructuralMatch(template, clientTrees, clientDF):
    partials = {} #dict of partial match rules and their counts
    tempOps = template.getOperators()
    varList = template.getAllVars()
    # print("temp ops", tempOps)
    # print(template.toString())

    # print("Doing partial match")

    for r in clientTrees:
        # first check for overall order of operators correct
        clientOps = r.getOperators()

        rVars = r.getAllVars()
        if any(item in varList for item in rVars) and operatorMatch(tempOps, clientOps):  # found operator match
            # print("partial match", r.toString())
            for v in varList:
                if v in rVars:
                    cCount = clientDF[clientDF["Rule"] == r.toString()]['Percent of Population'].item()
                    partials[v] = [r, cCount]

        if set(partials.keys()) == set(varList):
            return partials

    return None

def queryStructuralFullMatch(template, clientTrees):

    client = Client(clientNum=1, epsilon='inf', ruleSet=clientTrees)
    server = Server(clientList=[], varDict={}, params=None)

    # print("Temp vars", varList)
    # print("\ntemp", template.toString())
    ldpNodes = server.getTemplateNodes(template)
    ldpVars = template.getAllVars()

    # print("templt nodes", ldpNodes)

    r = client.queryStructuralRuleMatchReturn(ldpNodes, ldpVars)

    return r




#Load LDP rules
def loadLDPRuleset(resultsFilename):
    ldpDF = pd.read_csv(resultsFilename, index_col=0)

    ldpTrees = []
    ldpRules = []

    stlFac = STLFactory()
    for r in ldpDF['Rule']:
        rule = stlFac.constructFormulaTree(r + "\n")
        rule.getFormulaNoParams()

        ldpTrees.append(rule)
        ldpRules.append(rule.toString())


    ldpDF['Rule'] = ldpRules

    ldpDF['Percent Count'][ldpDF['Percent Count'] > 1.0] = 1.0
    ldpDF['Percent Count'] = ldpDF['Percent Count'].round(3)

    ldpDF = ldpDF.sort_values("Percent Count", ascending=False)


    return ldpDF, ldpTrees, ldpRules

def loadClientRules(popSize, dataFilename):
    clientRules = []
    clientTrees = []
    num = 1
    clientsAdded = 0
    while clientsAdded < popSize:
        fileName = dataFilename + repr(num) + "Rules.txt"
        fileFound, trees, rls = loadRuleSet(num, fileName)
        # c.logRuleSet()
        if fileFound:
            clientsAdded += 1
            clientTrees.extend(trees)
            clientRules.extend(rls)

        num += 1

        # get nonduplicate list of trees
    currRls = []
    ct = []
    for t in clientTrees:
        strRl = t.toString()
        # strRl = re.sub('>=', '>', strRl)
        # strRl = re.sub('<=', '<', strRl)

        if strRl not in currRls:
            ct.append(t)
            currRls.append(strRl)

    # Make dataframe of rules and their counts
    clientDF = pd.DataFrame.from_dict(dict(Counter(clientRules)), orient='index').reset_index()
    clientDF.columns = ["Rule", "Rule Count"]
    clientDF['Percent of Population'] = clientDF['Rule Count'] / popSize
    clientDF = clientDF.sort_values("Rule Count", ascending=False)
    #Fix counts > 100%
    clientDF['Percent of Population'][clientDF['Percent of Population'] > 1.0] = 1.0

    return ct, clientRules, clientDF

def loadRuleSet(num, textfile):
    ruleSet = []
    ruleTrees = []
    stlFac = STLFactory()
    try:
        file = open(textfile, "r")
        for line in file:
            if line[0] == "(" and line[-2] == ")":
                line = line[1:-2] + "\n"

            rule = stlFac.constructFormulaTree(line+"\n")
            rule.getFormulaNoParams()

            ruleTrees.append(rule)

            # fix relop for string rule
            strRl = rule.toString()
            # strRl = re.sub('>=', '>', strRl)
            # strRl = re.sub('<=', '<', strRl)
            ruleSet.append(strRl)

        file.close()
        return True, ruleTrees, ruleSet

    except:
        print("File not found for Client %d" % (num))
        return False, ruleTrees, ruleSet