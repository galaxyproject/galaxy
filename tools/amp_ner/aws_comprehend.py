#!/usr/bin/env python3


import sys
import tempfile
import shutil
import tarfile
import socket
import time
from datetime import datetime
import boto3

import mgm_utils
import ner_helper


def main():
    (amp_transcript, aws_entities, amp_entities, ignore_types, bucket, dataAccessRoleArn) = sys.argv[1:7]
    
    # preprocess NER inputs and initialize AMP entities output
    [amp_transcript_obj, amp_entities_obj, ignore_types_list] = ner_helper.initialize_amp_entities(amp_transcript, amp_entities, ignore_types)

    # if we reach here, further processing is needed, continue with preparation for AWS Comprehend job 
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

    # AWS Comprehend output should contain entities
    aws_entities_json = mgm_utils.read_json_file(aws_entities)
    if not 'Entities' in aws_entities_json.keys():
        raise Exception(f"Error: AWS Comprehend output does not contain entities list")
    aws_entities_list = aws_entities_json["Entities"]

    # populate AMP Entities list based on input AMP transcript words list and output AWS Entities list  
    ner_helper.populate_amp_entities(amp_transcript_obj, aws_entities_list, amp_entities_obj, ignore_types_list)

    # write the output AMP entities to JSON file
    mgm_utils.write_json_file(amp_entities_obj, amp_entities)
    
    
# Upload the transcript file created from amp_transcript_obj in tmpdir to the S3 bucket for the given job. 
def upload_input_to_s3(amp_transcript_obj, tmpdir, bucket, jobname):
    # write the transcript text into a tmp input file
    try:
        # use jobname as input filename
        input = tmpdir + "/" + jobname
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

# Download AWS Comprehend output from the given URL in the given S3 bucket to the tmpdir and extract it to aws_entities.
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

# Run AWS Comprehend job with the given jobname, using the input at the given S3 URL with the given dataAccessRoleArn.
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
    

if __name__ == "__main__":
    main()
