from MetricCalculation import Coverage as cov
import params
import logging
from Client import Client
from Server_Test import Server
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

def main():
    # get list of client rules sorted by count
    popSize = params.popSize
    clientFilename = "Data/ICU/Best/"

    logging.basicConfig(level=logging.INFO)

    #Load client rules for comparison
    # Load Client Rule Trees and Text Rule Structures, and get dataframe of rules and their counts
    clientTrees, clientRules, clientDF = cov.loadClientRules(popSize, clientFilename)

    #Load client rules for LDP Protocol
    logging.info("*** RUNNING LOCAL DIFFERENTIAL PRIVACY POPULATION RULE AGGREGATION PROTOCOL ***")
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


    # Params -- weighting btw scores for uct score and what to return for edit distance (median, min, avg)
    # edit distance method options are: 'median', 'avg', 'min', 'max'
    # methods = ['median', 'avg', 'min', 'max']
    # # UTC weighting is [score weight, edit dist weight]
    # weights = ['scoreXeditDist', 'scaledBy100', 'scaledBy10', 'scoreX10', 'scoreX100']
    # weights = [[1, 0.5], []]

    recordLst = []

    methods = ['median', 'avg', 'min', 'max']
    weights = ['baseline', 'log10', 'log10NoCp', 'log2', 'ln', 'log10x2', 'logscorex2','scoreXeditDist', 'scaledBy100', 'scaledBy10', 'scoreX10', 'scoreX100']

    for method in methods:
        for utcWeighting in weights:

            print("******************************************************** NEW PARAMS ********************************************************")
            print("METHOD:", method)
            print("UTC Weighting", utcWeighting, "\n")

            ldpFilename = "Param_Results/ICU_" + "method" + method + "_weighting" + utcWeighting
            graphName = 'Param_Results/Graphs/' + "method" + method + "_weighting" + utcWeighting #"_score" + str(utcWeighting[0]) + "_editDist" + str(utcWeighting[1])  # Name of count coverage graphs
            popThresh = 0.001  # Percentage match count

            # Make Server
            logging.info("Initializing Server")
            varDict = {}
            for v in params.variables.keys():  # Make var dict of variables and their ranges
                varDict[v] = params.variables.get(v)

            s = Server(clientList, varDict, params)

            # Run Protocol
            s.runProtocol('[eval#1]', method, utcWeighting)

            # Get dataframe of the generated rules and their percent counts
            s.finalRuleSet.ruleSetDF.to_csv(ldpFilename + ".csv") #Save Rules to File

            # Get count of client queries
            # clientQs = s.getClientQueryCount()
            # clientQs.to_csv(ldpFilename + "_ClientQueries.csv")

            #Get coverage results
            ldpDF, ldpTrees, ldpRules = cov.loadLDPRuleset(ldpFilename + ".csv")
            # cov.graphRuleCounts(clientDF, ldpDF, graphName)

            covDF, countDF = cov.getCoverageTable(popThresh, ldpDF, ldpTrees, clientDF)
            countDF.to_csv(ldpFilename + "_CovCountDF.csv")
            # cov.compareFoundRuleCounts(countDF, graphName)
            print("\n")
            print(covDF)
            print(countDF)

            #get number of unique structure types, ignoring vars to get sense of coverage
            numUniqueStructs = cov.countUniqueStructuresNoVars(ldpTrees)
            print("Total Unique Structures:", numUniqueStructs)

            recordLst.append([method, utcWeighting, covDF['Found Rules'].item(), numUniqueStructs])

            #Update Summary DF
            summaryDF = pd.DataFrame(recordLst, columns=['Method', 'UTC Wtg', 'Found Rules', '# Unique'])
            print("Current Summary:")
            print(summaryDF)
            summaryDF.to_csv("Param_Results/ICU_Summary_CoverageResults.csv")

            print("\n")



if __name__ == "__main__":
    main()