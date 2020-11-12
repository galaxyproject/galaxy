#!/usr/bin/env python3
import difflib
#from difflib_data import *


import json
import sys
import os
from os import path

sys.path.insert(0, os.path.abspath('../../../../../tools/amp_util'))
from mgm_logger import MgmLogger
import mgm_utils

sys.path.insert(0, os.path.abspath('../../../../../tools/amp_schema'))
from speech_to_text import SpeechToText, SpeechToTextMedia, SpeechToTextResult, SpeechToTextScore, SpeechToTextWord
# import aws_transcribe_to_schema

# Convert editor output to standardized json
def main():
    (root_dir, editor_output_file, output_json_file, media_file) = sys.argv[1:5]
    
    logger = MgmLogger(root_dir, "hmgm_transcript", editor_output_file)
    sys.stdout = logger
    sys.stderr = logger

    mgm_utils.exit_if_file_not_ready(editor_output_file)

    with open(editor_output_file) as json_file:
        d = json.load(json_file)
        data = eval(json.dumps(d))

    #read original file for extracting only the confidence score of each word
    original_input = open(media_file)
    original_json = json.loads(original_input.read())
    original_items = original_json["results"]["words"]
	
    #print("the data in editor output is:",data)
    results = SpeechToTextResult()
    word_type = text = ''
    confidence = start_time = end_time = -1
    duration = 0.0
    #Standardising draft js format
    if "entityMap" in data.keys():
        transcript = ''
        entityMap = data["entityMap"]
        for i in range(0, len(entityMap.keys())):
            punctuation = ''
            if str(i) not in entityMap.keys():
                continue
            entity = entityMap[str(i)]
            if "data" in entity:
                if "text" in entity["data"].keys():
                    text = entity["data"]["text"]
                    transcript += entity["data"]["text"]+" "
                    if text[-1] in [',','.','!','?']:
                        punctuation = text[-1]
                        text = text[0:-1]
                        
                if "type" in entity:
                    entity_type = entity["type"]
                    if entity_type == "WORD":
                        word_type = "pronunciation"
                        if "start" in entity["data"]:
                            start_time = float(entity["data"]["start"])

                        if "end" in entity["data"]:
                            end_time = float(entity["data"]["end"])

                        if end_time > duration:
                            duration = end_time
                    else:
                        word_type = entity_type

            results.addWord(word_type, start_time, end_time, text, "confidence",confidence)   
            if len(punctuation) > 0:
                results.addWord('punctuation', None, None, punctuation, "confidence",0.0)

        results.transcript = transcript
        words = results.words
        #Now retrieving the confidence values from the original input file and assigning them to 'results'
        list_items = []
        list_result = []
        for i in range(0,len(original_items)):
            list_items.append(original_items[i]["text"])
        
        for j in range(0, len(words)):
            list_result.append(words[j].text)
        
        d = difflib.Differ()
        res = list(d.compare(list_items, list_result))
        print(len(res[0]))
        print(res)
        i = j= 0
        word_count = len(words)
        original_item_count = len(original_items)
        print("original item count: " + str(original_item_count))
        print("word count: " + str(word_count))
        for ele in res:
            if j >= word_count or i >= original_item_count:
                break
            elif ele.startswith("- "):
                i += 1
            elif len(ele) > 2 and ele[0:2] == "+ ":
                words[j].score.scoreValue = 1.0
                j += 1
            elif ele[0:1] == " " and words[j].text == original_items[i]["text"]:
                words[j].score.scoreValue = float(original_items[i]["score"]["scoreValue"])
                i += 1
                j += 1
            print("i: " + str(i) + " j:" + str(j))

    #Standardizing AWS Transcribe file
    elif "jobName" in data.keys() and "results" in data.keys():
        transcripts = data["results"]["transcripts"]
        for t in transcripts:
            results.transcript = results.transcript + t["transcript"]
        
        # Parse items (words)
        items = data["results"]["items"]
	
        # For each item, get the necessary parts and store as a word
        for i in items:
            alternatives = i["alternatives"]
            # Choose an alternative
            max_confidence = 0.00
            text = ""

            # Each word is stored as an "alternative".  Get the one with the maximum confidence
            for a in alternatives:
                if float(a["confidence"]) >= max_confidence:
                    max_confidence = float(a["confidence"])
                    text = a["content"]

            end_time = -1
            start_time = -1

            # Two types (punctionation, pronunciation).  Only keep times for pronunciation
            if i["type"] == "pronunciation":
                end_time = float(i["end_time"])
                start_time = float(i["start_time"])

                # If this is the greatest end time, store it as duration
                if end_time > duration:
                    duration = end_time
            # Add the word to the results
            results.addWord(i["type"], start_time, end_time, text, "confidence", max_confidence)

    #Standardizing Kaldi file
    elif "words" in data.keys():
        start_time = 0
        confidence = 0
        for word in data["words"]:
            start_time = word["time"]
            end_time = start_time + float(str(word["duration"]))
            transcript += word["word"]+' '
            text = word["word"]
            
            #if float(str(word["duration"])) > duration:
            duration += float(str(word["duration"]))
            if text[-1] in [',','.','!','?'] and len(text) > 1:
                punctuation = text[-1]
                text = text[0:-1]
                results.addWord('pronunciation', start_time, end_time, text, "confidence",confidence)
                results.addWord('punctuation', None, None, punctuation, "confidence",confidence)
            elif text in [',','.','!','?']:
                results.addWord('punctuation', None, None, text, "confidence",confidence)
            else:
                results.addWord('pronunciation', start_time, end_time, text, "confidence",confidence)
        results.transcript = transcript
        
    # Create the media object
    media = SpeechToTextMedia(duration, media_file)

    # Create the final object
    outputFile = SpeechToText(media, results)

    # Write the output
    write_output_json(outputFile, output_json_file)


# Serialize schema obj and write it to output file
def write_output_json(input_json, json_file):
	with open(json_file, 'w') as outfile:
		json.dump(input_json, outfile, default=lambda x: x.__dict__)

# Retrieve the confidence values from the original file into the standardised output
#def retrieve_confidence_scores()

if __name__ == "__main__":
	main()