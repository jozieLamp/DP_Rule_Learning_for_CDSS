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

#Get count of coverage
def getCoverageTable(thresh, ldpDF, ldpTrees, clientDF):
    stlFac = STLFactory()

    # Get client rules above the threshold
    # df = clientDF[clientDF['Percent of Population'] >= thresh]
    clientRules = clientDF['Rule'].tolist()

    # From client rules, first make client trees
    clientTrees = []
    for c in clientRules:
        c = stlFac.constructFormulaTree(c + "\n")
        clientTrees.append(c)

    ## MAKE MAIN COVERAGE TABLE
    # Calculate num true rules, num false rules and precision (true rules / total rules found)
    foundRules = 0
    nonRules = 0
    matchLst = []
    nonRuleLst = []
    clientRulesFound = []

    for l in ldpTrees:
        # print("\nTemplate", l.toString(), "Per Count", ldpDF[ldpDF["Rule"] == l.toString()]['Percent Count'].item())

        cRule, cCount = findRuleMatch(l, clientTrees, clientDF)

        if cRule != None:  # check structural match
            if cRule not in clientRulesFound:
                clientRulesFound.append(cRule)
                foundRules += 1
                # print(l.toString())
                # print(ldpDF[ldpDF["Rule"] == l.toString()]['Percent Count'])
                lCount = ldpDF[ldpDF["Rule"] == l.toString()]['Percent Count'].item()
                # cCount = clientDF[clientDF["Rule"] == cRule]['Percent of Population'].item()
                matchLst.append([l.toString(), cRule, lCount, cCount])
        else:
            # print("LDP RULE NOT FOUND", l.toString())
            nonRuleLst.append(l.toString())
            nonRules += 1

    #Adjust overestimates of found rules
    if foundRules > len(clientRules):
        foundRules = len(clientRules)

    bot = foundRules + nonRules
    prec = foundRules / bot if bot else 0
    lst = [len(clientRules), foundRules, nonRules, prec]
    covDF = pd.DataFrame([lst], columns=["Total Client Rules", "Found Rules", "Non Rules", "Precision"])

    #Print missed client rules
    missedRules = np.setdiff1d(clientRules, clientRulesFound)
    # print("Missed Client Rules:")
    # print(missedRules)

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
    lst = [len(clientStructs), foundStructs, nonStructs, prec]
    structDF = pd.DataFrame([lst], columns=["Total Client Structures", "Found Structures", "Non Structures", "Precision"])

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

# def findRuleMatch(template, clientTrees, ldpDF, clientDF):
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

def plotQueryAnalysisPrivate(df, save):

    #Plot percentage found rules
    for q in sorted(list(set(df['Queries']))):
        qDF = df.loc[df['Queries'] == q]

        # Plot Rules
        plt.figure(figsize=(12, 7))
        plt.title("Percentage Found Client Rules for " + str(q) + " Queries")

        for method in sorted(list(set(qDF['Method']))):
            miniDF = qDF.loc[qDF['Method'] == method]
            eps = miniDF['Epsilon']
            rls = miniDF['Percentage Found Rules']
            plt.plot(eps, rls, label="Method: " + method)

        plt.xlabel("Epsilon")
        plt.ylabel("Percentage Found Client Client Rules")
        plt.xscale('log')
        plt.legend()
        save = save.replace(".", "-")
        plt.savefig(save + str(q) + "Queries_Percent_Found_Client_Rules")
        plt.show()

    # Plot percentage found structures
    for q in sorted(list(set(df['Queries']))):
        qDF = df.loc[df['Queries'] == q]

        # Plot Rules
        plt.figure(figsize=(12, 7))
        plt.title("Percentage Found Client Structures for " + str(q) + " Queries")

        for method in sorted(list(set(qDF['Method']))):
            miniDF = qDF.loc[qDF['Method'] == method]
            eps = miniDF['Epsilon']
            rls = miniDF['Percentage Found Structures']
            plt.plot(eps, rls, label="Method: " + method)

        plt.xlabel("Epsilon")
        plt.ylabel("Percentage Found Client Structures")
        plt.xscale('log')
        plt.legend()
        save = save.replace(".", "-")
        plt.savefig(save + str(q) + "Queries_Percent_Found_Client_Structures")
        plt.show()

    # Plot Rule Precision
    for q in sorted(list(set(df['Queries']))):
        qDF = df.loc[df['Queries'] == q]

        # Plot Rules
        plt.figure(figsize=(12, 7))
        plt.title("Rule Precision for " + str(q) + " Queries")

        for method in sorted(list(set(qDF['Method']))):
            miniDF = qDF.loc[qDF['Method'] == method]
            eps = miniDF['Epsilon']
            rls = miniDF['Rule Precision']
            plt.plot(eps, rls, label="Method: " + method)

        plt.xlabel("Epsilon")
        plt.ylabel("Rule Precision")
        plt.xscale('log')
        plt.legend()
        save = save.replace(".", "-")
        plt.savefig(save + str(q) + "Queries_Rule_Precision")
        plt.show()

    # Plot Structure Precision
    for q in sorted(list(set(df['Queries']))):
        qDF = df.loc[df['Queries'] == q]

        # Plot Rules
        plt.figure(figsize=(12, 7))
        plt.title("Structure Precision for " + str(q) + " Queries")

        for method in sorted(list(set(qDF['Method']))):
            miniDF = qDF.loc[qDF['Method'] == method]
            eps = miniDF['Epsilon']
            rls = miniDF['Structure Precision']
            plt.plot(eps, rls, label="Method: " + method)

        plt.xlabel("Epsilon")
        plt.ylabel("Structure Precision")
        plt.xscale('log')
        plt.legend()
        save = save.replace(".", "-")
        plt.savefig(save + str(q) + "Queries_Structure_Precision")
        plt.show()

    #TODO - note, may not need these ones
    # Plot Total Found Rules
    for q in sorted(list(set(df['Queries']))):
        qDF = df.loc[df['Queries'] == q]

        # Plot Rules
        plt.figure(figsize=(12, 7))
        plt.title("Total Found Rules for " + str(q) + " Queries")

        for method in sorted(list(set(qDF['Method']))):
            miniDF = qDF.loc[qDF['Method'] == method]
            eps = miniDF['Epsilon']
            rls = miniDF['Found Rules']
            plt.plot(eps, rls, label="Method: " + method)

        plt.xlabel("Epsilon")
        plt.ylabel("Total Found Rules")
        plt.xscale('log')
        plt.legend()
        save = save.replace(".", "-")
        plt.savefig(save + str(q) + "Queries_Found_Rules")
        plt.show()

    # Plot Total Non Rules
    for q in sorted(list(set(df['Queries']))):
        qDF = df.loc[df['Queries'] == q]

        # Plot Rules
        plt.figure(figsize=(12, 7))
        plt.title("Total Non Rules for " + str(q) + " Queries")

        for method in sorted(list(set(qDF['Method']))):
            miniDF = qDF.loc[qDF['Method'] == method]
            eps = miniDF['Epsilon']
            rls = miniDF['Non Rules']
            plt.plot(eps, rls, label="Method: " + method)

        plt.xlabel("Epsilon")
        plt.ylabel("Total Non Rules")
        plt.xscale('log')
        plt.legend()
        save = save.replace(".", "-")
        plt.savefig(save + str(q) + "Queries_Non_Rules")
        plt.show()

    # Plot summary of found rules, non rules for each eps
    for q in sorted(list(set(df['Queries']))):
        qDF = df.loc[df['Queries'] == q]
        methods = sorted(list(set(qDF['Method'])))
        epsilons = sorted(list(set(qDF['Epsilon'])))

        # plt.figure(figsize=(12, 7))
        fig, axes = plt.subplots(figsize=(20,7), nrows=1, ncols=len(methods))
        # plt.title("Rule Summary for " + str(q) + " Queries")
        ax_position = 0
        for concept in methods:
            # idx = pd.IndexSlice
            # subset = df.loc[idx[[concept], :],
            #                 ['Found Rules', 'Non Rules']]
            subset = qDF.loc[qDF['Method'] == concept][['Found Rules', 'Non Rules']]
            print(subset.info())
            # subset = subset.groupby(
            #     subset.index.get_level_values('datetime').year).sum()

            # ax = subset.plot(kind="bar", stacked=True, colormap="Blues",ax=axes[ax_position])
            ax = subset.plot(kind="bar", stacked=True, ax=axes[ax_position])


            if concept == methods[0]:
                ax.set_ylabel("Total Rules")
            if concept == methods[-1]:
                ax.legend(['Found Rules', 'Non Rules'], loc='upper right')

            ax.set_title(concept)
            ax.set_xlabel("Epsilon")
            # ax.set_title("Concept \"" + concept + "\"", fontsize=30, alpha=1.0)
            # ax.set_ylabel("Total Rules", fontsize=30)
            # ax.set_xlabel("Concept \"" + concept + "\"", fontsize=30, alpha=0.0)

            # ax.set_ylim(0, 9000)
            # ax.set_yticks(range(0, 9000, 1000))
            # ax.set_yticklabels(labels=range(0, 9000, 1000), rotation=0,
            #                    minor=False, fontsize=28)
            ax.set_xticklabels(labels=epsilons, rotation=0,minor=False)
            handles, labels = ax.get_legend_handles_labels()
            ax_position += 1


        # for method in sorted(list(set(qDF['Method']))):
        #     miniDF = qDF.loc[qDF['Method'] == method]
        #     eps = miniDF['Epsilon']
        #     rls = miniDF['Percentage Found Rules']
        #     plt.plot(eps, rls, label="Method: " + method)
        #
        # plt.xlabel("Epsilon")
        # plt.ylabel("Percentage Found Client Client Rules")
        # plt.xscale('log')
        # plt.legend()
        save = save.replace(".", "-")
        fig.savefig(save + str(q) + "Queries_Summary_Rules_Nonrules")
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