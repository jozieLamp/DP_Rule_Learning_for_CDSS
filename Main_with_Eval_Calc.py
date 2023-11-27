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



from scipy.stats import norm, multivariate_normal
from scipy.optimize import minimize_scalar, minimize, Bounds
from scipy.integrate import quad

if __name__ == "__main__":

    # # Load client rules
    # clientDF = cov.loadClientRules(params.popSize, params.dataFilename, cutoff=0.0)
    # print("CLIENT DF", clientDF)
    #
    # # # Load client rules w/ cutoff
    # # clientDF_cutoff = cov.loadClientRules(params.popSize, params.dataFilename, cutoff=0.01)
    # # print("CLIENT DF Cutoff", clientDF_cutoff)

    #
    # runProtocol(params)
    #
    # # Load learned LDP rules
    # ldpDF, ldpTrees, ldpRules = cov.loadLDPRuleset(params.resultsFilename + "_Rules.csv")
    #
    # ## COVERAGE EXPs
    #
    # # Calculate complete coverage
    # print("Complete Coverage")
    # covDF, structDF = calcCompleteCoverage(clientDF, ldpDF, ldpTrees, cutoff=params.cutoffThresh)
    #
    # # Calculate coverage for %client rules > cutoff threshold
    # print("\nCoverage at Cutoff Thresh")
    # covDF_cutoff, structDF_cutoff = calcCompleteCoverage(clientDF, ldpDF, ldpTrees, cutoff=params.cutoffThresh)
    #
    # # Try testing coverage on dif dataset ...

    beta = 0.01
    cutoffThresh = 0.05

    p = math.e ** beta / (1 + math.e ** beta)
    q = 1 - p

    n = 100
    c = cutoffThresh  # * n # assuming worst case where true count at valid rule threshold

    bottom = n * ((p - q) ** 2)
    # bottom = (p - q) ** 2
    sigma_c = q * (1 - q) / bottom if bottom else (q * (1 - q))

    def probTrue(y):
        c_hat = ((y * p) + (n - y) * q) / n
        # prob_prune_correct = norm.cdf(cutoffThresh, loc=c_hat, scale=sigma_c) / norm.cdf(cutoffThresh, loc=0.5,scale=sigma_c)
        # print("p", p, "c", c, "c_hat", c_hat, "c", c, "n / active clients", n, "sigma c", sigma_c)
        # print("y=", y, "Prob correct: P[c_hat >= V | c >= V]", prob_prune_correct)

        # p[c_hat < V | c = V]; prob we make an error
        prob_chat_lt_v = norm.cdf(c_hat, loc=c, scale=sigma_c)
        print("p", p, "c", c, "c_hat", c_hat, "c", c, "n / active clients", n, "sigma c", sigma_c)
        print("y=", y, "p[c_hat < V | c = V]; prob we make an error", prob_chat_lt_v)


        # return prob_prune_correct
        return prob_chat_lt_v


    conf_intrvl = quad(probTrue, 0, n)  # integrate over all possible values of y
    print("\nCONF INTRVL", conf_intrvl)
    print("CONF INTRVL", conf_intrvl[0] / (cutoffThresh * n))

    # # p[c_hat < V | c = V]; prob we make an error
    # prob_chat_lt_v = norm.cdf(c_hat, loc=c, scale=sigma_c)
    # print("y=", y, "P[c_hat < V | c = V]", prob_chat_lt_v)
    # return prob_chat_lt_v

    # print(norm.cdf(cutoffThresh, loc=0.5, scale=sigma_c))
    #
    # # p[c_hat < V | c >= V]; prob we make an error, assuming hardest case where c = V
    # prob_prune_incorrect = norm.cdf(cutoffThresh, loc=c_hat, scale=sigma_c) / (1 - norm.cdf(cutoffThresh, loc=0.5, scale=sigma_c))
    # print("y=", y, "Prob error: P[c_hat < V | c >= V]", prob_prune_incorrect)





