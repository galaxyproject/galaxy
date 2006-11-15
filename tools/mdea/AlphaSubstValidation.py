import re
import string

class AlphaSubstValidation:
    "This is a class that peforms data validation on the passed data"
    def __init__(self):
        "This is a general data validation class for the MDEA submodules"
        self.SequenceCount = 0
        self.Group1AlignmentCount = 0
        self.Group1Alignments = 0
        self.Group1AlignLength = 0
        self.TotalSequenceLength1 = 0
        self.Group2AlignmentCount = 0
        self.Group2Alignments = 0
        self.Group2AlignLength = 0
        self.TotalSequenceLength2 = 0

        self.SequenceArray = []
        self.SequenceLengths = []
        self.TotalSequenceLength = 0
        self.SequenceLength = 0
        self.Group1Headers = []
        self.Group2Headers = []
        self.TempAlignment = []
        self.TempAlignmentLength = 0
        self.TossAlignment = 0
        self.TossCount = 0

    def ValidateAlphaSubstData(self,AnalysisType,CompType,DoSingleBoot,SingleBootIterations,DoDoubleBoot,DoubleBootIterations,Sequences1,Sequences2,TreeDefinition,BaseMLLocation):
        "The meta function for validation of alpha subst data"
        ErrorString = ""
        if int(AnalysisType) == 0:
            AlignmentTogether = 1
        elif int(AnalysisType) == 1:
            AlignmentTogether = 0
        elif int(AnalysisType) == 2:
            AlignmentTogether = 0
    
        #Remove Spaces from the tree definition
        SpaceRemover = re.compile(" ")
        TreeDefinition = SpaceRemover.sub("",TreeDefinition)

        #Validate the tree
        TreeForeignChar = re.compile('[AWXYZ_\(\),{0-9}+]')
        BareTree = TreeForeignChar.sub("",TreeDefinition)
        if str(BareTree) != "":  #No use continuing past this point
            return "Malformed tree definition - foreign characters detected."

        #Alignment Validation
        if DoDoubleBoot == 0:      
            ErrorString = self.CleanData(Sequences1)
            if ErrorString != "": return ErrorString
            self.Group1Alignments = self.AlignmentArray
            self.Group1AlignmentCount = len(self.AlignmentArray)
            self.Group1AlignLength = self.SequenceLength
            self.TotalSequenceLength1 = self.SequenceLength
            self.TotalSequenceLength2 = 0
            self.SequenceLength = 0

            ErrorString = self.CheckSequenceCount(AlignmentTogether,Sequences1,Sequences2,TreeDefinition)  #Alignment Tree agreement check
            if ErrorString != "": return ErrorString

            if int(AlignmentTogether) == 0:    
                ErrorString = self.CleanData(Sequences2)
                if ErrorString != "": return ErrorString
                self.Group2Alignments = self.AlignmentArray
                self.Group2AlignmentCount = len(self.AlignmentArray)
                self.Group2AlignLength = self.SequenceLength
                self.TotalSequenceLength2 = self.SequenceLength

        else:
            #Double bootstrap validation
            ErrorString = self.DBS_AlignmentCheck(Sequences1,Sequences2,TreeDefinition,1)

        #Iteration Validation - > 10 iterations if there is bootstrapping
        if int(DoDoubleBoot) == 0:
            if int(SingleBootIterations) < 10:
                ErrorString += "For analysis with bootstrap there must be at least 10 replicas."
        elif int(DoSingleBoot) == 1:
            if int(DoubleBootIterations) < 10:
                ErrorString += "For analysis with bootstrap there must be at least 10 replicas."

        #General Tree Validation
        ErrorString += self.ValidateTree(TreeDefinition,self.SequenceCount)
        if ErrorString != "": return ErrorString

        #Check that the comparison type and the tree agree - are the branches tied together?
        if int(AlignmentTogether) == 1:
            ErrorString += self.CheckTreeVsCompType(TreeDefinition,CompType,self.SequenceCount)  #Must have a tagged tree
            if ErrorString != "": return ErrorString

        return ErrorString

    def ValidateBaseMLData(self,DoAlignBootStrap,Iterations,TreeDef,Sequence1,DoDoubleBoot,DoubleBootIterations):
        "This function will validate the BaseML section"
        ErrorString = ""
        if str(TreeDef) == "":
            return "Invalid tree format - foreign characters detected."

        #Remove Spaces from the tree definition
        SpaceRemover = re.compile(" ")
        TreeDef = SpaceRemover.sub("",TreeDef)

        #Validate the tree
        TreeForeignChar = re.compile('[AWXYZ_\(\),{0-9}+]')
        BareTree = TreeForeignChar.sub("",TreeDef)
        if str(BareTree) != "":  #No use continuing past this point
            return "Invalid tree format - foreign characters detected."

        #Alignment Validation
        if int(DoDoubleBoot) == 0:
            #Clean the sequences and move to an array - remove gaps and corresponsing sites
            ErrorString = self.CleanData(Sequence1)
            if ErrorString != "": return ErrorString
            self.Group1Alignments = self.AlignmentArray
            self.Group1AlignmentCount = len(self.AlignmentArray)
            self.Group1AlignLength = self.SequenceLength
            self.TotalSequenceLength1 = self.SequenceLength

            #Non double bootstrap validation
            ErrorString = self.CheckSequenceCount(1,Sequence1,"",TreeDef)  #Alignment Tree agreement check
            if ErrorString != "": return ErrorString

        else:
            #Double bootstrap validation
            ErrorString = self.DBS_AlignmentCheck(Sequence1,"",TreeDef,0)
            if ErrorString != "": return ErrorString            
            self.SequenceLength1 = self.TotalSequenceLength

            if int(self.SequenceLength1) == 0:
                return "All of the alignments in the file either do not have an ungapped length of 75 base pairs or do not contain at least one of the 4 bases (A,C,T,G).  Instead, try a concatanated FASTA file, and perform single loci analysis."

        #Tree Validation
        ErrorString = self.ValidateTree(TreeDef,self.SequenceCount)
        if ErrorString != "": return ErrorString
        #self.Group1Headers = self.GrabHeaders(Sequence1)

        #Iteration Validation - > 10 iterations if there is bootstrapping
        if int(Iterations) < 10 and int(DoAlignBootStrap) == 1:
            return "To generate confidence intervals there must be at least 10 replicas."
        return ""

    def CleanData(self,SequenceFile):
        "This function will remove gaps from an alignment"
        ReturnString = ""
        ReturnArray = []
        TempSeqArray = []
        FoundGap = 0
        FinishedWithSequence = 0  #Make sure this isn't a multi sequence file
        WroteSequence = 0

        seqfile = open(SequenceFile)
        for FileLine in seqfile.readlines():
            FileLine = FileLine.strip()
            if FileLine != "": 
                if FinishedWithSequence == 1: return "The file selected appears to be multi-fasta format.  Use multiple loci analysis instead."

                if FileLine[0] != ">" and FileLine[0] != "#":  #FASTA Headers
                    TempSeqArray.append(FileLine)
                    WroteSequence = 1

            elif WroteSequence == 1:
                FinishedWithSequence = 1

        for SeqIndex in range(0,len(TempSeqArray)):
            ReturnArray.append('')
        print len(TempSeqArray)
        for PositionIndex in range(0,len(TempSeqArray[0])):
            FoundGap = 0
            for SeqIndex in range(0,len(TempSeqArray)):
                # print PositionIndex
                try:
                    if str(TempSeqArray[SeqIndex][PositionIndex]) == "-": FoundGap = 1
                except:
                    pass
            if FoundGap == 0:
                for SequenceCounter in range(0,len(TempSeqArray)):
                    ReturnArray[SequenceCounter] += str(TempSeqArray[SequenceCounter][PositionIndex])

        #Validation for the same sequence length in the alignment
        TestSeqLength = len(ReturnArray[0])
        for SeqIndex in range(0,len(ReturnArray)):
            if int(TestSeqLength) != int(len(ReturnArray[SeqIndex])):
               return "All sequences in the alignment must be the same length.  Process terminated."

        self.AlignmentArray = ReturnArray
        self.SequenceLength = len(ReturnArray[0])

        return ""

    def GrabHeaders(self,Sequences):
        "This function gets the headers of sequences"
        FoundHeaders = 0
        HeaderArray = []
        SequenceIndex = 0

        seqfile = open(Sequences)
        for FileLine in seqfile.readlines():
            FileLine = FileLine.strip()
            if FileLine == "\n" or FileLine == "" and FoundHeaders == 1:  #Finished - return
                return HeaderArray
            elif FileLine[0] == ">" or FileLine[0] == "#":  #FASTA header locater
                #Check format - must be quasi-compatible with all FASTA headers
                FoundHeaders = 1
                SequenceIndex += 1
                PeriodLocation = FileLine.find('.')
                HyphenLocation = FileLine.find('-')
                if PeriodLocation > 1:
                    HeaderArray.append(str(FileLine[1:PeriodLocation]))
                elif HyphenLocation > 1:
                    HeaderArray.append(str(FileLine[1:HyphenLocation]))
                else:
                    HeaderArray.append(FileLine[1:])
        return HeaderArray

    def ValidateTree(self,Tree,SequenceCount):
        "This function will make sure the tree is formed correctly - check the count of left and right parens, comma count, all numbers represented"
        ErrorString = ""

        TreeCleaner = re.compile('[AWXYZ_]')  #Remove the male-mutation specific parts
        TreeArrayPrep = re.compile("[\(\)]")
        TreeCommaSplit = re.compile(",")
        Tree = TreeCleaner.sub("",Tree)
        #Parenthesis count check
        LeftParen = Tree.count("(")
        RightParen = Tree.count(")")
        if LeftParen != RightParen:
            return "Invalid tree format - there needs to be an equal number of '(' as ')'."

        #Are there the correct number of commas?  SequenceCount - 1 Commas
        CommaCount = Tree.count(",")
        if CommaCount != int(SequenceCount) - 1:
            return "Invalid tree format - there are an inadequate number of commas present."

        #Are all numbers present in the tree?
        Tree = TreeArrayPrep.sub("",Tree)
        TreeNodeArray = TreeCommaSplit.split(Tree)
        NotFoundNumber = 0
        for Number in range(1,int(SequenceCount) + 1):
            if not TreeNodeArray.__contains__(str(Number)):
                NotFoundNumber = 1
                return "Invalid tree format - all numbers from 1 to " + str(SequenceCount) + " must be present in the tree definition."

        #Does the tree have extra numbers?
        for TreeNodeIndex in range(0,len(TreeNodeArray)):
            for Number in range(1,int(SequenceCount) + 1):
                if str(Number) == str(TreeNodeArray[TreeNodeIndex]):
                    TreeNodeArray[TreeNodeIndex] = ""
        for TreeElements in TreeNodeArray:
            if TreeElements != "":
                return "Invalid tree format - sequence count does not match the tree definition."

        return ""

    def CheckTreeVsCompType(self,TreeDef,CompType,TotalSeqCount):
        "The function will determine if the tree definition matches the comparison type the user selected"
        ErrorString = ""
        Group1Char = ""
        Group2Char = ""
        Group1Count = 0
        Group2Count = 0
        TreeStripper = re.compile('[,\(\)_0-9\s]')
        Group1Char = self.ReturnGroupTag(CompType,1)
        Group2Char = self.ReturnGroupTag(CompType,2)
        
        #For a proper tree there should be equal amounts of each chromosome                
        TreeOwners = TreeStripper.sub("",TreeDef)
        for TreeOwnerChar in TreeOwners:
            if str(TreeOwnerChar) == str(Group1Char):
                Group1Count += 1
            if str(TreeOwnerChar) == str(Group2Char):
                Group2Count += 1

        if int(Group1Count) != int(Group2Count):
            ErrorString = "Malformed tree definition - there need to be an equal number of branches assigned to '" + str(Group1Char) + "' as there are to '" + str(Group2Char) + "'."
            return ErrorString

        TempGroupCount = int(Group1Count) + int(Group2Count)
        if TempGroupCount != int(TotalSeqCount):
            ErrorString = "Malformed tree definition - every branch needs to be labelled with a '" + str(Group1Char) + "' or a '" + str(Group2Char) + "'."

        return ErrorString

    def ReturnGroupTag(self,CompType,GroupID):
        "Returns the correct branch tag for a group"
        GroupTag = ""
        if str(CompType) == "1":
            if GroupID == 1: return "Y"
            if GroupID == 2: return "X"
        elif str(CompType) == "2":
            if GroupID == 1: return "Y"
            if GroupID == 2: return "A"
        elif str(CompType) == "3":
            if GroupID == 1: return "X"
            if GroupID == 2: return "A"
        elif str(CompType) == "4":
            if GroupID == 1: return "Z"
            if GroupID == 2: return "W"
        elif str(CompType) == "5":
            if GroupID == 1: return "Z"
            if GroupID == 2: return "A"
        elif str(CompType) == "6":
            if GroupID == 1: return "W"
            if GroupID == 2: return "A"
        return ""

    def DBS_AlignmentCheck(self,Sequences1,Sequences2,TreeDef,TwoSequences):
        "Check the alignments to make sure they agree with the tree"
        #Get the tree definitions sequence count (the highest number in the tree)
        ErrorString = ""
        CommaSplitter = re.compile(',')
        NewLineSplitter = re.compile('\n')
        RemoveAssign = re.compile('[_AWXYZ\(\)]') 
        TreeArray = CommaSplitter.split(RemoveAssign.sub("",TreeDef))
        TreeSequenceCount = 0
        for Numbers in TreeArray:
            if int(TreeSequenceCount) < int(Numbers): TreeSequenceCount = Numbers
        self.SequenceCount = TreeSequenceCount

        #Check the first group of alignements
        ErrorString = self.DoubleBootAlignmentCheck(Sequences1,TreeSequenceCount)
        if ErrorString != "": return ErrorString
        self.Group1AlignmentCount = len(self.SequenceLengths)
        self.Group1Alignments = self.SequenceArray
        self.Group1AlignLength = self.SequenceLengths
        self.TotalSequenceLength1 = self.TotalSequenceLength

        if TwoSequences == 1:
            #Check the second group of alignements
            ErrorString = self.DoubleBootAlignmentCheck(Sequences2,TreeSequenceCount)
            if ErrorString != "": return ErrorString
            self.Group2AlignmentCount = len(self.SequenceLengths)
            self.Group2Alignments = self.SequenceArray
            self.Group2AlignLength = self.SequenceLengths
            self.TotalSequenceLength2 = self.TotalSequenceLength

        return ErrorString

    def ValidateAlignment(self,Alignment,MinimumAlignmentLength,SequenceCount):
        "This function will validate a passed alignment for min sequence length, base content, and save an ungapped alignment"
        self.TempAlignment = []
        self.TossAlignment = 0
        self.TempAlignmentLength = 0
        SequenceCount = int(SequenceCount)

        A_Search = re.compile("[Aa]")
        C_Search = re.compile("[Cc]")
        T_Search = re.compile("[Tt]")
        G_Search = re.compile("[Gg]")
        ErrorString = ""

        #Sequence count agreeement?
        if len(Alignment) != SequenceCount:
            return "Your alignments must contain the same number of species as your tree."

        #Nucleotide base content - are all 4 bases present?
        GoodSequence = 1
        for Sequences in Alignment:
            if not A_Search.search(Sequences): GoodSequence = 0
            if not C_Search.search(Sequences): GoodSequence = 0
            if not T_Search.search(Sequences): GoodSequence = 0
            if not G_Search.search(Sequences): GoodSequence = 0
        if GoodSequence == 0:
            self.TossAlignment = 1
            self.TossCount += 1
            return ""

        #Remove gaps - save to new sequence
        FinalAlignment = []
        for AlignmentIndex in range(0,SequenceCount): 
            FinalAlignment.append([])
            self.TempAlignment.append([])

        for BaseIndex in range(0,len(Alignment[0])):
            GoodBase = 1
            for AlignmentIndex in range(0,SequenceCount):
                if Alignment[AlignmentIndex][BaseIndex] == "-": GoodBase = 0
            if GoodBase == 1:
                for AlignmentIndex in range(0,SequenceCount):
                    FinalAlignment[AlignmentIndex] += str(Alignment[AlignmentIndex][BaseIndex])

        #Min Sequence Length validation
        for AlignmentIndex in range(0,SequenceCount):
            if len(FinalAlignment[AlignmentIndex]) < MinimumAlignmentLength:
                self.TossAlignment = 1
                self.TossCount += 1
                return ""
        self.TempAlignmentLength = len(FinalAlignment[0])

        #Write new sequences
        SequenceString = ""
        for AlignmentIndex in range(0,SequenceCount):
            SequenceString = ""
            for Bases in FinalAlignment[AlignmentIndex]:
                SequenceString += Bases
            self.TempAlignment[AlignmentIndex] = SequenceString

        return ""
        
    def DoubleBootAlignmentCheck(self,Sequences,TreeSequenceCount):
        "This function checks the double boot sequences for proper format and returns useful items, also there is validation for sequence length consistency and validation for alignments with gaps at every position"
        FoundAlignment = 0
        SequenceCount = 0
        MinimumAlignmentLength = 75
        IndividualAlignment = []
        AlignmentLength = 0
        seqfile = open(Sequences)

        for FileLine in seqfile.readlines():
            FileLine = str(FileLine.strip())
            if FileLine == "":
                if FoundAlignment == 0: continue
                else: 
                    ErrorString = self.ValidateAlignment(IndividualAlignment,MinimumAlignmentLength,TreeSequenceCount)
                    if ErrorString != "": return ErrorString
                    if self.TossAlignment == 0:
                        self.SequenceArray.append(self.TempAlignment)
                        self.SequenceLengths.append(int(self.TempAlignmentLength))
                        self.TotalSequenceLength += int(self.TempAlignmentLength)
                    IndividualAlignment = []
                    FoundAlignment = 0

            elif FileLine[0] != "#" and FileLine[0] != ">": #Found a sequence
                if FoundAlignment == 0: FoundAlignment = 1
                IndividualAlignment.append(FileLine)                    
            
        if FoundAlignment == 1:
            ErrorString = self.ValidateAlignment(IndividualAlignment,MinimumAlignmentLength,TreeSequenceCount)
            if ErrorString != "": return ErrorString
            if self.TossAlignment == 0:
                self.SequenceArray.append(self.TempAlignment)
                self.SequenceLengths.append(int(self.TempAlignmentLength))
                self.TotalSequenceLength += int(self.TempAlignmentLength)

        seqfile.close()

        return ""

    def CheckSequenceCount(self,AlignmentTogether,Sequence1,Sequence2,TreeDef):
        "This module checks for the sequence count in the tree and the sequence(s) ensuring agreement between the two"
        #Get the tree definitions sequence count (the highest number in the tree)
        CommaSplitter = re.compile(',')
        NewLineSplitter = re.compile('\n')
        RemoveAssign = re.compile('[_AWXYZ\(\)]') 
        TreeArray = CommaSplitter.split(RemoveAssign.sub("",TreeDef))
        TreeSequenceCount = 0
        for Numbers in TreeArray:
            if int(TreeSequenceCount) < int(Numbers):
                TreeSequenceCount = Numbers
        self.SequenceCount = Numbers

        #Check the sequence counts from the sequences
        FileSeqCount1 = self.CheckSeqCount(Sequence1)
        if str(AlignmentTogether) == "0":
            FileSeqCount2 = self.CheckSeqCount(Sequence2)
        #If there is no agreement return the error string
        ErrorString = ""
        if AlignmentTogether == "0":
            if str(FileSeqCount1) != str(TreeSequenceCount) or str(FileSeqCount2) != str(TreeSequenceCount) or str(FileSeqCount1) != str(FileSeqCount2):
                ErrorString = "The tree definition doesn't match the sequences provided."
        else:
            if str(FileSeqCount1) != str(TreeSequenceCount):
                ErrorString = "The tree definition doesn't match the sequence provided."
        self.SequenceCount = TreeSequenceCount
        return ErrorString
        
    def CheckSeqCount(self,Sequence):
        Trimmer = re.compile('\s')
        SequencesFound = 0
        seqfile = open(Sequence)
        for FileLine in seqfile.readlines():
            FileLine = Trimmer.sub("",FileLine)
            if FileLine != "":
                if (FileLine[0] == ">" or FileLine[0] == "#") and FileLine != "":
                    SequencesFound += 1
        seqfile.close()
        return SequencesFound

    def GetSeqLength(self,Sequence):
        "This module will verify that all sequences are the same length, and return the length - also validate that there are no spaces in the alignment"
        SequenceLength = 0
        SequenceTestLengthArray = []
        ErrorString = ""
        FoundFirstHeader = 0
        FoundBlankLine = 0

        seqfile = open(Sequence)
        for FileLine in seqfile.readlines():
            FileLine = FileLine.strip()
            if FileLine != "": 
                if FoundBlankLine == 1:
                    return "Valid alignments cannot have blank lines between the sequences."

                if FileLine[0] != ">" and FileLine[0] != "#":  #FASTA Headers
                    SequenceLength += len(FileLine)
                elif FileLine[0] == ">" or FileLine[0] == "#":
                    FoundFirstHeader = 1
                    if int(SequenceLength) != 0:
                        SequenceTestLengthArray.append(SequenceLength)
                    SequenceLength = 0
            elif FoundFirstHeader == 1:
                FoundBlankLine = 1

        if int(SequenceLength) != 0:
            SequenceTestLengthArray.append(SequenceLength)

        seqfile.close()

        TestSeqLength = SequenceTestLengthArray[0]
        for SeqLength in SequenceTestLengthArray:
            if int(TestSeqLength) != int(SeqLength):    
               return "All sequences in the alignment must be the same length.  Process terminated."

        self.SequenceLength = TestSeqLength
        return ErrorString
