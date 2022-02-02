#!/bin/sh

# Script to run a aws transcribe job using aws-cli.

# Usage:
# transcribe $input_file $job_directory $output_file $audio_format $s3_bucket $s3_directory

# TODO: shall we use ENV var for <S3_bucket> <s3_directory>, <job_directory>? 
# The reason for it is to avoid passing parameter to script each time (although since the script is only called by Galaxy not a human, it probably doesn't matter);
# the reason against it is that it makes the tool less flexible and more dependent.

# record transcirbe command parameters
job_directory=$1
input_file=$2
output_file=$3
audio_format=$4
s3_bucket=$5
s3_directory=$6

# TODO 
# Galaxy change binary input file extension to .dat for all media files, which means we can't infer audio format from file extension.
# We could use file utility to extract MIME type to obtain audio format; for now We let user specify audio format as a parameter.

# AWS Transcribe service requires a unique job name when submitting a job under the same account.
# Suffixing to the job name with hostname and timestamp shall make the name unique enough in real case.
# In addition, all AWS job related files should go to a designated directory $job_directory, and file names can be prefixed by the job_name. 
#
# job_name_prefix="AwsTranscribe"
# job_name_suffix=$(printf "%s-%s-%s" $(hostname -s) $(date +%Y%m%d%H%M%S) $$)
#
# Change for LWLW job:
# Upon resume, the job needs to check if AWS request is already sent during previous run cycle;
# thus the job name needs to be inferable from some static info known to the job;
# timestamp is unique but previous timestamp is not known to the job;
# the best option would be replace timestamp with the param output_file, which is known to the job,
# doesn't change upon resume, and being the Galaxy dataset filename, is unique in each Galaxy instance.
#
# To shorten the job name, only the part useful for uniqueness is needed within output_file path, i.e.
# galaxy root (in case there're multiple galaxy instances on the same host) plus the dataset number.  
# dataset=`basename $output_file .dat`
# dataset_id=`echo "${dataset##*_}"`
# galaxy_root=
# job_name=AWST=$hostname=$galaxy_root=$dataset_id
#
hostname=`hostname -s`
# replace "/" with ":" to not interfere with filename
dataset=${output_file//[\/]/:} 
job_name=AWST=$hostname=$dataset
log_file=$job_directory/$job_name.log

# Note: It's assumed that galaxy/../galaxy_work/aws/transcribe dir exists prior to the job run.
#
# create job_directory if not existing yet
#if [ ! -d ${job_directory} ] 
#then
#    mkdir ${job_directory}
#fi

# Change for LWLW job:
# Skip all the operations prior to checking AWS job status, if this is a resume run. 
# If the log file already exists, we can assume this is a resumed run; as otherwise,
# if the previous run had failed (either before or after the resume point), a rerun from Galaxy 
# would use a new output_file with new dataset_id, thus resulting in a new job_name and new log file
# A more absoulte check would be to query AWS whether the job exists, but that's more costly
if [[ ! -f "$log_file" ]]; then
    # debug
    echo "echo ${input_file} ${output_file} ${audio_format} ${s3_bucket} ${s3_directory} ${job_directory} ${job_name} >> $log_file 2>&1"

    # if s3_directory is empty or ends with "/" return it as is; otherwise append "/" at the end
    s3_path=`echo $s3_directory | sed -E 's|([^/])$|\1/|'`

    # upload media file from local Galaxy source file to S3 directory; note that log redirects to aws log file from now on
    echo "Uploading ${input_file} to s3://${s3_bucket}/${s3_path}" >> $log_file 2>&1 
    aws s3 cp ${input_file} s3://${s3_bucket}/${s3_path} >> $log_file 2>&1

    # create json file in the aws directory, i.e. <job_directory>/<job_name>_request.json
    request_file=${job_directory}/${job_name}-request.json
    input_file_name=$(basename ${input_file})
    media_file_url="http://${s3_bucket}.s3.amazonaws.com/${s3_path}${input_file_name}"

    # use user-specified bucket for output for easier access control
    jq -n "{ \"TranscriptionJobName\": \"${job_name}\", \"LanguageCode\": \"en-US\", \"MediaFormat\": \"${audio_format}\", \"Media\": { \"MediaFileUri\": \"${media_file_url}\" }, \"OutputBucketName\": \"${s3_bucket}\", \"Settings\":{ \"ShowSpeakerLabels\": true, \"MaxSpeakerLabels\": 10 } }" > ${request_file}
    
    # submit transcribe job
    echo "Starting transcription job ${job_name} using request file ${request_file}" >> $log_file 2>&1
    aws transcribe start-transcription-job --cli-input-json file://${request_file} >> $log_file 2>&1
fi

# wait while job is running
echo "Waiting for ${job_name} to finish ..." >> $log_file 2>&1
# Note: both AWS query and jq parsing returns field value with double quotes, which needs to be striped off when comparing to string literal
# Change for LWLW job:
# instead of wait and sleep in while loop while job is still IN_PROGRESS, 
# exit with code 255 to let LWLW job runner to requeue the job 
#
# while [[ `aws transcribe get-transcription-job --transcription-job-name "${job_name}" --query "TranscriptionJob"."TranscriptionJobStatus" | sed -e 's/"//g'` = "IN_PROGRESS" ]] 
# do
#     sleep 60s
# done
if [[ `aws transcribe get-transcription-job --transcription-job-name "${job_name}" --query "TranscriptionJob"."TranscriptionJobStatus" | sed -e 's/"//g'` = "IN_PROGRESS" ]]; then
    exit 255
fi

# retrieve job response
response_file=${job_directory}/${job_name}-response.json
aws transcribe get-transcription-job --transcription-job-name "${job_name}" > ${response_file}
cat $response_file >> $log_file 2>&1
job_status=`jq '.TranscriptionJob.TranscriptionJobStatus' < $response_file | sed -e 's/"//g'`

# if job succeeded, retrieve output file URL and download output file from the URL to galaxy output file location
if [[ ${job_status} = "COMPLETED" ]]; then
# since we use user defined bucket for transcribe output, its S3 location can be inferred following the naming pattern as below
# and we don't need to use the provided URL in the response, as that would require using curl and would encounter permission issue for private files
	transcript_file_uri=s3://${s3_bucket}/${job_name}.json
	aws s3 cp $transcript_file_uri $output_file >> $log_file 2>&1
    echo "Job ${job_name} completed in success!" >> $log_file 2>&1
    exit 0
# otherwise print error message to the log and exit with error code
elif [[ ${job_status} = "FAILED" ]]; then
    echo "Job ${job_name} failed!" >> $log_file 2>&1
    exit 1
else
    echo "Job ${job_name} ended in unexpected status: ${job_status}" >> $log_file 2>&1
    exit 2
fi


