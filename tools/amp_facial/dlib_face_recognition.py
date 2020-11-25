#!/usr/bin/env python3

import configparser
import json
import os
import os.path
import sys
import shutil
import face_recognition
import cv2
import pickle
# from tqdm.notebook import tqdm
import dlib_face_training
from test.test_tracemalloc import frame

sys.path.insert(0, os.path.abspath('../../../../../tools/amp_schema'))
from face_recognition import FaceRecognition, FaceRecognitionMedia, FaceRecognitionMediaResolution, FaceRecognitionFrame, FaceRecognitionFrameObject, FaceRecognitionFrameObjectScore, FaceRecognitionFrameObjectVertices


FR_TRAINED_MODEL_SUFFIX = ".frt"
FR_SCORE_TYPE = "confidence"
FR_DEFAULT_TOLERANCE = 0.6


# Usage: dlib_face_recognition.py root_dir, input_video, training_photos, reuse_trained, tolerance, amp_faces 
def main():
    (root_dir, input_video, training_photos, reuse_trained, tolerance, amp_faces) = sys.argv[1:6]
    if not tolerance:
        tolerance = FR_DEFAULT_TOLERANCE
    
    # if reuse_trained is set to true, retrieve previous training results
    if reuse_trained:
        known_names, known_faces = get_trained_results(training_photos)
              
    # if no valid previous trained results is available, do the training
    if (known_names == [] or known_faces == []):
        known_names, known_faces = train_faces(training_photos)
              
    # run face recognition on the given video using the trained results at the given tolerance level
    fr_result = recognize_faces(input_video, known_names, known_faces, tolerance)
    
    # save the recognized_faces in the standard AMP Face JSON file
    save_faces(fr_result, amp_faces)
    
    
# Recognize faces in the input_video, given the known_names and known_faces from trained FR model, and the tolerance;
# return a list of identified names and faces. 
def recognized_faces(input_video, known_names, known_faces, tolerance):
    print ("Starting face recognition on video " + input_video + " with tolerance " + tolerance)
    
    # load the input video file with cv2
    cv2_video = cv2.VideoCapture(input_video)
    frame_count = cv2_video.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = cv2_video.get(cv2.CAP_PROP_FPS)

    # create AMP FR result object 
    fr_result = FaceRecognition()
    fr_result.media = FaceRecognitionMedia()
    fr_result.media.filename = input_video
    fr_result.media.duration = float(frame_count) / float(fps)
    fr_result.media.frameRate = fps
    fr_result.media.numFrames = frame_count
    fr_result.media.resolution = FaceRecognitionMediaResolution()
    fr_result.media.resolution.width = cv2_video.get(cv2.CAP_PROP_FRAME_WIDTH)
    fr_result.media.resolution.height = cv2_video.get(cv2.CAP_PROP_FRAME_HEIGHT)
    fr_result.frames = [];
    
    print ("Successfully loaded video " + input_video + ", total number of frames: " + frame_count)

    # process frames in the video
    for frame_number in range(0, frame_count):
        # grab a single frame of video
        ret, cv2_frame = cv2_video.read()
      
        # quit when the input video file ends
        if not ret:
            break

        # skip FR in every fps frames, i.e. take only one frame per second
        if frame_number % fps != 0:
            continue
        
        # convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_frame = cv2_frame[:, :, ::-1]

        # find all the faces and face encodings in the current frame of video
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        # if no face found in the current frame, skip it and move on to the next one
        if (not face_encodings or len(face_encodings) == 0):
            continue

        # otherwise create an AMP FR frame object in the AMP FR result object
        frame = FaceRecognitionFrame()
        frame.start = float(frame_number) / float(fps)
        frame.objects = []
         
        print ("Found " + len(face_encodings) + " faces in frame # " + frame_number)
        
        # initialize index of the current face_location or face_encoding among all faces found in the frame 
        location_index = 0;

        # for each face in the frame, see if it's a match for any known faces, if so use the first match
        for face_encoding in face_encodings:  
            matches = face_recognition.compare_faces(known_faces, face_encoding, tolerance)
            if any(matches):
                # find the index of the first match in known_faces
                matched_index = matches.index(True)
                
                # create an AMP FR face object in the AMP FR frame
                object = FaceRecognitionFrameObject()
                object.name = known_names[matched_index]
                object.score = FaceRecognitionFrameObjectScore()
                object.score.type = FR_SCORE_TYPE
                object.score.value = 1.0 - tolerance              
                object.vertices = FaceRecognitionFrameObjectVertices()
                object.vertices.ymin, object.vertices.xmin, object.vertices.ymax, object.vertices.xmax = face_locations[i]
                
                # add face object to the list
                frame.objects.append(object)
            
                print ("Recognized face of " + object.name + " in frame # " + frame_number)

            # move on to the next face in the frame
            location_index += 1          

        # if any face in the frame is recognized as a known face, add the current frame to AMP FR result
        if (frame and len(frame.objects) > 0):
            fr_result.frames.append(frame)
            
    # done with all frames, release resource 
    cv2_video.release()
    cv2.destroyAllWindows()
    print ("Completed face recognition on video " + input_video)

    # save FR result into AMP Face JSON file
    with open(amp_faces, 'w') as fr_file:
        json.dump(fr_result, fr_file, default = lambda x: x.__dict__)
    print ("Saved face recognition result to file " + amp_faces)
                        

# Serialize the given object and write it to given output_file
def write_json_file(object, output_file):
    # Serialize the object
    with open(output_file, 'w') as outfile:
        json.dump(object, outfile, default = lambda x: x.__dict__)
        
                        
# # Convert number of frames to formatted time.
# def frame_to_time(frames, fps):
#     h =  int(frames/(3600*fps))
#     m = int(frames/(60*fps) % 60)
#     s = int(frames/fps % 60)
#     return ("%02d:%02d:%02d" % ( h, m, s))
# 
# 
# # Convert formatted time to number of frames.
# def time_to_frame(time, fps):
#     h,m,s = time.split(":")
#     seconds = (int(h)*3600) + (int(m)*60) + int(s)
#     return seconds*fps
# 
# 
# # Convert formatted time to number of seconds.
# def time_to_second(time):
#     h,m,s = time.split(":")
#     return (int(h)*3600) + (int(m)*60) + int(s)
# 
# # Convert number of seconds to formatted time.
# def second_to_time(seconds):
#     h = seconds/3600
#     m = (seconds/60) % 60
#     s = seconds % 60
#     return ("%02d:%02d:%02d" % ( h, m, s))    
    

if __name__ == "__main__":
    main()    
