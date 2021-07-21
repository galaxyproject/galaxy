#!/usr/bin/env python3

import json
import sys
import traceback
import tempfile
import shutil
import tarfile
import socket
import time
from datetime import datetime
import boto3

from entity_extraction import EntityExtraction, EntityExtractionMedia
from speech_to_text import SpeechToText
import mgm_utils


def main():
    (amp_transcript, aws_entities, amp_entities, bucket, dataAccessRoleArn) = sys.argv[1:6]

    # get a list of categories to ignore when outputting entity list
    ignore_categories = list()
    if len(sys.argv) > 6:
        ignore_categories = get_ignore_categories(sys.argv[6])
        print(f"Ignore categories: {ignore_categories}")

    # parse input AMP Transcript JSON file into amp_entities object
    try:
        with open(amp_transcript, 'r') as amp_transcript_file:
            amp_transcript_obj = SpeechToText().from_json(json.load(amp_transcript_file))
    except Exception:
        print(f"Error: Exception while parsing AMP Transcript {amp_transcript}:")
        raise
        
    # initialize the amp_entities object with media information
    amp_entities_obj = EntityExtraction()
    mediaLength = len(amp_transcript_obj.results.transcript)
    amp_entities_obj.media = EntityExtractionMedia(mediaLength, amp_transcript)

    # If input AMP transcript is empty, don't error, instead, output AMP Entity JSON with empty entity list and complete the process
    if mediaLength == 0:
        print(f"Warning: Input AMP Transcript Json file has empty transcript, will output AMP NER Json with empty entities list.")
        mgm_utils.write_json_file(amp_entities_obj, amp_entities)
        exit(0)

    # otherwise, continue with preparation for AWS Comprehend job 
    s3uri = 's3://' + bucket + '/'
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    # hostname + timestamp should ensure unique job name
    jobname = 'AwsComprehend-' + socket.gethostname() + "-" + timestamp 

    # write AMP Transcript text into the input file in a temp directory and upload it to S3
    tmpdir = tempfile.mkdtemp(dir="/tmp")
    upload_input_to_s3(amp_transcript_obj, tmpdir, bucket, jobname)

    # Make call to AWS Comprehend
    outputuri = run_comprehend_job(jobname, s3uri, dataAccessRoleArn)

    # download AWS Comprehend output from s3 to the tmp directory, uncompress and copy it to output aws_entities output file
    download_output_from_s3(outputuri, s3uri, bucket, tmpdir, aws_entities)

    # populate AMP Entities list based on input AMP transcript words list and output AWS Entities list  
    aws_entities_json = read_aws_entities(aws_entities)
    populateAmpEntities(amp_transcript_obj, aws_entities_json, amp_entities_obj, ignore_categories)

    # Write the output AMP Entity JSON file
    mgm_utils.write_json_file(amp_entities_obj, amp_entities)
    

def upload_input_to_s3(amp_transcript_obj, tmpdir, bucket, jobname):
    # write the transcript text into a tmp input file
    try:
        # use jobname as input filename
        input = tmpdir + jobname
        with open(input, 'w') as infile:
            infile.write(amp_transcript_obj.results.transcript)
            print(f"Successfully created input file {input} containing transcript for AWS Comprehend job.")
    except Exception as e:
        print(f"Error: Exception while creating input file {input} containing transcript for AWS Comprehend job.")
        raise
    
    # upload the tmp file to s3
    try:
        s3_client = boto3.client('s3')
        response = s3_client.upload_file(input, bucket, jobname)
        print(f"Successfully uploaded input file {input} to S3 bucket {bucket} for AWS Comprehend job.")
    except Exception as e:
        print(f"Error: Exception while uploading input file {input} to S3 bucket {bucket} for AWS Comprehend job.")
        raise

def download_output_from_s3(outputuri, s3uri, bucket, tmpdir, aws_entities):
    # get the output file from s3
    try:
        outkey = outputuri.replace(s3uri, '')
        outname = outkey.rsplit("/", 1)[1]
        output = tmpdir + outname
        s3_client = boto3.client('s3')    
        s3_client.download_file(bucket, outkey, output)
        print(f"Successfully downloaded AWS Comprehend output {outputuri} to compressed output file {output}.")
    except Exception as e:
        print(f"Error: Exception while downloading AWS Comprehend output {outputuri} to compressed output file {output}.")
        raise
    
    # extract the contents of the output.tar.gz file and move the uncompressed file to galaxy output
    try:
        tar = tarfile.open(output)
        outputs = tar.getmembers()
        tar.extractall()
        tar.close()
                
        if len(outputs) > 0:
            source = outputs[0].name
            shutil.move(source, aws_entities) 
            print(f"Successfully uncompressed {output} to {source} and moved it to {aws_entities}.")
        else:
            raise Exception(f"Error: Compressed output file {output} does not contain any member.")
    except Exception as e:
        print(f"Error: Exception while uncompressing/moving {output} to {aws_entities}.")
        raise     

def run_comprehend_job(jobname, s3uri, dataAccessRoleArn):
    # submit AWS Comprehend job
    try:
        # TODO region name should be in MGM config
        comprehend = boto3.client(service_name='comprehend', region_name='us-east-2')
        # jobname was used as the object_name uploaded to s3
        inputs3uri = s3uri + jobname
        response = comprehend.start_entities_detection_job(
            InputDataConfig={
                'S3Uri': inputs3uri,
                "InputFormat": "ONE_DOC_PER_FILE"
            },
            OutputDataConfig={
                'S3Uri': s3uri
            },
            DataAccessRoleArn=dataAccessRoleArn,
            JobName=jobname,
            LanguageCode='en'
        )
        print(f"Successfully submitted AWS Comprehend job with input {inputs3uri}.")
    except Exception as e:
        print(f"Error: Exception while submitting AWS Comprehend job with input {inputs3uri}")
        raise

    # wait for AWS Comprehend job to end
    status = ''
    outputuri = ''
    try:
        # keep checking every 60 seconds while job still in progress
        while status not in ('COMPLETED','FAILED', 'STOP_REQUESTED','STOPPED'):
            jobStatusResponse = comprehend.describe_entities_detection_job(JobId=response['JobId'])
            status = jobStatusResponse['EntitiesDetectionJobProperties']['JobStatus']
            outputuri = jobStatusResponse['EntitiesDetectionJobProperties']['OutputDataConfig']['S3Uri']
            print(f"Waiting for AWS Comprehend job {jobname} to complete: status = {status}.")              
            time.sleep(60)        
    except Exception as e:
        print(f"Error: Exception while running AWS Comprehend job {jobname}")
        raise
    
    # check status of job upon ending
    print(jobStatusResponse)     
    if status == 'COMPLETED':
        print(f"AWS Comprehend job {jobname} completed in success with output {outputuri}.")  
        return outputuri
    else:
        raise Exception(f"Error: AWS Comprehend job {jobname} ended with status {status}.")

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

def populateAmpEntities(amp_transcript_obj, aws_entities_json, amp_entities_obj, ignore_categories):
    # AWS Comprehend output should contain entities
    if not 'Entities' in aws_entities_json.keys():
        raise Exception(f"Error: AWS Comprehend output does not contain entities list")
    
    words = amp_transcript_obj.results.words
    entities = aws_entities_json["Entities"]
    lenw = len(words)
    lene = len(entities)
    last = -1  # index of last matched word in AMP Transcript words list
    ignored = 0; # count of ignored entities
    
    # go through entities from AWS output
    for entity in entities:
        try:
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
                if words[i].offset == beginOffset:
                    textamp = words[i].text
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
                start = words[last].start
                amp_entities_obj.addEntity(type, text, beginOffset, endOffset, start, end, scoreType, scoreValue)
        except Exception:
            # in case of exception, most likely due to missing fields, skip the entity in error and continue with the rest
            print("Error: Exception while processing AWS entity {text} at offset {begineOffset}")
            traceback.print_exc()           

    lena = len(amp_entities_obj.entities)
    print(f"Among all {lene} AWS entities, {lena} are successfully populated into AMP Entities, {ignored} are ignored, {lene-lena-ignored} are unmatched.")


if __name__ == "__main__":
    main()
