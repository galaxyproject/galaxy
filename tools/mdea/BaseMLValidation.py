import re
import string

class BaseMLValidation:
	"This is a class that peforms data validation on the passed data"
	def __init__(self):
		"Doc Holder"

	def ValidateSubstData(self,AlignmentTogether,DoDoubleBoot,CompType,Iterations,Sequence1,Sequence2,TreeDef,BaseMLLocation,DoBootStrap):
		"This function checks the data for potential errors and returns an error string to the caller"
		#Do Foreign Characters exists in the tree?
		ErrorString = ""
		TreeForeignChar = re.compile('[AWXYZ_\(\),{0-9}+]')
		BareTree = TreeForeignChar.sub("",TreeDef)
		if str(BareTree) != "":  #No use continuing past this point
			ErrorString += "Malformed tree definition - foreign characters detected.<BR>"
		else:
			#Get the sequence count - and make sure that it is consistent among the tree and sequence(s)
			ErrorString += self.GetSequenceCount(AlignmentTogether,Sequence1,Sequence2,TreeDef)
			#Store important data for later use
			self.SequenceLength1 = self.GetSeqLength(Sequence1)
			self.SequenceLength2 = 0
			if str(AlignmentTogether) == "0":
				self.SequenceLength2 = self.GetSeqLength(Sequence2)
			#Tree Validation
			#Check that the comparison type and the tree agree - are the branches tied together?
			if str(AlignmentTogether) == "1":
				ErrorString += self.CheckTreeVsCompType(TreeDef,CompType)
			#General Tree Validation
			ErrorString += self.ValidateTree(TreeDef,self.SequenceCount)

		#Iteration Validation - > 10 iterations if there is bootstrapping
		if int(DoBootStrap) == 1:
			if int(Iterations) < 10:
				ErrorString += "For analysis with bootstrap there must be at least 10 replicas.<BR>"

		return ErrorString

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
			ErrorString += "Malformed tree definition - there needs to be an equal number of '(' as ')'.<BR>"

		#Are there the correct number of commas?  SequenceCount - 1 Commas
		CommaCount = Tree.count(",")
		if CommaCount != int(int(SequenceCount) - 1):
			ErrorString += "Malformed tree definition - there are an inadequate number of commas present.<BR>"

		#Are all numbers present in the tree?
		Tree = TreeArrayPrep.sub("",Tree)
		TreeNodeArray = TreeCommaSplit.split(Tree)
		NotFoundNumber = 0
		for Number in range(1,int(SequenceCount) + 1):
			if not TreeNodeArray.__contains__(str(Number)):
				NotFoundNumber = 1
				break

		if NotFoundNumber == 1:
			ErrorString += "Malformed tree definition - all numbers from 1 to " + str(SequenceCount) + " must be present in the tree definition.<BR>"

		return ErrorString

	def CheckTreeVsCompType(self,TreeDef,CompType):
		"The function will determine if the tree definition matches the comparison type the user selected"
		ErrorString = ""
		Group1Char = ""
		Group2Char = ""
		TreeStripper = re.compile('[,\(\)_0-9\s]')
		if str(CompType) == "1":
			Group1Char = "Y"
			Group2Char = "X"
		elif str(CompType) == "2":
			Group1Char = "Y"
			Group2Char = "A"
		elif str(CompType) == "3":
			Group1Char = "X"
			Group2Char = "A"
		elif str(CompType) == "4":
			Group1Char = "Z"
			Group2Char = "W"
		elif str(CompType) == "5":
			Group1Char = "Z"
			Group2Char = "A"
		elif str(CompType) == "6":
			Group1Char = "W"
			Group2Char = "A"
		
		#For a proper tree there should be equal amounts of each chromosome				
		Group1Count = 0
		Group2Count = 0
		TreeOwners = TreeStripper.sub("",TreeDef)
		for TreeOwnerChar in TreeOwners:
			if str(TreeOwnerChar) == str(Group1Char):
				Group1Count += 1
			if str(TreeOwnerChar) == str(Group2Char):
				Group2Count += 1

		if int(Group1Count) != int(Group2Count):
			ErrorString = "Malformed tree definition - there need to be an equal number of branches assigned to '" + str(Group1Char) + "' as there are to '" + str(Group2Char) + "'.<BR>"

		return ErrorString

	def GetSequenceCount(self,AlignmentTogether,Sequence1,Sequence2,TreeDef):
		"This module checks for the sequence count in the tree and the sequence(s) ensuring agreement between the two - It will also set the sequence length"
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
				ErrorString = "The tree definition doesn't match the sequences provided.<BR>"
		else:
			if str(FileSeqCount1) != str(TreeSequenceCount):
				ErrorString = "The tree definition doesn't match the sequence provided.<BR>"
		self.SequenceCount = TreeSequenceCount
		return ErrorString

	def CheckSeqCount(self,Sequence):
		SequenceArray = []
		seqfile = open(Sequence)
		for FileLine in seqfile.readlines():
			FileLine = FileLine[0:len(FileLine)-1]  #Remove the new line character
			if FileLine[0] != ">" and FileLine[0] != "#" and FileLine != "":
				SequenceArray.append(FileLine)
		seqfile.close()
		return len(SequenceArray)	

	def GetSeqLength(self,Sequence):
		SequenceLength = 0
		seqfile = open(Sequence)
		for FileLine in seqfile.readlines():
			FileLine = FileLine[0:len(FileLine)-1]  #Remove the new line character
			if FileLine[0] != ">" and FileLine[0] != "#" and FileLine != "":
				SequenceLength = len(FileLine)
				break
		seqfile.close()
		return SequenceLength
