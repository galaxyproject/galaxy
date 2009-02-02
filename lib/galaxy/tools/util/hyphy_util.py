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

NJ_tree_shared_ibf = """
COUNT_GAPS_IN_FREQUENCIES = 0;
methodIndex                  = 1;

/*-----------------------------------------------------------------------------------------------------------------------------------------*/

function InferTreeTopology(verbFlag)
{
    distanceMatrix = {ds.species,ds.species};

    MESSAGE_LOGGING              = 0;
    ExecuteAFile (HYPHY_BASE_DIRECTORY+"TemplateBatchFiles"+DIRECTORY_SEPARATOR+"chooseDistanceFormula.def");
    InitializeDistances (0);
        
    for (i = 0; i<ds.species; i=i+1)
    {
        for (j = i+1; j<ds.species; j = j+1)
        {
            distanceMatrix[i][j] = ComputeDistanceFormula (i,j);
        }
    }

    MESSAGE_LOGGING              = 1;
    cladesMade                     = 1;
    

    if (ds.species == 2)
    {
        d1 = distanceMatrix[0][1]/2;
        treeNodes = {{0,1,d1__},
                     {1,1,d1__},
                     {2,0,0}};
                     
        cladesInfo = {{2,0}};
    }
    else
    {
        if (ds.species == 3)
        {
            /* generate least squares estimates here */
            
            d1 = (distanceMatrix[0][1]+distanceMatrix[0][2]-distanceMatrix[1][2])/2;
            d2 = (distanceMatrix[0][1]-distanceMatrix[0][2]+distanceMatrix[1][2])/2;
            d3 = (distanceMatrix[1][2]+distanceMatrix[0][2]-distanceMatrix[0][1])/2;
            
            treeNodes = {{0,1,d1__},
                         {1,1,d2__},
                         {2,1,d3__}
                         {3,0,0}};
                         
            cladesInfo = {{3,0}};        
        }
        else
        {    
            njm = (distanceMatrix > methodIndex)>=ds.species;
                
            treeNodes         = {2*(ds.species+1),3};
            cladesInfo        = {ds.species-1,2};
            
            for (i=Rows(treeNodes)-1; i>=0; i=i-1)
            {
                treeNodes[i][0] = njm[i][0];
                treeNodes[i][1] = njm[i][1];
                treeNodes[i][2] = njm[i][2];
            }

            for (i=Rows(cladesInfo)-1; i>=0; i=i-1)
            {
                cladesInfo[i][0] = njm[i][3];
                cladesInfo[i][1] = njm[i][4];
            }
            
            njm = 0;
        }
    }
    return 1.0;
}

/*-----------------------------------------------------------------------------------------------------------------------------------------*/

function TreeMatrix2TreeString (doLengths)
{
    treeString = "";
    p = 0;
    k = 0;
    m = treeNodes[0][1];
    n = treeNodes[0][0];
    treeString*(Rows(treeNodes)*25);

    while (m)
    {    
        if (m>p)
        {
            if (p)
            {
                treeString*",";
            }
            for (j=p;j<m;j=j+1)
            {
                treeString*"(";
            }
        }
        else
        {
            if (m<p)
            {
                for (j=m;j<p;j=j+1)
                {
                    treeString*")";
                }
            }    
            else
            {
                treeString*",";
            }    
        }
        if (n<ds.species)
        {
            GetString (nodeName, ds, n);
            if (doLengths != 1)
            {
                treeString*nodeName;            
            }
            else
            {    
                treeString*taxonNameMap[nodeName];
            }
        }
        if (doLengths>.5)
        {
            nodeName = ":"+treeNodes[k][2];
            treeString*nodeName;
        }
        k=k+1;
        p=m;
        n=treeNodes[k][0];
        m=treeNodes[k][1];
    }

    for (j=m;j<p;j=j+1)
    {
        treeString*")";
    }
    
    treeString*0;
    return treeString;
}
"""

def get_NJ_tree (filename):
    return """
DISTANCE_PROMPTS            = 1;
ExecuteAFile ("%s");

DataSet                 ds              = ReadDataFile (PROMPT_FOR_FILE);
DataSetFilter             filteredData = CreateFilter (ds,1);

/* do sequence to branch map */

taxonNameMap = {};

for (k=0; k<ds.species; k=k+1)
{
    GetString         (thisName, ds,k);
    shortName         = (thisName^{{"\\\\..+",""}})&&1;
    taxonNameMap[shortName] = thisName;
    SetParameter (ds,k,shortName);
}

DataSetFilter             filteredData = CreateFilter (ds,1);
InferTreeTopology         (0);
treeString                 = TreeMatrix2TreeString (1);

fprintf                    (PROMPT_FOR_FILE, CLEAR_FILE, treeString);
fscanf                    (stdin, "String", ps_file);

if (Abs(ps_file))
{
    treeString = TreeMatrix2TreeString (2);
    UseModel (USE_NO_MODEL);
    Tree givenTree = treeString;
    baseHeight         = TipCount (givenTree)*28;
    TREE_OUTPUT_OPTIONS = {};
    TREE_OUTPUT_OPTIONS["__FONT_SIZE__"] = 14;
    baseWidth = 0;
    treeAVL                = givenTree^0;
    drawLetter            = "/drawletter {"+TREE_OUTPUT_OPTIONS["__FONT_SIZE__"]$4+" -"+TREE_OUTPUT_OPTIONS["__FONT_SIZE__"]$2+ " show} def\\n";
    for (k3 = 1; k3 < Abs(treeAVL); k3=k3+1)
    {
        nodeName = (treeAVL[k3])["Name"];
        if(Abs((treeAVL[k3])["Children"]) == 0)
        {
            mySpecs = {};
            mySpecs ["TREE_OUTPUT_BRANCH_LABEL"] = "(" + taxonNameMap[nodeName] + ") drawLetter";
            baseWidth = Max (baseWidth, (treeAVL[k3])["Depth"]);
        }
    }
    baseWidth = 40*baseWidth;
    
    fprintf (ps_file,  CLEAR_FILE, drawLetter, PSTreeString (givenTree, "STRING_SUPPLIED_LENGTHS",{{baseWidth,baseHeight}}));
}
""" % (filename)

def get_NJ_treeMF (filename):
    return  """
ExecuteAFile ("%s");

VERBOSITY_LEVEL            = -1;
fscanf                  (PROMPT_FOR_FILE, "Lines", inLines);

_linesIn                        = Columns (inLines);
isomorphicTreesBySequenceCount  = {};

/*---------------------------------------------------------*/

_currentGene   = 1; 
_currentState = 0;
geneSeqs      = "";
geneSeqs      * 128;

fprintf (PROMPT_FOR_FILE, CLEAR_FILE, KEEP_OPEN);
treeOutFile = LAST_FILE_PATH;

fscanf  (stdin,"String", ps_file);
if (Abs(ps_file))
{
    fprintf (ps_file, CLEAR_FILE, KEEP_OPEN);
}

for (l=0; l<_linesIn; l=l+1)
{
    if (Abs(inLines[l]) == 0)
    {
        if (_currentState == 1)
        {
            geneSeqs      * 0;
            DataSet       ds            = ReadFromString (geneSeqs);
            _processAGene (_currentGene,treeOutFile,ps_file);
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
        DataSet       ds            = ReadFromString (geneSeqs);
        _processAGene (_currentGene,treeOutFile,ps_file);
    }
}

fprintf (treeOutFile,CLOSE_FILE);
if (Abs(ps_file))
{
    fprintf (ps_file,CLOSE_FILE);
}
/*---------------------------------------------------------*/

function _processAGene (_geneID, nwk_file, ps_file)
{
    if (ds.species == 1)
    {
        fprintf                    (nwk_file, _geneID-1, "\\tNone \\tNone\\n");
        return 0;
        
    }
    
    DataSetFilter             filteredData = CreateFilter (ds,1);

    /* do sequence to branch map */

    taxonNameMap = {};

    for (k=0; k<ds.species; k=k+1)
    {
        GetString         (thisName, ds,k);
        shortName         = (thisName^{{"\\\\..+",""}});
        taxonNameMap[shortName] = thisName;
        SetParameter (ds,k,shortName);
    }

    DataSetFilter             filteredData = CreateFilter (ds,1);
    DISTANCE_PROMPTS        = (_geneID==1);

    InferTreeTopology         (0);
    baseTree                = TreeMatrix2TreeString (0);
    UseModel                 (USE_NO_MODEL);
    
    Tree             baseTop    = baseTree;
    
    /* standardize this top */
    
    for (k=0; k<Abs(isomorphicTreesBySequenceCount[filteredData.species]); k=k+1)
    {
        testString      = (isomorphicTreesBySequenceCount[filteredData.species])[k];
        Tree testTree = testString;
        if (testTree == baseTop)
        {
            baseTree = testString;
            break;
        }
    }
    if (k==Abs(isomorphicTreesBySequenceCount[filteredData.species]))
    {
        if (k==0)
        {
            isomorphicTreesBySequenceCount[filteredData.species] = {};
        }
        (isomorphicTreesBySequenceCount[filteredData.species])[k] = baseTree;
    }
    
    fprintf                    (nwk_file, _geneID-1, "\\t", baseTree, "\\t", TreeMatrix2TreeString (1), "\\n");
    if (Abs(ps_file))
    {
        treeString = TreeMatrix2TreeString (2);
        UseModel (USE_NO_MODEL);
        Tree givenTree = treeString;
        baseHeight         = TipCount (givenTree)*28;
        TREE_OUTPUT_OPTIONS = {};
        TREE_OUTPUT_OPTIONS["__FONT_SIZE__"] = 14;
        baseWidth = 0;
        treeAVL                = givenTree^0;
        drawLetter            = "/drawletter {"+TREE_OUTPUT_OPTIONS["__FONT_SIZE__"]$4+" -"+TREE_OUTPUT_OPTIONS["__FONT_SIZE__"]$2+ " show} def\\n";
        for (k3 = 1; k3 < Abs(treeAVL); k3=k3+1)
        {
            nodeName = (treeAVL[k3])["Name"];
            if(Abs((treeAVL[k3])["Children"]) == 0)
            {
                mySpecs = {};
                mySpecs ["TREE_OUTPUT_BRANCH_LABEL"] = "(" + taxonNameMap[nodeName] + ") drawLetter";
                baseWidth = Max (baseWidth, (treeAVL[k3])["Depth"]);
            }
        }
        baseWidth = 40*baseWidth;
        
        fprintf (stdout, _geneID, ":", givenTree,"\\n");
        fprintf (ps_file, PSTreeString (givenTree, "STRING_SUPPLIED_LENGTHS",{{baseWidth,baseHeight}}));
    }
    return 0;
}
""" % (filename)

BranchLengthsMF = """
VERBOSITY_LEVEL            = -1;

fscanf                  (PROMPT_FOR_FILE, "Lines", inLines);



_linesIn = Columns (inLines);



/*---------------------------------------------------------*/



_currentGene   = 1; 

_currentState = 0;

geneSeqs      = "";

geneSeqs      * 128;



for (l=0; l<_linesIn; l=l+1)

{

    if (Abs(inLines[l]) == 0)

    {

        if (_currentState == 1)

        {

            geneSeqs      * 0;

            DataSet       ds            = ReadFromString (geneSeqs);

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

        DataSet       ds            = ReadFromString (geneSeqs);

        _processAGene (_currentGene);

    }

}



fprintf (resultFile,CLOSE_FILE);



/*---------------------------------------------------------*/



function _processAGene (_geneID)

{

    DataSetFilter             filteredData = CreateFilter (ds,1);

    if (_currentGene == 1)

    {

        SelectTemplateModel        (filteredData);

        

        SetDialogPrompt           ("Tree file");

        fscanf                    (PROMPT_FOR_FILE, "Tree",  givenTree);

        fscanf                    (stdin, "String", resultFile);

        

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

        fprintf         (resultFile,CLEAR_FILE,KEEP_OPEN,"Block\\tBranch\\tLength\\tLowerBound\\tUpperBound\\n"); 

    }

    else

    {

        HarvestFrequencies (vectorOfFrequencies, filteredData, 1,1,1);

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

            fprintf         (resultFile,"ERROR:", thisName, " could not be matched to any of the leaves in tree ", givenTree,"\\n"); 

            return 0;

        }

    }

    

    /* */

    

    LikelihoodFunction lf = (filteredData,givenTree);

    Optimize                 (res,lf);

    

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
DataSet                 ds              = ReadDataFile (PROMPT_FOR_FILE);
DataSetFilter             filteredData = CreateFilter (ds,1);

SelectTemplateModel        (filteredData);

SetDialogPrompt         ("Tree file");
fscanf                    (PROMPT_FOR_FILE, "Tree",  givenTree);
fscanf                    (stdin, "String", resultFile);

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
        fprintf         (resultFile,CLEAR_FILE,"ERROR:", thisName, " could not be matched to any of the leaves in tree ", givenTree); 
        return 0;
    }
}

/* */

LikelihoodFunction lf = (filteredData,givenTree);

Optimize                 (res,lf);

timer = Time(0)-timer;

branchNames   = BranchName   (givenTree,-1);
branchLengths = BranchLength (givenTree,-1);

fprintf         (resultFile,CLEAR_FILE,KEEP_OPEN,"Branch\\tLength\\tLowerBound\\tUpperBound\\n"); 

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
VERBOSITY_LEVEL               = -1;
COUNT_GAPS_IN_FREQUENCIES  = 0;

/*---------------------------------------------------------*/

function returnResultHeaders (dummy)
{
    _analysisHeaders = {};
    _analysisHeaders[0] = "BLOCK";
    _analysisHeaders[1] = "BP";
    _analysisHeaders[2] = "S_sites";
    _analysisHeaders[3] = "NS_sites";
    _analysisHeaders[4] = "Stop_codons";
    _analysisHeaders[5] = "LogL";
    _analysisHeaders[6] = "AC";
    _analysisHeaders[7] = "AT";
    _analysisHeaders[8] = "CG";
    _analysisHeaders[9] = "CT";
    _analysisHeaders[10] = "GT";
    _analysisHeaders[11] = "Tree";

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

        ExecuteAFile             (HYPHY_BASE_DIRECTORY+"TemplateBatchFiles"+DIRECTORY_SEPARATOR+"TemplateModels"+DIRECTORY_SEPARATOR+"MG94custom.mdl",
                                 _MG94stdinOverload);
        
        Tree    codonTree           = treeString;
    }
    else
    {
        HarvestFrequencies               (observedFreq,filteredData,3,1,1);
        MULTIPLY_BY_FREQS             = PopulateModelMatrix ("MG94custom", observedFreq);
        vectorOfFrequencies         = BuildCodonFrequencies (observedFreq);
        Model MG94customModel         = (MG94custom,vectorOfFrequencies,0);

        Tree    codonTree            = treeString;
    }

    LikelihoodFunction lf     = (filteredData,codonTree);

    Optimize                     (res,lf);

    _snsAVL       =                 _computeSNSSites ("filteredData", _Genetic_Code, vectorOfFrequencies, 0);
    _cL           =                  ReturnVectorsOfCodonLengths (ComputeScalingStencils (0), "codonTree");


    _returnMe = {};
    _returnMe ["BLOCK"]              = myID;
    _returnMe ["LogL"]              = res[1][0];
    _returnMe ["BP"]                 = _snsAVL ["Sites"];
    _returnMe ["S_sites"]             = _snsAVL ["SSites"];
    _returnMe ["NS_sites"]             = _snsAVL ["NSSites"];
    _returnMe ["AC"]                 = AC;
    _returnMe ["AT"]                 = AT;
    _returnMe ["CG"]                 = CG;
    _returnMe ["CT"]                 = CT;
    _returnMe ["GT"]                 = GT;
    _returnMe ["Tree"]                 = Format(codonTree,0,1);

    for (_biterator = 0; _biterator < treeBranchCount; _biterator = _biterator + 1)
    {
        branchName = treeBranchNames[_biterator];

        _returnMe ["length("+branchName+")"]         = (_cL["Total"])[_biterator];
        _returnMe ["dS("+branchName+")"]                 = (_cL["Syn"])[_biterator]*(_returnMe ["BP"]/_returnMe ["S_sites"]);
        _returnMe ["dN("+branchName+")"]                 = (_cL["NonSyn"])[_biterator]*(_returnMe ["BP"]/_returnMe ["NS_sites"]);
        
        ExecuteCommands ("_lom = _standardizeRatio(codonTree."+treeBranchNames[_biterator]+".nonSynRate,codonTree."+treeBranchNames[_biterator]+".synRate);");
        _returnMe ["omega("+branchName+")"]                 = _lom;
    }
    
    return _returnMe;
}

"""

SimpleGlobalFitter = """
VERBOSITY_LEVEL               = -1;
COUNT_GAPS_IN_FREQUENCIES  = 0;

/*---------------------------------------------------------*/

function returnResultHeaders (dummy)
{
    _analysisHeaders = {};
    _analysisHeaders[0]  = "BLOCK";
    _analysisHeaders[1]  = "BP";
    _analysisHeaders[2]  = "S_sites";
    _analysisHeaders[3]  = "NS_sites";
    _analysisHeaders[4]  = "Stop_codons";
    _analysisHeaders[5]  = "LogL";
    _analysisHeaders[6]  = "omega";
    _analysisHeaders[7]  = "omega_range";
    _analysisHeaders[8]  = "AC";
    _analysisHeaders[9]  = "AT";
    _analysisHeaders[10] = "CG";
    _analysisHeaders[11] = "CT";
    _analysisHeaders[12] = "GT";
    _analysisHeaders[13] = "Tree";

    return _analysisHeaders;
}

/*---------------------------------------------------------*/

function runAGeneFit (myID)
{
    fprintf (stdout, "[SimpleGlobalFitter.bf on GENE ", myID, "]\\n");
    taxonNameMap = {};
    
    for (k=0; k<ds.species; k=k+1)
    {
        GetString         (thisName, ds,k);
        shortName         = (thisName^{{"\\\\..+",""}})&&1;
        taxonNameMap[shortName] = thisName;
        SetParameter (ds,k,shortName);
    }

    DataSetFilter filteredData = CreateFilter (ds,1);
    _nucSites                    = filteredData.sites;
    
    if (Abs(treeString))
    {
        givenTreeString = treeString;
    }
    else
    {
        if (_currentGene==1)
        {
            ExecuteAFile             (HYPHY_BASE_DIRECTORY+"TemplateBatchFiles"+DIRECTORY_SEPARATOR+"Utility"+DIRECTORY_SEPARATOR+"NJ.bf");
        }
        givenTreeString = InferTreeTopology (0);
        treeString        = "";
    }

    DataSetFilter filteredData = CreateFilter (ds,3,"","",GeneticCodeExclusions);

    if (_currentGene==1)
    {
        _MG94stdinOverload = {};
        _MG94stdinOverload ["0"] = "Global";
        _MG94stdinOverload ["1"] = modelSpecString;

        ExecuteAFile             (HYPHY_BASE_DIRECTORY+"TemplateBatchFiles"+DIRECTORY_SEPARATOR+"TemplateModels"+DIRECTORY_SEPARATOR+"MG94custom.mdl",
                                 _MG94stdinOverload);
        
        Tree    codonTree           = givenTreeString;
    }
    else
    {
        HarvestFrequencies               (observedFreq,filteredData,3,1,1);
        MULTIPLY_BY_FREQS             = PopulateModelMatrix ("MG94custom", observedFreq);
        vectorOfFrequencies         = BuildCodonFrequencies (observedFreq);
        Model MG94customModel         = (MG94custom,vectorOfFrequencies,0);

        Tree    codonTree            = givenTreeString;
    }

    LikelihoodFunction lf     = (filteredData,codonTree);

    Optimize                     (res,lf);

    _snsAVL       =                 _computeSNSSites ("filteredData", _Genetic_Code, vectorOfFrequencies, 0);
    _cL           =                  ReturnVectorsOfCodonLengths (ComputeScalingStencils (0), "codonTree");


    _returnMe = {};
    _returnMe ["BLOCK"]              = myID;
    _returnMe ["LogL"]              = res[1][0];
    _returnMe ["BP"]                 = _snsAVL ["Sites"];
    _returnMe ["S_sites"]             = _snsAVL ["SSites"];
    _returnMe ["NS_sites"]             = _snsAVL ["NSSites"];
    _returnMe ["Stop_codons"]         = (_nucSites-filteredData.sites*3)$3;
    _returnMe ["AC"]                 = AC;
    _returnMe ["AT"]                 = AT;
    _returnMe ["CG"]                 = CG;
    _returnMe ["CT"]                 = CT;
    _returnMe ["GT"]                 = GT;
    _returnMe ["omega"]             = R;
    COVARIANCE_PARAMETER             = "R";
    COVARIANCE_PRECISION             = 0.95;
    CovarianceMatrix                 (cmx,lf);
    _returnMe ["omega_range"]         = ""+cmx[0]+"-"+cmx[2];
    _returnMe ["Tree"]                 = Format(codonTree,0,1);


    return _returnMe;
}
"""

FastaReader = """
fscanf            (stdin, "String", _coreAnalysis);
fscanf            (stdin, "String", _outputDriver);

ExecuteAFile             (HYPHY_BASE_DIRECTORY+"TemplateBatchFiles"+DIRECTORY_SEPARATOR+"TemplateModels"+DIRECTORY_SEPARATOR+"chooseGeneticCode.def");
ExecuteAFile             (HYPHY_BASE_DIRECTORY+"TemplateBatchFiles"+DIRECTORY_SEPARATOR+"dSdNTreeTools.ibf");
ExecuteAFile             (HYPHY_BASE_DIRECTORY+"TemplateBatchFiles"+DIRECTORY_SEPARATOR+"Utility"+DIRECTORY_SEPARATOR+"CodonTools.bf");
ExecuteAFile             (HYPHY_BASE_DIRECTORY+"TemplateBatchFiles"+DIRECTORY_SEPARATOR+"Utility"+DIRECTORY_SEPARATOR+"GrabBag.bf");

SetDialogPrompt ("Tree file");
fscanf            (PROMPT_FOR_FILE, "Tree",  givenTree);

treeBranchNames               = BranchName (givenTree,-1);
treeBranchCount               = Columns    (treeBranchNames)-1;
treeString                    = Format (givenTree,1,1);

SetDialogPrompt ("Multiple gene FASTA file");
fscanf          (PROMPT_FOR_FILE, "Lines", inLines);
fscanf            (stdin, "String",  modelSpecString);
fscanf            (stdin, "String", _outPath);
 
ExecuteAFile    (_outputDriver);
ExecuteAFile    (_coreAnalysis);
 
/*---------------------------------------------------------*/

_linesIn     = Columns (inLines);
_currentGene   = 1; 
 _currentState = 0;
/* 0 - waiting for a non-empty line */
/* 1 - reading files */

geneSeqs       = "";
geneSeqs        * 0;

_prepareFileOutput (_outPath);

for (l=0; l<_linesIn; l=l+1)
{
    if (Abs(inLines[l]) == 0)
    {
        if (_currentState == 1)
        {
            geneSeqs      * 0;
            DataSet       ds            = ReadFromString (geneSeqs);
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
    DataSet       ds            = ReadFromString (geneSeqs);
    _processAGene (ds.species == treeBranchCount,_currentGene);
}

_finishFileOutput (0);
"""

TabWriter = """
/*---------------------------------------------------------*/
function _prepareFileOutput (_outPath)
{
    _outputFilePath = _outPath;
    
    _returnHeaders     = returnResultHeaders(0);
    
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
    /*
    else
    {
        fprintf (_outputFilePath, 
                _geneID, ", Incorrect number of sequences\\n");
    }
    */
    _currentState = 0;
    return 0;
}

/*---------------------------------------------------------*/
function _finishFileOutput (dummy)
{
    return 0;
}
"""

def get_dnds_config_filename(Fitter_filename, TabWriter_filename, genetic_code, tree_filename, input_filename, nuc_model, output_filename, FastaReader_filename ):
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
""" % (Fitter_filename, TabWriter_filename, genetic_code, tree_filename, input_filename, nuc_model, output_filename, FastaReader_filename )
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
    
    
def get_nj_tree_config_filename(input_filename, distance_metric, output_filename1, output_filename2, NJ_tree_filename):
    contents = """
_genomeScreenOptions = {};

/* all paths are either absolute or relative 
to the BuildNJTree.bf */

_genomeScreenOptions ["0"] = "%s"; 
    /* the file to analyze; */    
_genomeScreenOptions ["1"] = "%s"; 
    /* pick which distance metric to use; TN93 is a good default */    
_genomeScreenOptions ["2"] = "%s"; 
    /* write Newick tree output to; */    
_genomeScreenOptions ["3"] = "%s"; 
    /* write a postscript tree file to this file; leave blank to not write a tree */    
    
ExecuteAFile ("%s", _genomeScreenOptions);    
""" % (input_filename, distance_metric, output_filename1, output_filename2, NJ_tree_filename)
    return get_filled_temp_filename(contents)
    
    
def get_nj_treeMF_config_filename(input_filename, output_filename1, output_filename2, distance_metric, NJ_tree_filename):
    contents = """
_genomeScreenOptions = {};

/* all paths are either absolute or relative 
to the BuildNJTreeMF.bf */

_genomeScreenOptions ["0"] = "%s"; 
    /* the multiple alignment file to analyze; */    
_genomeScreenOptions ["1"] = "%s"; 
    /* write Newick tree output to; */    
_genomeScreenOptions ["2"] = "%s"; 
    /* write a postscript tree file to this file; leave blank to not write a tree */    
_genomeScreenOptions ["3"] = "%s"; 
    /* pick which distance metric to use; TN93 is a good default */    
    
ExecuteAFile ("%s", _genomeScreenOptions);        
""" % (input_filename, output_filename1, output_filename2, distance_metric, NJ_tree_filename)
    return get_filled_temp_filename(contents)
