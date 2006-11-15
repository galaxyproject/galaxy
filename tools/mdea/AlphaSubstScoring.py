import re

class AlphaSubstScoring:
    "Documentation Holder"
    def __init__(self,CompType,DoIntAlpha,DoExtAlpha,AlignmentTogether,BranchDescriptions,Group1Cols,Group2Cols,ExtGroup1,ExtGroup2,IntGroup1,IntGroup2,InternalBranches,ExternalBranches,DoBranchAlpha,GetSE):
        "This function will initialize the class with headings for all of the scores"
        self.NameScoreDictionary = {}
        self.BranchNameArray = []
        self.BranchScoreArray = []
        self.CompType = CompType
        self.DoIntAlpha = DoIntAlpha
        self.DoExtAlpha = DoExtAlpha
        self.AlignmentTogether = AlignmentTogether
        self.BranchDescriptions = BranchDescriptions
        self.Group1Cols = Group1Cols
        self.Group2Cols = Group2Cols
        self.Ext1Cols = ExtGroup1
        self.Ext2Cols = ExtGroup2
        self.Int1Cols = IntGroup1
        self.Int2Cols = IntGroup2
        self.IntCols = InternalBranches
        self.ExtCols = ExternalBranches
        self.GetSE = GetSE
        self.DoBranchAlpha = DoBranchAlpha
        self.TransRatio = ""
        self.BaseFreq = ""
        self.RateParameters = ""
        self.RateParameterHeaders = ""
        self.RateMatrix = ""

        ColArrayIndex = 0
        if int(CompType) != 0:  #0 = No comparison - so no alpha (function as baseML wrapper)
            ColArrayIndex = self.AddColumn("AlphaValue",ColArrayIndex)
            ColArrayIndex = self.AddColumn("AlphaRatio",ColArrayIndex)
            ColArrayIndex = self.AddColumn("Group1Length",ColArrayIndex)
            ColArrayIndex = self.AddColumn("Group2Length",ColArrayIndex)
            if int(DoIntAlpha) == 1:
                ColArrayIndex = self.AddColumn("IntAlphaValue",ColArrayIndex)
                ColArrayIndex = self.AddColumn("IntAlphaRatio",ColArrayIndex)
                ColArrayIndex = self.AddColumn("IntGroup1Length",ColArrayIndex)
                ColArrayIndex = self.AddColumn("IntGroup2Length",ColArrayIndex)
            if int(DoExtAlpha) == 1:
                ColArrayIndex = self.AddColumn("ExtAlphaValue",ColArrayIndex)
                ColArrayIndex = self.AddColumn("ExtAlphaRatio",ColArrayIndex)
                ColArrayIndex = self.AddColumn("ExtGroup1Length",ColArrayIndex)
                ColArrayIndex = self.AddColumn("ExtGroup2Length",ColArrayIndex)

        if str(AlignmentTogether) == "1":
            ColArrayIndex = self.AddColumn("TreeLength",ColArrayIndex)
        else:
            ColArrayIndex = self.AddColumn("TreeLength_1",ColArrayIndex)
            ColArrayIndex = self.AddColumn("TreeLength_2",ColArrayIndex)

        for Branch in BranchDescriptions:
            if int(AlignmentTogether) == 1:
                ColArrayIndex = self.AddColumn(Branch,ColArrayIndex)
                if int(GetSE) == 1:
                    ColArrayIndex = self.AddColumn(Branch + "_SE",ColArrayIndex)
            else:
                ColArrayIndex = self.AddColumn(Branch + "_1",ColArrayIndex)
                if int(GetSE) == 1:
                    ColArrayIndex = self.AddColumn(Branch + "_1_SE",ColArrayIndex)
                ColArrayIndex = self.AddColumn(Branch + "_2",ColArrayIndex)    
                if int(GetSE) == 1:
                    ColArrayIndex = self.AddColumn(Branch + "_2_SE",ColArrayIndex)
                if str(DoBranchAlpha) == "1":
                    ColArrayIndex = self.AddColumn(Branch + "_AlphaValue",ColArrayIndex)
                    ColArrayIndex = self.AddColumn(Branch + "_AlphaRatio",ColArrayIndex)

    def CalcMultiSeqAlphas(self,IterationIndex,DoBranchAlpha):
        "This function calculates alpha values for multiple sequences"
        CompType = int(self.CompType)
        DoIntAlpha = int(self.DoIntAlpha)
        DoExtAlpha = int(self.DoExtAlpha)
        LastIndex = IterationIndex - 1

        if CompType != 0:
            if str(DoBranchAlpha) == "1": #Branch by Branch Alphas
                for BranchName in self.BranchDescriptions:
                    BranchLength1 = self.BranchScoreArray[self.LookupArrayIndex(str(BranchName) + "_1")][LastIndex]
                    BranchLength2 = self.BranchScoreArray[self.LookupArrayIndex(str(BranchName) + "_2")][LastIndex]

                    if float(BranchLength2) != 0:
                        BranchRatio = BranchLength1 / BranchLength2
                        BranchAlpha = self.CalculateAlpha(BranchRatio,CompType,"")
                        self.BranchScoreArray[self.LookupArrayIndex(str(BranchName) + "_AlphaRatio")].append(BranchRatio)
                        self.BranchScoreArray[self.LookupArrayIndex(str(BranchName) + "_AlphaValue")].append(BranchAlpha)
                    else:
                        self.BranchScoreArray[self.LookupArrayIndex(str(BranchName) + "_AlphaRatio")].append(-1)
                        self.BranchScoreArray[self.LookupArrayIndex(str(BranchName) + "_AlphaValue")].append(-1)
            Group1Length = self.BranchScoreArray[self.LookupArrayIndex("Group1Length")][LastIndex]
            Group2Length = self.BranchScoreArray[self.LookupArrayIndex("Group2Length")][LastIndex]
            if float(Group2Length) == 0: AlphaRatio = 0
            else: AlphaRatio = Group1Length / Group2Length
            Alpha = self.CalculateAlpha(AlphaRatio,CompType,"")
            self.BranchScoreArray[self.LookupArrayIndex("AlphaRatio")].append(AlphaRatio)
            self.BranchScoreArray[self.LookupArrayIndex("AlphaValue")].append(Alpha)
            if DoIntAlpha == 1:
                Int1Length = self.BranchScoreArray[self.LookupArrayIndex("IntGroup1Length")][LastIndex]
                Int2Length = self.BranchScoreArray[self.LookupArrayIndex("IntGroup2Length")][LastIndex]
                if float(Int2Length) == 0: IntAlphaRatio = 0
                else: IntAlphaRatio = Int1Length / Int2Length
                IntAlpha = self.CalculateAlpha(IntAlphaRatio,CompType,"")
                self.BranchScoreArray[self.LookupArrayIndex("IntAlphaRatio")].append(IntAlphaRatio)
                self.BranchScoreArray[self.LookupArrayIndex("IntAlphaValue")].append(IntAlpha)
            if DoExtAlpha == 1:
                Ext1Length = self.BranchScoreArray[self.LookupArrayIndex("ExtGroup1Length")][LastIndex]
                Ext2Length = self.BranchScoreArray[self.LookupArrayIndex("ExtGroup2Length")][LastIndex]
                if float(Ext2Length) == 0: ExtAlphaRatio = 0
                else: ExtAlphaRatio = Ext1Length / Ext2Length
                ExtAlpha = self.CalculateAlpha(ExtAlphaRatio,CompType,"")
                self.BranchScoreArray[self.LookupArrayIndex("ExtAlphaRatio")].append(ExtAlphaRatio)
                self.BranchScoreArray[self.LookupArrayIndex("ExtAlphaValue")].append(ExtAlpha)

    def AddColumn(self,Description,GroupIndex):
        "This function adds a header column to the class"
        self.BranchNameArray.append(Description)
        self.BranchScoreArray.append([])  #Add a second dimension to the array for score storage
        self.NameScoreDictionary[GroupIndex] = Description
        GroupIndex += 1
        return GroupIndex

    def WeightBranchScore(self,Score,SequenceLength,TotalSequenceLength):
        "This function runs the weighted average alrogithim on a number"
        ReturnScore = (Score * SequenceLength) / TotalSequenceLength
        return ReturnScore

    def Get_DBS_Scores(self,ScoreArray,BaseMLBranchDesc,GroupID,SequenceLength,TotalSequenceLength):
        "This function will get the scores from baseml and weight them and return the scores"
        CompType = self.CompType
        AlignmentTogether = self.AlignmentTogether
        BranchScores = []
        IntLength = 0
        ExtLength = 0
        RemoveLeadWhiteSpace = re.compile('^\s')
        RemoveTrailWhiteSpace = re.compile('^\s')
        OneSpaceSplitter = re.compile('\s')        

        for BranchIndex in range(0,len(BaseMLBranchDesc)):
            BranchName = BaseMLBranchDesc[BranchIndex]
            BranchScore = str(ScoreArray[BranchIndex])
            BranchScore = RemoveLeadWhiteSpace.sub("",BranchScore)
            BranchScore = RemoveLeadWhiteSpace.sub("",BranchScore)
            if OneSpaceSplitter.search(BranchScore):
                BranchParts = OneSpaceSplitter.split(BranchScore)
                BranchScore = self.WeightBranchScore(float(BranchParts[0]),SequenceLength,TotalSequenceLength)
            else:
                BranchScore = self.WeightBranchScore(float(BranchScore),SequenceLength,TotalSequenceLength)

            BranchScores.append(BranchScore)
        return BranchScores

    def Save_DBS_Scores(self,ScoreArray,BaseMLBranchDesc,GroupID,BaseMLFlag):
        CompType = self.CompType
        DoIntAlpha = self.DoIntAlpha
        DoExtAlpha = self.DoExtAlpha
        Group1Cols = self.Group1Cols
        Group2Cols = self.Group2Cols
        Ext1Cols = self.Ext1Cols
        Ext2Cols = self.Ext2Cols
        Int1Cols = self.Int1Cols
        Int2Cols = self.Int2Cols
        IntCols = self.IntCols
        ExtCols = self.ExtCols
        TotalTreeLength = 0
        IntLength = 0
        ExtLength = 0
        AlignmentTogether = self.AlignmentTogether
        RemoveLeadWhiteSpace = re.compile('^\s')
        RemoveTrailWhiteSpace = re.compile('^\s')
        OneSpaceSplitter = re.compile('\s')        

        for BranchIndex in range(0,len(BaseMLBranchDesc)):
            BranchName = BaseMLBranchDesc[BranchIndex]
            BranchScore = str(ScoreArray[BranchIndex])
            BranchScore = RemoveLeadWhiteSpace.sub("",BranchScore)
            BranchScore = RemoveLeadWhiteSpace.sub("",BranchScore)
            if OneSpaceSplitter.search(BranchScore):
                BranchParts = OneSpaceSplitter.split(BranchScore)
                BranchScore = float(BranchParts[0])
            else:
                BranchScore = float(BranchScore)
            TotalTreeLength += BranchScore

            if int(BaseMLFlag) == 0:
                self.BranchScoreArray[self.LookupArrayIndex(str(BranchName) + "_" + str(GroupID))].append(BranchScore)
            else:
                self.BranchScoreArray[self.LookupArrayIndex(str(BranchName))].append(BranchScore)

            if int(CompType) != 0:  
                if str(DoIntAlpha) == "1":
                    if IntCols.__contains__(BranchName):
                        IntLength += BranchScore
                if str(DoExtAlpha) == "1":
                    if ExtCols.__contains__(BranchName):
                        ExtLength += BranchScore

        if int(BaseMLFlag) == 0:
            self.BranchScoreArray[self.LookupArrayIndex("TreeLength" + "_" + str(GroupID))].append(TotalTreeLength)
        else:
            self.BranchScoreArray[self.LookupArrayIndex("TreeLength")].append(TotalTreeLength)

        if int(CompType) != 0 and str(AlignmentTogether) == "0":
            self.BranchScoreArray[self.LookupArrayIndex("Group" + str(GroupID) + "Length")].append(TotalTreeLength)
            if str(DoExtAlpha) == "1":
                self.BranchScoreArray[self.LookupArrayIndex("ExtGroup" + str(GroupID) + "Length")].append(ExtLength)
            if str(DoIntAlpha) == "1":
                self.BranchScoreArray[self.LookupArrayIndex("IntGroup" + str(GroupID) + "Length")].append(IntLength)
        
    def AddScores(self,ScoreArray,BaseMLBranchDesc,GroupID,SEScores):
        "This function will add the passed scores and compute additional scores and add them to the class array"
        CompType = self.CompType
        DoIntAlpha = self.DoIntAlpha
        DoExtAlpha = self.DoExtAlpha
        AlignmentTogether = self.AlignmentTogether
        Group1Cols = self.Group1Cols
        Group2Cols = self.Group2Cols
        Ext1Cols = self.Ext1Cols
        Ext2Cols = self.Ext2Cols
        Int1Cols = self.Int1Cols
        Int2Cols = self.Int2Cols
        IntCols = self.IntCols
        ExtCols = self.ExtCols
        GetSE = self.GetSE

        RemoveLeadWhiteSpace = re.compile('^\s')
        RemoveTrailWhiteSpace = re.compile('^\s')
        OneSpaceSplitter = re.compile('\s')        

        #Write the branches to the database
        TotalTreeLength = 0
        Alpha = 0
        AlphaRatio = 0
        Group1Length = 0
        Group2Length = 0
        IntAlpha = 0
        IntAlphaRatio = 0
        Int1Length = 0
        Int2Length = 0
        ExtAlpha = 0
        ExtAlphaRatio = 0
        Ext1Length = 0
        Ext2Length = 0
        IntLength = 0
        ExtLength = 0

        for BranchIndex in range(0,len(BaseMLBranchDesc)):
            BranchName = BaseMLBranchDesc[BranchIndex]
            BranchScore = str(ScoreArray[BranchIndex])
            BranchScore = RemoveLeadWhiteSpace.sub("",BranchScore)
            BranchScore = RemoveLeadWhiteSpace.sub("",BranchScore)
            if OneSpaceSplitter.search(BranchScore):
                BranchParts = OneSpaceSplitter.split(BranchScore)
                BranchScore = float(BranchParts[0])
            else:
                BranchScore = float(BranchScore)
            TotalTreeLength += BranchScore

            if int(GetSE) == 1: #Format the SE data - single space paml workaround
                SEScore = str(SEScores[BranchIndex])
                SEScore = RemoveLeadWhiteSpace.sub("",SEScore)
                SEScore = RemoveLeadWhiteSpace.sub("",SEScore)
                if OneSpaceSplitter.search(SEScore):
                    SEScoreArray = OneSpaceSplitter.split(SEScore)
                    SEScore = float(SEScoreArray[0])
                else:
                    SEScore = float(SEScore)

            if str(AlignmentTogether) == "0":
                self.BranchScoreArray[self.LookupArrayIndex(str(BranchName) + "_" + str(GroupID))].append(BranchScore)
                if int(GetSE) == 1:
                    SEBranchName = str(BranchName) + "_" + str(GroupID) + "_SE"
                    self.BranchScoreArray[self.LookupArrayIndex(str(SEBranchName))].append(SEScore)
            else:
                self.BranchScoreArray[self.LookupArrayIndex(BranchName)].append(BranchScore)
                if int(GetSE) == 1:
                    self.BranchScoreArray[self.LookupArrayIndex(str(BranchName) + "_SE")].append(SEScore)
    
            if int(CompType) != 0:  
                if str(AlignmentTogether) == "1":  #Can't do Alpha specific calculations for a double sequence - because the second has been processed
                    if Group1Cols.__contains__(BranchName):
                        Group1Length += BranchScore    
                        if str(DoIntAlpha) == "1":    
                            if Int1Cols.__contains__(BranchName):
                                Int1Length += BranchScore
                        if str(DoExtAlpha) == "1":
                            if Ext1Cols.__contains__(BranchName):
                                Ext1Length += BranchScore
                    if Group2Cols.__contains__(BranchName):
                        Group2Length += BranchScore
                        if str(DoIntAlpha) == "1":
                            if Int2Cols.__contains__(BranchName):
                                Int2Length += BranchScore
                        if str(DoExtAlpha) == "1":
                            if Ext2Cols.__contains__(BranchName):
                                Ext2Length += BranchScore
                else:
                    if str(DoIntAlpha) == "1":
                        if IntCols.__contains__(BranchName):
                            IntLength += BranchScore
                    if str(DoExtAlpha) == "1":
                        if ExtCols.__contains__(BranchName):
                            ExtLength += BranchScore

        if str(AlignmentTogether) == "1":
            self.BranchScoreArray[self.LookupArrayIndex("TreeLength")].append(TotalTreeLength)
        else:
            self.BranchScoreArray[self.LookupArrayIndex("TreeLength" + "_" + str(GroupID))].append(TotalTreeLength)
    
        if int(CompType) != 0 and str(AlignmentTogether) == "1":  #Ratios and Alpha Values
            if Group2Length != 0: 
                AlphaRatio = Group1Length / Group2Length
                Alpha = self.CalculateAlpha(AlphaRatio,CompType,"Output")
            else: 
                AlphaRatio = 0
                Alpha = "0**"
            self.BranchScoreArray[self.LookupArrayIndex("Group1Length")].append(Group1Length)
            self.BranchScoreArray[self.LookupArrayIndex("Group2Length")].append(Group2Length)
            self.BranchScoreArray[self.LookupArrayIndex("AlphaRatio")].append(AlphaRatio)
            self.BranchScoreArray[self.LookupArrayIndex("AlphaValue")].append(Alpha)
            if str(DoIntAlpha) == "1":
                if Int2Length != 0: 
                    IntAlphaRatio = Int1Length / Int2Length
                    IntAlpha = self.CalculateAlpha(IntAlphaRatio,CompType,"Output")
                else: 
                    IntAlphaRatio = 0
                    IntAlpha = "0**"
                self.BranchScoreArray[self.LookupArrayIndex("IntGroup1Length")].append(Int1Length)
                self.BranchScoreArray[self.LookupArrayIndex("IntGroup2Length")].append(Int2Length)
                self.BranchScoreArray[self.LookupArrayIndex("IntAlphaRatio")].append(IntAlphaRatio)
                self.BranchScoreArray[self.LookupArrayIndex("IntAlphaValue")].append(IntAlpha)

            if str(DoExtAlpha) == "1":
                if Ext2Length != 0: 
                    ExtAlphaRatio = Ext1Length / Ext2Length
                    ExtAlpha = self.CalculateAlpha(ExtAlphaRatio,CompType,"Output")
                else: 
                    ExtAlphaRatio = 0
                    ExtAlpha = "0**"
                self.BranchScoreArray[self.LookupArrayIndex("ExtGroup1Length")].append(Ext1Length)
                self.BranchScoreArray[self.LookupArrayIndex("ExtGroup2Length")].append(Ext2Length)
                self.BranchScoreArray[self.LookupArrayIndex("ExtAlphaRatio")].append(ExtAlphaRatio)
                self.BranchScoreArray[self.LookupArrayIndex("ExtAlphaValue")].append(ExtAlpha)
        elif int(CompType) != 0 and str(AlignmentTogether) == "0":
            self.BranchScoreArray[self.LookupArrayIndex("Group" + str(GroupID) + "Length")].append(TotalTreeLength)
            if str(DoExtAlpha) == "1":
                self.BranchScoreArray[self.LookupArrayIndex("ExtGroup" + str(GroupID) + "Length")].append(ExtLength)
            if str(DoIntAlpha) == "1":
                self.BranchScoreArray[self.LookupArrayIndex("IntGroup" + str(GroupID) + "Length")].append(IntLength)

    def LookupArrayIndex(self,ColumnName):
        "This function will search the dictionary and return the array id of the column name key"
        for Index in range(0,len(self.NameScoreDictionary)):
            if self.NameScoreDictionary[Index] == ColumnName:
                return Index

    def CalculateAlpha(self,Ratio,CompType,DisplayFlag):
        "This function calculates alpha for the ratio and type of comparison passed to it"
        CompType = str(CompType)
        #Alpha Logic used for display function - negative numbers retain proper order
        if DisplayFlag == "Output": AlphaLogic = 1
        else: AlphaLogic = 0

        #This occurs when the second part of the ratio is 0 - handle division by zero errors
        AlphaValue = 0.0
        if CompType == "1":
            if AlphaLogic == 0 or float(Ratio) < 3:
                if float(Ratio) != 3: AlphaValue = (2 * Ratio) / (3 - Ratio)
                else: AlphaValue = -1
            else: AlphaValue = "-1"  #Program code to display infinity
        elif CompType == "2":
            if AlphaLogic == 0 or float(Ratio) < 2:
                if float(Ratio) != 2: AlphaValue = (Ratio) / (2 - Ratio)
                else: AlphaValue = -1
            else: AlphaValue = "-1"
        elif CompType == "3":
            if AlphaLogic == 0:
                if float(Ratio) != float(2/3): AlphaValue = ((3 * Ratio) - 4) / (2 - (3 * Ratio))
                else: AlphaValue = -1
            elif float(Ratio) <= float(2/3):
                AlphaValue = -1
            elif float(Ratio) >= float(4/3):    
                AlphaValue = 0
            else:
                if float(Ratio) != float(2/3): AlphaValue = ((3 * Ratio) - 4) / (2 - (3 * Ratio))
                else: AlphaValue = -1
        elif CompType == "4":
            if AlphaLogic == 0 or float(Ratio) > float(1/3):
                AlphaValue = ((3 * Ratio) - 1) / (2)
            elif float(Ratio) <= float(1/3):
                AlphaValue = 0
        elif CompType == "5":
            if AlphaLogic == 0:
                if float(Ratio) != float(4/3): AlphaValue = ((3 * Ratio) - 2) / (4 - (3 * Ratio))
                else: AlphaValue = -1
            elif float(Ratio) <= float(2/3):
                AlphaValue = 0
            elif  float(Ratio) >= float(4/3):
                AlphaValue = -1
            else:
                if float(Ratio) != float(4/3): AlphaValue = ((3 * Ratio) - 2) / (4 - (3 * Ratio))
                else: AlphaValue = -1
        elif CompType == "6":
            if AlphaLogic == 0 or float(Ratio) < 2:
                if float(Ratio) != 0: AlphaValue = (2 - Ratio) / (Ratio)
                else: AlphaValue = -1
            else:
                AlphaValue = 0

        return AlphaValue
                            
    def CalcStatScores(self,Iterations,CompType,DoInAlignBootStrap,AlignmentTogether,DoDoubleBoot,Sequences1,Sequences2,SubstModel,GetSE,ExtraBaseML,SeqLength1,SeqLength2,RunMode,Output_Format):
        "This function will perform mean, median, and confidence intervals and populate and return the results"
        #Determine offsets for median and confidence intervals
        ScoreArray = self.BranchScoreArray

        AlphaSearch = re.compile('AlphaValue')
        AlphaNameSearch = re.compile('Alpha')
        AlphaRatioSearch = re.compile('AlphaRatio')
        BranchLengthSearch = re.compile('\.\.[0-9]+_1')
        BranchSearch = re.compile('\.\.')
        SESearch = re.compile("_SE")
        TreeLengthSearch = re.compile('TreeLength')
        TotalTreeLength = re.compile('[Tt]otal')
        Iterations = int(Iterations)
        LowLimitResults = []
        HighLimitResults = []
        MedianResults = []
        MeanResults = []
        ColResults = []
        LowOffset = 0
        LowGetRec = 1
        MidOffset = 0
        MidGetRec = 1
        HighOffset = 0
        HighGetRec = 1
        SearchIndex = 0
        MeanValue = ""
        RowColor = ""
        ResultString = ""

        if int(Iterations) > 1:
            LowOffset = int(Iterations * .025)
            MidOffset = int(Iterations / 2)
            HighOffset = int(Iterations * .975)    - 1    
            if LowOffset == 0:
                LowOffset += 1

        #Get the stat scores for the fields

        for DicKeyIndex in range(0,len(self.NameScoreDictionary)):
            Mean = 0
            Median = 0
            LowLimit = 0
            HighLimit = 0

            ColumnName = self.NameScoreDictionary[DicKeyIndex]
            if AlphaSearch.search(ColumnName):  #This is an Alpha column - must order by the ratios
                SearchColumn = ColumnName.replace("AlphaValue","AlphaRatio")
                SearchIndex = self.LookupArrayIndex(SearchColumn)
                ScoreArray[SearchIndex].sort()
                if int(Iterations) != 1:
                    LowLimit = self.CalculateAlpha(ScoreArray[SearchIndex][LowOffset-1:LowOffset][0],CompType,"Output")
                    Median = self.CalculateAlpha(ScoreArray[SearchIndex][MidOffset-1:MidOffset][0],CompType,"Output")
                    HighLimit = self.CalculateAlpha(ScoreArray[SearchIndex][HighOffset-1:HighOffset][0],CompType,"Output")
                else:
                    Median = self.CalculateAlpha(ScoreArray[SearchIndex][0],CompType,"Output")
                Mean = ""
            else:
                ScoreArray[DicKeyIndex].sort()
                if int(Iterations) != 1:
                    LowLimit = float(ScoreArray[DicKeyIndex][LowOffset-1:LowOffset][0])
                    Median = float(ScoreArray[DicKeyIndex][MidOffset-1:MidOffset][0])
                    HighLimit = float(ScoreArray[DicKeyIndex][HighOffset-1:HighOffset][0])
                    Mean = float(self.AverageColumn(ScoreArray[DicKeyIndex]))
                else:
                    Median = float(ScoreArray[DicKeyIndex][0])

            ColResults.append(ColumnName)
            if SESearch.search(ColumnName):
                LowLimitResults.append(self.SigFigRound(LowLimit,5))
                HighLimitResults.append(self.SigFigRound(HighLimit,5))
                MedianResults.append(self.SigFigRound(Median,5))
                MeanResults.append(self.SigFigRound(Mean,5))
            else:
                if float(LowLimit) < 0: LowLimitResults.append("Infinity")
                elif float(LowLimit) == 0 and AlphaSearch.search(ColumnName): LowLimitResults.append("0*")
                elif float(LowLimit) == 0 and AlphaRatioSearch.search(ColumnName): LowLimitResults.append("0**")
                else: LowLimitResults.append(self.SigFigRound(LowLimit,5))

                if float(HighLimit) < 0: HighLimitResults.append("Infinity")
                elif float(HighLimit) == 0 and AlphaSearch.search(ColumnName): HighLimitResults.append("0*")
                elif float(HighLimit) == 0 and AlphaRatioSearch.search(ColumnName): HighLimitResults.append("0**")
                else: HighLimitResults.append(self.SigFigRound(HighLimit,5))

                if float(Median) < 0: MedianResults.append("Infinity")
                elif float(Median) == 0 and AlphaSearch.search(ColumnName): MedianResults.append("0*")
                elif float(Median) == 0 and AlphaRatioSearch.search(ColumnName): MedianResults.append("0**")
                else: MedianResults.append(self.SigFigRound(Median,5))

                if str(Mean) != "":
                    if float(Mean) < 0: MeanResults.append("Infinity")
                    elif float(Mean) == 0 and AlphaSearch.search(ColumnName): MeanResults.append("0*")
                    elif float(Mean) == 0 and AlphaRatioSearch.search(ColumnName): MeanResults.append("0**")
                    else: MeanResults.append(self.SigFigRound(Mean,5))
                else: MeanResults.append("")

        if Output_Format == "html":
            HeaderString = self.WriteHeader(Iterations,CompType,DoInAlignBootStrap,AlignmentTogether,DoDoubleBoot,Sequences1,Sequences2,SubstModel,ExtraBaseML,self.TransRatio,SeqLength1,SeqLength2,RunMode)
        if Output_Format == "html" and str(DoInAlignBootStrap) == "1":
            ResultString = "<TABLE cellpadding=5 cellspacing=0><TR><TH width=36%>&nbsp;</TH><TH width=16% align=left>Mean</TH><TH width=16% align=left>Median</TH><TH width=16% align=left>Lower 95% Confidence Limit</TH><TH width=16% align=left>Upper 95% Confidence Limit</TH></TR>"
        elif Output_Format == "html" and str(DoInAlignBootStrap) == "0":
            ResultString = "<TABLE cellpadding=5 cellspacing=0><TR><TH>&nbsp;</TH><TH>Value</TH></TR>"
        elif Output_Format == "Tabular" and str(DoInAlignBootStrap) == "1":
            ResultString = "Branch\tMean\tMedian\tLower_Limit\tUpper_Limit\n"
        elif Output_Format == "Tabular" and str(DoInAlignBootStrap) == "0":
            ResultString = "Branch\tValue\n"

        for ResultIndex in range(0,len(ColResults)):
            BranchTitle = ColResults[ResultIndex]
            if BranchLengthSearch.search(BranchTitle):
                if RowColor == "#9999FF": RowColor = "#CCCCFF"
                else: RowColor = "#9999FF"
            elif AlphaSearch.search(BranchTitle) and not BranchSearch.search(BranchTitle):
                if RowColor == "#9999FF": RowColor = "#CCCCFF"
                else: RowColor = "#9999FF"
            elif TreeLengthSearch.search(BranchTitle):
                RowColor = "#9999CC"

            if AlphaSearch.search(BranchTitle): 
                if str(Output_Format) == "html": MeanValue = "&nbsp;"
                elif str(Output_Format) == "Tabular": MeanValue = "----"
            else: MeanValue = str(MeanResults[ResultIndex])

            BranchTitle = self.DecodeBranchName(BranchTitle,CompType,AlignmentTogether,Output_Format)

            if not TotalTreeLength.search(BranchTitle):
                if str(MeanValue) == "0.0": MeanValue = "0.00000"
                if str(MedianResults[ResultIndex]) == "0.0": MedianResults[ResultIndex] = "0.00000"
                if str(LowLimitResults[ResultIndex]) == "0.0": LowLimitResults[ResultIndex] = "0.00000"
                if str(HighLimitResults[ResultIndex]) == "0.0": HighLimitResults[ResultIndex] = "0.00000"

                if Output_Format == "html" and str(DoInAlignBootStrap) == "1": ResultString += "<TR BGCOLOR=" + RowColor + "><TD>" + BranchTitle + "</TD><TD>" + MeanValue + "</TD><TD>" + str(MedianResults[ResultIndex]) + "</TD><TD>" + str(LowLimitResults[ResultIndex]) + "</TD><TD>" + str(HighLimitResults[ResultIndex]) + "</TD></TR>"
                elif Output_Format == "html" and str(DoInAlignBootStrap) == "0": ResultString += "<TR BGCOLOR=" + RowColor + "><TD>" + BranchTitle + "</TD><TD>" + str(MedianResults[ResultIndex]) + "</TD></TR>"
                elif Output_Format == "Tabular" and str(DoInAlignBootStrap) == "1": ResultString += BranchTitle + "\t" + MeanValue + "\t" + str(MedianResults[ResultIndex]) + "\t" + str(LowLimitResults[ResultIndex]) + "\t" + str(HighLimitResults[ResultIndex]) + "\n"
                elif Output_Format == "Tabular" and str(DoInAlignBootStrap) == "0": ResultString += BranchTitle + "\t" + str(MedianResults[ResultIndex]) + "\n"
            else:
                if Output_Format == "html" and RunMode == "AlphaSubst": ResultString += "<TR BGCOLOR=#FFFFFF><TD COLSPAN=5><HR></TD></TR>"
                elif Output_Format == "html" and RunMode == "BaseML" and str(DoInAlignBootStrap) == "1": ResultString += "<TR BGCOLOR=" + RowColor + "><TD>" + BranchTitle + "</TD><TD>" + MeanValue + "</TD><TD>" + str(MedianResults[ResultIndex]) + "</TD><TD>" + str(LowLimitResults[ResultIndex]) + "</TD><TD>" + str(HighLimitResults[ResultIndex]) + "</TD></TR>"
                elif Output_Format == "html" and RunMode == "BaseML" and str(DoInAlignBootStrap) == "0": ResultString += "<TR BGCOLOR=" + RowColor + "><TD>" + BranchTitle + "</TD><TD>" + str(MedianResults[ResultIndex]) + "</TD></TR>"
                elif Output_Format == "Tabular" and str(DoInAlignBootStrap) == "1": ResultString += "Total\t" + MeanValue + "\t" + str(MedianResults[ResultIndex]) + "\t" + str(LowLimitResults[ResultIndex]) + "\t" + str(HighLimitResults[ResultIndex]) + "\n"
                elif Output_Format == "Tabular" and str(DoInAlignBootStrap) == "0": ResultString += "Total\t" + str(MedianResults[ResultIndex]) + "\n"

        if Output_Format == "html":
            ResultString += "</TABLE>"

        if int(ExtraBaseML) == 1 and Output_Format == "html":
            if self.BaseFreq != "":  #Base Frequency Results
                ResultString += "<BR><DIV><B>Base Frequencies</B></DIV><BR>"
                ResultString += "<TABLE cellpadding=5 cellspacing=0><TR><TH align=left>&pi T</TH><TH align=left>&pi C</TH><TH align=left>&pi A</TH><TH align=left>&pi G</TH></TR>"
                ResultString += "<TR><TD>" + str(self.BaseFreq[0]) + "</TD><TD>" + str(self.BaseFreq[1]) + "</TD><TD>" + str(self.BaseFreq[2]) + "</TD><TD>" + str(self.BaseFreq[3]) + "</TD></TR>"
                ResultString += "</TABLE>"

            if self.RateParameterHeaders != []:
                ResultString += "<BR><DIV><B>Rate Parameters</B></DIV><BR>"
                ResultString += "<TABLE cellpadding=5 cellspacing=0><TR>"
                for Index in range(0,len(self.RateParameterHeaders)):
                    ResultString += "<TH align=left>" + str(self.RateParameterHeaders[Index]) + "</TH>"
                ResultString += "</TR><TR>"
                for Index in range(0,len(self.RateParameters)):
                    ResultString += "<TD align=left>" + str(self.RateParameters[Index]) + "</TD>"
                ResultString += "</TR></TABLE>"
            if self.RateMatrix != "": #Rate Matrix Results - REV and UNREST
                ResultString += "<BR><DIV><B>Rate Matrix</B></DIV><BR>"
                ResultString += "<TABLE cellpadding=5 cellspacing=0><TR><TH>&nbsp;</TH><TH align=left>T</TH><TH align=left>C</TH><TH align=left>A</TH><TH align=left>G</TH></TR>"
                RowChar = ""
                for Index in range(0,len(self.RateMatrix)):
                    if Index == 0: RowChar = "<B>T</B>"
                    elif Index == 1: RowChar = "<B>C</B>"
                    elif Index == 2: RowChar = "<B>A</B>"
                    elif Index == 3: RowChar = "<B>G</B>"
                    ResultString += "<TR><TD>" + RowChar + "</TD>"
                    for SubIndex in range(0,len(self.RateMatrix[Index])):
                        ResultString += "<TD>" + str(self.RateMatrix[Index][SubIndex]) + "</TD>"
                    ResultString += "</TR>"
                ResultString += "</TABLE>"        

        if Output_Format == "html":
            ResultString += "</BODY></HTML>"
            ResultString = HeaderString + "<HR>" + ResultString

        #Legend
        if str(RunMode) == "Alpha":
            ResultString += "<TABLE><TR><TD>*:</TD><TD>Alpha is undefined for this ratio.</TD></TR>"
            ResultString += "<TR><TD>**:</TD><TD>The denominator of this ratio was zero.  Alpha could not be calculated.</TD></TR></TABLE>\n\n"

        return ResultString    

    def DecodeBranchName(self,Name,CompType,AlignmentTogether,Output_Format):
        "This will give the branches a friendly name for display"
        NewBranchName = ""
        InternalSearch = re.compile('^Int')
        ExternalSearch = re.compile('^Ext')
        AlphaSearch = re.compile('Alpha')
        RatioSearch = re.compile('Ratio')
        GroupSearch = re.compile('Group')
        GroupBranchSearch = re.compile('\.\.[0-9]+_[12]')
        BranchSearch = re.compile('\.\.')
        SESearch = re.compile("_SE")
        TreeLengthSearch = re.compile('TreeLength')

        GroupID = 0
        UnderscorePosition = 0
        GroupPosition = 0
        GroupCharacter = ""

        if InternalSearch.search(Name):
            NewBranchName = "Internal "
        elif ExternalSearch.search(Name):
            NewBranchName = "External "
        else:
            NewBranchName = ""

        if str(Output_Format) == "Tabular": Separator = "_"
        else: Separator = " "

        if GroupSearch.search(Name):
            GroupPosition = Name.find('Group')
            GroupID = int(Name[GroupPosition+5:GroupPosition+6])
            GroupCharacter = self.DecodeCompType(CompType,GroupID)
            NewBranchName += str(GroupCharacter) + " specific length"
        elif RatioSearch.search(Name) and not BranchSearch.search(Name):
            if str(Output_Format) == "Tabular":
                NewBranchName += str(self.DecodeCompType(CompType,1)) + "_to_ " + str(self.DecodeCompType(CompType,2)) + "_ratio"
            else:
                NewBranchName += str(self.DecodeCompType(CompType,1)) + " to " + str(self.DecodeCompType(CompType,2)) + " ratio"
        elif AlphaSearch.search(Name) and not BranchSearch.search(Name):
            NewBranchName += "Alpha"
        elif TreeLengthSearch.search(Name):
            if str(AlignmentTogether) == "0":
                UnderscorePosition = Name.find("_")
                GroupID = int(Name[UnderscorePosition+1:UnderscorePosition+2])
                GroupCharacter = self.DecodeCompType(CompType,GroupID)
                NewBranchName += str(GroupCharacter) + " specific total length"
            else:
                NewBranchName += "Total Tree length"
        elif GroupBranchSearch.search(Name) and not SESearch.search(Name):
            UnderscorePosition = Name.find("_")
            GroupID = int(Name[UnderscorePosition+1:UnderscorePosition+2])
            GroupCharacter = self.DecodeCompType(CompType,GroupID)
            Name = Name[:UnderscorePosition]
            BranchParts = BranchSearch.split(Name)
            NewBranchName = str(BranchParts[0]) + Separator + "to" + Separator + str(BranchParts[1]) + Separator + "(" + str(GroupCharacter) + Separator + "specific)"

        elif BranchSearch.search(Name) and not SESearch.search(Name) and not AlphaSearch.search(Name):
            BranchParts = BranchSearch.split(Name)
            NewBranchName = str(BranchParts[0]) + Separator + "to" + Separator + str(BranchParts[1])

        elif SESearch.search(Name) and str(AlignmentTogether) == "1" and not AlphaSearch.search(Name):
            UnderscorePosition = Name.find("_")
            Name = Name[:UnderscorePosition]
            BranchParts = BranchSearch.split(Name)
            NewBranchName = str(BranchParts[0]) + Separator + "to" + Separator + str(BranchParts[1]) + Separator + "significant" + Separator + "error" + Separator + "value"

        elif SESearch.search(Name) and str(AlignmentTogether) == "0":
            #return Name
            UnderscorePosition = Name.find("_")
            GroupID = int(Name[UnderscorePosition+1:UnderscorePosition+2])
            GroupCharacter = self.DecodeCompType(CompType,GroupID)
            Name = Name[:UnderscorePosition]
            BranchParts = BranchSearch.split(Name)
            NewBranchName = str(BranchParts[0]) + Separator + "to" + Separator + str(BranchParts[1]) + Separator + "(" + str(GroupCharacter) + ")" + Separator + "significant" + Separator + "error" + Separator + "value"
        elif RatioSearch.search(Name):
            UnderscorePosition = Name.find("_")
            Name = Name[:UnderscorePosition]
            BranchParts = BranchSearch.split(Name)
            if str(Output_Format) == "Tabular":
                NewBranchName = str(BranchParts[0]) + "_to_" + str(BranchParts[1]) + "_ratio"
            else:
                NewBranchName = str(BranchParts[0]) + " to " + str(BranchParts[1]) + " ratio"
        elif AlphaSearch.search(Name):
            UnderscorePosition = Name.find("_")
            Name = Name[:UnderscorePosition]
            BranchParts = BranchSearch.split(Name)
            if str(Output_Format) == "Tabular":
                NewBranchName = str(BranchParts[0]) + "_to_" + str(BranchParts[1]) + "_Alpha"
            else:
                NewBranchName = str(BranchParts[0]) + " to " + str(BranchParts[1]) + " Alpha"
        else: 
            NewBranchName = Name
        return NewBranchName

    def DecodeCompType(self,CompType,GroupID):
        "This will return the character that corresponds to the group"
        CompType = str(CompType)
        GroupID = int(GroupID)
        GroupChar = ""

        if CompType == "1":
            if GroupID == 1: GroupChar = "Y"
            elif GroupID == 2: GroupChar = "X"
        elif CompType == "2":
            if GroupID == 1: GroupChar = "Y"
            elif GroupID == 2: GroupChar = "A"
        elif CompType == "3":
            if GroupID == 1: GroupChar = "X"
            elif GroupID == 2: GroupChar = "A"
        elif CompType == "4":
            if GroupID == 1: GroupChar = "Z"
            elif GroupID == 2: GroupChar = "W"
        elif CompType == "5":
            if GroupID == 1: GroupChar = "Z"
            elif GroupID == 2: GroupChar = "A"
        elif CompType == "6":
            if GroupID == 1: GroupChar = "W"
            elif GroupID == 2: GroupChar = "A"
        else:
            GroupChar = ""
        return GroupChar

    def WriteHeader(self,Iterations,CompType,DoInAlignBootStrap,AlignmentTogether,DoDoubleBoot,Sequences1,Sequences2,SubstModel,DoExtraBaseML,TransRatio,SeqLength1,SeqLength2,RunMode):
        DoIntAlpha = int(self.DoIntAlpha)
        DoExtAlpha = int(self.DoExtAlpha)
        DoBranchAlpha = int(self.DoBranchAlpha)
        TopLevelString = ""
        AlignmentString = ""
        ReturnString = ""
        ModelName = ""
        Group1 = ""
        Group2 = ""
        Prefix = ""

        if str(RunMode) == "Alpha":
            Prefix = "AlphaSubst"
        else:
            Prefix = "Baseml Wrapper"

        if int(DoDoubleBoot) == 1:
            TopLevelString = Prefix + " Double Boostrap Analysis"
        else:
            if int(DoInAlignBootStrap) == 1:
                TopLevelString = Prefix + " Boostrap Analysis"
            else:
                TopLevelString = Prefix + " Nucleotide Substitution Analysis"
                Iterations = "0"
        
        CompType = int(CompType)
        if CompType == 1:
            TopLevelString += " of Y and X chromosome specific alignments."
            Group1 = "Y"
            Group2 = "X"
        elif CompType == 2:
            TopLevelString += " of Y chromosome and autosomal specific alignments."
            Group1 = "Y"
            Group2 = "A"
        elif CompType == 3:
            TopLevelString += " of X chromosome and autosomal specific alignments."
            Group1 = "X"
            Group2 = "A"
        elif CompType == 4:
            TopLevelString += " of Z and W chromosome specific alignments."
            Group1 = "Z"
            Group2 = "W"
        elif CompType == 5:
            TopLevelString += " of Z chromosome and autosomal specific alignments."
            Group1 = "Z"
            Group2 = "A"
        elif CompType == 6:
            TopLevelString += " of W chromosome and autosomal specific alignments."
            Group1 = "W"
            Group2 = "A"

        SubstModel = int(SubstModel)
        if SubstModel == 0:
            ModelName = "Jukes Cantor 69"
        elif SubstModel == 1:
            ModelName = "Kimura 80"
        elif SubstModel == 2:
            ModelName = "Felsenstein 81"
        elif SubstModel == 3:
            ModelName = "Felsenstein 84"
        elif SubstModel == 4:
            ModelName = "Hasegawa, Yano, Kishino 85"
        elif SubstModel == 5:
            ModelName = "Tamura 92"
        elif SubstModel == 6:
            ModelName = "Tamura Nei 93"
        elif SubstModel == 7:
            ModelName = "REV"
        elif SubstModel == 8:
            ModelName = "UNREST"
        elif SubstModel == 9:
            ModelName = "REVu"
        elif SubstModel == 10:
            ModelName = "UNRESTu"

        if DoIntAlpha == 1: StringIntAlpha = "Yes"
        else: StringIntAlpha = "No"
        if DoExtAlpha == 1: StringExtAlpha = "Yes"
        else: StringExtAlpha = "No"
        if DoBranchAlpha == 1: StringBranchAlpha = "Yes"
        else: StringBranchAlpha = "No"

        #HTML Header formation
        ReturnString = "<HTML><BODY>\n<TABLE><TR><TD COLSPAN=4><B>Nucleotide Substitution Analysis Results</B></TD></TR>\n"
        ReturnString += "<TR><TD COLSPAN=4><HR></TD></TR>\n"
        ReturnString += "<TR><TD COLSPAN=4><B>" + TopLevelString + "</B></TD></TR>\n"
        ReturnString += "<TR><TD>Substitution Model</TD><TD><B>" + ModelName + "</B></TD><TD COLSPAN=2>&nbsp</TD></TR>\n"

        if RunMode == "Alpha":
            ReturnString += "<TR><TD>Internal Alpha Calculated</TD><TD><B>" + StringIntAlpha + "</B></TD><TD COLSPAN=2>&nbsp</TD></TR>\n"
            ReturnString += "<TR><TD>External Alpha Calculated</TD><TD><B>" + StringExtAlpha + "</B></TD><TD COLSPAN=2>&nbsp</TD></TR>\n"
            ReturnString += "<TR><TD>Per Branch Alpha Calculated</TD><TD><B>" + StringBranchAlpha + "</B></TD><TD COLSPAN=2>&nbsp</TD></TR>\n"

        if int(AlignmentTogether) == 1:
            ReturnString += "<TR><TD>Sequence Length</TD><TD><B>" + str(SeqLength1) + "</B></TD><TD colspan>&nbsp;</TD></TR>"
        else:
            ReturnString += "<TR><TD>" + Group1 + " Total Sequence Length</TD><TD><B>" + str(SeqLength1) + "</B></TD><TD COLSPAN=2>&nbsp</TD></TR>\n"
            ReturnString += "<TR><TD>" + Group2 + " Total Sequence Length</TD><TD><B>" + str(SeqLength2) + "</B></TD><TD COLSPAN=2>&nbsp</TD></TR>\n"
        
        ReturnString += "<TR><TD>Replicas Created</TD><TD><B>" + str(Iterations) + "</B></TD><TD COLSPAN=2>&nbsp</TD></TR>\n"

        if int(DoExtraBaseML) == 1 and TransRatio != "":
            ReturnString += "<TR><TD>Transition / Transversion ratio</TD><TD><B>" + str(TransRatio) + "</B></TD><TD COLSPAN=2>&nbsp</TD></TR>\n"

        ReturnString += "</TABLE>\n\n"

        return ReturnString

    def AverageColumn(self,ScoreList):
        "This will average the results of a list"
        Average = 0;
        for Number in ScoreList:
            if str(Number) != "0*" and str(Number) != "0**":
                Average += float(Number)
        Average = Average / len(ScoreList)
        return Average

    def SigFigRound(self,Number,SigDigits):
        "Doc Holder"
        Number = str(Number)
        if Number == "" or Number == "Infinity":
            return Number

        RemoveLeadingZeros = re.compile('^[0]+')
        PeriodRemove = re.compile('\.')
        Number = RemoveLeadingZeros.sub("",Number)
        ReturnNumber = ""
        PeriodExists = "0"
        PeriodLocation = Number.find('.')
        if PeriodLocation >= 0:
            Number = PeriodRemove.sub("",Number)
            PeriodExists = "1"
        ReturnNumber += Number[0:SigDigits-1]
        CurrentChar = Number[SigDigits-1:SigDigits]
        if CurrentChar == ".":
            CurrentChar = Number[SigDigits:SigDigits+1]
            NextChar = Number[SigDigits+1:SigDigits+2]
        else:
            NextChar = Number[SigDigits:SigDigits+1]
        ReturnNumber += str(self.RoundDigit(CurrentChar,NextChar))

        if PeriodExists == "1" and PeriodLocation < SigDigits:
            if PeriodLocation == 0: ReturnNumber = "0." + ReturnNumber
            else: ReturnNumber = ReturnNumber[0:PeriodLocation] + "." + ReturnNumber[PeriodLocation:]
        else: #Pad zeroes to the number
            if PeriodExists == "1":
                for Index in range(len(ReturnNumber),PeriodLocation): ReturnNumber += "0"
            else: 
                for Index in range(len(ReturnNumber),len(Number)): ReturnNumber += "0"
    
        #Now put the number in scientific notation
        #ReturnNumber = self.ScientificNotation(ReturnNumber,SigDigits)
        return ReturnNumber
    
    def ScientificNotation(self,Number,SigDigits):
        "This function will place a number in scientific notation - provided the range is greater than an order of magnitude"
        RemoveLeadingZeros = re.compile('^[0]+')
        PeriodRemove = re.compile('\.')
        TestNumber = RemoveLeadingZeros.sub("",Number)
        SavedNumber = Number

        PeriodExists = "0"
        PeriodLocation = TestNumber.find('.')
        if PeriodLocation >= 0:
            TestNumber = PeriodRemove.sub("",TestNumber)
            Power = PeriodLocation - 1
            PeriodExists = "1"
        else:
            Power = len(Number) - 1
        if Power > 1 or Power < -1: 
            return TestNumber[0:1] + "." + TestNumber[1:SigDigits] + "e" + str(Power)
        else: 
            return SavedNumber[0:SigDigits]
    
    def RoundDigit(self,CurrChar, CharAfter):
        "This function accepts a numeric character and rounds it up or down based on the second character passed"
        if str(CharAfter) != "" and str(CharAfter) != "*" and str(CharAfter) != "-":
            if int(CharAfter) >= 0 and int(CharAfter) <= 4:
                return CurrChar
            elif int(CharAfter) >= 5 and int(CharAfter) <= 9:
                return int(CurrChar) + 1
            else:
                return CurrChar
        else:
            return CurrChar
            
