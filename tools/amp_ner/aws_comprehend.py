#!/usr/bin/env python3

import os
import os.path
import json
import sys
import traceback
import tempfile
import string
import time
import tarfile
from datetime import datetime
import boto3

from entity_extraction import EntityExtraction, EntityExtractionMedia
from speech_to_text import SpeechToText

import mgm_utils

def main():
    (amp_transcript, aws_entities, amp_entities, bucketName, dataAccessRoleArn) = sys.argv[1:6]

    # Read a list of categories to ignore when outputting entity list
    ignore_cats_list = list()

    if len(sys.argv) > 6:
        print("ignore cats:" + sys.argv[6])
        ignore_cats_list = split_ignore_list(sys.argv[6])

    # Variable declaration
    outputS3Uri = 's3://' + bucketName + '/'
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    jobName = 'AwsComprehend-' + timestamp + ".json"
    inputS3Uri = outputS3Uri + jobName

    # Get the transcript text from the input file
    with open(amp_transcript, 'r') as file:
        stt = SpeechToText().from_json(json.load(file))

    # Create the ner object
    ner = EntityExtraction()

    # Add the media information
    if stt is None or stt.results is None:
        mediaLength = 0
    else:
        mediaLength = len(stt.results.transcript)
    ner.media = EntityExtractionMedia(mediaLength, amp_transcript)

    # If input transcript is empty, don't error, create an output json file with empty entity list to pass to the next process
    if mediaLength == 0:
        print(f"Input AMP Transcript Json file has empty transcript, output AMP NER Json will have empty emtities as well.")
        mgm_utils.write_json_file(ner, amp_entities)
        exit(0)

    # Create a temp file to upload to S3
    tmpfile = create_temp_transcript_file(jobName, stt.results.transcript)

    # Copy the temporary text file to S3
    copy_to_s3(tmpfile.name, bucketName, jobName)

    # Make call to aws comprehend
    output_uri = run_comprehend_job(jobName, inputS3Uri, outputS3Uri, dataAccessRoleArn)

    # download and decompress Comprehend output
    aws_entities = download_from_s3(output_uri, outputS3Uri, bucketName)
    if uncompressed_file is None:
        print(f"AWS Comprehend output downloaded and decompressed from {output_uri} doesn't exist.")
        exit(1)

    aws_entities_json = read_aws_entities(aws_entities)

    # Variables for filling time offsets based on speech to text
    lastPos = 0  # Iterator to keep track of location in STT word
    sttWords = len(stt.results.words) # Number of STT words

    if 'Entities' in aws_entities_json.keys():
        for entity in aws_entities_json["Entities"]:
            entity_type = entity["Type"]
            # Start and end time offsets
            start = None
            end = None
            text = entity["Text"]

            # Split the entity into an array of words based on whitespace
            entityParts = text.split()

            # For each word in the entity, find the corresponding word in the STT word list
            foundWordPos = None
            for entityPart in entityParts:
                for wordPos in range(lastPos, sttWords):
                    # If it matches, set the time offset.
                    word = stt.results.words[wordPos]
                    if clean_entity_word(word.text) == clean_entity_word(entityPart):
                        # Keep track of last position to save iterations
                        foundWordPos = wordPos
                        # Set start if we haven't set it yet
                        if start is None:
                            start = word.start
                        end = word.end
                        break
                    else:
                        start = None
                        end = None
                        foundWordPos = None

            if start is not None:
                lastPos = foundWordPos + 1
            else:
                print("Could not find word")
                print(text)
                print(entityParts)
                print(lastPos)
            if clean_text(entity_type) not in ignore_cats_list and start is not None:
                ner.addEntity(entity_type, text, None, None, "relevance", float(entity["Score"]), start, None)  #AMP-636 removed startOffset=endOffset=end=None

    # Write the json file
    mgm_utils.write_json_file(ner, amp_entities)

    # Cleanup temp files
    safe_delete(tmpfile.name)
    

def create_temp_transcript_file(jobName, transcript):
    # Dump the transcript text to a text file so it can be uploaded to S3
    tempdir = tempfile.gettempdir()
    with open(tempdir + jobName, 'w') as tmpfile:
        tmpfile.write(transcript)
    return tmpfile

def copy_to_s3(amp_transcript, bucket, jobname):
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(amp_transcript, bucket, jobname)
        print("Uploaded file " + amp_transcript + " to S3 bucket " + bucket + " for job " + jobname)
    except Exception as e:
        print("Failed to upload file " + amp_transcript + " to S3 bucket " + bucket + " for job " + jobname, e)
        traceback.print_exc()
        return False
    return True

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

# Split a comma separated string, standardize input, and return list
def split_ignore_list(ignore_list_string):
    to_return = list()
    ignore_cats_list = ignore_list_string.split(',')
    for cat in ignore_cats_list:
        to_return.append(clean_text(cat))
    return to_return

def clean_entity_word(entity_word):
    cleaned_word = entity_word
    if(entity_word.endswith('\'s')):
       cleaned_word = entity_word.replace('\'s', '')
    return cleaned_word.translate(str.maketrans('', '', string.punctuation))

def clean_text(text):
    return text.lower().strip()

def read_aws_entities(aws_entities):
    with open(aws_entities) as aws_entities_file:
        aws_entities_json = json.load(aws_entities_file)
    return aws_entities_json

def safe_delete(filename):
    try:
        if os.path.exists(filename):
            os.remove(filename)
            print("Deleted file " + filename)
    except Exception as e:
        print("Failed to delete file " + filename, e)
        traceback.print_exc()
        return False
    return True

if __name__ == "__main__":
    main()
