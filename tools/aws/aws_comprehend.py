#!/usr/bin/env python3

import os
import os.path
import json
import shutil
import subprocess
import sys
import tempfile
import uuid

import boto3
sys.path.insert(0, os.path.abspath('../../../../../tools/amp_json_schema'))

from entity_extraction_schema import EntityExtraction, EntityExtractionMedia, EntityExtractionEntity
from speech_to_text_schema import SpeechToText, SpeechToTextMedia, SpeechToTextResult, SpeechToTextScore, SpeechToTextWord

def main():
    (input_file, json_file) = sys.argv[1:3]

    comprehend = boto3.client(service_name='comprehend', region_name='us-east-1')

    with open(input_file, 'r') as file:
        stt = SpeechToText().from_json(json.load(file))
    
    # Create the result object
    result = EntityExtraction()

    # Add the media information
    if stt is None or stt.result is None:
        mediaLength = 0
    else:
        mediaLength = len(stt.result.transcript)

    # If the text doesn't exist, exit
    if mediaLength == 0:
        exit(1)

    # Make call to aws comprehend
    response = comprehend.detect_entities(Text=stt.result.transcript, LanguageCode='en')
    
    result.media = EntityExtractionMedia(mediaLength, input_file)

    if 'Entities' in response.keys():
        for entity in response["Entities"]:
            result.addEntity(entity["Type"], entity["Text"], int(entity["BeginOffset"]), int(entity["EndOffset"]), "relevance", float(entity["Score"]))

    # Write the json file
    write_json_file(result, json_file)

# Serialize obj and write it to output file
def write_json_file(obj, output_file):
    # Serialize the object
    with open(output_file, 'w') as outfile:
        json.dump(obj, outfile, default=lambda x: x.__dict__)

if __name__ == "__main__":
    main()