#!/usr/bin/python
import sys
from rpy import *
import sets,re

def crash(s):
    print >>sys.stderr,s
    sys.exit(1)

def main():

    message = "%s infile outfile formula" % sys.argv[0]

    if len(sys.argv) >= 4:
        datafile = sys.argv[1]
        outfile = sys.argv[2]
        formula = sys.argv[3]
    else: crash(message)

    if len(sys.argv) == 5:
        if sys.argv[4].find('none') < 0:
            tmp_rhs = sys.argv[4]
            tmp_rhs = tmp_rhs.replace(',','/')
            group_terms =  re.compile('c[0-9]+').findall(tmp_rhs)
            if len(group_terms) > 0:
                dep_var = group_terms[0]
                tmp_rhs = "|".join([ dep_var, tmp_rhs])
                formula = '~'.join([formula,tmp_rhs])
            else:
                crash("%s unrecognized for groups" % tmp_rhs)
        elif sys.argv[4] is 'none': pass

    of = open(outfile,'w')

    set_default_mode(NO_CONVERSION)
    df = read_table(datafile)

    # summary function and return labels

    f = r("function(x) { c(sum=sum(x,na.rm=T),mean=mean(x,na.rm=T),stdev=sd(x,na.rm=T),quantile(x,na.rm=TRUE))}")
    returns = ['sum', 'mean','stdev','0%', '25%', '50%', '75%', '100%']

    lhs = ""
    rhs = ""

    lhs_allowed = S3_METHODS()['Math']
    lhs_allowed.append( 'c' ) 

    ops_allowed = S3_METHODS()['Ops']
    ops_allowed = ops_allowed + ['(', ')', '~', ',']
    #print ops_allowed
    
    if formula.find("~") > 0:
        lhs,rhs = formula.split('~')
    else: 
        lhs = formula
    #for word in re.compile('[a-zA-Z]+').findall(lhs):
    for word in re.compile('[a-zA-Z]+').findall(formula):
        if word and not word in lhs_allowed: 
            crash("%s: Function/term %s is not recognized" % (formula,word))
    #for symbol in re.compile('[^a-z0-9\s]+').findall(lhs):
    for symbol in re.compile('[^a-z0-9\s]+').findall(formula):
        if symbol and not symbol in ops_allowed:
            crash("Operator \"%s\" is not recognized" % symbol)
    if not rhs:
        for col in re.compile('c[0-9]+').findall(lhs):
           r.assign(col,r["$"](df,col)) 
        try:
            summary = f(r(lhs))
        except RException, s:
            crash("Error! Choose a numeric column or expression.  The error was:\n\t%s" % s)

        summary = summary.as_py(BASIC_CONVERSION)
        print >>of,"#%s" % "\t".join(returns)
        print >>of,"\t".join([ "%.3f" % (summary[k]) for k in returns])
    
    else:

        # prepare R structures

        r.library("nlme",warn_conflicts=r.FALSE)
        r.library("lattice",warn_conflicts=r.FALSE)
        set_default_mode(NO_CONVERSION)

        try:
            df_g = r.groupedData(r.formula(formula), df)
            df_r = r.groupedData(r.formula(formula), r.data_frame(df_g, response=r.getResponse(df_g)))
        except RException, s:
            crash("Error! Choose a numeric column or expression on the left hand side.  The error was:\n\t%s" % s)


        # try some plotting stuff
        if (0):
            outfile = "plots.pdf"
        #   r.pdf(file=outfile,width=6,height=6)
        #    r.histogram(df_g)
            r.plot_default(df_g)
            r.dev_off()

        # apply summary function and returns

        summary_obj = r.gsummary(df_r,FUN=f)
        summary_response = r["$"](summary_obj,"response").as_py(BASIC_CONVERSION).tolist()
        summary_labels = r.rownames(summary_obj).as_py(BASIC_CONVERSION)

        print >>of,"%s\t%s" % ("#group","\t".join(returns))
        for index,row in enumerate( summary_labels ):
            print >>of,"%s: " % row,
            print >>of,"\t".join([ "%.3f" % (summary_response[index][k]) for k in returns])

def read_table(datafile):
    table = {}
    width = 0
    for line in open(datafile):
        line = line.strip()
        f = line.split()
        if not width: width = len(f)

        for col_i,val in enumerate(f):
            colname = "c" + str(col_i + 1) # c1 .. cn
            if not table.has_key( colname ): table[colname] = []
            table[colname].append( val )

    ### r dataframe:  c1=table['c1'], c2=table['c2'], ...

    terms = ["%s = %s(table[\"%s\"])" % (x,mode_func(table[x][0]),x) for x in ["c" + str(col_i + 1) for col_i in range(0,width)]]
    code = "d = r.data_frame(%s)" % ",".join(terms)
    #print >>sys.stderr,code

    try:
        exec code
    except Exception, e: 
        crash(e)
    return d


def mode_func(c):
    try:
        check = float(c)
        return "r.as_numeric"
    except:
        return "r.as_factor"

def order_for_display(l):
    if l[0].startswith("chr"):
        l.sort(byChr)
    else: l.sort() # alphanumerically
    return l

def byChr(a,b):

    fa = a.split()
    fb = b.split()

    if chrint(fa[0]) < chrint(fb[0]): return -1
    elif chrint(fa[0]) > chrint(fb[0]): return 1
    else:
        if len(fa) > 1 and len(fb) > 1:
            if int(fa[1]) < int(fb[1]): return -1
            elif int(fa[1]) > int(fb[1]): return 1
            else:
                if int(fa[2]) < int(fb[2]): return -1
                elif int(fa[2]) > int(fb[2]): return 1
    return 0

def chrint( x ):

    i = x.replace("chr","")
    if (i == "X"): return 23
    elif (i == "Y"): return 24
    elif (i == "Un"): return 25

    # for randoms and whatever
    elif ( i.find("_") > -1):
        parts = i.split("_")
        i = parts[0]
        if (i == "X"): return 23 + 25
        elif (i == "Y"): return 24 + 25
        elif (i == "Un"): return 24 + 25
        try: return 24 + int(i)
        except ValueError: return 0
    else: 
        try: return int(i)
        except ValueError: return 0

def S3_METHODS(all="key"):
    # See the R documentation for groupGeneric
    # help(.Method)

    Group_Math =  [ "abs", "sign", "sqrt", 
    "floor", "ceiling", "trunc",
    "round", "signif",
    "exp", "log", 
    "cos", "sin", "tan",
    "acos", "asin", "atan",
    "cosh", "sinh", "tanh",
    "acosh", "asinh", "atanh",
    "lgamma", "gamma", "gammaCody",
    "digamma", "trigamma",
    "cumsum", "cumprod", "cummax", "cummin"]

    Group_Ops = [ "+", "-", "*", "/", "^", "%%", "%/%",
    "&", "|", "!",
    "==", "!=", "<", "<=", ">=", ">"]

    Group_Summary = [ "all", "any"
    "sum", "prod",
    "min", "max",
    "range" ]

    if all is "key": return { 'Math' : Group_Math, 'Ops' : Group_Ops, 'Summary' : Group_Summary }


if __name__ == "__main__": main()
