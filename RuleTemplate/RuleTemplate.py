import treelib

class Node:
    def __init__(self, group, ruleTree=None):
        self.group = group
        self.ruleTree = ruleTree

class RuleTemplate(treelib.Tree):
    def __init__(self, default=True):
        super(RuleTemplate, self).__init__()

    # show tree structure and groups
    def showTree(self):
        self.show(idhidden=False, data_property="group")