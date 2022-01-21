from MetricCalculation import Coverage as cov
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
    mctsType = 'Base'

    #Load rules for experimental purposes
    params.popSize = 10
    clientTrees, clientRules, clientDF = cov.loadClientRules(params.popSize, params.dataFilename)

    coverageLst = []
    numQueries = [500, 100]

    for nq in numQueries:
        print("\n\n**************** QUERIES:", nq, " ****************")

        params.maxQueries = nq
        params.name = mctsType + "_" + str(nq) + "_queries"
        params.resultsFilename = "Results/NonPrivate/"+ dataset + "/" + mctsType + "_" + str(nq) + "_queries"

        #Run protocol
        runProt(params)

        #Calculate experimental results
        ldpDF, ldpTrees, ldpRules = cov.loadLDPRuleset(params.resultsFilename + "_Rules.csv")

        print("\nCalculating Coverage")
        covDF, countDF, clientTrees = cov.getCoverageTable(params.cutoffThresh, ldpDF, ldpTrees, clientDF)
        print(covDF)
        structDF = cov.countUniqueStructuresNoVars(clientTrees, ldpTrees)
        print(structDF)

        #Plot comparison of match counts
        cov.plotLDPClientCounts(clientDF, countDF, save=params.resultsFilename, title=params.name)
        #TODO - potentially fix over estimations from multiple partial rules in the rule count part

        lst = [nq, covDF['Total Client Rules'].item(), covDF['Found Rules'].item()/covDF['Total Client Rules'].item() ,covDF['Found Rules'].item(), covDF['Non Rules'].item(),
               covDF['Precision'].item(),structDF['Total Client Structures'].item(), structDF['Found Structures'].item()/structDF['Total Client Structures'].item(),
               structDF['Found Structures'].item(), structDF['Non Structures'].item(),
               structDF['Precision'].item()]

        print("LST", lst)
        coverageLst.append(lst)

    #Make final result DFs
    df = pd.DataFrame(coverageLst, columns=["Queries", "Total Client Rules", "Percentage Found Rules", "Found Rules", "Non Rules", "Rule Precision",
                    "Total Client Structures","Percentage Found Structures", "Found Structures", "Non Structures", "Structure Precision"])

    print("COVERAGE DF:")
    print(df)

    df.to_csv("Results/NonPrivate/"+ dataset + "/" + mctsType + "_CoverageSummaryDF.csv")

    #Make graphs of query analysis here
    cov.plotQueryAnalysis(df, save=params.resultsFilename)




def runProt(params):
    logging.basicConfig(level=logging.INFO)
    logging.info("*** RUNNING LOCAL DIFFERENTIAL PRIVACY POPULATION RULE AGGREGATION PROTOCOL ***")
    logging.info("*** NONPRIVATE ***")
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



if __name__ == "__main__":
    main()