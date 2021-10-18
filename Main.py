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

    # s.templateTree.addBranch(branch=['stlTerm', 'AND', 'stlTerm'], parentName='boolExpr1')
    # s.templateTree.addBranch(branch=['stlTerm'], parentName='boolExpr1')
    # s.templateTree.addBranch(branch=['F', 'timeBound', 'BooleanAtomic'], parentName='stlTerm1')
    # s.templateTree.addBranch(branch=['G', 'timeBound', 'BooleanAtomic'], parentName='stlTerm1')
    # s.templateTree.addBranch(branch=['G', 'timeBound', 'BooleanAtomic'], parentName='stlTerm2')
    # s.templateTree.addBranch(branch=['F', 'timeBound', 'BooleanAtomic'], parentName='stlTerm2')
    #
    # s.templateTree.addBranch(branch=['GT'], parentName='BooleanAtomic1')
    # s.templateTree.addBranch(branch=['GE'], parentName='BooleanAtomic1')
    # s.templateTree.addBranch(branch=['LT'], parentName='BooleanAtomic2')
    # s.templateTree.addBranch(branch=['LE'], parentName='BooleanAtomic2')
    #
    # # s.templateTree.showGraph()
    # # s.templateTree.getBranch('[stlTerm1 AND1 stlTerm2]').visits = 1
    #
    # s.templateTree.getBranch('[G2 timeBound3 BooleanAtomic3]').visits = 1
    # s.templateTree.getBranch('[F2 timeBound4 BooleanAtomic4]').visits = 1
    # s.templateTree.getBranch('[F1 timeBound1 BooleanAtomic1]').visits = 1
    # s.templateTree.getBranch('[G1 timeBound2 BooleanAtomic2]').visits = 1
    #



    # s.runMCTS(branchName='[boolExpr1]')
    s.runMCTS(branchName='[statementList1]')




if __name__ == "__main__":
    runProtocol(params)