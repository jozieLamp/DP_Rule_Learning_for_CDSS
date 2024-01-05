import logging
import params
from Client import Client
from Server import Server
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
    s.finalRuleSet.ruleSetDF.to_csv(params.resultsFilename + "_Rules.csv") #Save Rules to File

    # Get count of client queries
    clientQs = s.getClientQueryCount()
    clientQs.to_csv(params.resultsFilename + "_ClientQueries.csv")


def calcCompleteCoverage(clientDF, ldpDF, ldpTrees, cutoff=0.0):

    print("\nCalculating Coverage")
    covDF, countDF, nrDF, missedCR, clientTrees = cov.getCoverageTable(clientDF, ldpDF, ldpTrees, cutoff)
    print(covDF)
    # TODO - update or del this
    structDF = cov.countUniqueStructuresNoVars(clientTrees, ldpTrees)
    print(structDF)

    # save non rules and missed client rules to file
    nrDF.to_csv(params.resultsFilename + "_NonRules.csv")
    missedCR.to_csv(params.resultsFilename + "_MissedClientRules.csv")

    # TODO - fix or update this
    # # Plot comparison of match counts
    # cov.plotLDPClientCounts(clientDF, countDF, save=params.resultsFilename, title="Cov")#params.name)

    return covDF, structDF


if __name__ == "__main__":

    # Load client rules
    clientDF = cov.loadClientRules(params.popSize, params.dataFilename, cutoff=0.0)
    print("CLIENT DF", clientDF)

    # # Load client rules w/ cutoff
    # clientDF_cutoff = cov.loadClientRules(params.popSize, params.dataFilename, cutoff=0.01)
    # print("CLIENT DF Cutoff", clientDF_cutoff)

    runProtocol(params)

    # Load learned LDP rules
    ldpDF, ldpTrees, ldpRules = cov.loadLDPRuleset(params.resultsFilename + "_Rules.csv")

    ## COVERAGE EXPs

    # Calculate complete coverage
    print("Complete Coverage")
    covDF, structDF = calcCompleteCoverage(clientDF, ldpDF, ldpTrees, 0)

    # Calculate coverage for %client rules > cutoff threshold
    print("\nCoverage at Cutoff Thresh")
    covDF_cutoff, structDF_cutoff = calcCompleteCoverage(clientDF, ldpDF, ldpTrees, 0.01)#params.cutoffThresh)

    # Try testing coverage on dif dataset ...

