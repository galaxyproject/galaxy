import re
import sys
import datetime
import AlphaSubstValidation
import AlphaSubstPrep
import AlphaSubstBaseMLBootstrap
import AlphaSubstScoring
import random

def stop_err(msg):
    "Write the error message and exit"
    sys.stderr.write(msg)
    sys.exit()

#Retrieve Data
OutputFile = sys.argv[1]
AnalysisType = sys.argv[2]
SubstModel = sys.argv[3]
CompType = sys.argv[4]
DoSingleBoot = sys.argv[5]
SingleBootIterations = sys.argv[6]
DoDoubleBoot = sys.argv[7]
DoubleBootIterations = sys.argv[8]
Sequences1 = sys.argv[9]
Sequences2 = sys.argv[10]
TreeDefinition = sys.argv[11]
DoIntAlpha = sys.argv[12]
DoExtAlpha = sys.argv[13]
CleanData = sys.argv[14]
DoBranchAlpha = sys.argv[15]
Output_Format = sys.argv[16]

ExtraBaseML = 0

#Get galaxy location
OutputSplit = re.compile('database')
OutContents = OutputSplit.split(OutputFile)
GalaxyLocation = OutContents[0]
BaseMLLocation = "/home/universe/linux-i686/PAML/paml3.15/bin/"

if int(DoSingleBoot) == 0:
    Iterations = 1
    GetSE = 1
else: GetSE = 0

if int(AnalysisType) == 0: 
    AlignmentTogether = 1
    DoDoubleBoot = 0
elif int(AnalysisType) == 1:
    AlignmentTogether = 0
    DoDoubleBoot = 0
elif int(AnalysisType) == 2:
    AlignmentTogether = 0
    DoDoubleBoot = 1
    GetSE = 0

#Initial Data Validation
AlphaValid = AlphaSubstValidation.AlphaSubstValidation()

ValidationErrors = AlphaValid.ValidateAlphaSubstData(AnalysisType,CompType,DoSingleBoot,SingleBootIterations,DoDoubleBoot,DoubleBootIterations,Sequences1,Sequences2,TreeDefinition,BaseMLLocation)
if ValidationErrors != "":
    stop_err(ValidationErrors)

#Set post-validation work variables
SequenceCount = AlphaValid.SequenceCount
TotalSeqLength1 = AlphaValid.TotalSequenceLength1
TotalSeqLength2 = AlphaValid.TotalSequenceLength2

Group1AlignmentCount = AlphaValid.Group1AlignmentCount
Group1Alignments = AlphaValid.Group1Alignments
Group1AlignLength = AlphaValid.Group1AlignLength

Group2AlignmentCount = AlphaValid.Group2AlignmentCount
Group2Alignments = AlphaValid.Group2Alignments
Group2AlignLength = AlphaValid.Group2AlignLength

UserRandomKey = str(datetime.date.today()) + "-" + str(random.randrange(0,50000,1))

#Prepare the data for BaseML
AlphaPrep = AlphaSubstPrep.AlphaSubstPrep()
AlphaPrep.PrepBaseML(AnalysisType,TreeDefinition,SequenceCount,CompType,UserRandomKey,BaseMLLocation,SubstModel,GetSE,DoIntAlpha,DoExtAlpha,GalaxyLocation,1,0,1,2.5,1,0)

BranchDescriptions = AlphaPrep.BranchDescriptions
InternalBranches = AlphaPrep.InternalBranches
ExternalBranches = AlphaPrep.ExternalBranches
Group1BranchList = AlphaPrep.Group1Branches
Group2BranchList = AlphaPrep.Group2Branches
Group1ExtBranchList = AlphaPrep.Group1ExtBranches
Group2ExtBranchList = AlphaPrep.Group2ExtBranches
Group1IntBranchList = AlphaPrep.Group1IntBranches
Group2IntBranchList = AlphaPrep.Group2IntBranches
DoIntAlpha = AlphaPrep.DoIntAlpha
DoExtAlpha = AlphaPrep.DoExtAlpha

#Prepare scoring class
AlphaSaveData = AlphaSubstScoring.AlphaSubstScoring(CompType,DoIntAlpha,DoExtAlpha,AlignmentTogether,BranchDescriptions,Group1BranchList,Group2BranchList,Group1ExtBranchList,Group2ExtBranchList,Group1IntBranchList,Group2IntBranchList,InternalBranches,ExternalBranches,DoBranchAlpha,GetSE)
#Perform Boostrapping and BaseML Functions
AlphaSubstWork = AlphaSubstBaseMLBootstrap.AlphaSubstBaseMLBootstrap("")

TimesFailed = 0

if int(DoDoubleBoot) == 0: Iterations = SingleBootIterations
else: Iterations = DoubleBootIterations

for IterationIndex in range(0,int(Iterations)):
    SuccessfulStrap = 0
    TimesFailed = 0
    while SuccessfulStrap == 0 and TimesFailed <= 100:
        if str(DoDoubleBoot) == "0":
            AlphaSubstWork.StrapSequence(Group1Alignments,TotalSeqLength1,SequenceCount,UserRandomKey,DoSingleBoot)
            AlphaSubstWork.RunBaseML(BaseMLLocation,UserRandomKey,GalaxyLocation)
            SuccessfulStrap = int(AlphaSubstWork.ScoreBaseML(BaseMLLocation,UserRandomKey,BranchDescriptions,GalaxyLocation,GetSE,ExtraBaseML,SubstModel))  #Get the results from baseml execution
            #Save the baseml results to the score class
            if SuccessfulStrap != 0:
                AlphaSaveData.AddScores(AlphaSubstWork.BaseMLScores,AlphaSubstWork.BaseMLBranchDesc,1,AlphaSubstWork.SEScores)
            else: TimesFailed += 1

            if int(SuccessfulStrap) != "0" and str(AlignmentTogether) == "0":  
                #Process the second sequence
                AlphaSubstWork.StrapSequence(Group2Alignments,TotalSeqLength2,SequenceCount,UserRandomKey,DoSingleBoot)
                AlphaSubstWork.RunBaseML(BaseMLLocation,UserRandomKey,GalaxyLocation)
                SuccessfulStrap = int(AlphaSubstWork.ScoreBaseML(BaseMLLocation,UserRandomKey,BranchDescriptions,GalaxyLocation,GetSE,ExtraBaseML,SubstModel))
                if SuccessfulStrap != 0:
                    AlphaSaveData.AddScores(AlphaSubstWork.BaseMLScores,AlphaSubstWork.BaseMLBranchDesc,2,AlphaSubstWork.SEScores)
                    AlphaSaveData.CalcMultiSeqAlphas(IterationIndex,DoBranchAlpha)  #Now can calc multiple alignment alphas
                else: TimesFailed += 1
            elif int(SuccessfulStrap) == "0":  TimesFailed += 1

        else:  #Double Bootstrapping
            #FIRST ALIGNMENT

            #Initialize a blank array for per iteration storage
            IterationBranchScoreArray = []
            for TempBranch in BranchDescriptions: IterationBranchScoreArray.append(0)

            SequenceIDArray = []
            #Top level (double) bootstrapping
            for DoubleBootIndex in range(0,Group1AlignmentCount):
                SequenceIDArray.append(str(random.randrange(0,Group1AlignmentCount,1)))

            #Get new a total sequence length
            WeightedLength1 = 0
            for SequenceID in SequenceIDArray:
                WeightedLength1 += Group1AlignLength[int(SequenceID)]

            for SequenceID in SequenceIDArray:
                SequenceID = int(SequenceID)
                SequenceLength = Group1AlignLength[SequenceID]
                Sequence = Group1Alignments[SequenceID]

                AlphaSubstWork.WriteDBSAlignment(SequenceLength,SequenceCount,Sequence,UserRandomKey,DoSingleBoot)
                AlphaSubstWork.RunBaseML(BaseMLLocation,UserRandomKey,GalaxyLocation)
                SuccessfulStrap = int(AlphaSubstWork.ScoreBaseML(BaseMLLocation,UserRandomKey,BranchDescriptions,GalaxyLocation,GetSE,ExtraBaseML,SubstModel))
                if SuccessfulStrap != 0:
                    BranchScores = AlphaSaveData.Get_DBS_Scores(AlphaSubstWork.BaseMLScores,AlphaSubstWork.BaseMLBranchDesc,1,SequenceLength,WeightedLength1)
                    for BranchSubIndex in range (0,len(BranchScores)):
                        IterationBranchScoreArray[BranchSubIndex] += BranchScores[BranchSubIndex]
                else:
                    TimesFailed += 1

            #Save the data
            AlphaSaveData.Save_DBS_Scores(IterationBranchScoreArray,AlphaSubstWork.BaseMLBranchDesc,1,0)

            #SECOND SET OF ALIGNMENTS
            IterationBranchScoreArray = []
            for TempBranch in BranchDescriptions:
                IterationBranchScoreArray.append(0)

            SequenceIDArray = []
            for DoubleBootIndex in range(0,Group2AlignmentCount):
                SequenceIDArray.append(str(random.randrange(0,Group2AlignmentCount,1)))
                
            #Get a total sequence length
            WeightedLength2 = 0
            for SequenceID in SequenceIDArray:
                WeightedLength2 += Group2AlignLength[int(SequenceID)]

            for SequenceID in SequenceIDArray:
                SequenceID = int(SequenceID)
                SequenceLength = Group2AlignLength[SequenceID]
                Sequence = Group2Alignments[SequenceID]
                AlphaSubstWork.WriteDBSAlignment(SequenceLength,SequenceCount,Sequence,UserRandomKey,DoSingleBoot)
                AlphaSubstWork.RunBaseML(BaseMLLocation,UserRandomKey,GalaxyLocation)
                SuccessfulStrap = int(AlphaSubstWork.ScoreBaseML(BaseMLLocation,UserRandomKey,BranchDescriptions,GalaxyLocation,GetSE,ExtraBaseML,SubstModel))
                if SuccessfulStrap != 0:
                    BranchScores = AlphaSaveData.Get_DBS_Scores(AlphaSubstWork.BaseMLScores,AlphaSubstWork.BaseMLBranchDesc,2,SequenceLength,WeightedLength2)
                    for BranchSubIndex in range (0,len(BranchScores)):
                        IterationBranchScoreArray[BranchSubIndex] += BranchScores[BranchSubIndex]
                else:
                    TimesFailed += 1
            #Save the data
            AlphaSaveData.Save_DBS_Scores(IterationBranchScoreArray,AlphaSubstWork.BaseMLBranchDesc,2,0)

            #FOR BOTH ALIGNMENTS
            #Calculate the Alpha Specific Branches
            AlphaSaveData.CalcMultiSeqAlphas(IterationIndex,DoBranchAlpha)

    if TimesFailed > 100:
        stop_err("Maximum chances expended.  Please inspect your sequences.")

#Reporting
Results = AlphaSaveData.CalcStatScores(Iterations,CompType,DoSingleBoot,AlignmentTogether,DoDoubleBoot,Sequences1,Sequences2,SubstModel,GetSE,ExtraBaseML,TotalSeqLength1,TotalSeqLength2,"AlphaSubst",Output_Format)

#create output
of = open(OutputFile,'w')
print >>of,Results

#Clean up data
AlphaSubstWork.FinalCleanUp(BaseMLLocation,GalaxyLocation,UserRandomKey)
