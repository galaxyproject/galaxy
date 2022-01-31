#!/usr/bin/env python3
import difflib
#from difflib_data import *


import json
import string
import sys
import traceback

from mgm_logger import MgmLogger
import mgm_utils

from speech_to_text import SpeechToText, SpeechToTextMedia, SpeechToTextResult, SpeechToTextScore, SpeechToTextWord
# import aws_transcribe_to_schema

# Convert editor output to standardized json
def main():
    (root_dir, from_draftjs, original_transcript, to_transcript) = sys.argv[1:5]
    
    # using output instead of input filename as the latter is unique while the former could be used by multiple jobs     
    logger = MgmLogger(root_dir, "hmgm_transcript", to_transcript)
    sys.stdout = logger
    sys.stderr = logger

    try:
        # if from_draftjs is in error raise exception to notify HMGM job runner to fail the job
        # otherwise if from_draftjs doesn't exist yet, exit to requeue (keep waiting)
        mgm_utils.exit_if_file_not_ready(from_draftjs)
        print("Converting DraftJs " + from_draftjs + " to Transcript " + to_transcript)

        with open(from_draftjs) as json_file:
            d = json.load(json_file)
            data = eval(json.dumps(d))
    
        #read original file for extracting only the confidence score of each word
        original_input = open(original_transcript)
        original_json = json.loads(original_input.read())
        original_items = original_json["results"]["words"]
    	
        #print("the data in editor output is:",data)
        results = SpeechToTextResult()
        word_type = text = ''
        confidence = start_time = end_time = -1
        duration = 0.0
        
        # draftJS input file here always came from converted and corrected AMP Transcript,
        # so it should always contain 'entityMap', otherwise error should occur        
        #Standardising draft js format
#         if "entityMap" in data.keys():
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
                    if text[-1] in string.punctuation: #[',','.','!','?']:
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
        i = j = 0
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
                if ("score" in original_items[i]):
                    words[j].score.scoreValue = float(original_items[i]["score"]["scoreValue"])
                else:
                    words[j].score.scoreValue = 1.0 # default score to 1.0 if not existing originally    
                i += 1
                j += 1
            print("i: " + str(i) + " j:" + str(j))
            
        # Create the media object
        media = SpeechToTextMedia(duration, original_transcript)
    
        # Create the final object
        stt = SpeechToText(media, results)
    
        # Write the output
        mgm_utils.write_json_file(stt, to_transcript)
        print("Successfully converted from DraftJs " + from_draftjs + " to Transcript " + to_transcript)
        # as the last command in HMGM, implicitly exit 0 here to let the whole job complete in success
    except Exception as e:
        # as the last command in HMGM, exit 1 to let the whole job fail
        print ("Failed to convert from DraftJs " + from_draftjs + " to Transcript " + to_transcript, e)
        traceback.print_exc()
        sys.stdout.flush()
        exit(1)            


if __name__ == "__main__":
	main()