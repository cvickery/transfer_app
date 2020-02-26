# Generated from ReqBlock.g4 by ANTLR 4.8
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .ReqBlockParser import ReqBlockParser
else:
    from ReqBlockParser import ReqBlockParser

# This class defines a complete listener for a parse tree produced by ReqBlockParser.
class ReqBlockListener(ParseTreeListener):

    # Enter a parse tree produced by ReqBlockParser#req_block.
    def enterReq_block(self, ctx:ReqBlockParser.Req_blockContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#req_block.
    def exitReq_block(self, ctx:ReqBlockParser.Req_blockContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#head.
    def enterHead(self, ctx:ReqBlockParser.HeadContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#head.
    def exitHead(self, ctx:ReqBlockParser.HeadContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#body.
    def enterBody(self, ctx:ReqBlockParser.BodyContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#body.
    def exitBody(self, ctx:ReqBlockParser.BodyContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#class_item.
    def enterClass_item(self, ctx:ReqBlockParser.Class_itemContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#class_item.
    def exitClass_item(self, ctx:ReqBlockParser.Class_itemContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#or_courses.
    def enterOr_courses(self, ctx:ReqBlockParser.Or_coursesContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#or_courses.
    def exitOr_courses(self, ctx:ReqBlockParser.Or_coursesContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#and_courses.
    def enterAnd_courses(self, ctx:ReqBlockParser.And_coursesContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#and_courses.
    def exitAnd_courses(self, ctx:ReqBlockParser.And_coursesContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#rule_subset.
    def enterRule_subset(self, ctx:ReqBlockParser.Rule_subsetContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#rule_subset.
    def exitRule_subset(self, ctx:ReqBlockParser.Rule_subsetContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#blocktype.
    def enterBlocktype(self, ctx:ReqBlockParser.BlocktypeContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#blocktype.
    def exitBlocktype(self, ctx:ReqBlockParser.BlocktypeContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#label.
    def enterLabel(self, ctx:ReqBlockParser.LabelContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#label.
    def exitLabel(self, ctx:ReqBlockParser.LabelContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#remark.
    def enterRemark(self, ctx:ReqBlockParser.RemarkContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#remark.
    def exitRemark(self, ctx:ReqBlockParser.RemarkContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#mingpa.
    def enterMingpa(self, ctx:ReqBlockParser.MingpaContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#mingpa.
    def exitMingpa(self, ctx:ReqBlockParser.MingpaContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#minres.
    def enterMinres(self, ctx:ReqBlockParser.MinresContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#minres.
    def exitMinres(self, ctx:ReqBlockParser.MinresContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#mingrade.
    def enterMingrade(self, ctx:ReqBlockParser.MingradeContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#mingrade.
    def exitMingrade(self, ctx:ReqBlockParser.MingradeContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#numclasses.
    def enterNumclasses(self, ctx:ReqBlockParser.NumclassesContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#numclasses.
    def exitNumclasses(self, ctx:ReqBlockParser.NumclassesContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#numcredits.
    def enterNumcredits(self, ctx:ReqBlockParser.NumcreditsContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#numcredits.
    def exitNumcredits(self, ctx:ReqBlockParser.NumcreditsContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#maxclasses.
    def enterMaxclasses(self, ctx:ReqBlockParser.MaxclassesContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#maxclasses.
    def exitMaxclasses(self, ctx:ReqBlockParser.MaxclassesContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#maxcredits.
    def enterMaxcredits(self, ctx:ReqBlockParser.MaxcreditsContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#maxcredits.
    def exitMaxcredits(self, ctx:ReqBlockParser.MaxcreditsContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#proxy_advice.
    def enterProxy_advice(self, ctx:ReqBlockParser.Proxy_adviceContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#proxy_advice.
    def exitProxy_advice(self, ctx:ReqBlockParser.Proxy_adviceContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#share.
    def enterShare(self, ctx:ReqBlockParser.ShareContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#share.
    def exitShare(self, ctx:ReqBlockParser.ShareContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#maxperdisc.
    def enterMaxperdisc(self, ctx:ReqBlockParser.MaxperdiscContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#maxperdisc.
    def exitMaxperdisc(self, ctx:ReqBlockParser.MaxperdiscContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#maxpassfail.
    def enterMaxpassfail(self, ctx:ReqBlockParser.MaxpassfailContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#maxpassfail.
    def exitMaxpassfail(self, ctx:ReqBlockParser.MaxpassfailContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#noncourses.
    def enterNoncourses(self, ctx:ReqBlockParser.NoncoursesContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#noncourses.
    def exitNoncourses(self, ctx:ReqBlockParser.NoncoursesContext):
        pass


    # Enter a parse tree produced by ReqBlockParser#symbol.
    def enterSymbol(self, ctx:ReqBlockParser.SymbolContext):
        pass

    # Exit a parse tree produced by ReqBlockParser#symbol.
    def exitSymbol(self, ctx:ReqBlockParser.SymbolContext):
        pass



del ReqBlockParser