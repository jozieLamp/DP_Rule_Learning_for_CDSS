from enum import Enum

class OperatorEnum(Enum):
    G = ALW = 1
    U = UNTIL = 2
    F = EV = 3
    AND = 4
    OR = 5
    IMPLIES = 6
    LT = 7
    LE = 8
    GT = 9
    GE = 10
    EQ = 11
    NEQ = 12
    NONE = 13
    RELOP = 14

class Operator():
    def __init__(self, type=OperatorEnum.NONE, symbol="?"):
        self.type = type
        self.symbol = symbol

    def toString(self):
        return self.symbol

#Temporal Operators
class Operator_G(Operator):
    def __init__(self, type=OperatorEnum.G, symbol="G"):
        super(Operator_G, self).__init__()
        self.type = type
        self.symbol = symbol

class Operator_F(Operator):
    def __init__(self, type=OperatorEnum.F,  symbol="F"):
        super(Operator_F, self).__init__()
        self.type = type
        self.symbol = symbol

class Operator_U(Operator):
    def __init__(self, type=OperatorEnum.U, symbol="U"):
        super(Operator_U, self).__init__()
        self.type = type
        self.symbol = symbol

#Boolean Operators
class Operator_AND(Operator):
    def __init__(self, type=OperatorEnum.AND, symbol = "&"):
        super(Operator_AND, self).__init__()
        self.type = type
        self.symbol = symbol

class Operator_OR(Operator):
    def __init__(self, type=OperatorEnum.OR, symbol="|"):
        super(Operator_OR, self).__init__()
        self.type = type
        self.symbol = symbol

class Operator_IMPLIES(Operator):
    def __init__(self, type=OperatorEnum.IMPLIES, symbol="->"):
        super(Operator_IMPLIES, self).__init__()
        self.type = type
        self.symbol = symbol

#Relational Operators
class RelationalOperator(Operator):
    def __init__(self, type, atomic1=None, atomic2=None, symbol="?"):
        super(RelationalOperator, self).__init__(type)
        self.atomic1 = atomic1
        self.atomic2 = atomic2
        self.symbol = symbol

    def toString(self):
        return self.atomic1.toString() + " " + self.symbol + " " + self.atomic2.toString()

    def evaluateRobustness(self, traj, timeIndex):
        value1 = float(self.atomic1.evaluateRobustness(traj, timeIndex))
        value2 = float(self.atomic2.evaluateRobustness(traj, timeIndex)) #send variable name

        if self.type == OperatorEnum.LT:
            truthVal = value1 < value2
        elif self.type == OperatorEnum.LE:
            truthVal = value1 <= value2
        elif self.type == OperatorEnum.GT:
            truthVal = value1 > value2
        elif self.type == OperatorEnum.GE:
            truthVal = value1 >= value2
        elif self.type == OperatorEnum.EQ:
            truthVal = value1 == value2
        elif self.type == OperatorEnum.NEQ:
            truthVal = value1 != value2
        else:
            truthVal = False

        val = abs(value2 - value1)
        if truthVal == True:
            return val
        else:
            return -val

    def evaluateValue(self, traj, timeIndex):
        value1 = float(self.atomic1.evaluateRobustness(traj, timeIndex))
        value2 = float(self.atomic2.evaluateRobustness(traj, timeIndex))  # send variable name

        if self.type == OperatorEnum.LT:
            truthVal = value1 < value2
        elif self.type == OperatorEnum.LE:
            truthVal = value1 <= value2
        elif self.type == OperatorEnum.GT:
            truthVal = value1 > value2
        elif self.type == OperatorEnum.GE:
            truthVal = value1 >= value2
        elif self.type == OperatorEnum.EQ:
            truthVal = value1 == value2
        elif self.type == OperatorEnum.NEQ:
            truthVal = value1 != value2
        else:
            truthVal = False

        return truthVal

    def evaluateTruthValue(self, df, originalDF):

        varName = self.atomic1.value
        param = float(self.atomic2.value)
        value = df[varName].values[0]

        # print("\nIn RELOP for ", self.type)
        # print("Var Name", varName)
        # print("Param", param, "Value", value)


        if self.type == OperatorEnum.LT:
            truthVal = value < param
        elif self.type == OperatorEnum.LE:
            truthVal = value <= param
        elif self.type == OperatorEnum.GT:
            truthVal = value > param
        elif self.type == OperatorEnum.GE:
            truthVal = value >= param
        elif self.type == OperatorEnum.EQ:
            truthVal = value == param
        elif self.type == OperatorEnum.NEQ:
            truthVal = value != param
        else:
            truthVal = False

        # print(value, self.symbol, param)
        # print(truthVal)

        return truthVal

class Operator_LT(RelationalOperator):
    def __init__(self, atomic1=None, atomic2=None, type=OperatorEnum.LT, symbol="<"):
        super(Operator_LT, self).__init__(atomic1, atomic2, type)
        self.type=type
        self.symbol = symbol

class Operator_LE(RelationalOperator):
    def __init__(self, atomic1=None, atomic2=None, type=OperatorEnum.LE, symbol="<="):
        super(Operator_LE, self).__init__(atomic1, atomic2, type)
        self.type=type
        self.symbol  = symbol

class Operator_GT(RelationalOperator):
    def __init__(self, atomic1=None, atomic2=None, type=OperatorEnum.GT, symbol=">"):
        super(Operator_GT, self).__init__(atomic1, atomic2, type)
        self.type=type
        self.symbol  = symbol

class Operator_GE(RelationalOperator):
    def __init__(self, atomic1=None, atomic2=None, type=OperatorEnum.GE, symbol=">="):
        super(Operator_GE, self).__init__(atomic1, atomic2, type)
        self.type=type
        self.symbol  = symbol

class Operator_EQ(RelationalOperator):
    def __init__(self, atomic1=None, atomic2=None, type=OperatorEnum.EQ, symbol="="):
        super(Operator_EQ, self).__init__(atomic1, atomic2, type)
        self.type=type
        self.symbol  = symbol

class Operator_NEQ(RelationalOperator):
    def __init__(self, atomic1=None, atomic2=None, type=OperatorEnum.NEQ, symbol="!="):
        super(Operator_NEQ, self).__init__(atomic1, atomic2, type)
        self.type=type
        self.symbol  = symbol

