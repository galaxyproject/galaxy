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
    ignore_categories = list()

    if len(sys.argv) > 6:
        print("ignore categories:" + sys.argv[6])
        ignore_categories = get_ignore_categories(sys.argv[6])

    # Variable declaration
    outputS3Uri = 's3://' + bucketName + '/'
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    jobName = 'AwsComprehend-' + timestamp + ".json"
    inputS3Uri = outputS3Uri + jobName

    # Get the transcript text from the input file
    with open(amp_transcript, 'r') as amp_transcript_file:
        amp_transcript_json = SpeechToText().from_json(json.load(amp_transcript_file))

    # Create the amp_entities_json object
    amp_entities_json = EntityExtraction()

    # Add the media information
    if amp_transcript_json is None or amp_transcript_json.results is None:
        print(f"Error: Input AMP Transcript JSON is invalid.")
        exit(1)
    else:
        mediaLength = len(amp_transcript_json.results.transcript)
    amp_entities_json.media = EntityExtractionMedia(mediaLength, amp_transcript)

    # If input transcript is empty, don't error, create an output json file with empty entity list to pass to the next process
    if mediaLength == 0:
        print(f"Warning: Input AMP Transcript Json file has empty transcript, output AMP NER Json will have empty entities as well.")
        mgm_utils.write_json_file(amp_entities_json, amp_entities)
        exit(0)

    # Create a temp file to upload to S3
    tmpfile = create_temp_transcript_file(jobName, amp_transcript_json.results.transcript)

    # Copy the temporary text file to S3
    copy_to_s3(tmpfile.name, bucketName, jobName)

    # Make call to aws comprehend
    output_uri = run_comprehend_job(jobName, inputS3Uri, outputS3Uri, dataAccessRoleArn)

    # download and uncompress Comprehend output
    aws_entities = download_from_s3(output_uri, outputS3Uri, bucketName)
    if uncompressed_file is None:
        print(f"Error: AWS Comprehend output downloaded/uncompressed from {output_uri} doesn't exist.")
        exit(1)

    # populate AMP Entities list based on input AMP transcript words list and output AWS Entities list  
    aws_entities_json = read_aws_entities(aws_entities)
    populateAmpEntities(amp_transcript_json, aws_entities_json, amp_entities_json, ignore_categories)

    # Write the json file
    mgm_utils.write_json_file(amp_entities_json, amp_entities)

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
def get_ignore_categories(ignore_categories_string):
    ignore_categories = list()
    ignore_categories_list = ignore_categories_string.split(',')
    for category in ignore_categories_list:
        ignore_categories.append(clean_text(category))
    return ignore_categories

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

def populateAmpEntities(amp_transcript_json, aws_entities_json, amp_entities_json, ignore_categories):
    if not 'Entities' in aws_entities_json.keys():
        print(f"Warning: AWS Comprehend output does not contain entities list")
        return
    
    words = amp_transcript_json["results"]["words"]
    entities = aws_entities_json["Entities"]
    lenw = len(words)
    lene = len(entities)
    last = -1  # index of last matched word in AMP Transcript words list
    ignored = 0; # count of ignored entities
    
    for entity in entities:
        type = entity["Type"]
        text = entity["Text"]
        beginOffset = entity["BeginOffset"]
        endOffset = entity["EndOffset"]
        end = None
        scoreType = "relevance"
        scoreValue = entity["Score"]
        
        # skip entity in the ignore categories
        if clean_text(type) in ignore_categories:
            ignored = ignored + 1
            print(f"Ignoring entity {text} of type {type}.")
            continue

        # find the word in words list matching the offset of entity, starting from last matched word, as
        # we can assume that both AMP Transcript words and AWS Entities are sorted in the time/offset order        
        for i in range(last+1, lenw):
            # find a match by offset
            if words[i]["offset"] == beginOffset:
                textamp = words[i]["text"]
                # check if text match, note that entity could be multi-words, so we need to check if it starts with the matching word
                # if not, something is wrong; will still take it as a match 
                if not text.startswith(textamp):
                    print(f"Warning: AWS Entity {text} does not start with AMP Transcript words[{i}] = {textamp}, even though both start at offset {beginOffset}.")
                last = i
                break
        # reached the end of words list, match not found
        else:
            last = lenw
            
        # if reached end of words list and no matched word is found for current entity, no need to match the rest of entities
        if last == lenw:
            print(f"Warning: Reaching the end of AMP Transcript words list with some AWS entities remaining unmatched.")
            break
        # otherwise a match is found, add a new entity for it to entities list
        else:               
            start = words[last]["start"]
            amp_entities_json.addEntity(type, text, beginOffset, endOffset, start, end, scoreType, scoreValue)

    lena = len(amp_entities_json["entities"])
    print(f"Successfully added {lena} AMP entities; among all AWS entities, {ignored} are ignored, {lene-lena-ignored} are unmatched.")


if __name__ == "__main__":
    main()
