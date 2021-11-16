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


def compareFoundRuleCounts(countDF, name):
    cdf = countDF.sort_values("Client Count", ascending=False)

    plt.figure(figsize=(12, 7))
    plt.plot(cdf['Client Count'].values, label='Client')
    plt.plot(cdf['LDP Count'].values, label='LDP')
    plt.legend()
    plt.xlabel("Rule Number")
    plt.ylabel("Percent Count")
    plt.title("Comparison of Percent Count Scores in Found Rules")
    plt.savefig(name + "FoundRulePercentCountComparison")
    plt.show()

    plt.figure(figsize=(12, 7))
    error = abs(cdf['Client Count'].values - cdf['LDP Count'].values)
    plt.plot(error)
    plt.xlabel("Rule Number")
    plt.ylabel("Error Percentage")
    plt.title("Error in Percent Count Scores in Found Rules - sorted by highest client count to lowest")
    plt.savefig(name + "PercentCountError")
    plt.show()


# Get count of the number of true structures matched in client rules
def getTemplateNodes(temp):
    nodes = []

    for node in temp.expand_tree(mode=treelib.Tree.DEPTH, sorting=True):
        n = re.sub('[0-9]', '', node)
        nodes.append(n)

    return nodes

def findRuleMatch(template, clientTrees):
    ldpNodes = getTemplateNodes(template)
    ldpVars = template.getAllVars()

    for c in clientTrees:
        # check if variables in rule
        clVars = c.getAllVars()
        hasVars = True
        for v in ldpVars:
            if v not in clVars:
                hasVars = False

        if hasVars:
            # check for structural match
            clientNodes = []

            for node in c.expand_tree(mode=treelib.Tree.DEPTH, sorting=True):
                n = re.sub('[0-9]', '', node)
                clientNodes.append(n)

            # print("client nodes", clientNodes)
            if nodeListMatch(ldpNodes, clientNodes):
                return True, c.toString()  # found match

    return False, None


# check for match  between two lists of template nodes + client nodes
def nodeListMatch(tempList, cList):
    # Fix relop matches
    tempList[:] = [x if x != "LT" else "LE" for x in tempList]
    tempList[:] = [x if x != "GT" else "GE" for x in tempList]
    cList[:] = [x if x != "LT" else "LE" for x in cList]
    cList[:] = [x if x != "GT" else "GE" for x in cList]

    i = 0
    while i < len(tempList):
        if tempList[i] in cList:
            idx = cList.index(tempList[i])  # get idx of element of cList
            cList = cList[idx + 1:]
        else:
            return False

        i = i + 1

    return True


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
        fnd, cRule = findRuleMatch(l, clientTrees)
        if fnd:  # check structural match --> will count partial matches as a full match
            foundRules += 1
            lCount = ldpDF[ldpDF["Rule"] == l.toString()]['Percent Count'].item()
            cCount = clientDF[clientDF["Rule"] == cRule]['Percent of Population'].item()
            matchLst.append([l.toString(), cRule, lCount, cCount])
        else:
            nonRules += 1

    lst = [len(clientRules), foundRules, nonRules, foundRules / (foundRules + nonRules)]
    covDF = pd.DataFrame([lst], columns=["Total Client Rules", "Found Rules", "Non Rules", "Precision"])

    # Make DF that compares the count percentages of the ldp and client rules that were found
    countDF = pd.DataFrame(matchLst, columns=['LDP Rule', 'Client Rule', "LDP Count", "Client Count"])

    return covDF, countDF

def graphRuleCounts(clientDF, ldpDF, name):
    plt.figure(figsize=(12, 7))
    sns.distplot(clientDF['Percent of Population'].values, bins=1000, kde=True, label='Client')
    sns.distplot(ldpDF['Percent Count'].values, bins=1000, kde=True, label='LDP')
    plt.legend()
    plt.xscale('log')
    plt.xlabel("Percent of Population")
    plt.ylabel("Number of Rules")
    plt.savefig(name + "Distplot")
    plt.show()
    ##########

    cdf = dict(Counter(clientDF['Percent of Population']))
    cdf = dict(sorted(cdf.items(), key=operator.itemgetter(0), reverse=True))
    ldf = dict(Counter(ldpDF['Percent Count']))
    ldf = dict(sorted(ldf.items(), key=operator.itemgetter(0), reverse=True))

    plt.figure(figsize=(12, 7))
    plt.xscale('log')
    plt.yscale('log')
    plt.plot(cdf.keys(), cdf.values(), label='Client')
    plt.plot(ldf.keys(), ldf.values(), label='LDP')
    plt.legend()
    plt.xlabel("Percent of Population")
    plt.ylabel("Number of Rules")
    plt.savefig(name + "LineGraph")
    plt.show()




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
        strRl = re.sub('>=', '>', strRl)
        strRl = re.sub('<=', '<', strRl)

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
            strRl = re.sub('>=', '>', strRl)
            strRl = re.sub('<=', '<', strRl)
            ruleSet.append(strRl)

        file.close()
        return True, ruleTrees, ruleSet

    except:
        print("File not found for Client %d" % (num))
        return False, ruleTrees, ruleSet
