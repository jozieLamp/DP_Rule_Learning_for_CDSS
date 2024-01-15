import logging
import params
from Client import Client
from Server import Server
import pandas as pd
import numpy as np
import os
from MetricCalculation import Coverage as cov
from MetricCalculation import RuleQuality as RQ

import math
import decimal


def runProtocol(params):
    logging.basicConfig(level=logging.INFO)
    logging.info("*** RUNNING LOCAL DIFFERENTIAL PRIVACY POPULATION RULE AGGREGATION PROTOCOL ***")
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
    s.finalRuleSet.ruleSetDF.to_csv(params.resultsFilename + "/Coverage/" + "Eps_" + str(eps) + "_Run_" + str(n) + "_LDP_Rules.csv") #Save Rules to File

    # Get count of client queries
    clientQs = s.getClientQueryCount()
    clientQs.to_csv(params.resultsFilename + "/Coverage/" + "Eps_" + str(eps) + "_Run_" + str(n) + "_ClientQueries.csv")

    return s.numQueries


def calcCompleteCoverage(clientDF, ldpDF, ldpTrees, cutoff=0.0):

    print("\nCalculating Coverage")
    covDF, countDF, nrDF, missedCR, clientTrees = cov.getCoverageTable(clientDF, ldpDF, ldpTrees, cutoff)
    print(covDF)
    # TODO - update or del this
    structDF = cov.countUniqueStructuresNoVars(clientTrees, ldpTrees)
    print(structDF)

    # save non rules and missed client rules to file
    nrDF.to_csv(params.resultsFilename + "/Coverage/" + "Eps_" + str(eps) + "_Run_" + str(n) +"_NonRules.csv")
    missedCR.to_csv(params.resultsFilename + "/Coverage/" + "Eps_" + str(eps) + "_Run_" + str(n) +"_MissedClientRules.csv")

    # TODO - fix or update this
    # # Plot comparison of match counts
    # cov.plotLDPClientCounts(clientDF, countDF, save=params.resultsFilename, title="Cov")#params.name)

    return covDF, structDF

def loadClientQualityDFs(mctsType, popSize, clientRules):
    # Load client data
    clientData, clientLabels = RQ.loadClientData(params.popSize, "Data/ICU/DataFrames/")

    filepath = "Results/ICU/Clients/"

    # Calculate Rule Quality for client rules
    print("\nFirst Calculating Client Rule Quality")
    try:
        clientMCR = pd.read_csv(filepath + str(popSize) + "_Client_RulesetMCR.csv")
    except FileNotFoundError:
        print("Client MCR not found, calculating")
        clientMCR = RQ.getRulesetMCR(clientRules, clientData, clientLabels)
        clientMCR.to_csv(filepath + str(popSize) + "_Client_RulesetMCR.csv")
    try:
        clientCM = pd.read_csv(filepath + str(popSize) + "_Client_CM.csv")
    except FileNotFoundError:
        print("Client CM not found, calculating")
        clientCM = RQ.getSummaryConfusionMatrix(clientData, clientLabels, clientMCR, method='AVG')
        clientCM.to_csv(filepath + str(popSize) + "_Client_CM.csv")
    try:
        clientPtCM = pd.read_csv(filepath + str(popSize) + "_Client_Patient_CM.csv")
    except FileNotFoundError:
        print("Client Patient CM not found, calculating")
        clientPtCM = RQ.getPatientConfusionMatrix(clientData, clientLabels, clientMCR, method='AVG')
        clientPtCM.to_csv(filepath + str(popSize) + "_Client_Patient_CM.csv")

    return clientData, clientLabels, clientCM, clientPtCM

def calcIndivRuleQuality(fp, ldpRules, clientData, clientLabels):
    print("\nCalculating Rule Quality")
    # First get misclassification rate of each individual rule
    ldpMCR = RQ.getRulesetMCR(ldpRules, clientData, clientLabels)
    ldpMCR.to_csv(fp + "_RulesetMCR.csv")
    # print(ldpMCR)

    # return confusion matrix summary across all patients
    ldpCM = RQ.getSummaryConfusionMatrix(clientData, clientLabels, ldpMCR, method='AVG')
    ldpCM.to_csv(fp + "_CM.csv")
    # print(ldpCM)
    # return confusion matrix patient by patient
    ldpPtCM = RQ.getPatientConfusionMatrix(clientData, clientLabels, ldpMCR, method='AVG')
    ldpPtCM.to_csv(fp + "_Patient_CM.csv")
    print(ldpPtCM)

    return ldpCM, ldpPtCM

if __name__ == "__main__":

    # Set params
    budgets = [0.01, 0.1, 1, 10, 100, 1000, 10000]
    numTimes = 10
    computeRQ = True

    # Load client rules
    clientDF = cov.loadClientRules(params.popSize, params.dataFilename, cutoff=0.0)
    print("CLIENT DF", clientDF)

    # Load client rule quality data and dataframes
    if computeRQ:
        clientRules = clientDF['Rule'].tolist()
        clientData, clientLabels, clientCM, clientPtCM = loadClientQualityDFs(params.budgetAllocMethod, params.popSize, clientRules)


    lst = []
    lst_stds = []
    queries = []
    qualLst = []
    averagedQual = []

    for eps in budgets:
        params.epsilon = eps
        # params.name = "_Eps" + str(eps)
        print("\n\n**************** EPSILON: ", params.epsilon, "****************")

        covDFs = []
        structDFs = []
        aveQual = []
        for n in range(numTimes):

            # if not os.path.exists(params.resultsFilename):  # make path if it doesn't exist
            #     os.makedirs(params.resultsFilename)

            # filepath = params.resultsFilename + "Eps_" + str(eps) + "_Run_" + str(n)

            # Run protocol
            nq = runProtocol(params)

            # Load learned LDP rules
            ldpDF, ldpTrees, ldpRules = cov.loadLDPRuleset(params.resultsFilename + "/Coverage/" + "Eps_" + str(eps) + "_Run_" + str(n) + "_LDP_Rules.csv")

            ## COVERAGE EXPs

            # Calculate complete coverage
            # print("Complete Coverage")
            # covDF, structDF = calcCompleteCoverage(clientDF, ldpDF, ldpTrees, 0)

            # Calculate coverage for %client rules > cutoff threshold
            print("\nCoverage at Cutoff Thresh")
            covDF_cutoff, structDF_cutoff = calcCompleteCoverage(clientDF, ldpDF, ldpTrees, params.cutoffThresh)
            covDF_cutoff['Queries'] = nq

            covDFs.append(covDF_cutoff)
            structDFs.append(structDF_cutoff)

            covDF_cutoff.to_csv(params.resultsFilename + "/Coverage/" + "Eps_" + str(eps) + "_Run_" + str(n) + "_covDF")
            structDF_cutoff.to_csv(params.resultsFilename + "/Coverage/" + "Eps_" + str(eps) + "_Run_" + str(n) + "_structDF")

            # Try testing coverage on dif dataset ...
            print("\nTotal Queries Completed:", nq)

            ## RULE QUALITY EXPS
            if computeRQ:
                fp = params.resultsFilename + "/RuleQuality/" + "Eps_" + str(eps) + "_Run_" + str(n)
                ldpCM, ldpPtCM = calcIndivRuleQuality(fp, ldpRules, clientData, clientLabels)

                # Add results to list
                aveQual.append([ldpCM['Precision'].item(), ldpCM['Accuracy'].item(),ldpPtCM['Precision'].item(), ldpPtCM['Accuracy'].item()])

                qualLst.append([eps, ldpCM['Precision'].item(), ldpCM['Accuracy'].item(),ldpPtCM['Precision'].item(), ldpPtCM['Accuracy'].item()])

        # get averages and std devs
        conCovs = pd.concat(covDFs, axis=0)
        means = conCovs.mean()
        stds = conCovs.std()

        means.to_csv(params.resultsFilename + "/Coverage/" + "Eps_" + str(eps) + "_Averaged.csv")
        stds.to_csv(params.resultsFilename + "/Coverage/" + "Eps_" + str(eps) + "_Averaged_stds.csv")

        # Save them to Eps list
        lst.append([eps, means["Total Client Rules"], means["Found Rules"], means["Non Rules"], means["Precision"], means["Coverage"], means["Queries"]])
        lst_stds.append([eps, stds["Total Client Rules"], stds["Found Rules"], stds["Non Rules"], stds["Precision"], stds["Coverage"], stds["Queries"]])

        # Rule quality
        if computeRQ:
            stdDevQual = np.std(aveQual, axis=0)
            aveQual = np.average(aveQual, axis=0)

            q = [eps]
            q.extend(aveQual)
            q.extend(stdDevQual)
            averagedQual.append(q)

    # Get complete coverage summary
    df = pd.DataFrame(lst, columns=["Epsilon", "Total Client Rules", "Found Rules", "Non Rules", "Precision", "Coverage", "Queries"])
    df.to_csv(params.resultsFilename + "COMPLETE_Coverage.csv")

    df = pd.DataFrame(lst_stds,columns=["Epsilon", "Total Client Rules", "Found Rules", "Non Rules", "Precision", "Coverage","Queries"])
    df.to_csv(params.resultsFilename + "COMPLETE_Coverage_stds.csv")

    # Get complete Rule Quality
    if computeRQ:
        qualDF = pd.DataFrame(qualLst,columns=["Epsilon", 'Precision', 'Accuracy', 'Patient Precision', 'Patient Accuracy'])


        qualDF.to_csv(params.resultsFilename + "RuleQuality.csv")
        print("RULE QUALITY DF")
        print(qualDF)

        # # Make graphs of query analysis for rule quality
        # RQ.plotPrivateCM(qualDF, clientCM, metric='Accuracy', save=params.resultsFilename + "/RuleQuality/")
        # RQ.plotPrivateCM(qualDF, clientCM, metric='Precision', save=params.resultsFilename + "/RuleQuality/")
        # # Do for patient
        # RQ.plotPrivateCM(qualDF, clientPtCM, metric='Patient Accuracy', save=params.resultsFilename + "/RuleQuality/")
        # RQ.plotPrivateCM(qualDF, clientPtCM, metric='Patient Precision', save=params.resultsFilename + "/RuleQuality/")

        aveQualDF = pd.DataFrame(averagedQual,
                                 columns=["Epsilon", 'Precision', 'Accuracy', 'Patient Precision',
                                          'Patient Accuracy',
                                          'Precision Std', 'Accuracy Std', 'Patient Precision Std',
                                          'Patient Accuracy Std'])
        aveQualDF.to_csv(params.resultsFilename + "RuleQuality_AveragedComplete.csv")
