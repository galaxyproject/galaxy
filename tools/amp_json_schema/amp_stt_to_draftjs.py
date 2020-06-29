#!/usr/bin/env python3

import json
import os
from os import path
import sys
import logging

from adjustment import Adjustment

# Converts AMP speech to text json to Draft JS which is used by the transcript editor.
def main():

	(amp_json, segmentation_json, output_json) = sys.argv[1:4]
	exit_peacefully = False
	# Read the output file.  Check to see if we've already done this conversion. 
	if path.exists(output_json):
		try:
			with open(output_json) as output_json_file:
				draftjs_output = json.load(output_json_file)
				# Conversion already done.  Exit
				if 'entityMap' in draftjs_output.keys():
					print("Json already converted.  Exiting")
					exit_peacefully = True
		except ValueError:
			print("File exists, but not json.  Continue conversion")
			
	if exit_peacefully == False:
		fill_speakers(segmentation_json)
		out_json = dict()
		out_json['entityMap'] = {}
		out_json['blocks'] = []

		# Open the transcribe output
		with open(amp_json) as json_file:
			try:
				json_input = json.load(json_file)
			except ValueError:
				print("Invalid input file, exiting")
				exit(1)

			# Check to see if we have the required input
			if 'result' not in json_input.keys():
				print("Missing required result input.  Exiting")
				exit(0)

			ampResult = json_input['result']	

			if 'words' not in ampResult.keys() or 'transcript' not in ampResult.keys():
				print("Missing required words or transcript input.  Exiting")
				exit(0)

			ampResultWords = ampResult['words']
			ampTranscript = ampResult['transcript']

			blockWords = list() # Words in this data block
			data = dict() # Data element
			entityRanges = list() # A list of entity ranges
			lastOffset = 0  # The last offset of a word we searched for

			# Iterate through all of the words
			for w in range(0, len(ampResultWords)):
				word = ampResultWords[w]
				nextWord = None
				punctuation = ""
				wordText = word['text']

				# Check to see if the next "word" is punctuation.  If so, append it to the current word
				if len(ampResultWords) > w + 1:
					nextWord = ampResultWords[w + 1]
					if nextWord['type'] == 'punctuation':
						punctuation += nextWord['text']

				# If the current word is actually a word, create the necessary output
				if word['type'] == 'pronunciation':
					# Use the current position as the key
					key = len(blockWords)
					# Find the offset in the paragraph, starting with the last offset
					lastOffset = ampTranscript.index(wordText,lastOffset)
					start = word['start']
					# Append punctuation if there is any
					textWithPunct = wordText + punctuation

					# Create the word
					newWord = {
						'start': start,
						'end': word['end'],
						'confidence': word['score']['scoreValue'],
						'index':key,
						'punct': wordText + punctuation,
						'text': wordText
					}
					# Create the entity range
					entityRange = {
						'offset': lastOffset,
						'key': key,
						'length': len(textWithPunct),
						'start': start,
						'end': newWord['end'],
						'confidence': newWord['confidence'],
						'text': wordText
					}

					# Create the entity map listing
					out_json['entityMap'][key] = {
						'mutability': 'MUTABLE',
						'type': "WORD",
						'data': entityRange
					}

					# Add this to the entity range
					entityRanges.append(entityRange)
					# Add the word
					blockWords.append(newWord)
					# Increment offset
					lastOffset +=1

			# Create the data values necessary 
			data['speaker'] = 'Speaker 0' # Generic speaker since we don't have speakers at this point
			data['words'] = blockWords
			data['start'] = ampResultWords[0]['start']

			# Add this all as a block.  We only have one since only one speaker
			out_json['blocks'].append({
				'depth': 0,
				'data' : data,
				'entityRanges': entityRanges,
				'text' : ampTranscript,
				'type' : 'paragraph',
				'inlineStyleRanges': []
			})
			# Write the json
			write_output_json(out_json, output_json)

segments = list()
def fill_speakers(segmentation_json):
	log.debug("filling speakers")
	try:
		with open(segmentation_json) as segmentation_json:
			segmentation = json.load(segmentation_json)
			# Conversion already done.  Exit
			if 'segments' in segmentation.keys():
				for s in range(0, len(segmentation['segments'])):
					segments.append(s)
	except ValueError:
		print("Error reading segmentation json")
	log.debug(segments)

def add_to_speaker():
	return

def get_speaker():
	return

def load_segmentation():
	return

# Serialize schema obj and write it to output file
def write_output_json(input_json, json_file):
	# Serialize the segmentation object
	with open(json_file, 'w') as outfile:
		json.dump(input_json, outfile, default=lambda x: x.__dict__)

if __name__ == "__main__":
	main()