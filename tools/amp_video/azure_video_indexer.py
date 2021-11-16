#!/usr/bin/env python3
import sys
import traceback
import requests
import logging
import time
import json
import uuid
import boto3

import mgm_utils


def main():
    apiUrl = "https://api.videoindexer.ai"

    (input_file, include_ocr, location, root_dir, index_file, ocr_file) = sys.argv[1:7]

    try:
        import http.client as http_client
    except ImportError:
        # Python 2
        import httplib as http_client

    config = mgm_utils.get_config(root_dir)
    s3_bucket = config['azure']['s3Bucket']
    accountId = config['azure']['accountId']
    apiKey = config['azure']['apiKey']

    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig()

    # Turn on HTTP debugging here
    http_client.HTTPConnection.debuglevel = 1

    s3_path = upload_to_s3(input_file, s3_bucket)
    print("S3 path " + s3_path)
    
    # Get an authorization token for subsequent requests
    auth_token = get_auth_token(apiUrl, location, accountId, apiKey)
    
    video_url = "https://" + s3_bucket + ".s3.us-east-2.amazonaws.com/" + s3_path

    # Upload the video and get the ID to reference for indexing status and results
    videoId = upload_video(apiUrl, location, accountId, auth_token, input_file, video_url)

    # Get the auth token associated with this video    
    # video_auth_token = get_video_auth_token(apiUrl, location, accountId, apiKey, videoId)

    # Check on the indexing status
    while True:
        # The token expires after an hour.  Let's just refresh every iteration
        video_auth_token = get_video_auth_token(apiUrl, location, accountId, apiKey, videoId)

        state = get_processing_status(apiUrl, location, accountId, videoId, video_auth_token)
        
        # We have a status other than uploaded or processing, it is complete
        if state != "Uploaded" and state != "Processing":
            break
        
        # Wait a bit before checking again
        time.sleep(60)

    # Turn on HTTP debugging here
    http_client.HTTPConnection.debuglevel = 1

    # Get the simple video index json
    auth_token = get_auth_token(apiUrl, location, accountId, apiKey)
    index_json = get_video_index_json(apiUrl, location, accountId, videoId, auth_token, apiKey)
    mgm_utils.write_json_file(index_json, index_file)

    # Get the advanced OCR json via the artifact URL if requested
    if include_ocr.lower() == 'true':
        artifacts_url = get_artifacts_url(apiUrl, location, accountId, videoId, auth_token, 'ocr')
        download_artifacts(artifacts_url, ocr_file)
    # TODO otherwise do we need to generate a dummy file so the output is not empty and cause error?
    
    delete_from_s3(s3_path, s3_bucket)

# Retrieve the "artifacts" (ocr json) from the specified url
def download_artifacts(artifacts_url, output_name):
    r = requests.get(url = artifacts_url)
    with open(output_name, 'wb') as f:
        f.write(r.content)
    return output_name

# Get the url where the artifacts json is stored
def get_artifacts_url(apiUrl, location, accountId, videoId, auth_token, type):
    url = apiUrl + "/" + location + "/Accounts/" + accountId + "/Videos/" + videoId + "/ArtifactUrl"
    params = {'accessToken':auth_token,
                'type':type}
    r = requests.get(url = url, params = params)
    return r.text.replace("\"", "")

# Get the video index json, which contains OCR data
def get_video_index_json(apiUrl, location, accountId, videoId, auth_token, apiKey):
    url = apiUrl + "/" + location + "/Accounts/" + accountId + "/Videos/" + videoId + "/Index"
    params = {'accessToken':auth_token }
    headers = {"Ocp-Apim-Subscription-Key": apiKey}
    r = requests.get(url = url, params=params, headers = headers) 
    return json.loads(r.text)

# Get the processing status of the video
def get_processing_status(apiUrl, location, accountId, videoId, video_auth_token):
    video_url = apiUrl + "/" + location + "/Accounts/" + accountId + "/Videos/" + videoId + "/Index"
    params = {'accessToken':video_auth_token,
                'language':'English'}
    r = requests.get(url = video_url, params = params)
    data = json.loads(r.text)
    if 'videos' in data.keys():
        videos = data['videos']
        if 'state' in videos[0].keys():
            return videos[0]['state']
    return "Error"

# Create the auth token request
def request_auth_token(url, apiKey):
    params = {'allowEdit':True} 
    headers = {"Ocp-Apim-Subscription-Key": apiKey}
    # sending get request and saving the response as response object 
    r = requests.get(url = url, params = params, headers=headers) 
    if r.status_code == 200:
        return r.text.replace("\"", "")
    else:
        print("Auth failure")
        print(r)
        exit(1)

# Get general auth token
def get_auth_token(apiUrl, location, accountId, apiKey):
    token_url = apiUrl + "/auth/" + location + "/Accounts/" + accountId + "/AccessToken"
    return request_auth_token(token_url, apiKey)

# Get video auth token
def get_video_auth_token(apiUrl, location, accountId, apiKey, videoId):
    token_url = apiUrl + "/auth/" + location + "/Accounts/" + accountId + "/Videos/" + videoId + "/AccessToken"
    return request_auth_token(token_url, apiKey)

# Upload the video using multipart form upload
def upload_video(apiUrl, location, accountId, auth_token, input_file, video_url):

    # Create a unique file name 
    millis = int(round(time.time() * 1000))

    upload_url = apiUrl + "/" + location +  "/Accounts/" + accountId + "/Videos"
    
    data = {}
    with open(input_file, 'rb') as f:
        params = {'accessToken':auth_token,
                'name':'amp_video_' + str(millis),
                'description':'AMP File Upload',
                'privacy':'private',
                'partition':'No Partition',
                'videoUrl':video_url}
        r = requests.post(upload_url, params = params)
        
        if r.status_code != 200:
            print("Upload failure")
            print(r)
            exit(1)
        else:
            data = json.loads(r.text)
            if 'id' in data.keys():
                return data['id']
            else:
                exit(1)

def upload_to_s3(input_file, bucket):
    s3_client = boto3.client('s3')
    jobname = str(uuid.uuid1())
    try:
        response = s3_client.upload_file(input_file, bucket, jobname, ExtraArgs={'ACL': 'public-read'})
        print("Uploaded file " + input_file + " to s3 bucket " + bucket)
    except Exception as e:
        print("Failed to upload file " + input_file + " to s3 bucket " + bucket, e)
        traceback.print_exc()
        return None
    return jobname

def delete_from_s3(s3_path, bucket):
    s3_client = boto3.resource('s3')
    try:
        obj = s3_client.Object(bucket, s3_path)
        obj.delete()
        print("Deleted file " + s3_path + " from s3 bucket " + bucket)
    except Exception as e:
        print("Failed to delete file " + s3_path + " from s3 bucket " + bucket, e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
