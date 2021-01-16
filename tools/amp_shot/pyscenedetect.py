#!/usr/bin/env python3

import sys
import os
import json
import datetime

# Standard PySceneDetect imports:
from scenedetect.video_manager import VideoManager
from scenedetect.scene_manager import SceneManager
# For caching detection metrics and saving/loading to a stats file
from scenedetect.stats_manager import StatsManager

# For content-aware scene detection:
from scenedetect.detectors.content_detector import ContentDetector


def main():
    (input_file, threshold, output_json, output_csv) = sys.argv[1:5]
    # Get a list of scenes as tuples (start, end) 
    if threshold is None or isinstance(threshold, int) == False:
        threshold = 30
        print("Setting threshold to default because it wasn't a valid integer")

    shots = find_shots(input_file, output_csv, threshold)

    # Print for debugging purposes
    for shot in shots:
        print("start: " + str(shot[0]) + "  end: " + str(shot[1]))
    
    # Convert the result to json, save the file
    convert_to_json(shots, input_file, output_json)

# Get the duration based on the last output
def get_duration(shots):
    tc = shots[len(shots) - 1][1].get_timecode()
    return get_seconds_from_timecode(tc)

# Find a list of shots using pyscenedetect api
def find_shots(video_path, stats_file, threshold):
    video_manager = VideoManager([video_path])
    stats_manager = StatsManager()
    # Construct our SceneManager and pass it our StatsManager.
    scene_manager = SceneManager(stats_manager)

    # Add ContentDetector algorithm (each detector's constructor
    # takes detector options, e.g. threshold).
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    base_timecode = video_manager.get_base_timecode()

    scene_list = []

    try:
        # Set downscale factor to improve processing speed.
        video_manager.set_downscale_factor()

        # Start video_manager.
        video_manager.start()

        # Perform scene detection on video_manager.
        scene_manager.detect_scenes(frame_source=video_manager)

        # Obtain list of detected scenes.
        scene_list = scene_manager.get_scene_list(base_timecode)

        # Each scene is a tuple of (start, end) FrameTimecodes.
        print('List of shots obtained:')
        for i, scene in enumerate(scene_list):
            print(
                'Scene %2d: Start %s / Frame %d, End %s / Frame %d' % (
                i+1,
                scene[0].get_timecode(), scene[0].get_frames(),
                scene[1].get_timecode(), scene[1].get_frames(),))

        # Save a list of stats to a csv
        if stats_manager.is_save_required():
            with open(stats_file, 'w') as stats_file:
                stats_manager.save_to_csv(stats_file, base_timecode)
    except Exception as err:
        print("Failed to find shots for: video: " + video_path + ", stats: " + stats_file + ", threshold: " + threshold, err)
        traceback.print_exc()        
    finally:
        video_manager.release()

    return scene_list

def get_seconds_from_timecode(time_string):
    dt = datetime.datetime.strptime(time_string, "%H:%M:%S.%f")
    a_timedelta = dt - datetime.datetime(1900, 1, 1)
    return a_timedelta.total_seconds()

def convert_to_json(shots, input_file, output_json):
    duration = get_duration(shots)
    outputDict = {
        "media": {
            "filename": input_file,
            "duration": duration
        },
        "shots": []
    }

    for s in shots:
        start_seconds = get_seconds_from_timecode(s[0].get_timecode())
        end_seconds = get_seconds_from_timecode(s[1].get_timecode())
        shot = {
            "type": "shot",
            "start": start_seconds,
            "end": end_seconds
        }
        outputDict["shots"].append(shot)

    with open(output_json, "w") as f:
        json.dump(outputDict, f)

    return outputDict
if __name__ == "__main__":
    main()