#!/usr/bin/env python3

import json
import os
from os import path
import sys
import logging

from adjustment import Adjustment

log = logging.getLogger(__name__)

segments = list()
speaker_count = 0

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
			speaker_name = None
			block_start = None
			this_transcript = ''

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
					key = w
					start = word['start']
					
					# Record the start of the block
					if block_start is None:
						block_start = start

					# Check to see if speaker has changed
					tmp_speaker_name = get_speaker_name(start, word['end'])

					if speaker_name is None:
						speaker_name = tmp_speaker_name
					
					# If we have more than one word...
					if key > 0:
						# If it is a new speaker, record the words associated with the previous speaker and restart.
						if tmp_speaker_name != speaker_name:
							# Create the data values necessary 
							data['speaker'] = speaker_name # Generic speaker since we don't have speakers at this point
							data['words'] = blockWords
							data['start'] = block_start
							# Add this all as a block.  We only have one since only one speaker
							out_json['blocks'].append({
								'depth': 0,
								'data' : data,
								'entityRanges': entityRanges,
								'text' : this_transcript.strip(),
								'type' : 'paragraph',
								'inlineStyleRanges': []
							})
							# Once we have logged a block, reset the values
							blockWords = list() # Words in this data block
							data = dict() # Data element
							entityRanges = list()
							block_start = None
							this_transcript = ''
							speaker_name = tmp_speaker_name

					# Find the offset in the paragraph, starting with the last offset
					lastOffset = ampTranscript.index(wordText, lastOffset)

					# Append punctuation if there is any
					textWithPunct = wordText + punctuation
					this_transcript = this_transcript + " " + textWithPunct
					# Create the word
					newWord = {
						'start': start,
						'end': word['end'],
						'confidence': word['score']['scoreValue'],
						'index':key,
						'punct': textWithPunct,
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

			# DO THIS EVERY TIME A SPEAKER CHANGES

			

			
			# Write the json
			write_output_json(out_json, output_json)
speakers = list()
def add_data(speaker_name, words, start):
	this_speaker = None
	for s in range(0, len(speakers)):
		if speakers[s]['speaker'] == speaker_name:
			this_speaker = speakers[s]
			break
	
	if this_speaker is None:
		this_speaker = dict()
		this_speaker['speaker'] = speaker_name
		this_speaker['words'] = words
		this_speaker['start'] = start
		speakers.append(this_speaker)
	else:
		for w in range(0, len(words)):
			this_speaker['words'].append(words[w])
	
def fill_speakers(segmentation_json):
	print("filling speakers")
	try:
		with open(segmentation_json) as segmentation_json:
			segmentation = json.load(segmentation_json)
			# Conversion already done.  Exit
			if 'segments' in segmentation.keys():
				for s in range(0, len(segmentation['segments'])):
					segments.append(segmentation['segments'][s])
	except ValueError:
		print("Error reading segmentation json")

def get_speaker_name(start, end):
	name = None
	for s in range(0, len(segments)):
		this_segment = segments[s]
		if this_segment["start"] <= start and this_segment["end"] >= end:
			if this_segment['speakerLabel'] is not None:
				name = this_segment['speakerLabel']
			elif this_segment['label'] is not None:
				name = this_segment['label'] + "_" + str(s)

	if name is None:
		name = "Speaker_" + str(speaker_count)
		speaker_count += 1

	return name

def load_segmentation():
	return

# Serialize schema obj and write it to output file
def write_output_json(input_json, json_file):
	# Serialize the segmentation object
	with open(json_file, 'w') as outfile:
		json.dump(input_json, outfile, default=lambda x: x.__dict__)

if __name__ == "__main__":
	main()