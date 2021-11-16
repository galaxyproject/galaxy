#!/usr/bin/env python3

import json
import os
import os.path
import shutil
import subprocess
import sys
import tempfile
import uuid
import traceback

import mgm_utils


def main():
	(root_dir, speech_audio, amp_transcript_unaligned, gentle_transcript, amp_transcript_aligned) = sys.argv[1:6]
	exception = False
	try:
		# prefix random id to original filenames to ensure uniqueness for the tmp Gentle singularity input files 
		id = str(uuid.uuid4())
		tmp_speech_audio_name = "gentle-" + id + "-" + os.path.basename(speech_audio)
		tmp_amp_transcript_unaligned_name = "gentle-" + id + "-" + os.path.basename(amp_transcript_unaligned)
		tmp_gentle_transcript_name = "gentle-" + id + "-" + os.path.basename(gentle_transcript)

		# define directory accessible to singularity container
		tmpdir = '/tmp'

		# define tmp filepaths
		tmp_speech_audio = f"{tmpdir}/{tmp_speech_audio_name}"
		tmp_amp_transcript_unaligned = f"{tmpdir}/{tmp_amp_transcript_unaligned_name}"
		tmp_gentle_transcript = f"{tmpdir}/{tmp_gentle_transcript_name}"

		# Load the audio and transcript inputs into tmp dir and run gentle
		with open(amp_transcript_unaligned, "r") as amp_transcript_unaligned_file:
			amp_transcript_unaligned_json = json.load(amp_transcript_unaligned_file)

			# Write the transcript to an input file into gentle
			with open(tmp_amp_transcript_unaligned, "w") as tmp_amp_transcript_unaligned_file:
				tmp_amp_transcript_unaligned_file.write(amp_transcript_unaligned_json["results"]["transcript"])

			# Copy the audio file to a location accessible to the singularity container
			shutil.copy(speech_audio, tmp_speech_audio)

			# Run gentle
			print(f"Running Gentle... tmp_speech_audio: {tmp_speech_audio}, tmp_amp_transcript_unaligned: {tmp_amp_transcript_unaligned}, tmp_gentle_transcript: {tmp_gentle_transcript}")
			sif = mgm_utils.get_sif_dir(root_dir) + "/gentle_forced_alignment.sif"
			r = subprocess.run(["singularity", "run", sif, tmp_speech_audio, tmp_amp_transcript_unaligned, "-o", tmp_gentle_transcript], stdout=subprocess.PIPE)
			print(f"Finished running Gentle with return Code: {r.returncode}")

			# if Gentle completed in success, continue with transcript conversion
			if r.returncode == 0:
				# Copy the tmp Gentle output file to gentle_transcript
				shutil.copy(tmp_gentle_transcript, gentle_transcript)
	
				print("Creating AMP transcript aligned...")
				gentle_transcript_to_amp_transcript(gentle_transcript, amp_transcript_unaligned_json, amp_transcript_aligned)

			exit(r.returncode)
	except Exception as e:
		print("Exception while running Gentle:")
		traceback.print_exc()
		exit(1)


# Convert Gentle output transcript JSON file to AMP Transcript JSON file.
def gentle_transcript_to_amp_transcript(gentle_transcript, amp_transcript_unaligned_json, amp_transcript_aligned):
	with open(gentle_transcript, "r") as gentle_transcript_file:		
		# read gentle_transcript and initialize pointers
		gentle_transcript_json = json.load(gentle_transcript_file)
		transcript = gentle_transcript_json["transcript"]
		gwords = gentle_transcript_json["words"]
		uwords = amp_transcript_unaligned_json["results"]["words"]
		duration = amp_transcript_unaligned_json["media"]["duration"]
		words = list()
		next = -1	# index of next success match
		preoffset = 0	# end offset of previous word

		# initialize amp_transcript_aligned_json
		amp_transcript_aligned_json = dict()
		amp_transcript_aligned_json["media"] = amp_transcript_unaligned_json["media"]
		amp_transcript_aligned_json["results"] = dict()
		amp_transcript_aligned_json["results"]["transcript"] = transcript
		amp_transcript_aligned_json["results"]["words"] = words	
		
		# populate amp_transcript_aligned_json words list, based on gentle_transcript words list
		for gi in range(0, len(gwords)):
			# if current index is beyond the last found next successful alignment, then
			# find the new next success and the interval between previous success
			if gi > next:
				[last, next, lastend, interval] = find_next_success(gwords, gi, duration)
									
			# if current word is the next success, use the aligned timestamp, and default confidence 1.0
			if gi == next:
				start = gwords[gi]["start"]
				end = gwords[gi]["end"]
				confidence = 1.0
			# otherwise current word is unmatched, use same start/end timestamp as the last success time 
			# accumulated with the interval between the last-next alignment, and default confidence 0.0
			else:	# 0 <= gi < next
				start = end = lastend + interval * (gi - last)				
				confidence = 0.0
			
			# insert punctuations between the current and previous word if any, based on their offsets;
			# this is needed as Gentle doen't include punctuations in the words list, but the transcript does
			[preoffset, curoffset] = insert_punctuations(words, gwords, gi, preoffset, transcript)
				
			# append the current Gentle word to the AMP words list
			words.append({
				"type": "pronunciation", 
				"start": start, 
				"end": end, 
				"text": gwords[gi]["word"],
				"offset": curoffset,
				"score": {
					"type": "confidence", 
					"scoreValue": confidence,
				},
			})							
			
		# append punctuations after the last word if any text left
		[preoffset, curoffset] = insert_punctuations(words, gwords, gi, preoffset, transcript)
		print(f"Successfully added {len(words)} words into AMP aligned transcript, including {len(gwords)} words from Gentle words, and {len(words)-len(gwords)} punctuations inserted from Gentle transcript.")
		 	
		# update words confidence in amp_transcript_aligned_json, based on amp_transcript_unaligned_json words
		updated = update_confidence(words, uwords)
		print(f"Successfully updated confidence for {updated} words in AMP aligned transcript.")
		
		# write final amp_transcript_aligned_json to file
		mgm_utils.write_json_file(amp_transcript_aligned_json, amp_transcript_aligned)
		
		
# Find the next success match in the given words list starting at the given current index, return the last and next match index,
# as well as the end time of the last match and the average time interval between the last and next match:
# if next success is found, set next to its index, 
# If the next match is the current word, set interval to None;
# If the current index is 0, use 0 as the last match end timestamp;
# if no next match is found, use the given duration as the next match start timestamp. 
def find_next_success(words, current, duration):	
	# start with timestamp 0 with first word
	if current == 0:
		lastend = 0.0
	# otherwise the previous word must be the last success
	else:
		lastend = words[current-1]["end"]
		
	# search for the next success	
	next = None	
	length = len(words)	
	for i in range(current, length):
		# found next success
		if words[i]["case"] == "success":
			next = i
			# no need for interval is current word is success
			if next == current:
				interval = None
			# otherwise compute interval by distributing timestamps evenly between two success words	
			else:
				interval = (words[next]["start"] - lastend) / (next - current + 1)
			break;		
		
	# if next success not found, set it to the index boundary
	if next == None:
		next = length
		interval = (duration - lastend) / (next - current + 1)	
			
	# since we only look for next success at the end of the last success, the previous word must be the last success
	last = current - 1	
	if (next > current):
		print(f"Use timestamps with interval {interval} starting at time {lastend} for unmatached Gentle words between index {last} and {next}.")
	return [last, next, lastend, interval]
		
		
# Insert punctuations to the given AMP words list, if there is any in the given transcript between the word 
# at the given current index and the given previous word offset in the given Gentle words list;
# return the the end offset for future punctuation insert and current word start offset.
def insert_punctuations(words, gwords, gi, preoffset, transcript):	
	lenw = len(gwords)
	lent = len(transcript)
	
	# if current word index is within boundary, punctuation end boundary should be the start of the current word
	if gi < lenw:		
		curoffset = gwords[gi]["startOffset"]
		gword = gwords[gi]["word"]
	# otherwise it should be the end of transcript
	else:
		curoffset = lent
		gword = "EOF"
			
	# scan transcript between end of previous word and start of current word		
	for i in range(preoffset, curoffset):
		text = transcript[i]
		# only insert non-space chars, which should be punctuations
		if text != ' ':
			words.append({
				"type": "punctuation",
				"text": text,
				"offset": i,
				"score": {
					"type": "confidence",
					"scoreValue": 0.0,
				},
			})
			print(f"Insert punctuation as AMP words[{len(words)-1}]={text} after Gentle words[{gi}]={gword}")

	# if current word is not the last one, future punctuation end boundary should be the end of the current word
	if gi < lenw:		
		preoffset = gwords[gi]["endOffset"]
	# otherwise it should be the end of transcript
	else:
		preoffset = lent

	# return end offset for next future punctuation and current word start offset
	return [preoffset, curoffset]


# Update word confidence in the given aligned words list, based on the given unaligned words list.
def update_confidence(words, uwords):
	alen = len(words)
	ulen = len(uwords)
	if alen != ulen:
		print (f"Warning: The algined words list length = {alen} does not equal the unaligned words list length {ulen}.")	
	
	ui = -1
	i = si = 0
	stexts = list()
	updated = 0
	
	for word in words:
		# AMP transcript words list is supposed to contain one word in each element, 
		# but it's currently not the case for HMGM corrected transcript; thus we need to split multi-words text
		# if we reach the end of the last split multi-words sublist, try splitting the current word
		if si == len(stexts):	
			# reset si and increment ui	
			si = 0
			ui = ui + 1
			
			# check boundary of unaligned words
			if ui == len(uwords):
				print(f"Warning: Reaching the end of unaligned words at length {ui} while updating confidence for aligned word {word} at index {i}.")
			
			# check current word
			type = uwords[ui]["type"]
			stext = uwords[ui]["text"]
			
			# for pronunciation, split by space
			if (type == "pronunciation"):
				stexts = stext.split()
			# for punctuation, split into each char
			else:
				stexts = list(stext)
		
		# compare aligned/unaligned words and update confidence
		text = word["text"]
		if text != stexts[si]:
			print (f"Warning: Algined words[{i}] = {text} does not match unaligned words[{ui}][{si}] = {stexts[si]}, using default confidence for it.")
		elif "score" in uwords[ui]:
			word["score"]["scoreValue"] = uwords[ui]["score"]["scoreValue"]
			updated = updated + 1
			
		# move on to the next word in both the unaligned multi-word sublist and the aligned words list
		si = si + 1	
		i = i + 1

	return updated

		
if __name__ == "__main__":
	main()

# 	amp_transcript_unaligned = "amp_un.json"
# 	gentle_transcript = "amp_gen.json"
# 	amp_transcript_aligned = "amp_al.json"
#  	
# 	with open(amp_transcript_unaligned, "r") as amp_transcript_unaligned_file:
# 		amp_transcript_unaligned_json = json.load(amp_transcript_unaligned_file)
# 	gentle_transcript_to_amp_transcript(gentle_transcript, amp_transcript_unaligned_json, amp_transcript_aligned)