import os
import re
import random
import datetime

class AlphaSubstBaseMLBootstrap:
    "This package will perform bootstrap acoording to its parameters, and encapsulate the baseML functionality"

    def __init__(self, ResultsFolder):
        "Doc Holder"
        self.ResultsFolder = ResultsFolder
        self.BaseMLBranchDesc = []
        self.TransRatio = ""
        self.RateMatrix = []
        self.BaseFreq = []
        self.RateParameters = []
        self.RateParameterHeaders = []
        self.GotExtraBaseML = 0

    def RunBaseML(self,BaseMLLoc,UserRandomKey,GalaxyLocation):
        "This function will execute baseml and return the results for the branch description"
        op = os.popen(BaseMLLoc + "baseml " +  GalaxyLocation + "tools/mdea/BaseMLWork/" + str(UserRandomKey) + "-baseml.ctl")

    def FinalCleanUp(self,BaseMLLocation,GalaxyLocation,UserRandomKey):
        "This function will clear the tree and the baseml.ctl files"
        op = os.remove(GalaxyLocation + 'tools/mdea/BaseMLWork/' + str(UserRandomKey) + "-baseml.ctl")
        op = os.remove(GalaxyLocation + 'tools/mdea/BaseMLWork/' + str(UserRandomKey) + "-tmp.tree")

        self.DeleteOldFiles(GalaxyLocation,3)

    def DeleteOldFiles(self,DirectoryToSearch,DaysOld):
        "This program will search the work directory and delete files that are older than 3 days"
        CorrectFormatSearch = re.compile('^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]+-(baseml|tmp)')
        WorkDirectory = DirectoryToSearch + 'tools/mdea/BaseMLWork/' 
        TodaysDateValue = int(self.DateToDays(str(datetime.date.today())))
        DateDifference = 0
        #Open the directory and return the file names
        for FileName in os.listdir(WorkDirectory):
            if CorrectFormatSearch.search(FileName):
                FilesDateValue = int(self.DateToDays(FileName))
                DateDifference = TodaysDateValue - FilesDateValue

                if DateDifference > int(DaysOld):
                    op = os.remove(WorkDirectory + str(FileName))

    def MonthToDays(self,MonthValue):
        "This returns how many days have passed in the month - no leap year support as yet"
        DaysInMonths = [31,28,31,30,31,30,31,31,30,31,30,31]
        MonthDays = 0
        for MonthIndex in range(0,MonthValue - 1):
            MonthDays += int(DaysInMonths[MonthIndex])    
        return MonthDays

    def DateToDays(self,DateString):
        DateSplitter = re.compile("-")
        aDateParts = DateSplitter.split(DateString)
        Years = int(aDateParts[0][2:]) * 365
        Months = int(self.MonthToDays(int(aDateParts[1])))
        Days = int(aDateParts[2])
        return Years + Months + Days

    def ReturnBaseMLFile(self,UserRandomKey,GalaxyLocation):
        "This function will return the contents of the baseml output file, enclosed in a textarea"
        FileResults = ""
        BaseMLOut = open(GalaxyLocation + 'tools/mdea/BaseMLWork/' + str(UserRandomKey) + "-tmp.out")
        FileResults = BaseMLOut.read()
        return FileResults

    def ScoreBaseML(self,BaseMLLoc,UserRandomKey,BranchDescriptions,GalaxyLocation,GetSE,DoExtraBaseML,SubstModel):
        "This function will read tmp.out and set an array of the scores - return a 1 if it was successful - 0 otherwise"
        SuccessfulRun = 0
        SubstModel = int(SubstModel)
        ScoreLineCheck = re.compile('[0-99]\.\.[0-99]')
        SESearch = re.compile('SEs for parameters')
        BaseFreqSearch = re.compile('^Average')
        KappaSearch = re.compile('^Parameters \(kappa\)')
        RateParameterSearch = re.compile('Rate parameters')
        ThreeSpaceSplitter = re.compile('   ')
        TwoSpaceSplitter = re.compile('  ')
        OneSpaceSplitter = re.compile(" ")
        SpaceSplitter = re.compile("\s")
        CommaJoin = re.compile(",")
        NewLineSplitter = re.compile('\n')
        TransSearch = re.compile('Ts\/Tv');
        EqualSplit = re.compile('=')

        DoExtraBaseML = int(DoExtraBaseML)
        TransParts = []
        RateParts = []
        TransRatio = 0
        FileContents = []
        BranchNameArray = []
        BranchScoreArray = []
        BaseMLScoreResults = []
        FinalBranchEntry = []
        SEResults = []
        BaseMLOut = open(GalaxyLocation + 'tools/mdea/BaseMLWork/' + str(UserRandomKey) + "-tmp.out")
        FileContents = NewLineSplitter.split(BaseMLOut.read())
        for FileIndex in range(0,len(FileContents)):
            if ScoreLineCheck.search(FileContents[FileIndex]):
                FileContents[FileIndex] = FileContents[FileIndex].strip()
                FileContents[FileIndex+1] = FileContents[FileIndex+1].strip()
                BranchNameArray = ThreeSpaceSplitter.split(FileContents[FileIndex])
                while TwoSpaceSplitter.search(FileContents[FileIndex+1]):
                    FileContents[FileIndex+1] = TwoSpaceSplitter.sub(" ", FileContents[FileIndex+1])
                BranchScoreArray = OneSpaceSplitter.split(FileContents[FileIndex+1])
                if int(GetSE) == 0 and DoExtraBaseML == 0:
                    break
            if SESearch.search(FileContents[FileIndex]):
                FileContents[FileIndex+1] = FileContents[FileIndex+1].strip()
                while TwoSpaceSplitter.search(FileContents[FileIndex+1]):
                    FileContents[FileIndex+1] = TwoSpaceSplitter.sub(" ", FileContents[FileIndex+1])
                SEResults = OneSpaceSplitter.split(FileContents[FileIndex+1])
                if DoExtraBaseML == 0:
                    break

            if DoExtraBaseML == 1 and self.GotExtraBaseML == 0:
                if BaseFreqSearch.search(FileContents[FileIndex]):
                    BaseFreqLine = FileContents[FileIndex][10:]
                    self.BaseFreq = SpaceSplitter.split(BaseFreqLine.strip())

                if KappaSearch.search(FileContents[FileIndex]):
                    FileIndex += 1
                    KappaLine = FileContents[FileIndex].strip()
                    if SubstModel != 6:
                        self.RateParameters = [KappaLine]
                        self.RateParameterHeaders = ['Kappa']
                    else:
                        KappaValues = TwoSpaceSplitter.split(KappaLine)
                        self.RateParameters = [KappaValues[0],KappaValues[1]]
                        self.RateParameterHeaders = ['Kappa1','Kappa2']

                if SubstModel == 7 or SubstModel == 8:  #Rate Matrix for REV and UNREST
                    if TransSearch.search(FileContents[FileIndex]):
                        TransParts = EqualSplit.split(FileContents[FileIndex])
                        TransRatio = TransParts[1].strip()
                        self.TransRatio = float(TransRatio)
                        #Next 4 lines are the rate matrix data
                        for RateLineIndex in range(0,4):
                            self.RateMatrix.append([])
                            RateLine = FileContents[FileIndex+RateLineIndex+1]
                            RateLine = RateLine.strip()
                            RateParts = ThreeSpaceSplitter.split(RateLine)
                            for RatePartIndex in range(0,4):
                                RateParts[RatePartIndex] = RateParts[RatePartIndex].strip()
                                self.RateMatrix[RateLineIndex].append(float(RateParts[RatePartIndex]))
 
                    if RateParameterSearch.search(FileContents[FileIndex]):
                        RateParameterLine = FileContents[FileIndex][17:]
                        RateParameterLine = RateParameterLine.strip()
                        self.RateParameters = TwoSpaceSplitter.split(RateParameterLine)
                        if SubstModel == 7: self.RateParameterHeaders = ['A','B','C','D','E']
                        elif SubstModel == 8: self.RateParameterHeaders = []
                else:
                    self.RateMatrix = ""
                if SubstModel == 0 or SubstModel == 2:
                    self.RateParameters = ""
                    self.RateParameterHeaders = ""

        BaseMLOut.close()
        #Get BaseML ordered branch descriptions - if they aren't already present
        if len(self.BaseMLBranchDesc) == 0:
            for Branch in BranchNameArray:
                Branch = OneSpaceSplitter.sub("",Branch)
                self.BaseMLBranchDesc.append(Branch)

        if len(BranchNameArray) != 0:
            SuccessfulRun = 1
            self.BaseMLScores = BranchScoreArray
            self.SEScores = SEResults
        else:
            SuccessfulRun = 0
            self.BaseMLScores = []
            self.SEScores = []

        self.CleanData(UserRandomKey,GalaxyLocation + "tools/mdea/BaseMLWork/")

        return SuccessfulRun

    def CleanData(self,UserRandomKey,WorkDir):
        "This function will remove the tmp.out and tmp.seq files"
        op = os.remove(WorkDir + str(UserRandomKey) + "-tmp.out")
        op = os.remove(WorkDir + str(UserRandomKey) + "-tmp.seq")

    def WriteDBSAlignment(self,SequenceLength,SequenceCount,SequenceData,UserRandomKey,DoBootStrap):
        "This function will bootstrap and write a tmp.seq file for baseML"
        if str(DoBootStrap) == "1":
            StrappedSequence = self.DoStrap(SequenceData,SequenceLength,SequenceCount)
        else:
            StrappedSequence = "  " + str(SequenceCount) + " " + str(SequenceLength) + "\n"
            for Index in range(0,len(SequenceData)):
                StrappedSequence += ">Sequence" + str(Index + 1) + "\n"
                StrappedSequence += str(SequenceData[Index]) + "\n" 

        #Check Strapped sequence - for the presence of all nucleotides
        self.WriteFile("tools/mdea/BaseMLWork/" + str(UserRandomKey) + "-tmp.seq",StrappedSequence)

    def StrapSequence(self,StartSeqArray,SequenceLength,SequenceCount,UserRandomKey,DoBootStrap):
        "This will create a sequence replica from a starting Sequence (StartingSequence) - and write it as a tmp.out to the baseml work directory"
        SequenceLine = ""
        Splitter = re.compile('\n') 
    
        #Bootstrap and return
        if str(DoBootStrap) == "1":
            StrappedSequence = self.DoStrap(StartSeqArray,SequenceLength,SequenceCount)
        else:
            StrappedSequence = "   " + str(SequenceCount) + " " + str(SequenceLength) + "\n"  #BaseML Style header
            for BlankArrayIndex in range(0,int(SequenceCount)):
                StrappedSequence += ">Sequence" + str(BlankArrayIndex + 1) + "\n"
                StrappedSequence += str(StartSeqArray[BlankArrayIndex]) + "\n"
        self.WriteFile("tools/mdea/BaseMLWork/" + str(UserRandomKey) + "-tmp.seq",StrappedSequence)

    def DoStrap(self,Sequences,SequenceLength,SequenceCount):
        "Bootstraps a sequence array"
        FinalSequenceArray = []
        FinalSeqFile = ""
        for BlankArrayIndex in range(0,int(SequenceCount)):
            FinalSequenceArray.append('') #Initialize a blank array

        #Bootstrap the sequences
        
        for SequenceLengthIndex in range(0,int(SequenceLength)):
            SamplePosition = random.randrange(0,int(SequenceLength),1)
            for SequenceCountIndex in range(0,int(SequenceCount)):
                FinalSequenceArray[SequenceCountIndex] += Sequences[SequenceCountIndex][SamplePosition]

        #Assemble the replica and return to caller
        FinalSeqFile = "   " + str(SequenceCount) + " " + str(SequenceLength) + "\n"  #BaseML Style header
        for BlankArrayIndex in range(0,int(SequenceCount)):
            FinalSeqFile += ">Sequence" + str(BlankArrayIndex + 1) + "\n"
            FinalSeqFile += str(FinalSequenceArray[BlankArrayIndex][0:]) + "\n"
        return FinalSeqFile

    def WriteFile(self,FileName,Data):
        "This function will write the data passed to a file on the file system"
        TargetFile = file(FileName, "w")
        TargetFile.write(Data)
        TargetFile.close()
