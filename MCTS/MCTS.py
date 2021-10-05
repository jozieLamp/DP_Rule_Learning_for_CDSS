from RuleTemplate.RuleTemplate import stlGrammarDict
import re
import logging

logger = logging.getLogger('MCTS')

def runMCTS(tree, epsilon, root, verbose):
    usedBudget = 0
    states = [root]

    while usedBudget < epsilon:
        # SELECTION
        branches = []
        branch = selectBranch(states[-1], tree, verbose)


#state is string name of node
def selectBranch(state, tree, verbose):
    currNode = tree[state]

    # get available branch choices
    branchChoices = stlGrammarDict[currNode.data.type]
    if verbose:
        print("Next Set of Branch Choices", branchChoices)

    #If state unvisited
    if currNode.data.visitNum == 0: #state unvisited --> follow default policy
        pass
    #TODO - adapt tree policy potentially
    else: #follow tree policy
        #get branch choice that has max of uct score
        for bc in branchChoices:
            uctScore(currNode, bc)

def uctScore(currNode, branch):
    pass