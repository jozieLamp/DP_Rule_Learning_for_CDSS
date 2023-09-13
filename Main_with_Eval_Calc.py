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
    cov.plotLDPClientCounts(clientDF, countDF, save=params.resultsFilename, title="Cov")#params.name)

    return ldpRules, covDF, structDF



def sigma( n, p ,q):
    bottom =n * ((p - q) ** 2)
    # bottom = (p - q) ** 2
    stdDev = q * (1 - q) / bottom if bottom else (q * (1 - q))
    # print("top", q * (1 - q))
    # stdDev = stdDev / n
    # print("p, q, p-q", p, q, (p - q))
    # print("p-q std dev", math.pow((p - q), 2))
    # print("p-q std dev", ((p - q)**2))
    # stdDev = (q * (1 - q)) / ((p - q)**2)
    # print("sigma, bottom", bottom)
    # print("sigma, top", (n * q * (1 - q)))
    # print("top sigma", (n * (1 - p - q)))
    # bottom = p-q
    # stdDev = (n * (1 - p - q)) / bottom if bottom else 0
    # stdDev = n * ((-1 + beta) / (beta - 1)**2 )
    # if stdDev == 0:
    #     stdDev = 1

    return stdDev

from scipy.stats import norm
from scipy.integrate import quad
import numpy as np
if __name__ == "__main__":

    # # Load client rules
    # clientTrees, clientRules, clientDF = cov.loadClientRules(params.popSize, params.dataFilename)
    #
    # runProtocol(params)
    #
    # ## COVERAGE EXPs
    # ldpRules, covDF, structDF = calcIndivCoverage(clientDF)

    # TODO working here - figuring out why probs themselves are so low ...
    # Issue is that probs start low and then when multiplied together get high error rates when they actually should not be that high ...
    n = 100
    lmda = 0.1
    # c = 0.05
    c_hat = 0.0
    # print("c", c, "c_hat", c_hat)

    p = 0.9
    q = 1-p

    # I think issue here is the sigma calculation .... !!!!!!????
    # Problem that sigma is >
    sigma_c_hat = sigma(n, p, q) #if sigma big then prob c_hat > lmda gets really low b/c lots of variation in the distribution ...
    print("sigma c hat", sigma_c_hat)
    # sigma_c = 0.25#sigma(n, 0.49, 0.51)

    #integral of x from 0 to lmda P[true(c) = x | c_hat] --> Get a confidence interval that true count c < lambda
    # if conf interval within theshold, e.g., 95% that should or should not cut, use this budget, otherwise increase budget used

    def probTrue(x):
        # p[c = x | c_hat]
        prob_c_eqs_x = norm.pdf(x, loc=c_hat, scale=sigma_c_hat)
        print("x=", x, "P[c=x]", prob_c_eqs_x)

        return prob_c_eqs_x


    #Integral, could also just do a summation of the counts over up to lambda since they are discrete and may not need continuous distribution
    conf_intrvl_low = quad(probTrue, 0, lmda)
    conf_intrvl_high = quad(probTrue, lmda, 1)

    print("Conf that true count c < lambda", conf_intrvl_low)
    print("Conf that true count c > lambda", conf_intrvl_high)

    # #P[ˆc > λ | c ≤ λ]
    # falseContinue = (1 - norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat)) * norm.cdf(lmda, loc=c, scale=sigma_c)
    # print("P[c_hat > lmda]", 1 - norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat))
    # print("P[c <= lmda]", norm.cdf(lmda, loc=c, scale=sigma_c))
    # # falseContinue = ((1 - norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat)) * norm.cdf(lmda, loc=c,scale=sigma_c)) / norm.cdf(lmda, loc=c, scale=sigma_c)
    # # P[ˆc ≤ λ | c > λ]
    # falseCutoff = norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat) * (1 - norm.cdf(lmda, loc=c, scale=sigma_c))
    # # falseCutoff = (norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat) * (1 - norm.cdf(lmda, loc=c, scale=sigma_c))) / (1 - norm.cdf(lmda, loc=c, scale=sigma_c))
    # # print("P[c_hat > lambda", 1 - norm.cdf(self.Z(n, c_hat, sigma_c_hat) ))
    # # print("P[c <= lambda", norm.cdf(self.Z(n, c, sigma_c)))
    # print("Prob false continue", falseContinue)
    # print("P[c_hat <= lambda",norm.cdf(lmda, loc=c_hat, scale=sigma_c_hat))
    # # print("P[c > lambda", 1 - norm.cdf(self.Z(n, c, sigma_c)))
    # print("Prob false cutoff", falseCutoff)




