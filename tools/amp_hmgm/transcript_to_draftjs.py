#!/usr/bin/env python3

import json
import os
from os import path
import sys
import logging


sys.path.insert(0, os.path.abspath('../../../../../tools/amp_utils'))
from mgm_logger import MgmLogger
# from adjustment import Adjustment

# log = logging.getLogger(__name__)

segments = list()

# Converts AMP speech to text json to Draft JS which is used by the transcript editor.
def main():

	(root_dir, amp_json, segmentation_json, output_json) = sys.argv[1:5]

	logger = MgmLogger(root_dir, "hmgm_transcript", amp_json)
	sys.stdout = logger
	sys.stderr = logger

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
		if segmentation_json is not None and segmentation_json!='None':
			fill_speakers(segmentation_json)
		speaker_count = 0
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
					tmp_speaker_name = get_speaker_name(start, word['end'], speaker_count)

					if speaker_name is None:
						speaker_name = tmp_speaker_name
					
					# If we have more than one word...
					if key > 0:
						# If it is a new speaker, record the words associated with the previous speaker and restart.
						if tmp_speaker_name != speaker_name:
							speaker_count+=1
							# Create the data values necessary 
							data = createData(speaker_name, blockWords, block_start)
							# Add this all as a block.  We only have one since only one speaker
							block = createBlock(0, data, entityRanges, this_transcript)
							out_json['blocks'].append(block)
							
							# Once we have logged a block, reset the values
							blockWords = list() # Words in this data block
							entityRanges = list()
							block_start = start
							this_transcript = ''
							speaker_name = tmp_speaker_name
							lastOffset = 0

					# Append punctuation if there is any
					textWithPunct = wordText + punctuation

					# For this block, generate transcript text
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

					# Find the offset in the paragraph, starting with the last offset
					lastOffset = len(this_transcript)

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

				# If it's the end, make sure we get the 
				if w == (len(ampResultWords) -1):
					data = createData(speaker_name, blockWords, block_start)
					# Add this all as a block.  We only have one since only one speaker
					block = createBlock(0, data, entityRanges, this_transcript)
					out_json['blocks'].append(block)

			# Write the json
			write_output_json(out_json, output_json)

def createBlock(depth, data, entityRanges, transcript):
	return {
				'depth': depth,
				'data' : data,
				'entityRanges': entityRanges,
				'text' : transcript.strip(),
				'type' : 'paragraph',
				'inlineStyleRanges': []
			}

def createData(speaker, words, start):
	data = dict()
	data['speaker'] = speaker # Generic speaker since we don't have speakers at this point
	data['words'] = words
	data['start'] = start
	return data

def fill_speakers(segmentation_json):
	try:
		with open(segmentation_json) as segmentation_json:
			segmentation = json.load(segmentation_json)
			# Conversion already done.  Exit
			if 'segments' in segmentation.keys():
				for s in range(0, len(segmentation['segments'])):
					segments.append(segmentation['segments'][s])
	except ValueError:
		print("Error reading segmentation json")

def get_speaker_name(start, end, speaker_count):
	if len(segments)==0:
		return "Speaker_0"

	name = None
	for s in range(0, len(segments)):
		this_segment = segments[s]
		if this_segment["start"] <= start and this_segment["end"] >= end:
			if 'speakerLabel' in this_segment.keys() and this_segment['speakerLabel'] is not None:
				name = this_segment['speakerLabel']
			elif 'label' in this_segment.keys() and this_segment['label'] is not None:
				name = this_segment['label'] + "_" + str(s)

	if name is None:
		name = "Speaker_" + str(speaker_count)
		speaker_count += 1

	return name

# Serialize schema obj and write it to output file
def write_output_json(input_json, json_file):
	# Serialize the segmentation object
	with open(json_file, 'w') as outfile:
		json.dump(input_json, outfile, default=lambda x: x.__dict__)

if __name__ == "__main__":
	main()