#!/usr/bin/env python3

import os
import os.path
import traceback
import shutil
import face_recognition
import cv2
import pickle
# from tqdm.notebook import tqdm
from zipfile import ZipFile

import mgm_utils

FR_TRAINED_MODEL_SUFFIX = ".frt"


# Train Face Recognition model with the provided training_photos, using the facial directory under the given root_dir,
# save the results in a FRT model file with the same file path as training_photos, replacing extension .zip with .frt, 
# and return the trained results as a list of known_names and a list of known_faces encodings. 
# If training fails for any reason, exit in error, as face recognition won't work without training.
def train_faces(training_photos, root_dir):
    # unzip training_photos
    facial_dir = get_facial_dir(root_dir)
    photos_dir = unzip_training_photos(training_photos, facial_dir)
    
    # get all persons photo directories
    person_dir_names = [d for d in os.listdir(photos_dir) if os.path.isdir(os.path.join(photos_dir, d))]

#     # exit in error if no training data found    
#     if (len(person_dir_names) == 0):
#         print("Training failed as training photos " + training_photos + " contains no sub-directory")
#         exit(1)
         
    known_names = []
    known_faces = []
    model = []
    
    # train the face photos in each person's photo directory,  which is named after the person
    for person_dir_name in person_dir_names:
        name = person_dir_name
        person_dir = os.path.join(photos_dir, person_dir_name)
        photos = [f for f in os.listdir(person_dir) if os.path.isfile(os.path.join(person_dir, f))]

#         # skip the current person if no training photo found    
#         if (len(photos) == 0):
#             print("Skipped " + name + " as no training photo is found in the corresponding photo directory " + person_dir)
#             continue

        # initialize total number of usable photos for the current person
        count = 0;
        
        # train each photo in the sub-directory
        for photo in photos:
            path = os.path.join(person_dir, photo)
            face = face_recognition.load_image_file(path)   # load photo image
            face_locations = face_recognition.face_locations(face) # find faces in the photo

            # if training photo contains exactly one face
            # add face encoding for the current photo with the corresponding person name to the training model
            if len(face_locations) == 1:
                face_encoding = face_recognition.face_encodings(face, face_locations)[0]
                known_names.append(name)
                known_faces.append(face_encoding)
                model.append({"name": name, "encoding": face_encoding})
                count = count + 1
                print("Added face encoding from " + photo + " for " + name + " to training model")
            # otherwise skip this photo
            else:
                print("Warning: Skipped " + photo + " for " + name + " as it contains no or more than one faces")
        
        if count == 0: 
            print("Warning: Did not find any usable training photo for " + name)
    
    # done with training, clean up unzipped photos, so no conflict when unzipping if the same photos are trained again 
    cleanup_training_photos(photos_dir)

    # if there is any trained face, save the trained model into the model file for future use, and
    # return the training results as known_names and known_faces
    if (len(model) > 0):       
        save_trained_model(model, training_photos)
        print(f"Successfully trained a total of {len(known_faces)} faces for a total of {len(person_dir_names)} people")
        return known_names, known_faces
    # otherwise report error and exit in error as FR can't continue without any trained results
    else:
        print("Error: Failed training as there is no valid face detected in the given training photos " + training_photos)
        exit(1)


# Get the known faces names and encodings from previously trained face recognition model for training_photos.
def retrieve_trained_results(training_photos):
    model_file = get_model_file(training_photos)
    known_names, known_faces = [], []
    try:
        if os.path.exists(model_file) and os.stat(model_file).st_size > 0:
            trained_model = pickle.load(open(model_file, "rb"))
            known_names = [face["name"] for face in trained_model]
            known_faces = [face["encoding"] for face in trained_model]
            print(f"Successfully retrieved a total of {len(known_faces)} previously trained faces from {model_file} for training photos {training_photos}")
        else:
            print("Warning: Could not find previously trained model " + model_file + " for training photos " + training_photos + ", will retrain")
    except Exception as e:
        print("Failed to read previously trained model from " + model_file + " for training photos " + training_photos + ", will retrain", e)
        traceback.print_exc()
    return known_names, known_faces
    
    
# Get the file path of the trained model for the given training_photos.
def get_model_file(training_photos):
    # model file has the same file path as training_photos, but with extension .frt replacing .zip
    filename, file_extension = os.path.splitext(training_photos)
    model_file = filename + FR_TRAINED_MODEL_SUFFIX
    return model_file
                

# Get the facial recognition working directory path for training and matching.
def get_facial_dir(root_dir):
    return mgm_utils.get_work_dir(root_dir, "facial_io")

    
# Unzip training_photos zip file to a directory with the same name as training_photos under facial_dir.
def unzip_training_photos(training_photos, facial_dir):
    dirname = os.path.splitext(os.path.basename(training_photos))[0]
    dirpath = os.path.join(facial_dir, dirname)
    # TODO
    # It's assumed that the zip file contains directories of photos; 
    # if instead the zip file contains a parent directory which contains sub-directories of photos, 
    # we should put the parent directory in faical_dir without creating another layer of parent directory.
    try:
        with ZipFile(training_photos, 'r') as zipobj:
            zipobj.extractall(dirpath)
        print("Successfully unziped training photos " + training_photos + " into directory " + dirpath)
        return dirpath
    except Exception as e:
        print("Failed to unzip training photos " + training_photos + "into directory " + dirpath, e)
        traceback.print_exc()
        exit(1)
        # if training photos can't be unzipped, FR process can't continue, exit in error 
    

# Save the given face model trained from the training_photos into the corresponding model file.
def save_trained_model(model, training_photos):
    try:
        model_file = get_model_file(training_photos)
        pickle.dump(model, open(model_file, "wb"))        
        print("Successfully saved model trained from training photos " + training_photos + " to file " + model_file)
    except Exception as e:
        print("Failed to save model trained from training photos " + training_photos + " to file " + model_file, e)
        traceback.print_exc()
        # do not exit since FR process can still continue even if trained model fails to be saved
            

# Remove the temporary working directory for storing training photos.
def cleanup_training_photos(photos_dir):    
    try:
        shutil.rmtree(photos_dir)
        print("Successfully cleaned up training photos directory " + photos_dir)
    except Exception as e:
        print("Failed to clean up training photos directory " + photos_dir, e)  
        traceback.print_exc()
        # do not exit since FR process can still continue even if unzipped training photos fails to be cleaned up   
        
        