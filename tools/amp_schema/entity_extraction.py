import csv

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

	def addEntity(self, type, text, beginOffset, endOffset, start = None, end = None, scoreType = None, scoreValue = None):
		entity = EntityExtractionEntity(type, text, beginOffset, endOffset, start, end)
		if scoreType is not None and scoreValue is not None:
			entity.score = EntityExtractionEntityScore(scoreType, scoreValue)
		self.entities.append(entity)

	def toCsv(self, csvFile):
		# Write as csv
		with open(csvFile, mode='w') as csv_file:
			csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
			csv_writer.writerow(['Type', 'Text', 'Begin Offset', 'End Offset', 'Start Time', 'Score Type', 'Score Value'])
			for e in self.entities:
				if e.score is not None:
					scoreType = e.score.type
					scoreValue = e.score.scoreValue
				else:
					scoreType = ''
					scoreValue = ''
				if e.start is not None:
					start = e.start
				else:
					start = ''
				csv_writer.writerow([e.type, e.text, e.beginOffset, e.endOffset, start, scoreType, scoreValue])

	@classmethod
	def from_json(cls, json_data: dict):
		media = EntityExtractionMedia.from_json(json_data["media"])
		entities = list(map(EntityExtractionEntity.from_json, json_data["entities"]))
		return cls(media, entities)

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
	start = None
	end = None
	score = None
	def __init__(self, type = None, text = None, beginOffset = None, endOffset = None, start = None, end = None, score = None):
		self.type = type
		self.text = text
		self.beginOffset = beginOffset
		self.endOffset = endOffset
		if start is not None and  float(start) >= 0.00:
			self.start = start
		if end is not None and  float(end) >= 0.00:
			self.end = end
		self.score = score
		 
	@classmethod
	def from_json(cls, json_data: dict):
		start = None
		end = None
		score = None
		if 'start' in json_data.keys():
			start = json_data['start']
		if 'end' in json_data.keys():
			end = json_data['end']
		if 'score' in json_data.keys():
			score = EntityExtractionEntityScore.from_json(json_data['score'])
		return cls(json_data['type'], json_data['text'], json_data['beginOffset'], json_data['endOffset'], start, end, score)

class EntityExtractionEntityScore:
	type = ""
	scoreValue = 0.00
	def __init__(self, type = None, scoreValue = None):
		self.type = type
		self.scoreValue = scoreValue
	@classmethod
	def from_json(cls, json_data: dict):
		return cls(**json_data)


