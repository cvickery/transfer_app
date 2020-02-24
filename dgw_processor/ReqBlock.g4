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

req_block   : BEGIN head ';' body ENDDOT <EOF>;
head       :
            ( mingpa
            | minres
            | mingrade
            | numclasses
            | numcredits
            | maxcredits
            | maxclasses
            | maxpassfail
            | proxy_advice
            | share
            | remark
            | label
            )*
            ;
body        : rule_subset
            | blocktype
            | mingrade
            | label
            | remark
            | numclasses
            | numcredits
            | maxperdisc
            ;

class_item  : (SYMBOL | WILDSYMBOL)? (CATALOG_NUMBER | WILDNUMBER | NUMBER | RANGE) ;
or_courses  : INFROM? class_item (OR class_item)* ;
and_courses : INFROM? class_item (AND class_item)* ;

rule_subset : BEGINSUB (numclasses | numcredits label)+ ENDSUB label ;
blocktype   : NUMBER BLOCKTYPE SHARE_LIST label ;
label       : LABEL ALPHANUM*? STRING ';' label* ;
remark      : REMARK STRING ';' remark* ;
mingpa      : MINGPA NUMBER ;
minres      : MINRES NUMBER (CREDITS | CLASSES) ;
mingrade    : MINGRADE NUMBER ;
numclasses  : (NUMBER | RANGE) CLASSES (and_courses | or_courses)? TAG? label*;
numcredits  : (NUMBER | RANGE) CREDITS (and_courses | or_courses)? TAG? ;
maxclasses  : MAXCLASSES NUMBER (and_courses | or_courses) ;
maxcredits  : MAXCREDITS NUMBER (and_courses | or_courses) ;
proxy_advice: PROXYADVICE STRING proxy_advice* ;
share       : SHARE SHARE_LIST ;
maxperdisc  : MAXPERDISC NUMBER (CREDITS | CLASSES) INFROM? LP SYMBOL (',' SYMBOL)* TAG? ;
maxpassfail : MAXPASSFAIL NUMBER (CREDITS | CLASSES) TAG? ;
noncourses  : NUMBER NONCOURSES LP SYMBOL (',' SYMBOL)* RP ;
symbol      : SYMBOL ;

/*
 * Lexer Rules
 */

BEGIN       : [Bb][Ee][Gg][Ii][Nn] ;
ENDDOT      : [Ee][Nn][Dd]DOT ;
STRING      : '"' .*? '"' ;

BEGINSUB    : [Bb][Ee][Gg][Ii][Nn][Ss][Uu][Bb] ;
ENDSUB      : [Ee][Nn][Dd][Ss][Uu][Bb] ;
LABEL       : [Ll][Aa][Bb][Ee][Ll] ;
REMARK      : [Rr][Ee][Mm][Aa][Rr][Kk] ;

CREDITS     : [Cc][Rr][Ee][Dd][Ii][Tt][Ss]? ;
MINCREDITS  : [Mm][Ii][Nn] CREDITS ;
MAXCREDITS  : [Mm][Aa][Xx] CREDITS ;

NONCOURSES  : [Nn][Oo][Nn][Cc][Oo][Uu][Rr][Ss][Ee][Ss]? ;
CLASSES     : [Cc][Ll][Aa][Ss][Ss]([Ee][Ss])? ;
MINCLASSES  : [Mm][Ii][Nn] CLASSES ;
MAXCLASSES  : [Mm][Aa][Xx] CLASSES ;

MAXPERDISC  : [Mm][Aa][Xx][Pp][Ee][Rr][Dd][Ii][Ss][Cc] ;

MINRES      : [Mm][Ii][Nn][Rr][Ee][Ss] ;
MINGPA      : [Mm][Ii][Nn][Gg][Pp][Aa] ;
MINGRADE    : [Mm][Ii][Nn][Gg][Rr][Aa][Dd][Ee] ;
MAXPASSFAIL : [Mm][Aa][Xx][Pp][Aa][Ss][Ss][Ff][Aa][Ii][Ll] ;
PROXYADVICE : [Pp][Rr][Oo][Xx][Yy][\-]?[Aa][Dd][Vv][Ii][Cc][Ee] ;
SHARE       : ([Nn][Oo][Nn] '-'?)?[Ee][Xx][Cc][Ll][Uu][Ss][Ii][Vv][Ee]
            | [Dd][Oo][Nn][Tt][Ss][Ss][Hh][Aa][Rr][Ee]
            | [Ss][Hh][Aa][Rr][Ee]([Ww][Ii][Tt][Hh])?
            ;

BLOCKTYPE   : [Bb][Ll][Oo][Cc][Kk][Tt][Yy][Pp][Ee][Ss]? ;

SHARE_LIST  : LP SHARE_ITEM (COMMA SHARE_ITEM)* RP ;
SHARE_ITEM  : DEGREE | CONC | MAJOR | MINOR | (OTHER (EQ SYMBOL)?) ;

DEGREE      : [Dd][Ee][Gg][Rr][Ee][Ee] ;
CONC        : [Cc][Oo][Nn][Cc] ;
MAJOR       : [Mm][Aa][Jj][Oo][Rr] ;
MINOR       : [Mm][Ii][Nn][Oo][Rr] ;
OTHER       : [Oo][Tt][Hh][Ee][Rr] ;

/* DWResident, DW... etc. are DWIDs */
/* (Decide=DWID) is a phrase used for tie-breaking by the auditor.*/


OR          : (COMMA | ([Oo][Rr])) ;
AND         : (PLUS | ([Aa][Nn][Dd])) ;

INFROM      : ([Ii][Nn])|([Ff][Rr][Oo][Mm]) ;
TAG         : ([Tt][Aa][Gg]) ( EQ SYMBOL )?;

WILDNUMBER  : (DIGIT+ WILDCARD DIGIT* LETTER?) | (WILDCARD DIGIT+ LETTER?) ;
WILDSYMBOL  : ((LETTER | DIGIT)*  WILDCARD (LETTER | DIGIT)*)+ ;
WILDCARD    : '@' ;

CATALOG_NUMBER : NUMBER LETTER ;
RANGE       : NUMBER ':' NUMBER ;
NUMBER      : DIGIT+ (DOT DIGIT*)? ;
SYMBOL      : LETTER (LETTER | DIGIT | '_' | '-' | '&')* ;
ALPHANUM    : (LETTER | DIGIT | DOT | '_')+ ;

GE          : '>=' ;
GT          : '>' ;
LE          : '<=' ;
LT          : '<' ;
EQ          : '=' ;
LP          : '(' ;
RP          : ')' ;
COMMA       : ',' ;
PLUS        : '+' ;

fragment DOT         : '.' ;
fragment DIGIT       : [0-9] ;
fragment LETTER      : [a-zA-Z] ;

HIDE        : '{' [Hh][Ii][Dd][Ee] .*? '}' -> skip ;
DECIDE      : '(' [Dd] [Ee] [Cc] [Ii] [Dd] [Ee] .+? ')' -> skip ;
COMMENT     : '#' .*? '\n' -> skip ;
LOG         : [Ll][Oo][Gg] .*? '\n' -> skip ;
WHITESPACE  : [ \t\n\r]+ -> skip ;
