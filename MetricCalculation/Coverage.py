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
warnings.filterwarnings("ignore")
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

#Get count of coverage
def getCoverageTable(clientDF, ldpDF, ldpTrees, cutoff=0.0):
    stlFac = STLFactory()

    # Get client rules above the threshold
    cdf = clientDF[clientDF['Percent of Population'] > cutoff]
    clientRules = cdf['Rule'].tolist()
    print("Total Client Rules", len(clientDF))
    print("Total Client Rules at Cutoff Thresh", len(cdf))

    # From client rules, first make client trees
    clientTrees = []
    for c in clientRules:
        c = stlFac.constructFormulaTree(c + "\n")
        clientTrees.append(c)

    clientTrees_full = []
    for c in clientDF['Rule'].tolist():
        c = stlFac.constructFormulaTree(c + "\n")
        clientTrees_full.append(c)

    ## MAKE MAIN COVERAGE TABLE
    # Calculate num true rules, num false rules and precision (true rules / total rules found)
    foundRules = 0
    nonRules = 0
    matchLst = []
    nonRuleLst = []
    clientRulesFound = []

    for l in ldpTrees:
        # print("\nTemplate", l.toString(), "Per Count", ldpDF[ldpDF["Rule"] == l.toString()]['Percent Count'].item())

        cRule, cCount = findRuleMatch(l, clientTrees, cdf)

        if cRule != None:  # check structural match
            if cRule not in clientRulesFound:
                clientRulesFound.append(cRule)
                foundRules += 1
                # print(l.toString())
                # print(ldpDF[ldpDF["Rule"] == l.toString()]['Percent Count'])
                try:
                    lCount = ldpDF[ldpDF["Rule"] == l.toString()]['Percent Count'].item()
                except:
                    lCount = 0
                # cCount = clientDF[clientDF["Rule"] == cRule]['Percent of Population'].item()
                matchLst.append([l.toString(), cRule, lCount, cCount])
        else:
            # Check to make sure rule just not < thresh
            cRule, cCount = findRuleMatch(l, clientTrees_full, clientDF)

            if cRule != None:
                pass
            else:
                # print("LDP RULE NOT FOUND", l.toString())
                nonRuleLst.append(l.toString())
                nonRules += 1

    # print("Total found LDP rules", foundRules)

    #Double check missed client rules actually missed and not semantic match in ldp rule set
    missedRules = list(np.setdiff1d(clientRules, clientRulesFound))
    for mr in missedRules:

        # From client rule, first make client tree
        m = stlFac.constructFormulaTree(mr + "\n")

        # print("m", m.toString())
        cRule_thresh, cCount_thresh = findClientRuleMatch(m, ldpTrees, cdf)
        cRule, cCount = findClientRuleMatch(m, ldpTrees, clientDF)

        # print(cRule)
        if cRule != None or cRule_thresh != None:
            foundRules += 1
            missedRules.remove(mr)

    # if missedRules != []:
    #     print("Missed Client Rules:")
    #     print(missedRules)

    #Adjust overestimates of found rules from double rules (same rule twice)
    if foundRules > len(clientRules):
        foundRules = len(clientRules)

    bot = foundRules + nonRules
    prec = foundRules / bot if bot else 0
    cov = foundRules / len(clientRules)
    lst = [len(clientRules), foundRules, nonRules, prec, cov]
    covDF = pd.DataFrame([lst], columns=["Total Client Rules", "Found Rules", "Non Rules", "Precision", "Coverage"])

    #Make DF
    nrDF = pd.DataFrame(nonRuleLst, columns=['Non Rules'])
    missedCR = pd.DataFrame(missedRules, columns=['Missed Client Rules'])

    ## MAKE COUNT DF
    # Make DF that compares the count percentages of the ldp and client rules that were found
    countDF = pd.DataFrame(matchLst, columns=['LDP Rule', 'Client Rule', "LDP Count", "Client Count"])

    return covDF, countDF, nrDF, missedCR, clientTrees

def countUniqueStructuresNoVars(clientTrees, ldpTrees):
    ## MAKE STRUCTURE DF
    # Count unique structures with no vars
    clientStructs = getUniqueStructures(clientTrees)
    ldpStructs = getUniqueStructures(ldpTrees)
    # clientStrings = [x.toString() for x in clientStructs]

    # Check if find all client structures
    foundStructs = 0
    nonStructs = 0
    for l in clientStructs:
        cRule, cCount = findRuleMatch(l, ldpStructs, None)
        if cRule != None:  # check structural match
            foundStructs += 1
        else:
            pass
            # print("CLIENT STRUCT NOT FOUND", l.toString())

    # Count non structs from LDP
    for l in ldpStructs:
        cRule, cCount = findRuleMatch(l, clientStructs, None)
        if cRule == None:  # check structural match
            # print("LDP STRUCT NOT FOUND", l.toString())
            nonStructs += 1

    bot = foundStructs + nonStructs
    prec = foundStructs / bot if bot else 0
    cov = foundStructs / len(clientStructs)
    lst = [len(clientStructs), foundStructs, nonStructs, prec, cov]
    structDF = pd.DataFrame([lst], columns=["Total Strcts", "Found", "Non Strts", "Precision", "Coverage"])

    return structDF

def getUniqueStructures(trees):
    structs = []
    strings = []
    for lt in trees:
        l = copy.deepcopy(lt)
        l.getFormulaNoVars()
        if l.toString() not in strings:
            strings.append(l.toString())
            structs.append(l)

    return structs


def findRuleMatch(template, clientTrees, clientDF):
    cCount = None

    rule = queryStructuralFullMatch(template, clientTrees)

    if rule != None:
        # print("Full Match Found")
        rule = rule.toString()
        try:
            cCount = clientDF[clientDF["Rule"] == rule]['Percent of Population'].item()
        except:
            pass

    return rule, cCount

def findClientRuleMatch(template, ldpTrees, clientDF):
    cCount = None

    rule = queryStructuralFullMatch(template, ldpTrees)

    if rule != None:
        # print("Full Match Found")
        rule = rule.toString()
        try:
            cCount = clientDF[clientDF["Rule"] == rule]['Percent of Population'].item()
        except:
            pass

    return rule, cCount


# TODO - delete this?
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

def getClientRuleMatch(clientRule, ldpTrees):
    client = Client(clientNum=1, epsilon='inf', ruleSet=ldpTrees)
    server = Server(clientList=[], varDict={}, params=None)

    clientNodes = server.getTemplateNodes(clientRule)
    clientVars = clientRule.getAllVars()

    r = client.queryStructuralRuleMatchReturn(ldpNodes, ldpVars)


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

#Plot LDP vs percent client counts of rules
def plotLDPClientCounts(clientDF, countDF, save, title):
    lst = []
    for idx, row in clientDF.iterrows():
        lst.extend([row['Percent of Population'] for i in range(row['Rule Count'])])

    n_bins = 10
    plt.figure(figsize=(12, 7))
    # plt.hist([lst, countDF['LDP Count'].values], n_bins, density=True, histtype='bar', label=['Client', 'LDP'])
    plt.hist([lst, countDF['LDP Count'].values], n_bins, density=False, histtype='bar', label=['Client', 'LDP'])

    plt.title(title + " Population Percentage Comparison")
    plt.xlabel("Percentage of Population")
    plt.ylabel("Number of Rules")
    plt.yscale('log')
    plt.legend()
    save = save.replace(".", "-")
    plt.savefig(save + "_Pop_Percent_Comparison")

    # plt.show()

def plotQueryAnalysis(df, save):
    #Plot Rules
    rules = df["Percentage Found Rules"]
    queries = df["Queries"]

    plt.figure(figsize=(12, 7))
    plt.title("Rule Coverage Query Analysis")
    # plt.axhline(y=999, color='r', linestyle='-', label='Total Client Rules')
    plt.plot(queries, rules, label='Baseline')
    # plt.plot(queriesCov, rulesCov, label='Coverage')
    plt.xlabel("Number of Queries")
    plt.ylabel("Number of Rules")
    plt.legend()
    plt.savefig(save + " Rule_Query_Analysis")
    plt.show()

    #Plot Structures
    structs = df["Percentage Found Structures"]

    plt.figure(figsize=(12, 7))
    plt.title("Structure Coverage Query Analysis")
    # plt.axhline(y=999, color='r', linestyle='-', label='Total Client Rules')
    plt.plot(queries, structs, label='Baseline')
    # plt.plot(queriesCov, rulesCov, label='Coverage')
    plt.xlabel("Number of Queries")
    plt.ylabel("Number of Structures")
    plt.legend()
    plt.savefig(save + "Structure_Query_Analysis")
    plt.show()

def plotQueryAnalysisPrivate(df, save, value):
    cps = sorted(list(set(df['Cp'])))
    lambdas = sorted(list(set(df['Lambda'])))

    plt.figure(figsize=(12, 7))
    plt.title(value)
    for cp in cps:
        for l in lambdas:
            miniDF = df.loc[df['Cp'] == cp]
            miniDF = miniDF.loc[df['Lambda'] == l]
            # eps = miniDF['Epsilon']
            # rls = miniDF[value]
            #             plt.plot(eps, rls, label="Cp: " + cp + "; Lambda: " + l)
            sns.lineplot(data=miniDF, x="Epsilon", y=value, label="Cp: " + cp + "; Lambda: " + l)

    plt.xlabel("Epsilon")
    plt.ylabel(value)
    plt.xscale('log')
    plt.legend()

    save = save.replace(".", "-")
    plt.savefig(save + value)
    plt.show()


def summaryPrivRules(df, save):
    cps = sorted(list(set(df['Cp'])))
    lambdas = sorted(list(set(df['Lambda'])))
    epsilons = sorted(list(set(df['Epsilon'])))

    maxFR = max(df['Found Rules'])
    maxNR = max(df['Non Rules'])
    maxRules = maxFR + maxNR

    fig, axes = plt.subplots(figsize=(20, 20), nrows=len(cps), ncols=len(lambdas))
    row = 0
    col = 0
    for c in cps:
        col = 0
        for l in lambdas:
            cpdf = df.loc[df['Cp'] == c]
            subset = cpdf.loc[df['Lambda'] == l][['Found Rules', 'Non Rules']]
            FRErr = cpdf.loc[df['Lambda'] == l]['Found Rules Std']
            NRErr = cpdf.loc[df['Lambda'] == l]['Non Rules Std']

            ax = subset.plot(kind="bar", stacked=True, yerr=[FRErr, NRErr], ax=axes[row, col])

            ax.set_ylabel("Total Rules")
            ax.legend(['Found Rules', 'Non Rules'], loc='upper right')

            ax.set_title("Cp: " + c + "; Lambda: " + l)
            ax.set_xlabel("Epsilon")
            ax.set_ylim(0, maxRules)

            ax.set_xticklabels(labels=epsilons, rotation=0, minor=False)
            handles, labels = ax.get_legend_handles_labels()
            col += 1
        row += 1
    fig.tight_layout()
    save = save.replace(".", "-")
    fig.savefig(save + "Summary_Rules_Nonrules")
    fig.show()


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



def loadClientRules(popSize, dataFilename, cutoff=0.0):
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

    print("clients added", clientsAdded)

    # get nonduplicate list of trees
    currRls = []
    ct = []
    for t in clientTrees:
        strRl = t.toString()
        # strRl = re.sub(' = ', '>=', strRl)
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

    # Drop rules below cutoff thresh
    clientDF = clientDF[clientDF['Percent of Population'] > cutoff]

    return clientDF

def loadRuleSet(num, textfile):
    ruleSet = []
    ruleTrees = []
    stlFac = STLFactory()
    try:
        file = open(textfile, "r")
        for line in file:
            if line[0] == "(" and line[-2] == ")":
                line = line[1:-2] + "\n"
            # line = re.sub(' = ', '>=', line)
            line = re.sub('e-', '', line)  # fix issue where scientific notation confuses matching

            rule = stlFac.constructFormulaTree(line+"\n")
            rule.getFormulaNoParams()

            ruleTrees.append(rule)

            # fix relop for string rule
            strRl = rule.toString()
            # strRl = re.sub('>=', '>', strRl)
            # strRl = re.sub('<=', '<', strRl)

            if " = " not in strRl:
                ruleSet.append(strRl)

        file.close()
        return True, ruleTrees, ruleSet

    except:
        print("File not found for Client %d" % (num))
        return False, ruleTrees, ruleSet