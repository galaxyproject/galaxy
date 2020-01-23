#!/usr/bin/env python3

import json
import os
import sys

from speech_to_text_schema import SpeechToText, SpeechToTextMedia, SpeechToTextResult, SpeechToTextScore, SpeechToTextWord
from segmentation_schema import SegmentationSchema, SegmentationSchemaMedia, SegmentationSchemaSegment

def main():
	(media_file, transcribe_file, output_stt_json_file, output_seg_json_file) = sys.argv[1:5]
	
	# Open the transcribe output
	with open(transcribe_file) as json_file:
		data = json.load(json_file)
		
	result = SpeechToTextResult()

	# Fail if we don't have results
	if "results" not in data.keys():
		exit(1)

	results = data["results"]

	if "transcripts" not in results.keys():
		exit(1)

	# Parse transcript
	transcripts = results["transcripts"]
	for t in transcripts:
		result.transcript = result.transcript + t["transcript"]

	# Fail if we don't have any keys
	if "items" not in results.keys():
		exit(1)

	# Parse items (words)
	items = results["items"]
	duration = 0.00
	
	# For each item, get the necessary parts and store as a word
	for i in items:
		alternatives = i["alternatives"]
		# Choose an alternative
		max_confidence = 0.00
		text = ""

		# Each word is stored as an "alternative".  Get the one with the maximum confidence
		for a in alternatives:
			if float(a["confidence"]) > max_confidence:
				max_confidence = float(a["confidence"])
				text = a["content"]

		end_time = -1
		start_time = -1

		# Two types (punctionation, pronunciation).  Only keep times for pronunciation
		if i["type"] == "pronunciation":
			end_time = float(i["end_time"])
			start_time = float(i["start_time"])

			# If this is the greatest end time, store it as duration
			if end_time > duration:
				duration = end_time
		# Add the word to the result
		result.addWord(i["type"], start_time, end_time, text, "confidence", max_confidence)
	
	# Create the media object
	media = SpeechToTextMedia(duration, media_file)

	# Create the final object
	outputFile = SpeechToText(media, result)

	# Write the output
	write_output_json(outputFile, output_stt_json_file)

	# Start segmentation schema with diarization data
	if "speaker_labels" in results.keys():
    	# Create a segmentation object to serialize
		seg_schema = SegmentationSchema()

		# Create the media object
		segMedia = SegmentationSchemaMedia(duration, media_file)
		seg_schema.media = segMedia

		speakerLabels = results["speaker_labels"]
		seg_schema.numSpeakers = speakerLabels["speakers"]

		# For each segment, get the start time, end time and speaker label
		segments = speakerLabels["segments"]
		for segment in segments:
			seg_schema.addSegment(None, None, float(segment["start_time"]), float(segment["end_time"]), segment["speaker_label"])
		
		# Write the output
		write_output_json(seg_schema, output_seg_json_file)

# Serialize schema obj and write it to output file
def write_output_json(input_json, json_file):
	# Serialize the segmentation object
	with open(json_file, 'w') as outfile:
		json.dump(input_json, outfile, default=lambda x: x.__dict__)

if __name__ == "__main__":
	main()