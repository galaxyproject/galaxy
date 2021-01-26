import json

class Segmentation:
	MINIMUM_SILENCE = 10.0
	def __init__(self, segments=[], media=None, numSpeakers=0):
		self.segments = segments
		self.numSpeakers = numSpeakers
		if media is None:
			self.media = SegmentationMedia()
		else:
			self.media = media
			
	def addDiarizationSegment(self, start=None, end=None, speakerLabel = None):
		self.segments.append(SegmentationSegment(None, None, start, end, speakerLabel))

	def addSegment(self, label, gender=None, start=None, end=None, speakerLabel = None):
		# Format the label for comparison purposes
		tmp_label = SegmentationSegment.formatLabel(label)

		# Get the last segment if we have at least on in the list
		last_segment = None
		if len(self.segments) >= 1:
			last_segment = self.segments[-1]

		if last_segment is not None:
			print(last_segment)

		# If the time of the segment is less than 10 seconds, we have another segment, and the current 
		# segment is noise or silence, don't add it but add the time to the previous segment
		if (float(end) - float(start)) < self.MINIMUM_SILENCE and last_segment is not None and tmp_label in ('noise', 'silence'):
			last_segment.end = end
		else:
			# Format the gender
			tmp_gender = SegmentationSegment.formatGender(gender)

			# If the last segment matches the type, merge the two
			if last_segment is not None and last_segment.label == tmp_label and last_segment.gender == tmp_gender:
				last_segment.end = end
			else:
				# Otherwise add the segment
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
		self.label = SegmentationSegment.formatLabel(label)
		if gender is not None:
			self.gender = SegmentationSegment.formatGender(gender)
		self.start = start
		self.end = end
		self.speakerLabel = speakerLabel

	@staticmethod
	def formatGender( value):
		if value is None:
			return None
		tmp_value = value.lower()
		if tmp_value in ("male", "female"):
			return tmp_value.lower()
		return ""

	@staticmethod
	def formatLabel(value):
		if value is None:
			return None
		tmp_value = value.lower()
		if tmp_value in ("male", "female", "speech"):
			return "speech"
		elif tmp_value == "music":
			return "music"
		elif tmp_value in ("noactivity", "noenergy"):
			return "silence"
		return tmp_value

	@classmethod
	def from_json(cls, json_data: dict):
		return cls(**json_data)