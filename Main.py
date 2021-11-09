import logging
import params
from Client import Client
from Server import Server


def runProtocol(params):
    logging.basicConfig(level=logging.INFO)
    logging.info("*** RUNNING LOCAL DIFFERENTIAL PRIVACY POPULATION RULE AGGREGATION PROTOCOL ***")

    ## PHASE I - INITIALIZATION
    logging.info("PHASE I - INITIALIZATION")
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

    # for i in range(1, params.popSize + 1):
    #     fileName = params.dataFilename + repr(i) + "Rules.txt"
    #     c = Client(clientNum=i, ruleSet=[])
    #     fileFound = c.loadRuleSet(fileName)
    #     # c.logRuleSet()
    #     if fileFound:
    #         clientList[i] = c

    logging.info("Total of %s Clients Found" % (len(clientList)))

    # Make Server
    logging.info("Initializing Server")
    varDict = {}
    for v in params.variables.keys():  # Make var dict of variables and their ranges
        varDict[v] = params.variables.get(v)

    s = Server(clientList, varDict, params)

    #Run MCTS
    s.startProtocol(branchName='[eval1]')

    # Get dataframe of the generated rules and their percent counts
    df = s.getRulesetDF()
    df.to_csv(params.resultsFilename) #Save Rules to File


    # from RuleTemplate.RuleTemplate import RuleTemplate
    # test = RuleTemplate()
    # test.addBranch(["statementList"], "eval1")
    # test.addBranch(["statement"], "statementList1")
    # test.addBranch([ "boolExpr"], "statement1")
    # test.addBranch(["stlTerm"], "boolExpr1")
    # test.addBranch(["stlTerm", "AND", "stlTerm"], "boolExpr1")
    # test.addBranch(["stlTerm", "OR", "stlTerm"], "boolExpr1")
    # test.addBranch(["stlTerm", "IMPLIES", "stlTerm"], "boolExpr1")
    #
    # #stl1
    # test.addBranch(["BooleanAtomic", "U", "timeBound",  "BooleanAtomic"], "stlTerm1")
    # test.addBranch(["F", "timeBound", "BooleanAtomic"], "stlTerm1")
    # test.addBranch(["G", "timeBound", "BooleanAtomic"], "stlTerm1")
    # test.addBranch(["BooleanAtomic"], "stlTerm1")
    #
    # test.addBranch(["(", "boolExpr", ")"], "BooleanAtomic1")
    # test.addBranch(["stlTerm"], "boolExpr2")
    # test.addBranch(["BooleanAtomic"], "stlTerm8")
    # test.addBranch(["LT"], "BooleanAtomic6")
    # test.addBranch(["Variable", "Parameter"], "LT1")
    #
    #
    # s.getQuery(test._branches['[LT1]'])

    # test.addBranch(["(", "boolExpr", ")"], "BooleanAtomic2")
    # test.addBranch(["stlTerm"], "boolExpr3")
    # test.addBranch(["BooleanAtomic"], "stlTerm9")
    # test.addBranch(["GE"], "BooleanAtomic7")
    # test.addBranch(["Variable", "Parameter"], "GE1")
    #
    # #G part
    # test.addBranch(["(", "boolExpr", ")"], "BooleanAtomic4")
    # test.addBranch(["stlTerm", "AND", "stlTerm"], "boolExpr4")
    # test.addBranch(["BooleanAtomic"], "stlTerm11")
    # test.addBranch(["BooleanAtomic"], "stlTerm10")
    #
    # test.addBranch(["LE"], "BooleanAtomic9")
    # test.addBranch(["Variable", "Parameter"], "LE2")
    # test.addBranch(["GE"], "BooleanAtomic8")
    # test.addBranch(["Variable", "Parameter"], "GE2")
    #
    # test.addBranch(["LE"], "BooleanAtomic1")
    # test.addBranch(["Variable", "Parameter"], "LE1")
    # test.addBranch(["GE"], "BooleanAtomic2")
    # test.addBranch(["Variable", "Parameter"], "GE1")
    #
    # rules = test.generateRuleSet(verbose=True)
    # print("FORMATTED RULES:")
    # for r in rules:
    #     print(r.toString())

    # test.showGraph()





if __name__ == "__main__":
    runProtocol(params)