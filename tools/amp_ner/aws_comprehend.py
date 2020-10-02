#!/usr/bin/env python3

import gzip
import os
import os.path
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
import time
import tarfile
from datetime import datetime
import boto3

sys.path.insert(0, os.path.abspath('../../../../../tools/amp_schema'))
from entity_extraction import EntityExtraction, EntityExtractionMedia, EntityExtractionEntity
from speech_to_text import SpeechToText, SpeechToTextMedia, SpeechToTextResult, SpeechToTextScore, SpeechToTextWord

def main():
    (input_file, json_file, bucketName, dataAccessRoleArn) = sys.argv[1:5]

    # Read a list of categories to ignore when outputting entity list
    ignore_cats_list = list()

    if len(sys.argv) > 5:
        print("ignore cats:" + sys.argv[5])
        ignore_cats_list = split_ignore_list(sys.argv[5])

    # Variable declaration
    outputS3Uri = 's3://' + bucketName + '/'
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    jobName = 'AwsComprehend-' + timestamp + ".json"
    inputS3Uri = outputS3Uri + jobName

    # Get the transcript text from the input file
    with open(input_file, 'r') as file:
        stt = SpeechToText().from_json(json.load(file))
    
    # Create the ner object
    ner = EntityExtraction()

    # Add the media information
    if stt is None or stt.results is None:
        mediaLength = 0
    else:
        mediaLength = len(stt.results.transcript)

    # If we have a blank file, don't error.  Create another blank json file to pass to the next process
    if mediaLength == 0:
        ner.media = EntityExtractionMedia(mediaLength, input_file)
        write_json_file(ner, json_file)
        exit(0)
    
    # Create a temp file to upload to S3
    tmpfile = create_temp_transcript_file(jobName, stt.results.transcript)

    # Copy the temporary text file to S3
    copy_to_s3(tmpfile.name, bucketName, jobName)

    # Make call to aws comprehend
    output_uri = run_comprehend_job(jobName, inputS3Uri, outputS3Uri, dataAccessRoleArn)

    uncompressed_file = download_from_s3(output_uri, outputS3Uri, bucketName)
    
    if uncompressed_file is None:
        exit(1)

    comprehend_data = read_comprehend_response(uncompressed_file)
    
    ner.media = EntityExtractionMedia(mediaLength, input_file)

    # Variables for filling time offsets based on speech to text
    lastPos = 0  # Iterator to keep track of location in STT word
    sttWords = len(stt.results.words) # Number of STT words

    if 'Entities' in comprehend_data.keys():
        for entity in comprehend_data["Entities"]:
            entity_type = entity["Type"]
            # Start and end time offsets
            start = None
            end = None
            text = entity["Text"]

            # Split the entity into an array of words based on whitespace
            entityParts = text.split()

            # For each word in the entity, find the corresponding word in the STT word list
            for entityPart in entityParts:
                for wordPos in range(lastPos, sttWords):
                    # If it matches, set the time offset.
                    word = stt.results.words[wordPos]
                    if clean_entity_word(word.text) == entityPart:
                        # Keep track of last position to save iterations
                        lastPos = wordPos
                        # Set start if we haven't set it yet
                        if start == None:
                            start = word.start
                        end = word.end
                        break
                    else:
                        start = None
                        end = None
            
            if clean_text(entity_type) not in ignore_cats_list and start is not None:
                ner.addEntity(entity_type, text, None, None, "relevance", float(entity["Score"]), start, None)  #AMP-636 removed startOffset=endOffset=end=None

    #Write the json file
    write_json_file(ner, json_file)

    #Cleanup temp files
    safe_delete(uncompressed_file)
    safe_delete(tmpfile.name)

def create_temp_transcript_file(jobName, transcript):
    # Dump the transcript text to a text file so it can be uploaded to S3
    tempdir = tempfile.gettempdir()
    with open(tempdir + jobName, 'w') as tmpfile:
        tmpfile.write(transcript)
    return tmpfile

def clean_entity_word(entity_word):
    cleaned_word = entity_word 
    if(entity_word.endswith('\'s')):
        cleaned_word = entity_word.replace('\'s', '')
    return cleaned_word
    
# Serialize obj and write it to output file
def write_json_file(obj, output_file):
    # Serialize the object
    with open(output_file, 'w') as outfile:
        json.dump(obj, outfile, default=lambda x: x.__dict__)

def download_from_s3(output_uri, base_uri, bucket_name):
    tarFileName = "comprehend_output.tar.gz"
    output_key = output_uri.replace(base_uri, '')
    s3_client = boto3.client('s3')

    # get the file from s3
    with open(tarFileName, 'wb') as f:
        s3_client.download_fileobj(bucket_name, output_key, f)

    # extract the contents of the .tar.gz file
    tar = tarfile.open(tarFileName)
    test = tar.getmembers()
    tar.extractall()
    tar.close()

    safe_delete(tarFileName)

    if len(test) > 0:
        return test[0].name
    else:
        return None

def run_comprehend_job(jobName, inputS3Uri, outputS3Uri, dataAccessRoleArn):
    comprehend = boto3.client(service_name='comprehend', region_name='us-east-2')
    print("input uri:" + inputS3Uri)
    response = comprehend.start_entities_detection_job(
        InputDataConfig={
            'S3Uri': inputS3Uri,
            "InputFormat": "ONE_DOC_PER_FILE"
        },
        OutputDataConfig={
            'S3Uri': outputS3Uri
        },
        DataAccessRoleArn=dataAccessRoleArn,
        JobName=jobName,
        LanguageCode='en'
    )
    
    status = ''
    output_uri = ''

    while status not in ('COMPLETED','FAILED', 'STOP_REQUESTED','STOPPED'):
        jobStatusResponse = comprehend.describe_entities_detection_job(
            JobId=response['JobId']
        )
        if 'EntitiesDetectionJobProperties' in jobStatusResponse.keys():
            print(jobStatusResponse)
            status = jobStatusResponse['EntitiesDetectionJobProperties']['JobStatus']
            output_uri = jobStatusResponse['EntitiesDetectionJobProperties']['OutputDataConfig']['S3Uri']
            print(status)
            time.sleep(20)
    
    return output_uri

# Read a list of categories to ignore
def read_ignore_list(ignore_list_filename):
    print("Reading list")
    ignore_cats_list = list()
    f = open(ignore_list_filename, "r")
    # For each value in the comma separated list.  Standardize text
    for val in f.read().split(","):
        ignore_cats_list.append(clean_text(val))
    print(ignore_cats_list)
    return ignore_cats_list

# Split a comma separated string, standardize input, and return list
def split_ignore_list(ignore_list_string):
    to_return = list()
    ignore_cats_list = ignore_list_string.split(',')
    for cat in ignore_cats_list:
        to_return.append(clean_text(cat))
    return to_return

def clean_text(text):
    return text.lower().strip()

def read_comprehend_response(reponse_filename):
    with open(reponse_filename) as json_file:
        data = json.load(json_file)
    return data

def safe_delete(filename):
    try:
        if os.path.exists(filename):
            print("removing: " + filename)
            os.remove(filename)
    except Exception as e:
        print(e)
        return False
    return True

def copy_to_s3(input_file, bucket, jobname):
    s3_client = boto3.client('s3')
    try:
        print('before response')
        response = s3_client.upload_file(input_file, bucket, jobname)
        print('after response')
    except Exception as e:
        print(e)
        return False
    return True

if __name__ == "__main__":
    main()
