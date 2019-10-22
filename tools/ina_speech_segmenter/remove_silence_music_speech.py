#!/usr/bin/env python3


import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from shutil import copyfile

sys.path.insert(0, os.path.abspath('../../../../../tools/amp_json_schema'))

from segmentation_schema import SegmentationSchema

# Seconds to buffer beginning and end of audio segments by
buffer = 1

def main():
	(input_file, input_segmentation_json, remove_type, output_file, kept_segments_file) = sys.argv[1:6]

	# Turn segmentation json file into segmentation object
	with open(input_segmentation_json, 'r') as file:
		seg_data = SegmentationSchema().from_json(json.load(file))
	
	# Remove silence and get a list of kept segments
	kept_segments = remove_silence(remove_type, seg_data, input_file, output_file)

	# Write kept segments to json file
	write_kept_segments_json(kept_segments, kept_segments_file)
	exit(0)

# Given segmentation data, an audio file, and output file, remove silence
def remove_silence(remove_type, seg_data, filename, output_file):
	kept_segments = {}
	start_block = -1  # Beginning of a speech segment
	previous_end = 0  # Last end of a speech segment
	segments = 0  # Num of speech segments

	# For each segment, calculate the blocks of speech segments
	for s in seg_data.segments:

		if should_remove_segment(remove_type, s, start_block) == True:
			# If we have catalogued speech, create a segment from that chunk
			if previous_end > 0 and start_block >= 0:
				kept_segment = create_audio_part(filename, start_block, previous_end, segments, seg_data.media.duration)
				kept_segments.update(kept_segment)
				# Reset the variables
				start_block = -1
				previous_end = 0
				segments += 1
		elif s.label not in ["silence", remove_type]:
			# If this is a new block, mark the start
			if start_block < 0:
				start_block = s.start
			previous_end = s.end

	# If we reached the end and still have an open block of speech, output it
	if previous_end > 0:
		kept_segment = create_audio_part(filename, start_block, previous_end, segments, seg_data.media.duration)
		kept_segments.update(kept_segment)

	# Concetenate each of the individual parts into one audio file of speech
	concat_files(segments, output_file)
	return kept_segments

# Get the start offset after removing the buffer
def get_start_with_buffer(start):
	if start <= buffer:
		return 0
	else:
		return start - buffer

def get_end_with_buffer(end, file_duration):
	if end + buffer > file_duration:
		return file_duration
	else:
		return end + buffer

# Given a start and end offset, create a segment of audio 
def create_audio_part(input_file, start, end, segment, file_duration):
	
	# Create a temporary file name
	tmp_filename = "tmp_" + str(segment) + ".wav"

	start_offset = get_start_with_buffer(start)

	# Convert the seconds to a timestamp
	start_str = time.strftime('%H:%M:%S', time.gmtime(start_offset))

	end_offset = get_end_with_buffer(end, file_duration)

	# Calculate duration of segment convert it to a timestamp
	duration = (end_offset - start_offset)
	duration_str = time.strftime('%H:%M:%S', time.gmtime(duration))

	print("Removeing segment starting at " + start_str + " for " + duration_str)

	# Execute ffmpeg command to split of the segment
	ffmpeg_out = subprocess.Popen(['ffmpeg', '-i', input_file, '-ss', start_str, '-t', duration_str, '-acodec', 'copy', tmp_filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	
	stdout,stderr = ffmpeg_out.communicate()

	# Print the output
	print("Creating audio segment " + str(segment))
	print(stdout)
	print(stderr)

	return {start_offset : end_offset}

# Take each of the individual parts, create one larger file and copy it to the destination file
def concat_files(segments, output_file):
	# Create the ffmpeg command, adding an input file for each segment created
	if segments > 1:
		ffmpegCmd = ['ffmpeg']
		for s in range(0, segments):
			this_segment_name = "tmp_" + str(s) + ".wav"
			ffmpegCmd.append("-i")
			ffmpegCmd.append(this_segment_name)
		ffmpegCmd.extend(['-filter_complex', "[0:0][1:0][2:0]concat=n=" + str(segments) + ":v=0:a=1[out]", "-map", "[out]", "output.wav"])

		# Run ffmpeg 
		ffmpeg_out = subprocess.Popen(ffmpegCmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		stdout, stderr = ffmpeg_out.communicate()

		# Print the output
		print("Creating complete audio")
		print(stdout)
		print(stderr)

		# Copy the temporary result to the final destination
		copyfile("output.wav", output_file)
	else:
		# Only have one segment, copy it to output file
		copyfile("tmp_0.wav", output_file)
	# Cleanup temp files
	cleanup_files(segments)

def cleanup_files(segments):
	# Remove concatenated temporary file
	if os.path.exists("output.wav"):
		os.remove("output.wav") 
	# Remove each individual part if it exists
	for s in range(0, segments):
		this_segment_name = "tmp_" + str(s) + ".wav"
		if os.path.exists(this_segment_name):
			os.remove(this_segment_name)

def should_remove_segment(remove_type, segment, start_block):
	if (segment.label == "silence" or segment.label == remove_type):
		duration = segment.end - segment.start
		# If it is the middle of the file, account for buffers on both the start and end of the file
		if start_block > 0 and duration > (buffer*2):
			return True
		# If it is the beginning of the file, only account for buffer at the end of the file
		if start_block == 0 and duration > buffer:
			return True
	return False

# Serialize obj and write it to output file
def write_kept_segments_json(kept_segments, kept_segments_file):
	# Serialize the segmentation object
	with open(kept_segments_file, 'w') as outfile:
		json.dump(kept_segments, outfile, default=lambda x: x.__dict__)

if __name__ == "__main__":
	main()
