from MetricCalculation import Coverage as cov
from MetricCalculation import RuleQuality as RQ
import params
import logging
from Client import Client
from Server import Server
import pandas as pd
import math
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def main():
    #Main params
    dataset = 'ICU'
    mctsType = 'Baseline'
    computeRQ = True
    params.popSize = 8000
    params.maxQueries = 1000
    numTimes = 10

    #Load client rules
    clientTrees, clientRules, clientDF = cov.loadClientRules(params.popSize, params.dataFilename)

    #Load client rule quality data and dataframes
    if computeRQ:
        clientData, clientLabels, clientCM, clientPtCM = loadClientQualityDFs(mctsType, params.popSize, clientRules)


    coverageLst = []
    qualLst = []

    averagedCov = []
    averagedQual = []

    budgets = [1000, 100, 10, 1, 0.1, 0.01, 0.001]
    cps = ['basic', 'beta', 'eps', '1', '2']
    prunes = ['10', '1', '0-1', '0-001']



    for cpMethod in cps:
        for pruneMethod in prunes:
            for eps in budgets:

                # Update params
                if cpMethod == 'basic':
                    params.cp = 1 / math.sqrt(2)
                #Adapt Cp as a function of beta --> more noise should favor higher match scores over more breadth searching
                elif cpMethod == 'beta': #just set cp to beta (budget/query)
                    params.cp = eps / params.maxQueries
                elif cpMethod == 'eps': #set to epsilon
                    params.cp = eps
                elif cpMethod == '1': #set to epsilon
                    params.cp = 1
                elif cpMethod == '2': #set to epsilon
                    params.cp = 2

                if pruneMethod == '10':
                    params.cutoffThresh = 0.10
                elif pruneMethod == '1':
                    params.cutoffThresh = 0.01
                elif pruneMethod == '0-1':
                    params.cutoffThresh = 0.001
                elif pruneMethod == '0-001':
                    params.cutoffThresh = 0.0001

                params.epsilon = eps
                params.name = "Cp" + cpMethod + "_Lambda" + pruneMethod + "_Eps" + str(eps)
                params.resultsFilename = "Results/Private/"+ dataset + "/" + mctsType + "/Cp" + cpMethod + "_Lambda" + pruneMethod + "_Eps" + str(eps)

                print("\n\n**************** CP: " + cpMethod + "; Lambda:", pruneMethod, "; EPSILON: ", params.epsilon, "****************")

                aveCov = []
                aveQual = []
                for n in range(numTimes):
                    #Run protocol
                    runProt(params)

                    ## COVERAGE EXPs
                    ldpRules, covDF, structDF = calcIndivCoverage(clientDF)

                    aveCov.append([covDF['Total Client Rules'].item(), covDF['Found Rules'].item()/covDF['Total Client Rules'].item() ,covDF['Found Rules'].item(), covDF['Non Rules'].item(),
                       covDF['Precision'].item(),structDF['Total Client Structures'].item(), structDF['Found Structures'].item()/structDF['Total Client Structures'].item(),
                       structDF['Found Structures'].item(), structDF['Non Structures'].item(),
                       structDF['Precision'].item()])

                    coverageLst.append([cpMethod, pruneMethod, eps, covDF['Total Client Rules'].item(), covDF['Found Rules'].item()/covDF['Total Client Rules'].item() ,covDF['Found Rules'].item(), covDF['Non Rules'].item(),
                       covDF['Precision'].item(),structDF['Total Client Structures'].item(), structDF['Found Structures'].item()/structDF['Total Client Structures'].item(),
                       structDF['Found Structures'].item(), structDF['Non Structures'].item(),
                       structDF['Precision'].item()])

                    ## RULE QUALITY EXPS
                    if computeRQ:
                        ldpCM, ldpPtCM = calcIndivRuleQuality(ldpRules, clientData, clientLabels)

                        # Add results to list
                        aveQual.append([ldpCM['Precision'].item(), ldpCM['Accuracy'].item(),
                             ldpPtCM['Precision'].item(), ldpPtCM['Accuracy'].item()])

                        qualLst.append([cpMethod, pruneMethod, eps, ldpCM['Precision'].item(), ldpCM['Accuracy'].item(),
                             ldpPtCM['Precision'].item(), ldpPtCM['Accuracy'].item()])


                #Ave results
                stdDevCov = np.std(aveCov, axis=0)
                aveCov = np.average(aveCov, axis=0)

                if computeRQ:
                    stdDevQual = np.std(aveQual, axis=0)
                    aveQual = np.average(aveQual, axis=0)

                #Add averaged results to list
                #Coverage
                lst = [cpMethod, pruneMethod, eps]
                lst.extend(aveCov)
                lst.extend(stdDevCov)
                averagedCov.append(lst)

                #Rule quality
                if computeRQ:
                    q = [cpMethod, pruneMethod, eps]
                    q.extend(aveQual)
                    q.extend(stdDevQual)
                    averagedQual.append(q)


    #Make final result DFs
    #Coverage DF
    df = pd.DataFrame(coverageLst, columns=["Cp", "Lambda", "Epsilon", "Total Client Rules", "Percentage Found Rules", "Found Rules", "Non Rules", "Rule Precision",
                    "Total Client Structures","Percentage Found Structures", "Found Structures", "Non Structures", "Structure Precision"])
    df.to_csv("Results/Private/"+ dataset + "/" + mctsType + "/Coverage/CoverageSummaryDF.csv")
    print("COVERAGE DF:")
    print(df)

    # Make graphs of query analysis for coverage
    cov.plotQueryAnalysisPrivate(df, save="Results/Private/" + dataset + "/" + mctsType +"/Coverage/", value='Percentage Found Rules')
    cov.plotQueryAnalysisPrivate(df, save="Results/Private/" + dataset + "/" + mctsType + "/Coverage/",value='Percentage Found Structures')
    cov.plotQueryAnalysisPrivate(df, save="Results/Private/" + dataset + "/" + mctsType + "/Coverage/",value='Rule Precision')
    cov.plotQueryAnalysisPrivate(df, save="Results/Private/" + dataset + "/" + mctsType + "/Coverage/",value='Structure Precision')
    cov.plotQueryAnalysisPrivate(df, save="Results/Private/" + dataset + "/" + mctsType + "/Coverage/",value='Found Rules')
    cov.plotQueryAnalysisPrivate(df, save="Results/Private/" + dataset + "/" + mctsType + "/Coverage/",value='Non Rules')

    aveCovDf = pd.DataFrame(averagedCov,columns=["Cp", "Lambda", "Epsilon", "Total Client Rules", "Percentage Found Rules", "Found Rules","Non Rules", "Rule Precision",
                               "Total Client Structures", "Percentage Found Structures", "Found Structures","Non Structures", "Structure Precision",
                                "Total Client Rules Std", "Percentage Found Rules Std", "Found Rules Std","Non Rules Std", "Rule Precision Std","Total Client Structures Std",
                                "Percentage Found Structures Std","Found Structures Std","Non Structures Std", "Structure Precision Std" ])
    aveCovDf.to_csv("Results/Private/" + dataset + "/" + mctsType + "/Coverage/AveragedCoverageSummaryDF.csv")
    cov.summaryPrivRules(aveCovDf, save="Results/Private/" + dataset + "/" + mctsType + "/Coverage/")



    # Quality DF
    if computeRQ:
        qualDF = pd.DataFrame(qualLst, columns=["Cp", 'Lambda', "Epsilon", 'Precision', 'Accuracy', 'Patient Precision', 'Patient Accuracy'])
        qualDF.to_csv("Results/Private/"+ dataset + "/" + mctsType + "/Rule Quality/RuleQualitySummaryDF.csv")
        print("RULE QUALITY DF")
        print(qualDF)

        # Make graphs of query analysis for rule quality
        RQ.plotPrivateCM(qualDF, clientCM, metric='Accuracy', save="Results/Private/"+ dataset + "/" + mctsType + "/Rule Quality/")
        RQ.plotPrivateCM(qualDF, clientCM, metric='Precision', save="Results/Private/"+ dataset + "/" + mctsType + "/Rule Quality/")
        #Do for patient
        RQ.plotPrivateCM(qualDF, clientPtCM, metric='Patient Accuracy', save="Results/Private/"+ dataset + "/" + mctsType + "/Rule Quality/")
        RQ.plotPrivateCM(qualDF, clientPtCM, metric='Patient Precision', save="Results/Private/"+ dataset + "/" + mctsType + "/Rule Quality/")

        aveQualDF = pd.DataFrame(averagedQual, columns=["Cp", 'Lambda', "Epsilon", 'Precision', 'Accuracy', 'Patient Precision', 'Patient Accuracy',
                                                        'Precision Std', 'Accuracy Std', 'Patient Precision Std', 'Patient Accuracy Std'])
        aveQualDF.to_csv("Results/Private/"+ dataset + "/" + mctsType + "/Rule Quality/AveragedRuleQualitySummaryDF.csv")



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