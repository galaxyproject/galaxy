#!/usr/bin/env python3

import json
import os
import sys

from speech_to_text_schema import SpeechToText, SpeechToTextMedia, SpeechToTextResult, SpeechToTextScore, SpeechToTextWord

def main():
	(media_file, transcribe_file, output_json_file) = sys.argv[1:4]
	
	# Open the transcribe output
	with open(transcribe_file) as json_file:
		data = json.load(json_file)
		
	result = SpeechToTextResult()

	# Parse transcript
	transcripts = data["results"]["transcripts"]
	for t in transcripts:
		result.transcript = result.transcript + t["transcript"]

	# Parse items (words)
	items = data["results"]["items"]
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
	write_output_json(outputFile, output_json_file)


# Serialize schema obj and write it to output file
def write_output_json(transcribe_schema, json_file):
	# Serialize the segmentation object
	with open(json_file, 'w') as outfile:
		json.dump(transcribe_schema, outfile, default=lambda x: x.__dict__)

if __name__ == "__main__":
	main()