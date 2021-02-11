#!/usr/bin/env python3
import json
import sys
import os
import time

MIN_WORD_COUNT = 6	# minimum number of words per line
MAX_WORD_COUNT = 10	# maximum number of words per line
MIN_SEGMENT_GAP = 5.00	# minimum gap in seconds between segment for speaker switch

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

	# initialize status before first (new) line
	nword = 0	# number of pronunciation words in current line so far 
	curseg = 0	# index of current segment (to get current speaker)
	start = end = 0	# start/end timestamp for current line
	line = ''	# text of current line	
	newline = False	# true if current word is the start of a new line
				
	# process all words which are in time order
	for i, word in enumerate(words):
		# find the next segment the current word belongs to
		# note that if segments list is empty, nextseg/curseg will stay at 0
		nextseg = findWordSegment(word, segments, curseg)

		# the current word should be the start of a new line if it's pronunciation and  
		if word['type'] == 'pronunciation' and (
			# no previous line, this is the very first word, or
			nword == 0 or
			# there are already 10 words in current line, or
			nword == MAX_WORD_COUNT or
			# there are at least 6 words plus punctuation in current line, or	
			nword >= MIN_WORD_COUNT and words[i-1]['type'] == 'punctuation' or
			# it's from a new speaker
			speakSwitched(segments, curseg, nextseg, MIN_SEGMENT_GAP) ):
			newline = True
		
		# starting a new line	
		if newline:
			# write the current line (if any word) before starting a new line
			# note that punctuation words before the very first pronunciation word (in which case nword = 0) will be ignored 
			if (nword > 0):
				out_file.write(writeEmptyLine())
				out_file.write(writeTime(start, end))
				out_file.write(writeLine(getSegmentSpeaker(segments, curseg), line))
			# reset status for the new line
			nword = 0 
			# new line always starts with a pronunciation, use its start time as line start time
			start = word['start']	 
			line = ''	
			newline = False
			
		# now we can move current segment pointer to next if they are different	
		if nextseg > curseg:
			curseg = nextseg
		
		# update current line with current word
		if word['type'] == 'pronunciation':
			nword += 1
			# record potential line end time from current pronunciation (can't end time of last word on a line since it may be punctuation)
			end = word['end']
			line += ' ' + word['text']	# space before pronunciation
		else:
			line += word['text']	# no space before punctuation
				
	# write the last line to file if any word in it; note that 
	# the last line should always contain some pronunciation words unless the whole words list contains no pronunciation
	if nword > 0:
		out_file.write(writeEmptyLine())
		out_file.write(writeTime(start, end))
		out_file.write(writeLine(getSegmentSpeaker(segments, curseg), line))
	out_file.close()
		
# Find the index of the next segment among the given segments to which the given word belongs to, starting at the given (current) 
# segment index (always >= 0). A word belongs to a segment if its timestamp is within the segment's time range,  
def findWordSegment(word, segments, curseg):
	# non pronunciation word always stays with the current segment
	if word['type'] != 'pronunciation':
		return curseg		
	# if we are already beyond segments index bound, stay with current segment
	if curseg >= len(segments):
		return curseg
	# if word start time is within current segment end time, stay with current segment 
	if word['start'] < segments[curseg]['end']:
		return curseg
	
	# otherwise, scan the following segments for the next containing one, based on following assumptions: 
	# need to scan as some segments may not contain any word (otherwise we can just return the next segment); 
	# can scan segments sequentially as segments are in time order;
	# instead of requiring word's [start, end] time within segment's [start, end] time,
	# only check word's start time against segment's end time (i.e. consider segments continuous in time), 
	# to ensure each word fall into some segment, and handle well even when word crosses segment boundary (unlikely) 
	nextseg = curseg + 1
	while nextseg < len(segments) and word['start'] >= segments[nextseg]['end']:
		nextseg += 1		
	return nextseg
	
# Returns true if the given current segment and next segment have different speakers, 
# or having same speakers but the time gap between the segments are greater than the given threshold.
def speakSwitched(segments, curseg, nextseg, threshold):	
	curspeaker = getSegmentSpeaker(segments, curseg)
	nextspeaker = getSegmentSpeaker(segments, nextseg)
	curend = getSegmentTime(segments, curseg, False)
	nextstart = getSegmentTime(segments, nextseg, True) 
	if curspeaker != nextspeaker or (nextstart - curend > threshold):
		return True
	else:
		return False
		
# Gets the speaker of the given segments[iseg]. 	
def getSegmentSpeaker(segments, iseg):
	if iseg < 0 or iseg >= len(segments):
		return "No Speaker"
	if 'speakerLabel' in segments[iseg]:
		return segments[iseg]['speakerLabel']
	else:
		return "Unlabeled Speaker"
	
# Gets the start/end timestamp of the given segments[iseg]. 	
def getSegmentTime(segments, iseg,  forstart):
	if iseg < 0 or iseg >= len(segments):
		return 0
	if forstart:		
		return segments[iseg]['start']
	else:
		return segments[iseg]['end']
	
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
	return str(convert(start_time))+" --> "+str(convert(end_time))+"\n"
	
def convert(seconds): 
    return time.strftime("%H:%M:%S", time.gmtime(seconds)) 
   
   
if __name__ == "__main__":
	main()
		
