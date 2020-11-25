#!/usr/bin/env python3

import configparser
import os
import os.path
import shutil
import face_recognition
import cv2
import pickle
# from tqdm.notebook import tqdm
from zipfile import ZipFile


FR_TRAINED_MODEL_SUFFIX = ".frt"


# Train Face Recognition model with the provided training_photos,  
# save the results in a FRT model file with the same file path as training_photos, replacing extension .zip with .frt, 
# and return the trained results as a list of known_names and a list of known_faces encodings. 
# If training fails for any reason, exit in error, as face recognition won't work without training.
def train_faces(training_photos):
    # unzip training_photos
    facial_dir = get_facial_dir(root_dir)
    photos_dir = unzip_training_photos(training_photos, facial_dir)
    
    # get all persons photo directories
    person_dirs = [d for d in os.listdir(photos_dir) if os.path.isdir(os.path.join(image_dir, d))]

    # exit in error if no training data found    
    if (len(person_dirs) == 0):
        print("Training failed as training photos " + training_photos + " contains no sub-directory")
        exit(-1)
         
    known_names = []
    known_faces = []
    model = []
    
    # train the face photos in each person's photo directory
    for person_dir in person_dirs:
        name = person_dir   # each directory of photos is named after the person
        photos = [f for f in os.listdir(person_dir) if os.path.isfile(os.path.join(person_dir, f))]

        # skip the current person if no training photo found    
        if (len(photos) == 0):
            print("Skipped " + name + " as no training photo is found in the corresponding sub-directory")
            continue
        
        # train each photo in the sub-directory
        for photo in photos:
            path = os.path.join(person_dir, photo)
            face = face_recognition.load_image_file(path)
            face_bounding_boxes = face_recognition.face_locations(face) # Find faces in the photo

            # if training photo contains exactly one face
            # add face encoding for the current photo with the corresponding person name to the training model
            if len(face_bounding_boxes) == 1:
                face_enc = face_recognition.face_encodings(face)[0]
                known_names.append(name)
                known_faces.append(face_enc)
                model.append({"name": name, "encoding": face_enc})
                print("Added face encoding from " + photo + " for " + name + " to training model")
            # otherwise we can't use this photo
            else:
                print("Skipped " + photo + " for " + name + " as it contains no or more than one faces")
              
    # save the trained model into model file for future use, and clean up unzipped training photos
    save_trained_model(training_photos, model)
    cleanup_training_photos(photos_dir)
    
    # return the training results as known_names and known_faces if any
    if (len(known_faces) > 0):
        print("Successfully trained a total of " + len(known_faces)  + " faces for a total of " + len(person_dirs) + " people")
        return known_names, known_faces
    # otherwise exit in error as FR can't continue without trained results
    else:
        print("Failed training as there is no valid face detected in the given training photos " + training_photos)
        exit(-1)


# Get the file path of the trained model for the given training_photos.
def get_model_file(training_photos):
    # model file has the same file path as training_photos, but with extension .frt replacing .zip
    filename, file_extension = os.path.splitext(training_photos)
    model_file = os.path.join(filename, FR_TRAINED_MODEL_SUFFIX)
    return model_file
            

# Get the facial recognition working directory path for training and matching.
def get_facial_dir(root_dir):
    config = configparser.ConfigParser()
    config.read(root_dir + "/config/mgm.ini")    
    facial_dir = config["general"]["facial_dir"]
    return facial_dir

    
# Get the known faces names and encodings from previously trained face recognition model for training_photos.
def get_trained_results(training_photos):
    model_file = get_model_file(training_photos)
    known_names, known_faces = [], []
    try:
        if os.path.exists(model_file) and os.stat(model_file).st_size > 0:
            trained_model = pickle.load(open("model.p", "rb"))
            known_names = [face["name"] for face in trained_model]
            known_faces = [face["encoding"] for face in trained_model]
            print(len(known_names) + " previous trained faces are retrieved for training photos: " + training_photos)
        else:
            print("Could not find previously trained Face Recognition model: " + model_file + " for training photos: " + training_photos)
    except Exception as e:
        print("Failed to read previously trained Face Recognition model: " + model_file + " for training photos: " + training_photos, e)
    return known_names, known_faces
    
    
# Unzip training_photos zip file to a sub-directory with the same name as training_photos under facial_dir.
def unzip_training_photos(training_photos, facial_dir):
    dirname = os.path.splitext(os.path.basename(training_photos))[0]
    dirpath = os.path.join(facial_dir, dirname)
    # TODO
    # It's assumed that the zip file contains directories of photos; 
    # if instead the zip file contains a parent directory which contains sub-directories of photos, 
    # we should put the parent directory in faical_dir without creating another layer of parent dir.
    try:
        with ZipFile(training_photos, 'r') as zipobj:
            zipobj.extractall(dirpath)
        print("Successfully unziped training photos " + training_photos + " into directory " + dirpath)
        return dirpath
    except Exception as e:
        print ("Failed to unzip training photos: " + training_photos + "to working directory for facial recognition: " + facial_dir, e)
        exit(-1)
        # if training photos can't be unzipped, FR process can't continue, exit in error 
    

# Save the given face model trained from the training_photos.
def save_trained_model(training_photos, model):
    try:
        model_file = get_trained_results(training_photos)
        pickle.dump(model, open(model_file, "wb"))        
        print ("Successfully saved model trained from training photos " + training_photos + " to file " + model_file)
    except Exception as e:
        print ("Failed to save model trained from training photos " + training_photos + " to file " + model_file, e)
        # even if trained model fails to be saved, FR process can still continue
            

# Remove the temporary working directory for storing training photos.
def cleanup_training_photos(photos_dir):    
    try:
        shutil.rmtree(photos_dir)
        print("Successfully cleaned up training photos directory: " + photos_dir)
    except Exception as e:
        print ("Failed to clean up training photos directory: " + photos_dir, e)  
        # even if unzipped training photos fails to be cleaned up, FR process can still continue   
        
        