import logging
import copy
from RuleTemplate.RuleTemplate import RuleTemplate
from RuleTemplate.RuleTemplate import stlGrammarDict


class Server :
    def __init__(self, clientList, varDict, params):
        self.clientList = clientList  # dict of clients
        self.varDict = varDict  # variable dictionary to store vars + ranges
        self.variables = list(self.varDict.keys())

        #template params
        if params.template == None:
            # make default rule template tree to start
            self.templateTree = RuleTemplate(default=True)
            self.rootNode = 'boolExpr1'

        else: #TODO - add option to start from preset template
            pass

        #Privacy budget params
        self.epsilon = params.epsilon

        #Output params
        self.verbose = params.verbose
        self.logger = logging.getLogger('SERVER')
        self.mcLogger = logging.getLogger('MCTS')

    # RUN Monte Carlo Tree Search
    def runMCTS(self):
        usedBudget = 0
        states = [self.rootNode]

        while usedBudget < self.epsilon:
            # SELECTION
            branches = []
            branch = self.selectBranch(states[-1])


    # state is string name of node
    def selectBranch(self, state):
        currNode = self.templateTree[state]

        # get available branch choices
        branchChoices = stlGrammarDict[currNode.data.type]
        if self.verbose:
            print("Next Set of Branch Choices", branchChoices)

        # If state unvisited
        if currNode.data.visitNum == 0:  # state unvisited --> follow default policy
            pass
        # TODO - adapt tree policy potentially
        else:  # follow tree policy
            # get branch choice that has max of uct score
            for bc in branchChoices:
                self.uctScore(currNode, bc)

    def uctScore(self, currNode, branch):
        #get reward for current node --> count of client yes responses
        #Make test template
        testTemp = copy.deepcopy(currNode.data.ruleTree)
        for n in branch:
            id = testTemp.generateID(n)
            testTemp.create_node(identifier=id, parent=currNode.identifier)

        numClients = self.queryClientRuleMatch(testTemp)
        self.queryClientRuleMatch()


    def queryClientRuleMatch(self, template):
        #TODO working here~~~
        # get template node list
        tempNodes = self.getTemplateNodes(template)
        # print("temp nodes", tempNodes)

        # get count from clients of who have template
        yesCount = 0
        p = None

        for c in self.clientList:
            resp, p = c.randResponseQueryStruct(tempNodes, varList)
            if resp == "BUDGET USED":
                self.clientsWithUsedBudgets.append(c)
            else:
                yesCount += resp

        if not self.checkClientBudgetsUsed():
            qe = 1 / ((2 * p) - 1)
            q = yesCount * qe  # corrected num yesses
            percentCount = q / len(self.clientList)

            if self.protocolTrace:
                print("p", p, "qe", qe, "q", q, "percent count", percentCount)
                # print("yescount", yesCount / len(self.clientList))
                print("Num Yesses", float(percentCount))

            return percentCount

        # else:
        return "BUDGET USED"