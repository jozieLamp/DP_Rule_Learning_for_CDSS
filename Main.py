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
    # s.runMCTS(branchName='[eval1]')

    from RuleTemplate.RuleTemplate import RuleTemplate
    test = RuleTemplate()
    test.addBranch(["statementList"], "eval1")
    test.addBranch(["statement"], "statementList1")
    test.addBranch(["boolExpr"], "statement1")
    test.addBranch(["stlTerm"], "boolExpr1")
    test.addBranch(["stlTerm", "AND", "stlTerm"], "boolExpr1")
    test.addBranch(["stlTerm", "OR", "stlTerm"], "boolExpr1")
    test.addBranch(["stlTerm", "IMPLIES", "stlTerm"], "boolExpr1")

    test.addBranch(["BooleanAtomic", "U", "timeBound",  "BooleanAtomic"], "stlTerm1")
    test.addBranch(["F", "timeBound", "BooleanAtomic"], "stlTerm1")
    test.addBranch(["G", "timeBound", "BooleanAtomic"], "stlTerm1")
    test.addBranch(["BooleanAtomic"], "stlTerm1")


    test.showGraph()





if __name__ == "__main__":
    runProtocol(params)