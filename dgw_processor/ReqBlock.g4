grammar ReqBlock;

/*
 *  The words reserved by the python antlr runtime are as follows:
 *
 *  python3Keywords = {
 *     "abs", "all", "any", "apply", "as", "assert",
 *     "bin", "bool", "buffer", "bytearray",
 *     "callable", "chr", "classmethod", "coerce", "compile", "complex",
 *     "del", "delattr", "dict", "dir", "divmod",
 *     "enumerate", "eval", "execfile",
 *     "file", "filter", "float", "format", "frozenset",
 *     "getattr", "globals",
 *     "hasattr", "hash", "help", "hex",
 *     "id", "input", "int", "intern", "isinstance", "issubclass", "iter",
 *     "len", "list", "locals",
 *     "map", "max", "min", "next",
 *     "memoryview",
 *     "object", "oct", "open", "ord",
 *     "pow", "print", "property",
 *     "range", "raw_input", "reduce", "reload", "repr", "return", "reversed", "round",
 *     "set", "setattr", "slice", "sorted", "staticmethod", "str", "sum", "super",
 *     "tuple", "type",
 *     "unichr", "unicode",
 *     "vars",
 *     "with",
 *     "zip",
 *     "__import__",
 *     "True", "False", "None"
 *  };
 *
 *  All these raise an error. If they don’t, it’s a bug.
 *
 */

/*
 * Parser Rules
 */

req_text    : .*? req_block .*? EOF ;
req_block   : BEGIN headers ';' rules ENDDOT ;
headers     :
            ( mingpa
            | minres
            | mingrade
            | numclasses
            | numcredits
            | maxcredits
            | maxclasses
            | maxcredits
            | maxpassfail
            | proxy_advice
            | exclusive
            | remark
            | label
            )*
            ;
rules       : .*? ;

or_courses  : INFROM? class_item (OR class_item)* ;
and_courses : INFROM? class_item (AND class_item)* ;

class_item  : (SYMBOL | WILDSYMBOL)? (NUMBER | RANGE | WILDNUMBER) ;
mingpa      : MINGPA NUMBER ;
minres      : MINRES NUMBER (CREDITS | CLASSES) ;
mingrade    : MINGRADE NUMBER ;
numclasses  : NUMBER CLASSES (and_courses | or_courses) ;
numcredits  : (NUMBER | RANGE) CREDITS (and_courses | or_courses)? ;
maxclasses  : MAXCLASSES NUMBER (and_courses | or_courses) ;
maxcredits  : MAXCREDITS NUMBER (and_courses | or_courses) ;
proxy_advice: PROXYADVICE STRING proxy_advice* ;
exclusive   : EXCLUSIVE '(' ~')'* ')' ;
maxpassfail : MAXPASSFAIL NUMBER (CREDITS | CLASSES) (TAG '=' SYMBOL)? ;
remark      : REMARK STRING ';' remark* ;
label       : LABEL ALPHANUM? STRING ';'? label* ;

/*
 * Lexer Rules
 */

BEGIN       : [Bb][Ee][Gg][Ii][Nn] ;
ENDDOT      : [Ee][Nn][Dd]DOT ;
STRING      : '"' .*? '"' ;


LABEL       : [Ll][Aa][Bb][Ee][Ll] ;
REMARK      : [Rr][Ee][Mm][Aa][Rr][Kk] ;

CREDITS     : [Cc][Rr][Ee][Dd][Ii][Tt][Ss]? ;
MINCREDITS  : [Mm][Ii][Nn] CREDITS ;
MAXCREDITS  : [Mm][Aa][Xx] CREDITS ;


CLASSES     : [Cc][Ll][Aa][Ss][Ss]([Ee][Ss])? ;
MINCLASSES  : [Mm][Ii][Nn] CLASSES ;
MAXCLASSES  : [Mm][Aa][Xx] CLASSES ;


MINRES      : [Mm][Ii][Nn][Rr][Ee][Ss] ;
MINGPA      : [Mm][Ii][Nn][Gg][Pp][Aa] ;
MINGRADE    : [Mm][Ii][Nn][Gg][Rr][Aa][Dd][Ee] ;
MAXPASSFAIL : [Mm][Aa][Xx][Pp][Aa][Ss][Ss][Ff][Aa][Ii][Ll] ;
PROXYADVICE : [Pp][Rr][Oo][Xx][Yy][\-]?[Aa][Dd][Vv][Ii][Cc][Ee] ;
EXCLUSIVE   : [Ee][Xx][Cc][Ll][Uu][Ss][Ii][Vv][Ee]
            | [Nn][Oo][Nn] '-'? EXCLUSIVE
            ;


BLOCKTYPE   : ([Dd][Ee][Gg][Rr][Ee][Ee]
            | [Cc][Oo][Nn][Cc]
            | [Mm][Aa][Jj][Oo][Rr]
            | [Mm][Ii][Nn][Oo][Rr]
            | [Oo][Tt][Hh][Ee][Rr])
            ;

/* DWResident, DW... etc. are DWIDs */
/* (Decide=DWID) is a phrase used for tie-breaking by the auditor.*/


OR          : (COMMA | ([Oo][Rr])) ;
AND         : (PLUS | ([Aa][Nn][Dd])) ;

INFROM      : ([Ii][Nn])|([Ff][Rr][Oo][Mm]) ;
TAG         : [Tt][Aa][Gg] ;

WILDNUMBER  : (DIGIT+ WILDCARD DIGIT*) | (WILDCARD DIGIT+) ;
WILDSYMBOL  : ((LETTER | DIGIT)*  WILDCARD (LETTER | DIGIT)*)+ ;

RANGE       : NUMBER ':' NUMBER ;
NUMBER      : DIGIT+ DOT? DIGIT* ;
SYMBOL      : LETTER (LETTER | DIGIT | '_')* ;
ALPHANUM    : (LETTER | DIGIT | DOT | '_')+ ;
WILDCARD    : '@' ;

GE          : '>=' ;
GT          : '>' ;
LE          : '<=' ;
LT          : '<' ;

fragment DOT         : '.' ;
fragment COMMA       : ',' ;
fragment PLUS        : '+' ;
fragment DIGIT       : [0-9] ;
fragment LETTER      : [a-zA-Z] ;

HIDE        : '{' [Hh][Ii][Dd][Ee] .*? '}' -> skip ;
DECIDE      : '(' [Dd] [Ee] [Cc] [Ii] [Dd] [Ee] .+? ')' -> skip ;
COMMENT     : '#' .*? '\n' -> skip ;
LOG         : [Ll][Oo][Gg] .*? '\n' -> skip ;
WHITESPACE  : [ \t\n\r]+ -> skip ;
