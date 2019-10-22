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
	@classmethod
	def from_json(cls, json_data: dict):
		return cls(json_data['media'], SpeechToTextResult().from_json(json_data['result']))

class SpeechToTextMedia:
	filename = ""
	duration = 0.00
	def __init__(self, duration = 0.00, filename = ""):
		print("setting duration " + str(duration))
		self.duration = duration
		self.filename = filename
	@classmethod
	def from_json(cls, json_data: dict):
		return cls(**json_data)

class SpeechToTextResult:
	transcript = ""
	words = []
	def __init__(self, words=[], transcript=""):
		self.transcript = transcript
		self.words = words
	def addWord(self, type, start:float, end:float, text, scoreType, scoreValue):
		newWord = SpeechToTextWord(type, text, start, end, scoreType, scoreValue)
		self.words.append(newWord)
	@classmethod
	def from_json(cls, json_data: dict):
		words_dict = json_data['words']
		words = []
		words = list(map(SpeechToTextWord.from_json, words_dict))
		return cls(words, json_data['transcript'])

class SpeechToTextWord:
	type = ""
	start = None
	end = None
	text = ""
	score = None
	def __init__(self, type = None, text = None, start = None, end = None, scoreType = None, scoreValue = None):
		if scoreValue is not None:
			self.score = SpeechToTextScore(scoreType, scoreValue)
		self.type = type
		if start is not None and float(start) >= 0.00:
			self.start = start
		if end is not None and  float(end) >= 0.00:
			self.end = end
		self.text = text
	@classmethod
	def from_json(cls, json_data: dict):
		scoreType = None
		scoreValue = None
		if 'score' in json_data.keys():
			score = json_data['score']
			scoreValue = score['scoreValue']
			scoreType = score['type']
		start = None
		end = None
		if 'start' in json_data.keys():
			start = json_data['start']
		if 'end' in json_data.keys():
			end = json_data['end']
		return cls(json_data['type'],json_data['text'],start,end, scoreType, scoreValue)


class SpeechToTextScore:
	type = ""
	scoreValue = 0.0
	def __init__(self, type = None, scoreValue = None):
		self.type = type
		self.scoreValue = scoreValue
	@classmethod
	def from_json(cls, json_data: dict):
		return cls(**json_data)


	