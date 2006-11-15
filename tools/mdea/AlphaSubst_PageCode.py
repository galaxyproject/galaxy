def ShowYesNo(bShowYesNo):
	rval = []
	if bShowYesNo == "0":
		rval.append( ('No','0',True) )
	else:
		rval.append( ('Yes','1',True) )
		rval.append( ('No','0',False) )
	return rval

def ShowBranchAlphaYesNo(CompType,AnalysisType):
	rval = []
	if str(CompType) == "0" or str(AnalysisType) == "0":
		rval.append( ('No','0',True) )
	else:
		rval.append( ('Yes','1',True) )
		rval.append( ('No','0',False) )
	return rval

def ShowGetSE(DoBootStrap):
	rval = []
	if DoBootStrap == 1:
		rval.append( ('Yes','1',True) )
		rval.append( ('No','0',False) )
	else:
		rval.append( ('No','0',True) )
	return rval

def ShowFixKappa(Model):
	rval = []
	if Model == "1" or Model == "3" or Model == "4":
		rval.append( ('No','0',False) )
		rval.append( ('Yes','1',True) )
	else:
		rval.append( ('No','0',True) )
	return rval

def ShowDoubleBoot_AlphaSubst(AnalysisType):
    rval = []
    if int(AnalysisType) == 2:
		rval.append( ('No','0',True) )
		rval.append( ('Yes','1',True) )
    else:
		rval.append( ('No','0',True) )
    return rval

def ShowDoubleBoot(Method):
    rval = []
    if int(Method) == 0:
		rval.append( ('No','0',True) )
    elif int(Method) == 1:
		rval.append( ('No','0',True) )
		rval.append( ('Yes','1',True) )
    return rval

def OutputOptions(Method):
    rval = []
    if int(Method) == 0:
        rval.append( ('baseml output file','txt',True) )
        rval.append( ('Tabular','Tabular',True) )
        rval.append( ('HTML','html',True) )
    elif int(Method) == 1:
        rval.append( ('Tabular','Tabular',True) )
        rval.append( ('HTML','html',True) )

    return rval
