class EntityExtraction:
	def __init__(self, media=None, entities=None):
		if media is None:
			self.media = EntityExtractionMedia()
		else:
			 self.media = media
		if entities is None:
			self.entities = []
		else:
			 self.entities = entities

	def addEntity(self, type, text, beginOffset, endOffset, scoreType = None, scoreValue = None):
		entity = EntityExtractionEntity(type, text, beginOffset, endOffset)
		if scoreType is not None and scoreValue is not None:
			entity.score = EntityExtractionEntityScore(scoreType, scoreValue)
		self.entities.append(entity)

	@classmethod
	def from_json(cls, json_data: dict):
		return cls(json_data['media'], json_data['entities'])

class EntityExtractionMedia:
	filename = ""
	characters = 0
	def __init__(self, characters = 0, filename = ""):
		self.characters = characters
		self.filename = filename
	@classmethod
	def from_json(cls, json_data: dict):
		return cls(**json_data)

class EntityExtractionEntityScore:
	type = ""
	scoreValue = 0.00
	def __init__(self, type = None, scoreValue = None):
		self.type = type
		self.scoreValue = scoreValue
	@classmethod
	def from_json(cls, json_data: dict):
		return cls(**json_data)

class EntityExtractionEntity:
	text = ""
	type = None
	beginOffset = None
	endOffset = None
	score = None
	def __init__(self, type = None, text = None, beginOffset = None, endOffset = None, score = None):
		self.type = type
		self.text = text
		if beginOffset is not None and float(beginOffset) >= 0.00:
			self.beginOffset = beginOffset
		if endOffset is not None and  float(endOffset) >= 0.00:
			self.endOffset = endOffset
	@classmethod
	def from_json(cls, json_data: dict):
		beginOffset = None
		endOffset = None
		if 'beginOffset' in json_data.keys():
			beginOffset = json_data['beginOffset']
		if 'endOffset' in json_data.keys():
			endOffset = json_data['endOffset']
		return cls(json_data['type'], json_data['text'], beginOffset,endOffset)

	