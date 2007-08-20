#!/usr/bin/python
# Greg Von Kuster

import sys
from rpy import *
import sets,re

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

def stop_out(msg):
    sys.stdout.write(msg)
    sys.exit()

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
    if chrint(fa[0]) < chrint(fb[0]): 
        return -1
    elif chrint(fa[0]) > chrint(fb[0]): 
        return 1
    else:
        if len(fa) > 1 and len(fb) > 1:
            if int(fa[1]) < int(fb[1]): 
                return -1
            elif int(fa[1]) > int(fb[1]): 
                return 1
            else:
                if int(fa[2]) < int(fb[2]): 
                    return -1
                elif int(fa[2]) > int(fb[2]): 
                    return 1
    return 0

def chrint( x ):
    i = x.replace("chr","")
    if (i == "X"): 
        return 23
    elif (i == "Y"): 
        return 24
    elif (i == "Un"): 
        return 25
    # for randoms and whatever
    elif ( i.find("_") > -1):
        parts = i.split("_")
        i = parts[0]
        if (i == "X"): 
            return 23 + 25
        elif (i == "Y"): 
            return 24 + 25
        elif (i == "Un"): 
            return 24 + 25
        try: 
            return 24 + int(i)
        except ValueError: 
            return 0
    else: 
        try: 
            return int(i)
        except ValueError: 
            return 0

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
    Group_Ops = [ "+", "-", "*", "/", "^", "%%", "%/%", "&", "|", "!", "==", "!=", "<", "<=", ">=", ">"]
    Group_Summary = [ "all", "any", "sum", "prod", "min", "max", "range" ]

    if all is "key": return { 'Math' : Group_Math, 'Ops' : Group_Ops, 'Summary' : Group_Summary }

def read_table(datafile, cols):
    table = {}
    width = 0
    skipped_lines = 0
    first_invalid_line = 0
    for i, line in enumerate(file(datafile)):
        valid = True
        line = line.rstrip('\r\n')
        if line and not line.startswith( '#' ):
            f = line.split()
            for col in cols:
                if col > len(f):
                    valid = False
                    skipped_lines += 1
                    if not first_invalid_line:
                        first_invalid_line = i+1
                    break
                if valid:
                    """
                    Make sure the column value is numeric
                    """
                    try:
                        check = float(f[col-1])
                    except:
                        valid = False
                        skipped_lines += 1
                        if not first_invalid_line:
                            first_invalid_line = i+1
                        break
            if valid:
                for col_i, val in enumerate(f):
                    """
                    Create column names c1..cn
                    """
                    colname = "c" + str(col_i + 1)
                    if not table.has_key( colname ): 
                        table[colname] = []
                    table[colname].append( val )
                if not width:
                    width = len(f)
    if len(table) > 0:
        """
        terms will look like this: c7 = r.as_numeric(table["c7"]), c8 = r.as_numeric(table["c8"]), ...
        """
        terms = ["%s = %s(table[\"%s\"])" % (x, mode_func(table[x][0]), x) for x in ["c" + str(col_i + 1) for col_i in range(0, width)]]
        code = "d = r.data_frame(%s)" % ",".join(terms)
        try:
            exec code
        except Exception, e: 
            stop_err(e)
        return (skipped_lines, first_invalid_line, d)
    else:
        return (skipped_lines, first_invalid_line, None)

def main():

    if len(sys.argv) >= 4:
        datafile = sys.argv[1]
        outfile = sys.argv[2]
        expression = sys.argv[3]
    else: 
        print sys.argv
        stop_err('Usage: python gsummary.py input_file ouput_file expression')

    if len(sys.argv) == 5:
        if sys.argv[4].find('none') < 0:
            tmp_rhs = sys.argv[4]
            tmp_rhs = tmp_rhs.replace(',','/')
            group_terms =  re.compile('c[0-9]+').findall(tmp_rhs)
            if len(group_terms) > 0:
                dep_var = group_terms[0]
                tmp_rhs = "|".join([ dep_var, tmp_rhs])
                expression = '~'.join([expression,tmp_rhs])
            else:
                stop_err("%s unrecognized for groups" % tmp_rhs)
        elif sys.argv[4] is 'none': 
            pass

    """
    summary function and return labels
    """
    f = r("function(x) { c(sum=sum(x,na.rm=T),mean=mean(x,na.rm=T),stdev=sd(x,na.rm=T),quantile(x,na.rm=TRUE))}")
    returns = ['sum', 'mean','stdev','0%', '25%', '50%', '75%', '100%']

    lhs = ""
    rhs = ""

    lhs_allowed = S3_METHODS()['Math']
    lhs_allowed.append( 'c' ) 

    ops_allowed = S3_METHODS()['Ops']
    ops_allowed = ops_allowed + ['(', ')', '~', ',']

    of = open(outfile,'w')
    
    if expression.find("~") > 0:
        lhs,rhs = expression.split('~')
    else: 
        lhs = expression

    for word in re.compile('[a-zA-Z]+').findall(expression):
        if word and not word in lhs_allowed: 
            of.close()
            stop_out("Invalid expression '%s': term '%s' is not recognized or allowed" % (expression, word))

    """
    Users sometimes want statistics for more than 1 column, so they enter a comma-separated
    string of columns in the free text field.  This tool only handles a single column or an
    expression (computed for 1 or more columns), so we'll use the following hack to provide a
    useful response for multiple column entries.
    """
    symbols = sets.Set()
    for symbol in re.compile('[^a-z0-9\s]+').findall(expression):
        if symbol and not symbol in ops_allowed:
            of.close()
            stop_out("Invalid expression '%s': operator '%s' is not recognized or allowed" % (expression, symbol))
        else:
            symbols.add(symbol)
    if len(symbols) == 1 and ',' in symbols:
        of.close()
        stop_out( "Invalid columns '%s': this tool requires a single column or expression" %expression )

    cols = []
    if lhs:
        for col in re.compile('c[0-9]+').findall(lhs):
            try:
                cols.append(int(col[1:]))
            except:
                # This is a weakness, but hopefully we won't arrive here
                pass

    if rhs:
        for col in re.compile('c[0-9]+').findall(rhs):
            try:
                cols.append(int(col[1:]))
            except:
                # This is a weakness, but hopefully we won't arrive here
                pass
         
    set_default_mode(NO_CONVERSION)
    skipped_lines, first_invalid_line, df = read_table(datafile, cols)   
    
    if df is not None:
        if not rhs:
            for col in re.compile('c[0-9]+').findall(lhs):
                r.assign(col,r["$"](df,col)) 
            try:
                summary = f(r(lhs))
            except RException, s:
                # Due to previous checking, this should not occur
                of.close()
                stop_err("Computation attempted on invalid data in column %s.  Exception: %s" %(lhs, s))

            summary = summary.as_py(BASIC_CONVERSION)
            print >>of,"#%s" % "\t".join(returns)
            print >>of,"\t".join([ "%.3f" % (summary[k]) for k in returns])
        else:
            """
            Prepare R structures
            """
            r.library("nlme",warn_conflicts=r.FALSE)
            r.library("lattice",warn_conflicts=r.FALSE)
            set_default_mode(NO_CONVERSION)

            try:
                df_g = r.groupedData(r.expression(expression), df)
                df_r = r.groupedData(r.expression(expression), r.data_frame(df_g, response=r.getResponse(df_g)))
            except RException, s:
                stop-err("Computation attempted on invalid data in column on the left hand side of expression.  Exception:\n\t%s" % s)

            """
            Try some plotting stuff
            """
            if (0):
                outfile = "plots.pdf"
                #   r.pdf(file=outfile,width=6,height=6)
                #   r.histogram(df_g)
                r.plot_default(df_g)
                r.dev_off()

            """
            Apply summary function and returns
            """
            summary_obj = r.gsummary(df_r,FUN=f)
            summary_response = r["$"](summary_obj,"response").as_py(BASIC_CONVERSION).tolist()
            summary_labels = r.rownames(summary_obj).as_py(BASIC_CONVERSION)

            print >>of,"%s\t%s" % ("#group","\t".join(returns))
            for index,row in enumerate( summary_labels ):
                print >>of,"%s: " % row,
                print >>of,"\t".join([ "%.3f" % (summary_response[index][k]) for k in returns])
        
        if skipped_lines > 0:
            print "..Skipped %d lines in query beginning with line #%d due to data issues.  See tool tips for data requirements." % (skipped_lines, first_invalid_line)
    else:
        print "..Entire data column consisting of %d lines invalid for computation.  See tool tips for data requirements." %skipped_lines

if __name__ == "__main__": main()
