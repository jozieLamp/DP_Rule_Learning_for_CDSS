from SignalTemporalLogic.STLFactory import STLFactory
from STLTree.STLTree import STLTree
import logging


class Client:
    def __init__(self, clientNum, ruleSet):
        self.clientNum = clientNum
        self.ruleSet = ruleSet

        self.logger = logging.getLogger('CLIENT')
        self.budgetUsed = 0


    def loadRuleSet(self, textfile):
        stlFac = STLFactory()
        try:
            file = open(textfile, "r")
            for line in file:
                if line[0] == "(" and line[-2] == ")":
                    line = line[1:-2] + "\n"

                rule = stlFac.constructFormulaTree(line)
                self.ruleSet.append(rule)

            file.close()
            return True

        except:
            self.logger.error("File not found for Client %d" % (self.clientNum) )
            return False


    def logRuleSet(self):
        self.logger.info("\nRule Set for Client %s" % (str(self.clientNum)))
        for i in range(len(self.ruleSet)):
            self.logger.info(self.ruleSet[i].toString())
