from collections import namedtuple
import json

class SegmentationSchema:
	def __init__(self, segments=[], media=None):
		self.segments = segments
		if media is None:
			self.media = SegmentationSchemaMedia()
		else:
			 self.media = media
	def addSegment(self, label, gender=None, start=None, end=None):
		self.segments.append(SegmentationSchemaSegment(label, gender, start, end))
		if end is not None and end > self.media.duration:
			self.media.duration = end
		return
	def setFilename(self, filename):
		self.media.filename = filename
		return
	@classmethod
	def from_json(cls, json_data: dict):
		segments = list(map(SegmentationSchemaSegment.from_json, json_data["segments"]))
		media = SegmentationSchemaMedia(json_data["media"]["duration"], json_data["media"]["filename"])
		return cls(segments, media)

class SegmentationSchemaMedia:
	filename = ""
	duration = 0
	def __init__(self, duration = 0, filename = ""):
		self.duration = duration
		self.filename = filename

	@classmethod
	def from_json(cls, json_data):
		return cls(**json_data)

class SegmentationSchemaSegment:
	label = ""
	start = 0
	end = 0
	gender = None
	def __init__(self, label, gender=None, start=None, end=None):
		self.label = label
		if gender is not None:
			self.gender = gender
		self.start = start
		self.end = end
	@classmethod
	def from_json(cls, json_data: dict):
		return cls(**json_data)