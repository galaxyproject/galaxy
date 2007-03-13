#Dan Blankenberg
#Contains file contents and helper methods for HYPHY configurations
import tempfile, os

def get_filled_temp_filename(contents):
    fh = tempfile.NamedTemporaryFile('w')
    filename = fh.name
    fh.close()
    fh = open(filename, 'w')
    fh.write(contents)
    fh.close()
    return filename

#Hard Coded hyphy path, this will need to be the same across the cluster
HYPHY_PATH = "/home/universe/linux-i686/HYPHY"
HYPHY_EXECUTABLE = os.path.join(HYPHY_PATH,"HYPHY")

BranchLengthsMF = """
VERBOSITY_LEVEL			= -1;
fscanf          		(PROMPT_FOR_FILE, "Lines", inLines);

_linesIn = Columns (inLines);

/*---------------------------------------------------------*/

_currentGene   = 1; 
_currentState = 0;
geneSeqs	  = "";
geneSeqs	  * 128;

for (l=0; l<_linesIn; l=l+1)
{
	if (Abs(inLines[l]) == 0)
	{
		if (_currentState == 1)
		{
			geneSeqs      * 0;
			DataSet 	  ds 		   = ReadFromString (geneSeqs);
			_processAGene (_currentGene);
			geneSeqs * 128;
			_currentGene = _currentGene + 1;
		}
	}
	else
	{
		if (_currentState == 0)
		{
			_currentState = 1;
		}
		geneSeqs * inLines[l];
		geneSeqs * "\\n";
	}
}

if (_currentState == 1)
{
	geneSeqs      * 0;
	if (Abs(geneSeqs))
	{
		DataSet 	  ds 		   = ReadFromString (geneSeqs);
		_processAGene (_currentGene);
	}
}

fprintf (resultFile,CLOSE_FILE);

/*---------------------------------------------------------*/

function _processAGene (_geneID)
{
	DataSetFilter 			filteredData = CreateFilter (ds,1);
	if (_currentGene == 1)
	{
		SelectTemplateModel		(filteredData);
		
		SetDialogPrompt 		("Tree file");
		fscanf	        		(PROMPT_FOR_FILE, "Tree",  givenTree);
		fscanf					(stdin, "String", resultFile);
		
		/* do sequence to branch map */
		
		validNames = {};
		taxonNameMap = {};
		
		for (k=0; k<TipCount(givenTree); k=k+1)
		{
			validNames[TipName(givenTree,k)&&1] = 1;
		}
		
		for (k=0; k<BranchCount(givenTree); k=k+1)
		{
			thisName = BranchName(givenTree,k);
			taxonNameMap[thisName&&1] = thisName;
		}
		
		storeValidNames = validNames;
		fprintf 		(resultFile,CLEAR_FILE,KEEP_OPEN,"Block\\tBranch\\tLength\\tLowerBound\\tUpperBound\\n"); 
	}
	else
	{
		validNames = storeValidNames;
	}
	
	for (k=0; k<ds.species; k=k+1)
	{
		GetString (thisName, ds,k);
		shortName = (thisName^{{"\\\\..+",""}})&&1;
		if (validNames[shortName])
		{
			taxonNameMap[shortName] = thisName;
			validNames - (shortName);
			SetParameter (ds,k,shortName);
		}
		else
		{
			fprintf 		(resultFile,"ERROR:", thisName, " could not be matched to any of the leaves in tree ", givenTree,"\\n"); 
			return 0;
		}
	}
	
	/* */
	
	LikelihoodFunction lf = (filteredData,givenTree);
	
	Optimize 				(res,lf);
	
	timer = Time(0)-timer;
	
	branchNames   = BranchName   (givenTree,-1);
	branchLengths = BranchLength (givenTree,-1);
	
	
	for (k=0; k<Columns(branchNames)-1; k=k+1)
	{
		COVARIANCE_PARAMETER = "givenTree."+branchNames[k]+".t";
		COVARIANCE_PRECISION = 0.95;
		CovarianceMatrix (cmx,lf);
		if (k==0)
		{
			/* compute a scaling factor */
			ExecuteCommands ("givenTree."+branchNames[0]+".t=1");
			scaleFactor = BranchLength (givenTree,0);
			ExecuteCommands ("givenTree."+branchNames[0]+".t="+cmx[0][1]);
		}
		fprintf (resultFile,_geneID,"\\t",taxonNameMap[branchNames[k]&&1],"\\t",branchLengths[k],"\\t",scaleFactor*cmx[0][0],"\\t",scaleFactor*cmx[0][2],"\\n");
	}
	
	ttl = (branchLengths*(Transpose(branchLengths["1"])))[0];
	global treeScaler = 1;
	ReplicateConstraint ("this1.?.t:=treeScaler*this2.?.t__",givenTree,givenTree);
	COVARIANCE_PARAMETER = "treeScaler";
	COVARIANCE_PRECISION = 0.95;
	CovarianceMatrix (cmx,lf);
	fprintf (resultFile,_geneID,"\\tTotal Tree\\t",ttl,"\\t",ttl*cmx[0][0],"\\t",ttl*cmx[0][2],"\\n");
	ClearConstraints (givenTree);
	return 0;
}
"""

BranchLengths = """
DataSet 				ds 			 = ReadDataFile (PROMPT_FOR_FILE);
DataSetFilter 			filteredData = CreateFilter (ds,1);

SelectTemplateModel		(filteredData);

SetDialogPrompt 		("Tree file");
fscanf	        		(PROMPT_FOR_FILE, "Tree",  givenTree);
fscanf					(stdin, "String", resultFile);

/* do sequence to branch map */

validNames = {};
taxonNameMap = {};

for (k=0; k<TipCount(givenTree); k=k+1)
{
	validNames[TipName(givenTree,k)&&1] = 1;
}

for (k=0; k<BranchCount(givenTree); k=k+1)
{
	thisName = BranchName(givenTree,k);
	taxonNameMap[thisName&&1] = thisName;
}

for (k=0; k<ds.species; k=k+1)
{
	GetString (thisName, ds,k);
	shortName = (thisName^{{"\\\\..+",""}})&&1;
	if (validNames[shortName])
	{
		taxonNameMap[shortName] = thisName;
		validNames - (shortName);
		SetParameter (ds,k,shortName);
	}
	else
	{
		fprintf 		(resultFile,CLEAR_FILE,"ERROR:", thisName, " could not be matched to any of the leaves in tree ", givenTree); 
		return 0;
	}
}

/* */

LikelihoodFunction lf = (filteredData,givenTree);

Optimize 				(res,lf);

timer = Time(0)-timer;

branchNames   = BranchName   (givenTree,-1);
branchLengths = BranchLength (givenTree,-1);

fprintf 		(resultFile,CLEAR_FILE,KEEP_OPEN,"Branch\\tLength\\tLowerBound\\tUpperBound\\n"); 

for (k=0; k<Columns(branchNames)-1; k=k+1)
{
	COVARIANCE_PARAMETER = "givenTree."+branchNames[k]+".t";
	COVARIANCE_PRECISION = 0.95;
	CovarianceMatrix (cmx,lf);
	if (k==0)
	{
		/* compute a scaling factor */
		ExecuteCommands ("givenTree."+branchNames[0]+".t=1");
		scaleFactor = BranchLength (givenTree,0);
		ExecuteCommands ("givenTree."+branchNames[0]+".t="+cmx[0][1]);
	}
	fprintf (resultFile,taxonNameMap[branchNames[k]&&1],"\\t",branchLengths[k],"\\t",scaleFactor*cmx[0][0],"\\t",scaleFactor*cmx[0][2],"\\n");
}

ttl = (branchLengths*(Transpose(branchLengths["1"])))[0];
global treeScaler = 1;
ReplicateConstraint ("this1.?.t:=treeScaler*this2.?.t__",givenTree,givenTree);
COVARIANCE_PARAMETER = "treeScaler";
COVARIANCE_PRECISION = 0.95;
CovarianceMatrix (cmx,lf);
ClearConstraints (givenTree);
fprintf (resultFile,"Total Tree\\t",ttl,"\\t",ttl*cmx[0][0],"\\t",ttl*cmx[0][2],"\\n");
fprintf (resultFile,CLOSE_FILE);
"""


SimpleLocalFitter = """
VERBOSITY_LEVEL			   = -1;
COUNT_GAPS_IN_FREQUENCIES  = 0;

/*---------------------------------------------------------*/

function returnResultHeaders (dummy)
{
	_analysisHeaders = {};
	_analysisHeaders[0] = "GENE";
	_analysisHeaders[1] = "BP";
	_analysisHeaders[2] = "S_sites";
	_analysisHeaders[3] = "NS_sites";
	_analysisHeaders[4] = "LogL";
	_analysisHeaders[5] = "AC";
	_analysisHeaders[6] = "AT";
	_analysisHeaders[7] = "CG";
	_analysisHeaders[8] = "CT";
	_analysisHeaders[9] = "GT";

	for (_biterator = 0; _biterator < treeBranchCount; _biterator = _biterator + 1)
	{
		branchName = treeBranchNames[_biterator];
		
		_analysisHeaders [Abs(_analysisHeaders)] = "length("+branchName+")";
		_analysisHeaders [Abs(_analysisHeaders)] = "dS("+branchName+")";
		_analysisHeaders [Abs(_analysisHeaders)] = "dN("+branchName+")";
		_analysisHeaders [Abs(_analysisHeaders)] = "omega("+branchName+")";
	}

	return _analysisHeaders;
}

/*---------------------------------------------------------*/

function runAGeneFit (myID)
{
	DataSetFilter filteredData = CreateFilter (ds,3,"","",GeneticCodeExclusions);

	if (_currentGene==1)
	{
		_MG94stdinOverload = {};
		_MG94stdinOverload ["0"] = "Local";
		_MG94stdinOverload ["1"] = modelSpecString;

		ExecuteAFile 			(HYPHY_BASE_DIRECTORY+"TemplateBatchFiles"+DIRECTORY_SEPARATOR+"TemplateModels"+DIRECTORY_SEPARATOR+"MG94custom.mdl",
							     _MG94stdinOverload);
		
		Tree	codonTree		   = treeString;
	}
	else
	{
		HarvestFrequencies 			  (observedFreq,filteredData,3,1,1);
		MULTIPLY_BY_FREQS 		    = PopulateModelMatrix ("MG94custom", observedFreq);
		vectorOfFrequencies 	    = BuildCodonFrequencies (observedFreq);
		Model MG94customModel 		= (MG94custom,vectorOfFrequencies,0);

		Tree	codonTree		    = treeString;
	}

	LikelihoodFunction lf     = (filteredData,codonTree);

	Optimize 					(res,lf);

	_snsAVL	   = 				_computeSNSSites ("filteredData", _Genetic_Code, vectorOfFrequencies, 0);
	_cL		   =  				ReturnVectorsOfCodonLengths (ComputeScalingStencils (0), "codonTree");


	_returnMe = {};
	_returnMe ["GENE"]  			= myID;
	_returnMe ["LogL"]  			= res[1][0];
	_returnMe ["BP"] 				= _snsAVL ["Sites"];
	_returnMe ["S_sites"] 			= _snsAVL ["SSites"];
	_returnMe ["NS_sites"] 			= _snsAVL ["NSSites"];
	_returnMe ["AC"] 				= AC;
	_returnMe ["AT"] 				= AT;
	_returnMe ["CG"] 				= CG;
	_returnMe ["CT"] 				= CT;
	_returnMe ["GT"] 				= GT;


	for (_biterator = 0; _biterator < treeBranchCount; _biterator = _biterator + 1)
	{
		branchName = treeBranchNames[_biterator];

		_returnMe ["length("+branchName+")"] 		= (_cL["Total"])[_biterator];
		_returnMe ["dS("+branchName+")"] 				= (_cL["Syn"])[_biterator]*(_returnMe ["BP"]/_returnMe ["S_sites"]);
		_returnMe ["dN("+branchName+")"] 				= (_cL["NonSyn"])[_biterator]*(_returnMe ["BP"]/_returnMe ["NS_sites"]);
		
		ExecuteCommands ("_lom = _standardizeRatio(codonTree."+treeBranchNames[_biterator]+".nonSynRate,codonTree."+treeBranchNames[_biterator]+".synRate);");
		_returnMe ["omega("+branchName+")"] 				= _lom;
	}
	
	return _returnMe;
}
"""

FastaReader = """
fscanf			(stdin, "String", _coreAnalysis);
fscanf			(stdin, "String", _outputDriver);

ExecuteAFile 			(HYPHY_BASE_DIRECTORY+"TemplateBatchFiles"+DIRECTORY_SEPARATOR+"TemplateModels"+DIRECTORY_SEPARATOR+"chooseGeneticCode.def");
ExecuteAFile 			(HYPHY_BASE_DIRECTORY+"TemplateBatchFiles"+DIRECTORY_SEPARATOR+"dSdNTreeTools.ibf");
ExecuteAFile 			(HYPHY_BASE_DIRECTORY+"TemplateBatchFiles"+DIRECTORY_SEPARATOR+"Utility"+DIRECTORY_SEPARATOR+"CodonTools.bf");
ExecuteAFile 			(HYPHY_BASE_DIRECTORY+"TemplateBatchFiles"+DIRECTORY_SEPARATOR+"Utility"+DIRECTORY_SEPARATOR+"GrabBag.bf");

SetDialogPrompt ("Tree file");
fscanf	        (PROMPT_FOR_FILE, "Tree",  givenTree);

treeBranchNames			   = BranchName (givenTree,-1);
treeBranchCount			   = Columns    (treeBranchNames)-1;
treeString 				   = Format (givenTree,1,1);

SetDialogPrompt ("Multiple gene FASTA file");
fscanf          (PROMPT_FOR_FILE, "Lines", inLines);
fscanf			(stdin, "String",  modelSpecString);
fscanf			(stdin, "String", _outPath);
 
ExecuteAFile	(_outputDriver);
ExecuteAFile	(_coreAnalysis);
 
/*---------------------------------------------------------*/

_linesIn     = Columns (inLines);
_currentGene   = 1; 
 _currentState = 0;
/* 0 - waiting for a non-empty line */
/* 1 - reading files */

geneSeqs       = "";
geneSeqs 	   * 0;

_prepareFileOutput (_outPath);

for (l=0; l<_linesIn; l=l+1)
{
	if (Abs(inLines[l]) == 0)
	{
		if (_currentState == 1)
		{
			geneSeqs      * 0;
			DataSet 	  ds 		   = ReadFromString (geneSeqs);
			_processAGene (ds.species == treeBranchCount,_currentGene);
			geneSeqs * 128;
			_currentGene = _currentGene + 1;
		}
	}
	else
	{
		if (_currentState == 0)
		{
			_currentState = 1;
		}
		geneSeqs * inLines[l];
		geneSeqs * "\\n";
	}
}

if (_currentState == 1)
{
	geneSeqs      * 0;
	DataSet 	  ds 		   = ReadFromString (geneSeqs);
	_processAGene (ds.species == treeBranchCount,_currentGene);
}

_finishFileOutput (0);
"""

TabWriter = """
/*---------------------------------------------------------*/
function _prepareFileOutput (_outPath)
{
	_outputFilePath = _outPath;
	
	_returnHeaders 	= returnResultHeaders(0);
	
	fprintf (_outputFilePath, CLEAR_FILE, KEEP_OPEN, _returnHeaders[0]);
	for (_biterator = 1; _biterator < Abs(_returnHeaders); _biterator = _biterator + 1)
	{
		fprintf (_outputFilePath,"\\t",_returnHeaders[_biterator]);
	}


	
	fprintf (_outputFilePath,"\\n");
	return 0;
}

/*---------------------------------------------------------*/

function _processAGene (valid, _geneID)
{
	if (valid)
	{
		returnValue = runAGeneFit (_geneID);
		fprintf (_outputFilePath, returnValue[_returnHeaders[0]]);
		for (_biterator = 1; _biterator < Abs(_returnHeaders); _biterator = _biterator + 1)
		{
			fprintf (_outputFilePath,"\\t",returnValue[_returnHeaders[_biterator]]);
		}
		fprintf (_outputFilePath, "\\n");
	}
	else
	{
		fprintf (_outputFilePath, 
				_geneID, ", Incorrect number of sequences\\n");
	}
	_currentState = 0;
	return 0;
}

/*---------------------------------------------------------*/
function _finishFileOutput (dummy)
{
	return 0;
}
"""

def get_dN_dS_config_filename(SimpleLocalFitter_filename, TabWriter_filename, genetic_code, tree_filename, input_filename, nuc_model, output_filename, FastaReader_filename ):
    contents = """
_genomeScreenOptions = {};

/* all paths are either absolute or relative 
to the DATA READER */

_genomeScreenOptions ["0"] = "%s"; 
	/* which analysis to run on each gene; */	
_genomeScreenOptions ["1"] = "%s"; 
	/* what output to produce; */	

_genomeScreenOptions ["2"] = "%s"; 
	/* genetic code */	
_genomeScreenOptions ["3"] = "%s"; 
	/* tree file */
_genomeScreenOptions ["4"] = "%s"; 
	/* alignment file */
_genomeScreenOptions ["5"] = "%s"; 
	/* nucleotide bias string; can define any of the 203 models */
_genomeScreenOptions ["6"] = "%s"; 
	/* output csv file */
	
ExecuteAFile ("%s", _genomeScreenOptions);	
""" % (SimpleLocalFitter_filename, TabWriter_filename, genetic_code, tree_filename, input_filename, nuc_model, output_filename, FastaReader_filename )
    return get_filled_temp_filename(contents)
    
    
def get_branch_lengths_config_filename(input_filename, nuc_model, model_options, base_freq, tree_filename, output_filename, BranchLengths_filename):
    contents = """
_genomeScreenOptions = {};

/* all paths are either absolute or relative 
to the NucDataBranchLengths.bf */

_genomeScreenOptions ["0"] = "%s"; 
	/* the file to analyze; */	
_genomeScreenOptions ["1"] = "CUSTOM"; 
	/* use an arbitrary nucleotide model */	
_genomeScreenOptions ["2"] = "%s";
	/* which model to use */ 
_genomeScreenOptions ["3"] = "%s"; 
	/* model options */
_genomeScreenOptions ["4"] = "Estimated"; 
	/* rate parameters */
_genomeScreenOptions ["5"] = "%s"; 
	/* base frequencies */
_genomeScreenOptions ["6"] = "%s"; 
	/* the tree to use; */	
_genomeScreenOptions ["7"] = "%s"; 
	/* write .csv output to; */	
	
ExecuteAFile ("%s", _genomeScreenOptions);	
""" % (input_filename, nuc_model, model_options, base_freq, tree_filename, output_filename, BranchLengths_filename)
    return get_filled_temp_filename(contents)
    