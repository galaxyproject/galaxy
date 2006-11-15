
def validate(incoming):
    """Validator for the plotting program"""
    
    bins = incoming.get("bins","")
    col  = incoming.get("col","")

    if not bins or not col:
        raise Exception, "You need to specify a number for bins and columns"

    try:
        bins = int(bins)
        col  = int(col)
    except:
        raise Exception, "Parameters are not valid numbers, columns:%s, bins:%s" % (col, bins)

    if not 1<bins<100:
        raise Exception, "The number of bins %s must be a number between 1 and 100" % bins

