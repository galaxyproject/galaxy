class SpeechToText:
	def __init__(self, media=None, result=None):
		if media is None:
			self.media = SpeechToTextMedia()
		else:
			 self.media = media
		if result is None:
			self.result = SpeechToTextResult()
		else:
			 self.result = result

class SpeechToTextMedia:
	filename = ""
	duration = 0.00
	def __init__(self, duration = 0.00, filename = ""):
		print("setting duration " + str(duration))
		self.duration = duration
		self.filename = filename

class SpeechToTextResult:
	transcript = ""
	words = []
	def __init__(self, words=[], transcript=""):
		self.transcript = transcript
		self.words = words
	def addWord(self, type, start:float, end:float, text, scoreType, scoreValue):
		newWord = SpeechToTextWord(type, text, start, end, scoreType, scoreValue)
		self.words.append(newWord)

class SpeechToTextWord:
	type = ""
	start = 0.00
	end = 0.00
	text = ""
	score = None
	def __init__(self, type, text, start:float = None, end:float = None, scoreType = None, scoreValue = None):
		if scoreValue is not None:
			self.score = SpeechToTextScore(scoreType, scoreValue)
		self.type = type
		if float(start) >= 0.00:
			self.start = start
		if float(end) >= 0.00:
			self.end = end
		self.text = text


class SpeechToTextScore:
	type = ""
	scoreValue = 0.0
	def __init__(self, scoreType, scoreValue):
		self.type = scoreType
		self.scoreValue = scoreValue


	