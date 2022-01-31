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
job_name_prefix="AwsTranscribe"
job_name_suffix=$(printf "%s-%s-%s" $(hostname -s) $(date +%Y%m%d%H%M%S) $$)
job_name=${job_name_prefix}-${job_name_suffix}
log_file=${job_directory}/${job_name}.log
# create job_directory if not existing yet
#if [ ! -d ${job_directory} ] 
#then
#    mkdir ${job_directory}
#fi
echo "echo ${input_file} ${output_file} ${audio_format} ${s3_bucket} ${s3_directory} ${job_directory} ${job_name} >> $log_file 2>&1" # debug

# if s3_directory is empty or ends with "/" return it as is; otherwise append "/" at the end
s3_path=`echo $s3_directory| sed -E 's|([^/])$|\1/|'`
# upload media file from local Galaxy source file to S3 directory
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

# wait while job is running
echo "Waiting for ${job_name} to finish ..." >> $log_file 2>&1
# note: both AWS query and jq parsing returns field value with double quotes, which needs to be striped off when comparing to string literal
while [[ `aws transcribe get-transcription-job --transcription-job-name "${job_name}" --query "TranscriptionJob"."TranscriptionJobStatus" | sed -e 's/"//g'` = "IN_PROGRESS" ]] 
do
# exit with code 255 to let LWLW job runner to requeue the job 
    exit 255
#    sleep 60s
done

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


