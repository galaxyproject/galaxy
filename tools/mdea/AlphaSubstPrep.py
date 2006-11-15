import re
import string

class AlphaSubstPrep:
    "This is an encapsulation of BaseML functionality"
    def __init__(self):
        "Doc Holder"

    def PrepBaseML(self,AnalysisType,TreeData,SequenceCount,CompType,UserRandomKey,BaseMLLocation,SubstModel,GetSE,DoIntAlpha,DoExtAlpha,GalaxyLocation,FixAlpha,AlphaValue,FixKappa,KappaValue,FixRho,RhoValue):
        "This function will initialize baseml - writes baseml.ctl, and tmp.tree"
        self.Group1Branches = []
        self.Group2Branches = []
        self.Group1IntBranches = []
        self.Group2IntBranches = []
        self.Group1ExtBranches = []
        self.Group2ExtBranches = []
        self.InternalBranches = []
        self.ExternalBranches = []
        if int(AnalysisType) == 0: AlignmentTogether = 1
        else: AlignmentTogether = 0

        #Remove Spaces from the tree definition
        SpaceRemover = re.compile(" ")
        TreeData = SpaceRemover.sub("",TreeData)

        self.WriteTreeDef(AlignmentTogether,TreeData,SequenceCount,CompType,UserRandomKey,DoIntAlpha,DoExtAlpha)
        self.WriteBaseMLctl(BaseMLLocation,UserRandomKey,SubstModel,GetSE,GalaxyLocation,FixAlpha,AlphaValue,FixKappa,KappaValue,FixRho,RhoValue)

    def WriteBaseMLctl(self,BaseMLLocation,UserRandomKey,SubstModel,GetSE,GalaxyLocation,FixAlpha,AlphaValue,FixKappa,KappaValue,FixRho,RhoValue):
        "This function will write baseml.ctl - the control file for baseml, which is constant for each submission"
        OutFile = GalaxyLocation + "tools/mdea/BaseMLWork/" + str(UserRandomKey) + "-tmp.out"
        TreeFile = GalaxyLocation + "tools/mdea/BaseMLWork/" + str(UserRandomKey) + "-tmp.tree"
        SeqFile = GalaxyLocation + "tools/mdea/BaseMLWork/" + str(UserRandomKey) + "-tmp.seq"
        BaseMLControlFile = "\n     outfile = " + OutFile + "\n     treefile = " + TreeFile + "\n     seqfile = " + SeqFile + "\n\n"
        BaseMLControlFile += "     noisy = 0\n     verbose = 0\n    runmode = 0\n     model = " + str(SubstModel) + "\n"
        BaseMLControlFile += "     Mgene = 0\n     fix_kappa = " + str(FixKappa) + "\n     kappa = " + str(KappaValue) + "\n"
        BaseMLControlFile += "     fix_alpha = " + str(FixAlpha) + "\n     alpha = " + str(AlphaValue) + "\n     Malpha = 0\n"
        BaseMLControlFile += "     ncatG = 5\n     fix_rho = " + str(FixRho) + "\n     rho = " + str(RhoValue) + "\n     nparK = 0\n     clock = 0\n     nhomo = 0\n"
        BaseMLControlFile += "     getSE = " + str(GetSE) + "\n     RateAncestor = 0\n     Small_Diff = 7e-6\n"
        BaseMLControlFile += "     cleandata = 1\n     method = 0\n"
        self.WriteFile("tools/mdea/BaseMLWork/" + str(UserRandomKey) + "-baseml.ctl",BaseMLControlFile)

    def WriteTreeDef(self,AlignmentTogether,TreeData,SequenceCount,CompType,UserRandomKey,DoIntAlpha,DoExtAlpha):
        "This function will accept a AlphaSubst formatted tree - determine relationships and write the baseml tree to the file system"
        #Determine tree topology - explode the tree
        RemoveAssign = re.compile('[_AWXYZ]') 
        BaseTreeDef = RemoveAssign.sub("",TreeData)

        self.BranchDescriptions = self.ExplodeTree(BaseTreeDef,SequenceCount)

        #Check the sub branches to determine their chromosomal ownership - also internal and external alpha
        self.DetermineBranchOwnership(AlignmentTogether, self.BranchDescriptions,TreeData,CompType,SequenceCount,DoIntAlpha,DoExtAlpha)
        
        #Write tmp.tree
        BaseTreeDef = "   " + str(SequenceCount) + " 1\n\n" + str(BaseTreeDef)
        self.WriteFile("tools/mdea/BaseMLWork/" + str(UserRandomKey) + "-tmp.tree",BaseTreeDef)

    def DetermineBranchOwnership(self,AlignmentTogether,BranchDesc,TreeData,CompType,SequenceCount,DoIntAlpha,DoExtAlpha):
        #First determine which terminal nodes are assigned to which chromosome"
        Group1IDS = []
        Group2IDS = []
        OrderedBranchList = []
        Group1Tag = self.ReturnGroupTag(CompType,"1")
        Group2Tag = self.ReturnGroupTag(CompType,"2")
        CommaSplitter = re.compile(',') 
        TwoPeriodSplitter = re.compile('\.\.')
        UnderScoreSplitter = re.compile('_')
        RemoveParens = re.compile('[\(\)]')

        if str(AlignmentTogether) == "1":
            #Assign initial newick branches
            TreeDefinition = RemoveParens.sub("",TreeData)
            TreeDefinition = CommaSplitter.split(TreeDefinition)
            for NodeAssignment in TreeDefinition:
                if CompType != 0:
                    NodeParts = UnderScoreSplitter.split(NodeAssignment)
                    if NodeParts[1][0:] == Group1Tag:
                        Group1IDS.append(NodeParts[0])
                    elif NodeParts[1][0:] == Group2Tag:
                        Group2IDS.append(NodeParts[0])

        #What is the highest numbered element in the branch descriptions?
        HighestBranch = 0
        for Branch in BranchDesc:
            BranchParts = TwoPeriodSplitter.split(Branch)
            if int(BranchParts[0]) > int(HighestBranch):
                HighestBranch = BranchParts[0]
            if int(BranchParts[1]) > int(HighestBranch):
                HighestBranch = BranchParts[1]

        #Split the branches into elements and sort them lowest to highest
        for CountingIndex in range(1,int(HighestBranch)):
            for BranchIndex in range(0,len(BranchDesc)):
                if str(BranchDesc[BranchIndex]) != "":
                    BranchParts = TwoPeriodSplitter.split(BranchDesc[BranchIndex])
                    if str(BranchParts[0]) == str(CountingIndex) or str(BranchParts[1]) == str(CountingIndex):
                        BranchString = str(BranchParts[0]) + ".." + str(BranchParts[1])
                        if not OrderedBranchList.__contains__(BranchString):
                            OrderedBranchList.append(BranchString)

        #Now search for attached branches (that aren't the origin node)
        OriginNode = int(SequenceCount) + 1
        InternalBranchesPresent1 = 0
        ExternalBranchesPresent1 = 0
        InternalBranchesPresent2 = 0
        ExternalBranchesPresent2 = 0

        for Branch in OrderedBranchList:
            BranchParts = TwoPeriodSplitter.split(Branch)
            BranchString = str(BranchParts[0]) + ".." + str(BranchParts[1])

            if str(AlignmentTogether) == "1":
                for Group1 in Group1IDS:
                    if int(Group1) == int(BranchParts[0]) or int(Group1) == int(BranchParts[1]):
                        if str(OriginNode) != str(BranchParts[0]) and str(OriginNode) != str(BranchParts[1]):
                            if not Group1IDS.__contains__(str(BranchParts[0])):
                                Group1IDS.append(str(BranchParts[0]))
                            if not Group1IDS.__contains__(str(BranchParts[1])):
                                Group1IDS.append(str(BranchParts[1]))
                            if not self.Group1Branches.__contains__(BranchString):
                                self.Group1Branches.append(BranchString)
    
                            if int(DoIntAlpha) == 1:
                                if int(BranchParts[0]) > int(SequenceCount) and int(BranchParts[1]) > int(SequenceCount):
                                    if not self.Group1IntBranches.__contains__(BranchString):
                                        self.Group1IntBranches.append(BranchString)
                                        InternalBranchesPresent1 = 1
                            if int(DoExtAlpha) == 1:
                                if int(BranchParts[0]) <= int(SequenceCount) or int(BranchParts[1]) <= int(SequenceCount):
                                    if not self.Group1ExtBranches.__contains__(BranchString):
                                        self.Group1ExtBranches.append(BranchString)
                                        ExternalBranchesPresent1 = 1
                for Group2 in Group2IDS:
                    BranchString = str(BranchParts[0]) + ".." + str(BranchParts[1])
                    if str(Group2) == str(BranchParts[0]) or str(Group2) == str(BranchParts[1]):
                        if str(OriginNode) != str(BranchParts[0]) and str(OriginNode) != str(BranchParts[1]):
                            if not Group2IDS.__contains__(str(BranchParts[0])):
                                Group2IDS.append(str(BranchParts[0]))
                            if not Group2IDS.__contains__(str(BranchParts[1])):
                                Group2IDS.append(str(BranchParts[1]))
                            if not self.Group2Branches.__contains__(BranchString):
                                self.Group2Branches.append(str(BranchParts[0]) + ".." + str(BranchParts[1]))
                            if int(DoIntAlpha) == 1:
                                if int(BranchParts[0]) > int(SequenceCount) and int(BranchParts[1]) > int(SequenceCount):
                                    if not self.Group2IntBranches.__contains__(BranchString):
                                        self.Group2IntBranches.append(BranchString)
                                        InternalBranchesPresent2 = 1
                            if int(DoExtAlpha) == 1:
                                if int(BranchParts[0]) <= int(SequenceCount) or int(BranchParts[1]) <= int(SequenceCount):
                                    if not self.Group2ExtBranches.__contains__(BranchString):
                                        self.Group2ExtBranches.append(BranchString)
                                        ExternalBranchesPresent2 = 1
            else:  #Seperate alignments
                if int(DoIntAlpha) == 1:
                    if int(BranchParts[0]) > int(SequenceCount) and int(BranchParts[1]) > int(SequenceCount):
                        if not self.InternalBranches.__contains__(BranchString):
                            self.InternalBranches.append(BranchString)
                            InternalBranchesPresent1 = 1
                            InternalBranchesPresent2 = 1
                if int(DoExtAlpha) == 1:
                    if int(BranchParts[0]) <= int(SequenceCount) or int(BranchParts[1]) <= int(SequenceCount):
                        if not self.ExternalBranches.__contains__(BranchString):
                            self.ExternalBranches.append(BranchString)
                            if int(BranchParts[0]) != int(SequenceCount) + 1 and int(BranchParts[1]) != int(SequenceCount) + 1:
                                ExternalBranchesPresent1 = 1
                                ExternalBranchesPresent2 = 1
        #If doing an internal or external alpha - branches must be present
        if int(DoIntAlpha) == 1 and    InternalBranchesPresent1 == 1 and InternalBranchesPresent2 == 1:
            self.DoIntAlpha = 1
        else:
            self.DoIntAlpha = 0
        if int(DoExtAlpha) == 1 and    ExternalBranchesPresent1 == 1 and ExternalBranchesPresent2 == 1:
            self.DoExtAlpha = 1
        else:
            self.DoExtAlpha = 0

    def ReturnGroupTag(self,CompType,GroupID):
        "This module will decode the comparision type and return the letter tags for the group ID"
        if str(CompType) == "1":
            if GroupID == "1":
                return "Y"
            else: 
                return "X"
        elif str(CompType) == "2":
            if GroupID == "1":
                return "Y"
            else: 
                return "A"
        elif str(CompType) == "3":
            if GroupID == "1":
                return "X"
            else: 
                return "A"
        elif str(CompType) == "4":
            if GroupID == "1":
                return "Z"
            else: 
                return "W"
        elif str(CompType) == "5":
            if GroupID == "1":
                return "Z"
            else: 
                return "A"
        elif str(CompType) == "6":
            if GroupID == "1":
                return "W"
            else: 
                return "A"
        return ""


    def ExplodeTree(self,TreeData,SequenceCount):
        "This module will expand the tree definition passed to encompass all branches of the tree"
        #Search the tree backwards for a enclosed group
        NodePairs = []
        NodeIDs = []
        NodeLetters = []
        NodeComponents = []
        BranchDescription = []
        FoundPair = "0"
        Alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        CurrentAlphabetChar = ""
        CommaSplitter = re.compile(',')
        while (1):
            FoundPair = "0"
            for RevIndex in range(len(TreeData)-1,-1,-1):
                if TreeData[RevIndex] == ")":
                    for InnerRevIndex in range(RevIndex-1,-1,-1):
                        if TreeData[InnerRevIndex] == ")":
                            break
                        elif TreeData[InnerRevIndex] == "(":
                            #Located an enclosed group - save it, remove it and replace it with a letter
                            FoundPair = "1"
                            NodePairs.append(TreeData[InnerRevIndex+1:RevIndex])
                            CurrentAlphabetChar = self.PrevAlphabetChar(CurrentAlphabetChar)
                            NodeLetters.append(CurrentAlphabetChar)
                            TreeData = TreeData[:InnerRevIndex] + str(CurrentAlphabetChar) + TreeData[RevIndex+1:]
                            break
                if FoundPair == "1":
                    break
            if FoundPair == "0":
                break

        #Now index the new groups - Start with what is left in Tree Data, and work backwards
        SequenceCount = int(SequenceCount)
        for NodePairsIndex in range(len(NodePairs),-1,-1):
            SequenceCount += 1  #Get max node number
        for NodePairsIndex in range(len(NodePairs),0,-1):
            SequenceCount -= 1 #Assign nodes in reverse order
            NodeIDs.append(SequenceCount)

        #Now determine the nodes of the branches by looking up letters
        for NodePairsIndex in range(len(NodePairs)-1,-1,-1):
            #The node ID will connext to the Node Pairs
            NodeComponents = CommaSplitter.split(NodePairs[NodePairsIndex])  
            for NodeItem in NodeComponents:
                if Alphabet.find(NodeItem) >= 0: #This is alphabetic - look up the node id that the letter represents
                    BranchDescription.append(str(NodeIDs[NodePairsIndex]) + ".." + str(self.FindParent(NodeLetters,NodeIDs,NodeItem)))
                else:  #This is numeric - assemble the node
                    BranchDescription.append(str(NodeIDs[NodePairsIndex]) + ".." + str(NodeItem))
        return BranchDescription

    def FindParent(self,Letters,IDs,SearchLetter):
        "This function will return the child of a particular letter"
        for Index in range(0,len(Letters)):
            if Letters[Index] == SearchLetter:
                return IDs[Index]
        return 0

    def PrevAlphabetChar(self,CurrChar):
        "This function will return the previous character in the alphabet"
        RevAlphabet = "ZYXWVUTSRQPONMLKJIHGFEDCBA"
        if CurrChar == "":
            return "Z"
        else:
            return RevAlphabet[RevAlphabet.find(CurrChar) + 1]

    def WriteFile(self,FileName,Data):
        "This function will write the data passed to a file on the file system"
        TargetFile = file(FileName, "w")
        TargetFile.write(Data)
