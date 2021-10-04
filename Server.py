import logging


class Server :
    def __init__(self, clientList, varDict, epsilon):
        self.clientList = clientList  # dict of clients
        self.varDict = varDict  # variable dictionary to store vars + ranges
        self.variables = list(self.varDict.keys())

        self.epsilon = epsilon

        self.logger = logging.getLogger('SERVER')