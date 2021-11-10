import logging
import params
from Client import Client
from Server import Server


def runProtocol(params):
    logging.basicConfig(level=logging.INFO)
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

    # Make Server
    logging.info("Initializing Server")
    varDict = {}
    for v in params.variables.keys():  # Make var dict of variables and their ranges
        varDict[v] = params.variables.get(v)

    s = Server(clientList, varDict, params)

    # Run Protocol
    s.runProtocol(branchName='[eval#1]')

    # Get dataframe of the generated rules and their percent counts
    s.finalRuleSet.ruleSetDF.to_csv(params.resultsFilename + ".csv") #Save Rules to File

    # Get count of client queries
    clientQs = s.getClientQueryCount()
    clientQs.to_csv(params.resultsFilename + "_ClientQueries.csv")


if __name__ == "__main__":
    runProtocol(params)