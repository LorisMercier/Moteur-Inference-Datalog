import re
from keyword import iskeyword
import pandas as pd
import sys


class DatalogInternalError(Exception):
    pass


base = {}
lineNumber = 0
fileNameIn = ""
fileNameOut = "out.txt"
listAggregateFct = ["COUNT", "AVG", "SUM", "MAX", "MIN"]
listOperator = ["==", "!=", "<=", ">=", "<", ">"]

def printBDD(base):
    print("{\n" + "\n".join("{!r}:\n {!r},".format(k, v) for k, v in base.items()) + "\n}")

def printIDB(df, idbName, idbArgs):
    param = "(" + ", ".join(str(element) for element in idbArgs) + ")"
    dfAsString = df.to_string(header=False, index=False)
    print(idbName + param + ':')
    print(dfAsString + '\n')

def writeIDBintoFile(dfRes, idbName, idbArgs, firstIDB, fileName):
    if(firstIDB):
        f = open(fileName, "w")
    else:
        f = open(fileName, "a")        
    param = "(" + ", ".join(str(element) for element in idbArgs) + ")"
    f.write(idbName + param + ':\n')
    dfAsString = dfRes.to_string(header=False, index=False)
    f.write(dfAsString+'\n\n')
    f.close()

def convStrToNumber(str):
    try:        
        return int(str)
    except ValueError:
        try:
            return float(str)
        except ValueError:
            return str
        
def createColumnName(name, number):
    return name + '_' + str(number)

def addEDBLineToBase(key, tokens):
    df = base[key]
    df.loc[len(df)] = tokens

def removeFirstToken(tokens):
    return tokens[1:]

def removeFinalPoint(tokens):
    # If last token is a point
    if(tokens[-1] == '.'):
        return tokens[:-1]
    
    #If last token have a point at the end
    elif tokens[-1][-1] == '.':
        tokens[-1] = tokens[-1][:-1]
        return tokens
    else:
        raise DatalogInternalError(
            f"In '{fileNameIn}', line '{lineNumber}' : Missing '.' at the end of the line"
        )

def checkRuleName(key):
    if not(key[0].islower()):
        raise DatalogInternalError(
            f"In '{fileNameIn}', line '{lineNumber}' : rule '{key}' should start with a lowercase letter"
        )
    
def isIDB(tokens):
    if ':' in tokens:
        return True
    return False

def checkDBArgsNumber(key, tokens):
    if len(tokens) != len(base[key].columns):
        raise DatalogInternalError(
            f"In '{fileNameIn}', line '{lineNumber}' : Wrong number of arguments for '{key}' rule. Expected {len(base[key].columns)}, found {len(tokens)}"
        )
    else:
        return True
    
def treatEDBRule(tokens):
    key = tokens[0]
    checkRuleName(key)
    tokens = removeFirstToken(tokens)
    if not(key in base):
        #if not in known rules, add it to the base
        columnsName = []
        for ind,token in enumerate(tokens):
            columnsName.append(createColumnName(key,ind))
        base[key] = pd.DataFrame([tokens], columns=columnsName)
    else:
        #if the rule already exists, check that the right number of args are given
        checkDBArgsNumber(key, tokens)
        addEDBLineToBase(key, tokens)

def getArgsForIDB(tokens):
    i = 0
    args = []
    while tokens[i] != ':':
        args.append(tokens[i])
        i += 1
    return args

def removeArgsForIDB(tokens):
    i = 0
    while tokens[i] != ':':
        i += 1
    #1 more to remove the dots
    i += 1
    return tokens[i:]

def getArgsForRule(tokens, number):
    return tokens[:number]

def removeArgsForRule(tokens, number):
    return tokens[number:]

def whichElementInList(liste, chaine):
    for element in liste:
        if element in chaine:
            return element
    return ""

def parseIDBBody(tokens):
    global listAggregateFct
    global listOperator
    rules = []

    while len(tokens) > 0:
        tmpListOneToken = [[],[]]    
        key = tokens[0]
        tokens = removeFirstToken(tokens)

        # check if key contain operator and return operator if true
        op = whichElementInList(listOperator,key)

        if key in base:
            #next token is a rule in base
            ruleArgsLen = len(base[key].columns)
            ruleArgs = getArgsForRule(tokens, ruleArgsLen)
            tokens = removeArgsForRule(tokens, ruleArgsLen)
            tmpListOneToken[0] = key 
            tmpListOneToken[1] = ruleArgs
            rules.append(tmpListOneToken)

        #agregate functions
        elif key in listAggregateFct:
            ruleArgsLen = 2
            ruleArgs = getArgsForRule(tokens, ruleArgsLen)
            tokens = removeArgsForRule(tokens, ruleArgsLen)
            tmpListOneToken[0] = key 
            tmpListOneToken[1] = ruleArgs
            rules.append(tmpListOneToken)

        #if operator in key
        elif op != "":
            #get arguments at left/right of operator
            ruleArgs = key.split(op)
            tokens = removeArgsForRule(tokens, 0)
            tmpListOneToken[0] = op 
            tmpListOneToken[1] = ruleArgs
            rules.append(tmpListOneToken)

        else:
            raise DatalogInternalError(
                f"In '{fileNameIn}', line '{lineNumber}' : Error with the predicate '{key}'. Check syntax or if predicate exists"
            )

    return rules

def isVarArg(args):
    if isinstance(args, str):
        return args[0].isupper()
    else:
        return False

def treatIDBRule(tokens, firstIDB):
    global listAggregateFct
    global listOperator
    
    #idb name
    idbName = tokens[0]
    checkRuleName(idbName)
    tokens = removeFirstToken(tokens)

    #idb args
    idbArgs = getArgsForIDB(tokens)
    tokens = removeArgsForIDB(tokens)

    #idb body
    rules = parseIDBBody(tokens)

    if idbName in base:
        checkDBArgsNumber(idbName, listInd)

    print(" --TRAITEMENT DE IDB '" + idbName + "'--")
    
    #dataframe for results
    dfRes = pd.DataFrame()

    #Dict to keep the index of the column for each variable
    varColumnName = {}

    # {name: ['X', 'Y'], '==': ['X', 'Y']}

    #for each XDB=EDB/IDB of the body
    for predicate in rules:
        predicateName = predicate[0]
        predicateArg = predicate[1]         
        #agregate functions
        if predicateName in listAggregateFct:
            #retrieve all columns but the one we count on -> act like a group by
            column = varColumnName[predicateArg[0]]
            allColumns = list(dfRes.columns)
            allColumns.remove(column)

            if predicateName == "COUNT":    
                #agregate function
                dfRes = dfRes.groupby(allColumns, as_index=False).count()

            else:
                #Conversion to numeric, otherwise computation doesn't work
                dfRes[column] = pd.to_numeric(dfRes[column])

                if predicateName == "AVG":
                    #agregate function
                    dfRes = dfRes.groupby(allColumns, as_index=False).mean()

                elif predicateName == "SUM":
                    #agregate function
                    dfRes = dfRes.groupby(allColumns, as_index=False).sum()
                
                elif predicateName == "MAX":
                    #agregate function
                    dfRes = dfRes.groupby(allColumns, as_index=False).max()

                elif predicateName == "MIN":
                    #agregate function
                    dfRes = dfRes.groupby(allColumns, as_index=False).min()
                
            #name of the result column
            varColumnName[predicateArg[1]] = column

        #Operator
        elif predicateName in listOperator:
            listTypeOfArg = [[],[]]
            for ind, arg in enumerate(predicateArg):
                #if arg is a var (i.e. first car is upper)
                if(isVarArg(arg)):
                    #if var already exists in the result
                    if arg in varColumnName:  
                        #We store the type and the column name of the arg  
                        listTypeOfArg[ind].append("var")  
                        listTypeOfArg[ind].append(varColumnName[arg])                          
                    else:
                        #if arg is undefined, we can't evaluate the constraint
                        raise DatalogInternalError(
                            f"In '{fileNameIn}', line '{lineNumber}' : Undefined variable => {arg}"
                        )
                else:
                    #We store the type and the value of the arg 
                    listTypeOfArg[ind].append("atom")
                    listTypeOfArg[ind].append(arg)

            paramsOfFilter = []
            # Preparation of filter
            for ind, token in enumerate(listTypeOfArg):
                if token[0] == 'var':
                    # if operator with numeric value
                    if not(predicateName == '==') and not(predicateName == '!='):
                        dfRes[token[1]] = pd.to_numeric(dfRes[token[1]])  
                    paramsOfFilter.append("dfRes['"+token[1]+"']")
                else:
                    # if operator with numeric value
                    if not(predicateName == '==') and not(predicateName == '!='):
                        paramsOfFilter.append(token[1])
                    else:
                        #if '==' or '!=
                        paramsOfFilter.append("'"+token[1]+"'")

            #We define the filter
            query = "dfRes[" + paramsOfFilter[0] + predicateName + paramsOfFilter[1] +"]"
            #We apply the filter
            dfRes = eval(query)

        #EDB/IDB
        else:
            #index of the columns for the joins
            listJoin = [[],[]]

            #retrieve the base for the XDB 
            dftmp = base[predicateName]
            
            #for each arg in XDB
            #ind = position in XDB columns
            #arg = name of arg
            for ind, arg in enumerate(predicateArg):
                #if arg is a var (i.e. first car is upper)
                if(isVarArg(arg)):
                    #if var already exists in the result
                    if arg in varColumnName:  
                        #a join is needed, we store the columns on which to join           
                        listJoin[0].append(varColumnName[arg])
                        listJoin[1].append(createColumnName(predicateName,ind))
                    else:
                        # var doesn't already exist in result, we store its location after the join
                        varColumnName[arg] = createColumnName(predicateName, ind)
                        
                elif arg != '_':
                    #arg is not a var (i.e. a value), we filter the base with this value
                    dftmp = dftmp[dftmp[createColumnName(predicateName,ind)] == arg]

                
            if dfRes.empty:
                    #for the first XDB
                    dfRes = dftmp
            else:
                if listJoin[0]:
                    #join dataframe with result dataframe
                    dfRes = pd.merge(dfRes, dftmp, left_on=listJoin[0], right_on=listJoin[1])
                else:
                    #if no join, cartesien product
                    dfRes = pd.merge(dfRes, dftmp, how='cross')

    # we retrieve only the args in the head
    listInd = []
    columnsName = []
    for ind,var in enumerate(idbArgs):
        listInd.append(varColumnName[var])
        columnsName.append(createColumnName(idbName,ind))

    #renaming columns to match base
    dfToAdd = dfRes[listInd]
    dfToAdd.columns = columnsName
    
    #add result to base
    if idbName in base:
        #concat to base
        base[idbName] = pd.concat([base[idbName], dfToAdd])

    else:
        base[idbName] = dfToAdd

    writeIDBintoFile(dfToAdd, idbName, idbArgs, firstIDB, fileNameOut)
    printIDB(dfToAdd, idbName, idbArgs)


def treatRule(tokens,firstIDB):
    tokens = removeFinalPoint(tokens)
    if isIDB(tokens):
        treatIDBRule(tokens,firstIDB)
        firstIDB = False
    else:
        treatEDBRule(tokens)
    return firstIDB

def init(nameFileIn, nameFileOut='out.txt'):
    global lineNumber, fileNameIn, fileNameOut
    lineNumber = 0
    fileNameIn = nameFileIn
    fileNameOut = nameFileOut
    firstIDB = True
    with open(fileNameIn, "r") as file:        
        for line in file:
            lineNumber += 1
            line = line.strip()
            tokens = re.split('[(, )-]',line)
            #remove empty strings created by the parsing
            tokens = [i for i in tokens if i != '']
            if tokens and tokens[0] != "#":
                firstIDB = treatRule(tokens, firstIDB)
            
if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) >=1:
        if len(args) == 1 and ".txt" in args[0] :
            init(args[0])
        if len(args) == 2 and ".txt" in args[0] :
            if not(".txt" in args[1]):
                args[1] = args[1]+'.txt'
            init(args[0], args[1])

    else:
        print("Pas de fichier spécifié...")
        print("Analyse du fichier master.txt")
        init('master.txt')
    