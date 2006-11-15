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
Method = sys.argv[2]
SubstModel = sys.argv[3]
DoSingleBoot = sys.argv[4]
SingleBootIterations = sys.argv[5]
DoDoubleBoot = sys.argv[6]
DoubleBootIterations = sys.argv[7]
Sequences1 = sys.argv[8]
TreeDefinition = sys.argv[9]
FixKappa = sys.argv[10]
KappaValue = sys.argv[11]
Output_Format = sys.argv[12]
#Stat_Results_Outfile = sys.argv[13]

FixAlpha = 1
AlphaValue = 0
FixRho = 1
RhoValue = 0
AlgMethod = 0
MClock = 0

#Get galaxy location
OutputSplit = re.compile('database')
OutContents = OutputSplit.split(OutputFile)
GalaxyLocation = OutContents[0]
BaseMLLocation = "/home/universe/linux-i686/PAML/paml3.15/bin/"

UserRandomKey = str(datetime.date.today()) + "-" + str(random.randrange(0,50000,1))

GetSE = 0
ExtraBaseML = 0
if int(Method) == 0: ExtraBaseML = 1
elif int(Method) == 1 and int(DoDoubleBoot) == 0:    
    DoDoubleBoot = 1
    DoSingleBoot = 0
    DoubleBootIterations = 1

if int(DoSingleBoot) == 0: SingleBootIterations = 1

#Stat reporting - debugging
Stat_Results_Iteration = []
Stat_Results_Sample = []
Stat_Results = ""

#Initial Data Validation
AlphaValid = AlphaSubstValidation.AlphaSubstValidation()
ValidationErrors = AlphaValid.ValidateBaseMLData(DoSingleBoot,SingleBootIterations,TreeDefinition,Sequences1,DoDoubleBoot,DoubleBootIterations)
if ValidationErrors != "":
    stop_err(ValidationErrors)

#No projected errors; continue
SequenceCount = AlphaValid.SequenceCount
Group1AlignmentCount = AlphaValid.Group1AlignmentCount
Group1Alignments = AlphaValid.Group1Alignments
Group1AlignLength = AlphaValid.Group1AlignLength
TotalSequenceLength1 = AlphaValid.TotalSequenceLength1
#HeaderList = AlphaValid.Group1Headers

#Prepare the data for BaseML
AlphaPrep = AlphaSubstPrep.AlphaSubstPrep()
AlphaPrep.PrepBaseML(1,TreeDefinition,SequenceCount,0,UserRandomKey,BaseMLLocation,SubstModel,GetSE,0,0,GalaxyLocation,FixAlpha,AlphaValue,FixKappa,KappaValue,FixRho,RhoValue)
BranchDescriptions = AlphaPrep.BranchDescriptions

#Prepare scoring class
AlphaSaveData = AlphaSubstScoring.AlphaSubstScoring(0,0,0,1,BranchDescriptions,"","","","","","","","",0,GetSE)

#Perform Boostrapping and BaseML Functions
AlphaSubstWork = AlphaSubstBaseMLBootstrap.AlphaSubstBaseMLBootstrap("")

TimesFailed = 0
if Output_Format == "txt":
    AlphaSubstWork.StrapSequence(Group1Alignments,TotalSequenceLength1,SequenceCount,UserRandomKey,0)
    AlphaSubstWork.RunBaseML(BaseMLLocation,UserRandomKey,GalaxyLocation)
    Results = AlphaSubstWork.ReturnBaseMLFile(UserRandomKey,GalaxyLocation)  #Get the results from baseml execution
else:
    if int(ExtraBaseML) == 1 and int(DoDoubleBoot) == 0:
        #This performs an initial run on the data
        AlphaSubstWork.StrapSequence(Group1Alignments,TotalSequenceLength1,SequenceCount,UserRandomKey,0)
        AlphaSubstWork.RunBaseML(BaseMLLocation,UserRandomKey,GalaxyLocation)
        SuccessfulStrap = int(AlphaSubstWork.ScoreBaseML(BaseMLLocation,UserRandomKey,BranchDescriptions,GalaxyLocation,GetSE,ExtraBaseML,SubstModel))  #Get the results from baseml execution
        if SuccessfulStrap != 0:
            AlphaSubstWork.GotExtraBaseML = 1
            AlphaSaveData.TransRatio = AlphaSubstWork.TransRatio
            AlphaSaveData.BaseFreq = AlphaSubstWork.BaseFreq
            AlphaSaveData.RateParameters = AlphaSubstWork.RateParameters
            AlphaSaveData.RateParameterHeaders = AlphaSubstWork.RateParameterHeaders
            AlphaSaveData.RateMatrix = AlphaSubstWork.RateMatrix
        else:
            stop_err("Alignment appears to be incompatible.  Process terminated.")

    TimesFailed = 0;
    if int(DoDoubleBoot) == 0: Iterations = SingleBootIterations
    else: Iterations = DoubleBootIterations

    for IterationIndex in range(0,int(Iterations)):
        SuccessfulStrap = 0
        if int(DoDoubleBoot) == 0:
            while int(SuccessfulStrap) == 0 and int(TimesFailed) <= 100:
                AlphaSubstWork.StrapSequence(Group1Alignments,TotalSequenceLength1,SequenceCount,UserRandomKey,DoSingleBoot)
                AlphaSubstWork.RunBaseML(BaseMLLocation,UserRandomKey,GalaxyLocation)
                SuccessfulStrap = int(AlphaSubstWork.ScoreBaseML(BaseMLLocation,UserRandomKey,BranchDescriptions,GalaxyLocation,GetSE,ExtraBaseML,SubstModel))  #Get the results from baseml execution
                #Save the baseml results to the score class
                if SuccessfulStrap != 0:
                    AlphaSaveData.AddScores(AlphaSubstWork.BaseMLScores,AlphaSubstWork.BaseMLBranchDesc,1,AlphaSubstWork.SEScores)
                else: 
                    TimesFailed += 1
        else:  
            #Double Bootstrapping
            #Initialize a blank array for per iteration storage
            IterationBranchScoreArray = []
            for TempBranch in BranchDescriptions: IterationBranchScoreArray.append(0)

            SequenceIDArray = []
            #Top level (double) bootstrapping

            for DoubleBootIndex in range(0,Group1AlignmentCount):
                if DoSingleBoot == 1:
                    SequenceIDArray.append(str(random.randrange(0,Group1AlignmentCount,1)))
                else:
                    SequenceIDArray.append(str(DoubleBootIndex))

            #Get new a total sequence length
            WeightedLength1 = 0
            for SequenceID in SequenceIDArray:
                WeightedLength1 += Group1AlignLength[int(SequenceID)]

            for DoubleBootIndex in range(0,Group1AlignmentCount):
                SequenceID = random.randrange(0,Group1AlignmentCount,1)    
                SequenceLength = Group1AlignLength[SequenceID]
                Sequence = Group1Alignments[SequenceID]

            for SequenceID in SequenceIDArray:
                SequenceID = int(SequenceID)
                SequenceLength = Group1AlignLength[SequenceID]
                Sequence = Group1Alignments[SequenceID]
                SuccessfulStrap = 0

                while SuccessfulStrap == 0 and TimesFailed <= 100:
                    AlphaSubstWork.WriteDBSAlignment(SequenceLength,SequenceCount,Sequence,UserRandomKey,DoSingleBoot)
                    AlphaSubstWork.RunBaseML(BaseMLLocation,UserRandomKey,GalaxyLocation)
                    SuccessfulStrap = int(AlphaSubstWork.ScoreBaseML(BaseMLLocation,UserRandomKey,BranchDescriptions,GalaxyLocation,0,ExtraBaseML,SubstModel))
                    if SuccessfulStrap != 0:
                        BranchScores = AlphaSaveData.Get_DBS_Scores(AlphaSubstWork.BaseMLScores,AlphaSubstWork.BaseMLBranchDesc,1,SequenceLength,WeightedLength1)
                        for BranchSubIndex in range (0,len(BranchScores)):
                            IterationBranchScoreArray[BranchSubIndex] += BranchScores[BranchSubIndex]
                    else: TimesFailed += 1
                    if TimesFailed > 100: 
                        stop_err("Maximum chances expended.  Please inspect your sequences.")

            #Save the data
            AlphaSaveData.Save_DBS_Scores(IterationBranchScoreArray,AlphaSubstWork.BaseMLBranchDesc,1,1)

        if TimesFailed > 100:
            stop_err("Maximum chances expended.  Please inspect your sequences.")

    #Reporting
    Results = AlphaSaveData.CalcStatScores(Iterations,0,DoSingleBoot,1,DoDoubleBoot,Sequences1,"",SubstModel,GetSE,ExtraBaseML,TotalSequenceLength1,0,"BaseML", Output_Format)

#create output
of = open(OutputFile,'w')
print >>of,Results

#Debugging Statistics
#Stat_Results = "DoubleBoot = " + str(DoDoubleBoot) + "<BR>"
#Stat_Results += "Iterations = " + str(Iterations) + "<BR>"
#Stat_Results += "Alignments = " + str(Group1AlignmentCount) + "<BR><BR>"

#Stat_Results += "Keys = "
#for KeyIndex in range(0,len(AlphaSaveData.NameScoreDictionary)):
#    Stat_Results += str(AlphaSaveData.NameScoreDictionary[KeyIndex]) + " "

#Stat_Results += "<BR><BR>"

#for Index in range(0,len(Stat_Results_Sample)):
#    Stat_Results += "Run #" + str(Index + 1) + ": "
#    for SampleIndex in range(0,len(Stat_Results_Sample)):
#        Stat_Results += str(Stat_Results_Sample[SampleIndex]) + " "

#    Stat_Results += "<BR>Branch Scores " 
#    for SampleIndex in range(0,len(Stat_Results_Iteration)):
#        Stat_Results += str(Stat_Results_Iteration[SampleIndex]) + " "

#Stat_Results += "<BR><BR>"

#of2 = open(Stat_Results_Outfile,'w')
#print >>of2,Stat_Results

#Clean up data
AlphaSubstWork.FinalCleanUp(BaseMLLocation,GalaxyLocation,UserRandomKey)
