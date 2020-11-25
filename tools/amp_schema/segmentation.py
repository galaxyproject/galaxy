import json

class Segmentation:
	def __init__(self, segments=[], media=None, numSpeakers=None):
		self.segments = segments
		self.numSpeakers = numSpeakers
		if media is None:
			self.media = SegmentationMedia()
		else:
			 self.media = media
	def addSegment(self, label, gender=None, start=None, end=None, speakerLabel = None):
		self.segments.append(SegmentationSegment(label, gender, start, end, speakerLabel))
		if end is not None and end > self.media.duration:
			self.media.duration = end
		return
	def setFilename(self, filename):
		self.media.filename = filename
		return
	@classmethod
	def from_json(cls, json_data: dict):
		segments = list(map(SegmentationSegment.from_json, json_data["segments"]))
		media = SegmentationMedia(json_data["media"]["duration"], json_data["media"]["filename"])
		return cls(segments, media)

class SegmentationMedia:
	filename = ""
	duration = 0
	def __init__(self, duration = 0, filename = ""):
		self.duration = duration
		self.filename = filename

	@classmethod
	def from_json(cls, json_data):
		return cls(**json_data)

class SegmentationSegment:
	label = ""
	start = 0
	end = 0
	gender = None
	speakerLabel = None
	def __init__(self, label, gender=None, start=None, end=None, speakerLabel = None):
		self.label = label
		if gender is not None:
			self.gender = gender
		self.start = start
		self.end = end
		self.speakerLabel = speakerLabel
	@classmethod
	def from_json(cls, json_data: dict):
		return cls(**json_data)