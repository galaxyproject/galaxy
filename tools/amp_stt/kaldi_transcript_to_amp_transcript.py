#!/usr/bin/env python3

import json
import sys
import os

sys.path.insert(0, os.path.abspath('../../../../../tools/amp_util'))
import mgm_utils

sys.path.insert(0, os.path.abspath('../../../../../tools/amp_schema'))
from speech_to_text import SpeechToText, SpeechToTextMedia, SpeechToTextResult, SpeechToTextScore, SpeechToTextWord

# Convert kaldi output to standardized json
def main():
	(media_file, kaldi_file, kaldi_transcript_file, output_json_file) = sys.argv[1:5]
	mgm_utils.exception_if_file_not_exist(kaldi_file)
	if not os.path.exists(kaldi_transcript_file):
		raise Exception("Exception: File " + kaldi_transcript_file + " doesn't exist, the previous command generating it must have failed.")
	results = SpeechToTextResult()

	# Open the kaldi json
	with open(kaldi_file) as json_file:
		data = json.load(json_file)

	# Get the kaldi transcript
	transcript = open(kaldi_transcript_file, "r")	
	results.transcript = transcript.read()

	# Get a list of words
	words = data["words"]
	duration = 0.00

	# For each word, add a word to our results
	for w in words:
		time = float(w["time"])
		end = time + float(w["duration"])
		# Keep track of the last time and use it as the duration
		if end > duration:
			duration = end
		results.addWord("", time, end, w["word"], None, None)

	# Create the media objeect
	media = SpeechToTextMedia(duration, media_file)

	# Create the final object
	outputFile = SpeechToText(media, results)

	#write the output
	write_output_json(outputFile, output_json_file)


# Serialize schema obj and write it to output file
def write_output_json(transcribe_schema, json_file):
	# Serialize the segmentation object
	with open(json_file, 'w') as outfile:
		json.dump(transcribe_schema, outfile, default=lambda x: x.__dict__)

if __name__ == "__main__":
	main()