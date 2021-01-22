#!/usr/bin/env python3
import json
import sys
import os
from _ast import Or


# Reads the AMP Transcript and Segment inputs and convert them to Web VTT output.
def main():
	(seg_file, stt_file, vtt_file) =  sys.argv[1:4] 

	# read words and segments from input files
	segments = []
	words = []
	if os.path.exists(seg_file):
		json_seg = open(seg_file)
		dict_seg = json.loads(json_seg.read())
		segments = dict_seg['segments']
	if os.path.exists(stt_file):
		json_stt = open(stt_file)
		dict_stt = json.loads(json_stt.read())
		words = dict_stt['results']['words']
	
	# write header to output vtt file
	out_file = open(vtt_file, "w")
	out_file.write(writeHeader())
	out_file.write(writeEmptyLine())

	# initialize status before first (new) line
	nword = 0	# number of pronunciation words in current line so far 
	curseg = 0	# index of current segment (to get current speaker)
	start = end = 0	# start/end timestamp for current line
	line = ''	# text of current line	
	newline = False	# true if current word is the start of a new line
				
	# process all words which are in time order
	for i, word in enumerate(words):
		# the current word should be the start of a new line if it's pronunciation and  
		if word['type'] == 'pronunciation':
			# no previous line, this is the very first word
			if (nword == 0):
				newline = True
			# there are already 10 words in current line
			elif nword == 10:
				newline = True
			# or there are at least 6 words plus punctuation in current line	
			elif nword >= 6 and words[i-1]['type'] == 'punctuation':
				newline = True
			# or it's from a new speaker
			else:
				# note that if segments is empty, iseg/curseg will stay at 0
				iseg = findWordSegmentIndex(word, segments, curseg)
				if iseg > curseg:
					newline = True
					curseg = iseg
		
		# starting a new line	
		if newline:
			# write the current line (if any word) before starting a new line
			# note that punctuation words before the very first pronunciation word (in which case nword = 0) will be ignored 
			if (nword > 0):
				out_file.write(writeTime(start, end))
				out_file.write(writeLine(getSpeaker(segments, curseg), line))
				out_file.write(writeEmptyLine())
			# reset status for the new line
			nword = 0 
			# new line always starts with a pronunciation, use its start time as line start time
			start = word['start']	 
			line = ''	
			newline = False
		
		# update current line with current word
		if word['type'] == 'pronunciation':
			nword += 1
			# record potential line end time from current pronunciation (can't end time of last word on a line since it may be punctuation)
			end = word['end']
		line += ' ' + word['text']
		
	# write the last line to file if any word in it; note that 
	# the last line should always contain some pronunciation words unless the whole words list contains no pronunciation
	if nword > 0:
		out_file.write(writeTime(start, end))
		out_file.write(writeLine(getSpeaker(segments, curseg), line))
		out_file.write(writeEmptyLine())
	out_file.close()
		
# Find the index of the next segment among the given segments to which the given word belongs to, starting at the given (current) 
# segment index (always >= 0). A word belongs to a segment if its timestamp is within the segment's time range,  
def findWordSegmentIndex(word, segments, istart):
	# non pronunciation word always stays with the current segment
	if word['type'] != 'pronunciation':
		return istart		
	# if we are already beyond segments index bound, stay with current segment
	if istart >= len(segments):
		return istart
	# if word start time is within current segment end time, stay with current segment 
	if word['start'] < segments[istart]['end']:
		return istart
	
	# otherwise, scan the following segments for the next containing one, based on following assumptions: 
	# need to scan as some segments may not contain any word (otherwise we can just return the next segment); 
	# can scan segments sequentially as segments are in time order;
	# instead of requiring word's [start, end] time within segment's [start, end] time,
	# only check word's start time against segment's end time (i.e. consider segments continuous in time), 
	# to ensure each word fall into some segment, and handle well even when word crosses segment boundary (unlikely) 
	iseg = istart + 1
	while iseg < len(segments) and word['start'] >= segments[iseg]['end']:
		iseg += 1		
	return iseg
	
# Gets the speaker of the given segments[iseg]. 	
def getSpeaker(segments, iseg):
	if iseg < 0 or iseg >= len(segments):
		return "No Speaker"
	if 'speakerLabel' in segments[iseg]:
		return segments[iseg]['speakerLabel']
	else:
		return "Unlabeled Speaker"
		
def writeHeader():
	#this fuction writes the header of the vtt file
	return "WEBVTT"+"\n"
		
def writeLine(speaker, text):
	#This function writes a new line to the vtt output
	return "<v "+speaker+">"+text+"\n"

def writeEmptyLine():
	# This function writes an empty line to the vtt output
	return "\n"

def writeTime(start_time, end_time):
	#This function writes a time entry to the vtt output
	return str(start_time)+" --> "+str(end_time)+"\n"
	
		
# 	# Gets the speaker for the given pronunciation word belonging to the given segments[iseg]. 	
# 	def getSpeaker(word, segments, iseg):
# 		if wordWithinSegment(word, segments, iseg):
# 			if 'speakerLabel' in segments[iseg]:
# 				return segments[iseg]['speakerLabel']
# 			else:
# 				return "Unlabeled Speaker"
# 		return "Unidentified Speaker"
# 		
# 	# Return true if the given pronunciation word's start/end time is within the given segments[iseg] start/end time, false otherwise.
# 	def wordWithinSegment(word, segments, iseg):
# 		if iseg < 0 or iseg >= len(segments):
# 			return False		
# 		if word['type'] == 'pronunciation' and word['start'] >= segments[iseg]['start'] and word['end'] <= segments[iseg]['end']:
# 			return True
# 		return False 
#		
# 	# Return true if the given word is pronunciation and its end time is beyond the given segments[iseg] end time, false otherwise.
# 	# If the segment index iseg is out of the segments index range, return false.
# 	def wordBeyondSegment(word, segments, iseg):
# 		if iseg < 0 or iseg >= len(segments):
# 			return False		
# 		if word['type'] == 'pronunciation' and word['end'] > segments[iseg]['end']:
# 			return True
# 		return False 
	
	
# 		start = end = -1	# start/end timestamp for current line: -1 indicates uninitialized
# 		nword = 0;	# number of pronunciation words in current line so far 
# 		line = ''	# text of current line
# 		curr_speaker = ''	# speaker of current line
# 		status = -1	# status of current line: start: -1, continue: 0, end: 1
# 				
# 		for i, word in enumerate(words):
# 			if word['type'] == 'pronunciation':
# 				if getSpeaker(word['start'], word['end'], segments) != curr_speaker and curr_speaker != '':
# 					new_line = 0
# 			if new_line == 0:                  # 0 signifies ready for wrting in a new line. 
# 				if word['type'] == 'punctuation':
# 					line += word['text']
# 					continue
# 				else:
# 					new_line = 1
# 			if new_line == 1:                  #new_line= 1 signifies start wrting a new line
# 				out_file.write(writeTime(start, end))
# 				out_file.write(writeLine(curr_speaker,line))
# 				out_file.write(writeEmptyLine())
# 				line = ''
# 				new_line = -1		
# 			
# 			if len(line) == 0:
# 				start = word['start'] 
# 			line += ' '+word['text']
# 			if 'end' in word:
# 				end = word['end']
# 				curr_speaker = getSpeaker(word['start'], word['end'], segments)
# 			if word['type'] == 'punctuation' or len(line) == max_words:
# 				new_line = 0
#		
# 	#This function gets the current speaker from the segmenattion file
# 	def getSpeaker(start, end, segments):
# 		speaker_found = 'No Speaker'
# 		for segment in segments:
# 			if segment['start'] <= start and segment['end'] >= end:
# 				if 'speakerLabel' in segment:	# speakerLabel is optional field in segments
# 					speaker_found = segment['speakerLabel']
# 				break
# 		return speaker_found
#
# def getOutput():
# 	#This function writes the content to the vtt output
# 	return output	

if __name__ == "__main__":
	main()
		
