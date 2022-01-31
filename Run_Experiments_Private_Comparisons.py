from MetricCalculation import Coverage as cov
from MetricCalculation import RuleQuality as RQ
import params
import logging
from Client import Client
from Server import Server
import pandas as pd
import math
import warnings
warnings.filterwarnings('ignore')

def main():
    #Main params
    dataset = 'ICU'
    mctsType = 'Breadth'
    computeRQ = True
    params.popSize = 10

    #Load client rules
    clientTrees, clientRules, clientDF = cov.loadClientRules(params.popSize, params.dataFilename)

    #Load client rule quality data and dataframes
    if computeRQ:
        clientData, clientLabels, clientCM, clientPtCM = loadClientQualityDFs(mctsType, params.popSize, clientRules)


    coverageLst = []
    qualLst = []
    # numQueries = list(range(10000,0,-100))
    numQueries = [1000]
    budgets= [1000, 100, 10, 1, 0.1, 0.01, 0.001]

    cps = ['basic', 'beta', 'eps']
    # prunes = ['basic', 'zero', 'small', 'beta', 'activeClients']
    prunes = ['basic', 'one', 'small']



    for cpMethod in cps:
        for pruneMethod in prunes:
            # adjust name of cp method for prunes
            cpMethodName = cpMethod + "_Prune" + pruneMethod

            for nq in numQueries:
                for eps in budgets:
                    # Update params
                    if cpMethod == 'basic':
                        params.cp = 1 / math.sqrt(2)
                    #Adapt Cp as a function of beta --> more noise should favor higher match scores over more breadth searching
                    elif cpMethod == 'beta': #just set cp to beta (budget/query)
                        params.cp = eps / nq
                    elif cpMethod == 'eps': #set to epsilon
                        params.cp = eps

                    if pruneMethod == 'basic':
                        params.cutoffThresh = 0.01
                    elif pruneMethod == 'zero':
                        params.cutoffThresh = 0
                    elif pruneMethod == 'one':
                        params.cutoffThresh = 0.001
                    elif pruneMethod == 'small':
                        params.cutoffThresh = 0.0001
                    elif pruneMethod == 'beta':
                        params.cutoffThresh = eps / nq
                    elif pruneMethod == 'activeClients': #only prune when active clients at 0
                        params.cutoffThresh = -10000


                    params.maxQueries = nq
                    params.epsilon = eps
                    params.name = "Cp" + cpMethodName + "_Queries" + str(nq) + "_Eps" + str(eps)
                    params.resultsFilename = "Results/Private/"+ dataset + "/" + mctsType + "/Cp" + cpMethodName + "_Queries" + str(nq) + "_Eps" + str(eps)

                    print("\n\n**************** CP: " + cpMethodName + "; QUERIES:", params.maxQueries, "; EPSILON: ", params.epsilon, "****************")
                    #Run protocol
                    runProt(params)

                    ## COVERAGE EXPs
                    ldpRules, covDF, structDF = calcIndivCoverage(clientDF)

                    #Add results to list
                    lst = [cpMethodName, nq, eps, covDF['Total Client Rules'].item(), covDF['Found Rules'].item()/covDF['Total Client Rules'].item() ,covDF['Found Rules'].item(), covDF['Non Rules'].item(),
                           covDF['Precision'].item(),structDF['Total Client Structures'].item(), structDF['Found Structures'].item()/structDF['Total Client Structures'].item(),
                           structDF['Found Structures'].item(), structDF['Non Structures'].item(),
                           structDF['Precision'].item()]

                    print("LST", lst)
                    coverageLst.append(lst)

                    ## RULE QUALITY EXPS
                    if computeRQ:
                        ldpCM, ldpPtCM = calcIndivRuleQuality(ldpRules, clientData, clientLabels)

                        # Add results to list
                        q = [cpMethodName, nq, eps, ldpCM['Precision'].item(), ldpCM['Accuracy'].item(), ldpPtCM['Precision'].item(), ldpPtCM['Accuracy'].item()]
                        qualLst.append(q)
                        print("Current qual list", qualLst)


    #Make final result DFs
    #Coverage DF
    df = pd.DataFrame(coverageLst, columns=["Method", "Queries", "Epsilon", "Total Client Rules", "Percentage Found Rules", "Found Rules", "Non Rules", "Rule Precision",
                    "Total Client Structures","Percentage Found Structures", "Found Structures", "Non Structures", "Structure Precision"])
    df.to_csv("Results/Private/"+ dataset + "/" + mctsType + "/Coverage/CoverageSummaryDF.csv")
    print("COVERAGE DF:")
    print(df)

    # Make graphs of query analysis for coverage
    cov.plotQueryAnalysisPrivate(df, save="Results/Private/" + dataset + "/" + mctsType +"/Coverage/")

    # Quality DF
    if computeRQ:
        qualDF = pd.DataFrame(qualLst, columns=["Method", 'Queries', "Epsilon", 'Precision', 'Accuracy', 'Patient Precision', 'Patient Accuracy'])
        qualDF.to_csv("Results/Private/"+ dataset + "/" + mctsType + "/Rule Quality/RuleQualitySummaryDF.csv")
        print("RULE QUALITY DF")
        print(qualDF)

        # Make graphs of query analysis for rule quality
        RQ.plotPrivateCM(qualDF, clientCM, metric='Accuracy', save="Results/Private/"+ dataset + "/" + mctsType + "/Rule Quality/")
        RQ.plotPrivateCM(qualDF, clientCM, metric='Precision', save="Results/Private/"+ dataset + "/" + mctsType + "/Rule Quality/")
        #Do for patient
        RQ.plotPrivateCM(qualDF, clientPtCM, metric='Patient Accuracy', save="Results/Private/"+ dataset + "/" + mctsType + "/Rule Quality/")
        RQ.plotPrivateCM(qualDF, clientPtCM, metric='Patient Precision', save="Results/Private/"+ dataset + "/" + mctsType + "/Rule Quality/")



def runProt(params):
    logging.basicConfig(level=logging.INFO)
    logging.info("*** RUNNING LOCAL DIFFERENTIAL PRIVACY POPULATION RULE AGGREGATION PROTOCOL ***")
    logging.info("*** PRIVATE ***")
    logging.info("*** MCTS VERSION: " + params.mctsType + " ***")

    logging.info("Initial Set Population Size is %s" % (params.popSize))

    # Make Clients
    logging.info("Loading Client Rules")
    clientList = {}  # dict of clients

    num = 1
    while len(clientList) < params.popSize:
        fileName = params.dataFilename + repr(num) + "Rules.txt"
        c = Client(clientNum=num, epsilon=params.epsilon, ruleSet=[])
        fileFound = c.loadRuleSet(fileName)
        # c.logRuleSet()
        if fileFound:
            clientList[num] = c

        num += 1

    logging.info("Total of %s Clients Found" % (len(clientList)))

    # Make Server
    logging.info("Initializing Server")
    varDict = {}
    for v in params.variables.keys():  # Make var dict of variables and their ranges
        varDict[v] = params.variables.get(v)

    s = Server(clientList, varDict, params)

    # Run Protocol
    s.runProtocol(branchName='[eval#1]')

    # Get dataframe of the generated rules and their percent counts
    s.finalRuleSet.ruleSetDF.to_csv(params.resultsFilename + "_Rules.csv") #Save Rules to File

    # Get count of client queries
    clientQs = s.getClientQueryCount()
    clientQs.to_csv(params.resultsFilename + "_ClientQueries.csv")

def calcIndivRuleQuality(ldpRules, clientData, clientLabels):
    print("\nCalculating Rule Quality")
    # First get misclassification rate of each individual rule
    ldpMCR = RQ.getRulesetMCR(ldpRules, clientData, clientLabels)
    ldpMCR.to_csv(params.resultsFilename + "_RulesetMCR.csv")
    print(ldpMCR)

    # return confusion matrix summary across all patients
    ldpCM = RQ.getSummaryConfusionMatrix(clientData, clientLabels, ldpMCR, method='AVG')
    ldpCM.to_csv(params.resultsFilename + "_CM.csv")
    print(ldpCM)
    # return confusion matrix patient by patient
    ldpPtCM = RQ.getPatientConfusionMatrix(clientData, clientLabels, ldpMCR, method='AVG')
    ldpPtCM.to_csv(params.resultsFilename + "_Patient_CM.csv")
    print(ldpPtCM)

    return ldpCM, ldpPtCM

def calcIndivCoverage(clientDF):
    # Calculate experimental results
    ldpDF, ldpTrees, ldpRules = cov.loadLDPRuleset(params.resultsFilename + "_Rules.csv")

    print("\nCalculating Coverage")
    covDF, countDF, nrDF, missedCR, clientTrees = cov.getCoverageTable(params.cutoffThresh, ldpDF, ldpTrees, clientDF)
    print(covDF)
    structDF = cov.countUniqueStructuresNoVars(clientTrees, ldpTrees)
    print(structDF)

    # save non rules and missed client rules to file
    nrDF.to_csv(params.resultsFilename + "_NonRules.csv")
    missedCR.to_csv(params.resultsFilename + "_MissedClientRules.csv")

    # Plot comparison of match counts
    cov.plotLDPClientCounts(clientDF, countDF, save=params.resultsFilename, title=params.name)

    return ldpRules, covDF, structDF

def loadClientQualityDFs(mctsType, popSize, clientRules):
    # Load client data
    clientData, clientLabels = RQ.loadClientData(params.popSize, "Data/ICU/DataFrames/")

    # Calculate Rule Quality for client rules
    print("\nFirst Calculating Client Rule Quality")
    try:
        clientMCR = pd.read_csv("Results/Client/" + mctsType + "/" + str(popSize) + " Clients" + "/Client_RulesetMCR.csv")
    except FileNotFoundError:
        print("Client MCR not found, calculating")
        clientMCR = RQ.getRulesetMCR(clientRules, clientData, clientLabels)
        clientMCR.to_csv("Results/Client/" + mctsType + "/" + str(popSize) + " Clients" + "/Client_RulesetMCR.csv")
    try:
        clientCM = pd.read_csv("Results/Client/" + mctsType + "/" + str(popSize) + " Clients" + "/Client_CM.csv")
    except FileNotFoundError:
        print("Client CM not found, calculating")
        clientCM = RQ.getSummaryConfusionMatrix(clientData, clientLabels, clientMCR, method='AVG')
        clientCM.to_csv("Results/Client/" + mctsType + "/" + str(popSize) + " Clients" + "/Client_CM.csv")
    try:
        clientPtCM = pd.read_csv("Results/Client/" + mctsType + "/" + str(popSize) + " Clients" + "/Client_Patient_CM.csv")
    except FileNotFoundError:
        print("Client Patient CM not found, calculating")
        clientPtCM = RQ.getPatientConfusionMatrix(clientData, clientLabels, clientMCR, method='AVG')
        clientPtCM.to_csv("Results/Client/" + mctsType + "/" + str(popSize) + " Clients" + "/Client_Patient_CM.csv")

    return clientData, clientLabels, clientCM, clientPtCM


if __name__ == "__main__":
    main()