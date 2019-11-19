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

	def addEntity(self, type, text, beginOffset, endOffset):
		self.entities.append(EntityExtractionEntity(type, text, beginOffset, endOffset))

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

class EntityExtractionEntity:
	text = ""
	type = None
	beginOffset = None
	endOffset = None
	def __init__(self, type = None, text = None, beginOffset = None, endOffset = None):
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

	