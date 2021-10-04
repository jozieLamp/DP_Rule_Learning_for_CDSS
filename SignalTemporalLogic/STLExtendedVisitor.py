from SignalTemporalLogic.SignalTemporalLogicVisitor import SignalTemporalLogicVisitor
from STLTree.STLTree import STLTree
from STLTree.STLExpr import ExprEnum
from STLTree.Operator import OperatorEnum
from STLTree.STLExpr import TimeBound
from STLTree.Operator import *
from STLTree.Atomic import *
import re
from antlr4.tree.Tree import TerminalNodeImpl
from STLTree.Operator import RelationalOperator
from STLTree.STLExpr import BoolExpr
from STLTree.STLExpr import STLTerm
from STLTree.STLExpr import Statement
from STLTree.STLExpr import Missing
import treelib as treelib


#Parse rule and save it into appropriate formula data structure
class STLExtendedVisitor(SignalTemporalLogicVisitor):

    #Overwrite of parse tree methods
    def visit(self, tree):
        self.formulaTree = STLTree()
        self.idDict =  {}
        return tree.accept(self), self.formulaTree

    def visitChildren(self, node, parentID=None):
        result = self.defaultResult()
        n = node.getChildCount()
        for i in range(n):
            if not self.shouldVisitNextChild(node, result):
                return result

            c = node.getChild(i)
            if type(c) == TerminalNodeImpl:
                childResult = c.accept(self)
            else:
                childResult = c.accept(self, parentID)
            result = self.aggregateResult(result, childResult)

        return result


    # Visit a parse tree produced by SignalTemporalLogicParser#evl.
    def visitEvl(self, ctx, parentID=None):
        #print("Evl")
        id = self.generateID(ExprEnum.evl)
        self.formulaTree.create_node(id, id, parent=None, data=STLExpr(type=ExprEnum.evl))
        return self.visitChildren(ctx, id)


    # Visit a parse tree produced by SignalTemporalLogicParser#statementList.
    def visitStatementList(self, ctx, parentID=None):
        #print("statementList", ctx.getText())
        id = self.generateID(ExprEnum.statementList)
        self.formulaTree.create_node(id, id, parent=parentID, data=STLExpr(type=ExprEnum.statementList))
        return self.visitChildren(ctx, id)


    # Visit a parse tree produced by SignalTemporalLogicParser#statement.
    def visitStatement(self, ctx, parentID=None):
        #print("statement", ctx.getText())
        id = self.generateID(ExprEnum.statement)
        self.formulaTree.create_node(id, id, parent=parentID, data=Statement(type=ExprEnum.statement))
        return self.visitChildren(ctx, id)


    # Visit a parse tree produced by SignalTemporalLogicParser#declaration.
    def visitDeclaration(self, ctx, parentID=None):
        #print("declaration", ctx.getText())
        id = self.generateID(ExprEnum.declaration)
        d = self.formulaTree.create_node(id, id, parent=parentID, data=STLExpr(type=ExprEnum.declaration))

        p = self.formulaTree.get_node(parentID)
        pNode = p.data
        if pNode.type == ExprEnum.statement:
            pNode.declaration = d.data

        return self.visitChildren(ctx, id)

    # Visit a parse tree produced by SignalTemporalLogicParser#boolExpr.
    def visitBoolExpr(self, ctx, parentID=None):
        #print("bool expr")
        boolId = self.generateID(ExprEnum.boolExpr)
        bi= self.formulaTree.create_node(boolId, boolId, parent=parentID, data=BoolExpr(type=ExprEnum.boolExpr))

        clds = []
        for c in ctx.getChildren():
            clds.append(c.getText())

        if "|" in clds:
            ct = clds.count("|")
            for c in range(0,ct):
                id = self.generateID(OperatorEnum.OR)
                b = self.formulaTree.create_node(id, id, parent=boolId, data=Operator_OR())
                bi.data.boolOperator = b.data
        elif "&" in clds:
            ct = clds.count("&")
            for c in range(0, ct):
                id = self.generateID(OperatorEnum.AND)
                b  = self.formulaTree.create_node(id, id, parent=boolId, data=Operator_AND())
                bi.data.boolOperator = b.data
        elif "->" in clds:
            ct = clds.count("->")
            for c in range(0, ct):
                id = self.generateID(OperatorEnum.IMPLIES)
                b = self.formulaTree.create_node(id, id, parent=boolId, data=Operator_IMPLIES())
                bi.data.boolOperator = b.data
        elif "?" in clds:
            ct = clds.count("?")
            for c in range(0, ct):
                id = self.generateID(ExprEnum.missing)
                b = self.formulaTree.create_node(id, id, parent=boolId, data=Missing())
                bi.data.boolOperator = b.data
        else: #no actual and  or implies bool operator
            pass


        # handle bool expr for bool atomic and statement
        p = self.formulaTree.get_node(parentID)
        pNode = p.data
        if pNode.type == AtomicEnum.BooleanAtomic:
            pNode.boolExpr = bi.data
        elif pNode.type == ExprEnum.statement:
            pNode.boolExpr = bi.data


        return self.visitChildren(ctx, boolId)


    # Visit a parse tree produced by SignalTemporalLogicParser#stlTerm.
    def visitStlTerm(self, ctx, parentID=None):
        #print("stlTerm")

        stlID = self.generateID(ExprEnum.stlTerm)
        st = self.formulaTree.create_node(stlID, stlID, parent=parentID, data=STLTerm(type=ExprEnum.stlTerm))
        stData = st.data

        #Handle bool expr
        p = self.formulaTree.get_node(parentID)
        pNode = p.data
        if pNode.type == ExprEnum.boolExpr:
            if pNode.stlTerm1 == None:
                pNode.stlTerm1 = st.data
            elif pNode.stlTerm2 == None:
                pNode.stlTerm2 = st.data
            else:
                pNode.stlTerm2 = [pNode.stlTerm2, st.data]


        clds = []
        for c in ctx.getChildren():
            clds.append(c.getText())

        if "G" in clds:
            id = self.generateID(OperatorEnum.G)
            g = self.formulaTree.create_node(id, id, parent=stlID, data=Operator_G())
            stData.tempOperator = g.data
        elif "F" in clds:
            id = self.generateID(OperatorEnum.F)
            f = self.formulaTree.create_node(id, id, parent=stlID, data=Operator_F())
            stData.tempOperator = f.data
        elif "U" in clds:
            id = self.generateID(OperatorEnum.U)
            u = self.formulaTree.create_node(id, id, parent=stlID, data=Operator_U())
            stData.tempOperator = u.data
        elif "?" in clds:
            if clds != ['?']:
                id = self.generateID(ExprEnum.missing)
                u = self.formulaTree.create_node(id, id, parent=stlID, data=Operator())
                stData.tempOperator = u.data
        else:
            pass

        return self.visitChildren(ctx, stlID)


    # Visit a parse tree produced by SignalTemporalLogicParser#timeBound.
    def visitTimeBound(self, ctx, parentID=None):
        #print("timebound")
        time = ctx.getText()
        numbers = re.findall(r"[\w|?']+", time)
        id = self.generateID(ExprEnum.timeBound)
        tb = self.formulaTree.create_node(id, id, parent=parentID, data=TimeBound(lowerBound=numbers[0], upperBound=numbers[1]))

        #handle timebound for stl  term
        p = self.formulaTree.get_node(parentID)
        pNode = p.data
        if pNode.type == ExprEnum.stlTerm:
            pNode.timebound = tb.data


        return self.visitChildren(ctx, "NA")


    # Visit a parse tree produced by SignalTemporalLogicParser#booelanAtomic.
    def visitBooelanAtomic(self, ctx, parentID=None):
        #print("boolean expr")


        clds = []
        for c in ctx.getChildren():
            clds.append(c.getText())


        if "true" in clds or "false" in clds:
            id = self.generateID(AtomicEnum.BooleanAtomic)
            b = self.formulaTree.create_node(id, id, parent=parentID, data=BooleanAtomic(truthVal=clds))
        elif "?" in clds:
            id = self.generateID(AtomicEnum.BooleanAtomic)
            b = self.formulaTree.create_node(id, id, parent=parentID, data=BooleanAtomic(missing=Missing()))
        else:
            id = self.generateID(AtomicEnum.BooleanAtomic)
            b = self.formulaTree.create_node(id, id, parent=parentID, data=BooleanAtomic())

        if "!" in clds:
            b.data.notExpr = True

        #handle bool atomic for stl term
        p = self.formulaTree.get_node(parentID)
        pNode = p.data
        if pNode.type == ExprEnum.stlTerm:
            if pNode.boolAtomic1 == None:
                pNode.boolAtomic1 = b.data
            else:
                pNode.boolAtomic2 = b.data

        return self.visitChildren(ctx, id)


    # Visit a parse tree produced by SignalTemporalLogicParser#relationalExpr.
    def visitRelationalExpr(self, ctx, parentID=None):
        #print("relational expr")

        clds = []
        for c in ctx.getChildren():
            clds.append(c.getText())

        if "<" in clds:
            id = self.generateID(OperatorEnum.LT)
            r = self.formulaTree.create_node(id, id, parent=parentID, data=Operator_LT())
        elif "<=" in clds:
            id = self.generateID(OperatorEnum.LE)
            r = self.formulaTree.create_node(id, id, parent=parentID, data=Operator_LE())
        elif ">" in clds:
            id = self.generateID(OperatorEnum.GT)
            r = self.formulaTree.create_node(id, id, parent=parentID, data=Operator_GT())
        elif ">=" in clds:
            id = self.generateID(OperatorEnum.GE)
            r = self.formulaTree.create_node(id, id, parent=parentID, data=Operator_GE())
        elif "=" in clds:
            id = self.generateID(OperatorEnum.EQ)
            r = self.formulaTree.create_node(id, id, parent=parentID, data=Operator_EQ())
        elif "!=" in clds:
            id = self.generateID(OperatorEnum.NEQ)
            r = self.formulaTree.create_node(id, id, parent=parentID, data=Operator_NEQ())
        else: #missing
            id = self.generateID(ExprEnum.missing)
            r = self.formulaTree.create_node(id, id, parent=parentID, data=RelationalOperator(type=OperatorEnum.NONE))

        #handle bool atomic
        p = self.formulaTree.get_node(parentID)
        pNode = p.data
        if pNode.type == AtomicEnum.BooleanAtomic:
            pNode.relExpr = r.data

        return self.visitChildren(ctx, id)


    def visitAtomic(self, ctx, parentID=None):

        if parentID != "NA":
            if ctx.getText().lstrip('-+').replace('.', '', 1).isdigit():
                id = self.generateID(AtomicEnum.Parameter)
                n=self.formulaTree.create_node(id, id, parent=parentID, data=Parameter(name="", value=ctx.getText()))
            elif "theta_" in ctx.getText():
                id = self.generateID(AtomicEnum.Parameter)
                n = self.formulaTree.create_node(id, id, parent=parentID, data=Parameter(name=ctx.getText(), value=0))
            else:
                id = self.generateID(AtomicEnum.Variable)
                n=self.formulaTree.create_node(id, id, parent=parentID, data=Variable(value=ctx.getText()))

            #add atomics to relop
            p = self.formulaTree.get_node(parentID)
            pNode = p.data

            if isinstance(pNode, RelationalOperator):
                if pNode.atomic1 == None:
                    pNode.atomic1 = n.data
                else:
                    pNode.atomic2 = n.data

        return ctx.getText()

    #generate unique ids for tree
    def generateID(self, type):
        if type in self.idDict:
            val = self.idDict.get(type) + 1
            self.idDict[type] = val
        else:
            val = 1
            self.idDict[type] = val

        return type.name + str(val)

