#!/usr/bin/env python3

import json
import traceback

from entity_extraction import EntityExtraction, EntityExtractionMedia
from speech_to_text import SpeechToText
import mgm_utils


# Shared helper methods for NER MGMs

# Preprocess before submitting inputs to NER MGM: extract ignore types, parse input AMP Transcript, and initialize AMP Entity output.
# If input transcript is empty, complete the process with empty output entities; otherwise return data needed by following process.
def initialize_amp_entities(amp_transcript, amp_entities, ignore_types):
    # get a list of entity types to ignore when outputting entity list
    ignore_types_list = extract_ignore_types(ignore_types)
    print(f"Ignore types: {ignore_types_list}")    

    # parse input AMP Transcript JSON file into amp_entities object
    try:
        amp_transcript_obj = SpeechToText().from_json(mgm_utils.read_json_file(amp_transcript))
    except Exception:
        print(f"Error: Exception while parsing AMP Transcript {amp_transcript}:")
        raise
        
    # initialize the amp_entities object with media information
    amp_entities_obj = EntityExtraction()
    mediaLength = len(amp_transcript_obj.results.transcript)
    amp_entities_obj.media = EntityExtractionMedia(mediaLength, amp_transcript)

    # If input AMP transcript is empty, don't error, instead, output AMP Entity JSON with empty entity list and complete the whole process
    if mediaLength == 0:
        print(f"Warning: Input AMP Transcript Json file has empty transcript, will output AMP NER Json with empty entities list.")
        mgm_utils.write_json_file(amp_entities_obj, amp_entities)
        exit(0)

    # otherwise return the intermediate results of the preprocess
    return [amp_transcript_obj, amp_entities_obj, ignore_types_list]


# Populate entities in output AMP entities object, based on the input AMP transcript object, the output NER entities list, and the ignored categories.
def populate_amp_entities(amp_transcript_obj, ner_entities_list, amp_entities_obj, ignore_types_list):
    words = amp_transcript_obj.results.words
    lenw = len(words)
    lene = len(ner_entities_list)
    last = -1  # index of last matched word in AMP Transcript words list
    ignored = 0 # count of ignored entities
    mgm = "NER" # initialize for AWS/Spacy in case ner_entities_list is empty 
    
    # go through entities from NER output
    for entity in ner_entities_list:
        try:
            if isinstance(entity, dict):
                mgm = "AWS"
                type = entity["Type"]
                text = entity["Text"]
                beginOffset = entity["BeginOffset"]
                endOffset = entity["EndOffset"]
                scoreType = "relevance"
                scoreValue = entity["Score"]
            else: 
                mgm = "Spacy"
                type = entity.label_
                text = entity.text
                beginOffset = entity.start_char
                endOffset = entity.end_char
                scoreType = None
                scoreValue = None
            end = None
            
            # skip entity in the ignore categories
            if clean_type(type) in ignore_types_list:
                ignored = ignored + 1
                print(f"Ignoring entity {text} of type {type}.")
                continue
    
            # find the word in words list matching the offset of entity, starting from last matched word, as
            # we can assume that both AMP Transcript words and NER Entities are sorted in the time/offset order        
            for i in range(last+1, lenw):
                # find a match by offset
                if words[i].offset == beginOffset:
                    textamp = words[i].text
                    # check if text match, note that entity could be multi-words, so we need to check if it starts with the matching word
                    # if not, something is wrong; will still take it as a match 
                    if not text.startswith(clean_word(textamp)):
                        print(f"Warning: output {mgm} Entity {text} does not start with input AMP Transcript words[{i}] = {textamp}, even though both start at offset {beginOffset}.")
                    last = i
                    break
                # reached the end of words list, match not found
                else:
                    last = lenw
                
            # if reached end of words list and no matched word is found for current entity, no need to match the rest of entities
            if last == lenw:
                print(f"Warning: Reaching the end of AMP Transcript words list with some {mgm} entities remaining unmatched.")
                break
            # otherwise a match is found, add a new entity for it to entities list
            else:               
                start = words[last].start
                amp_entities_obj.addEntity(type, text, beginOffset, endOffset, start, end, scoreType, scoreValue)
        except Exception:
            # in case of exception, most likely due to missing fields, skip the entity in error and continue with the rest
            print("Error: Exception while processing {mgm} entity {text} at offset {begineOffset}")
            traceback.print_exc()           

    lena = len(amp_entities_obj.entities)
    print(f"Among all {lene} {mgm} entities, {lena} are successfully populated into AMP Entities, {ignored} are ignored, {lene-lena-ignored} are unmatched.")
    

# Extract a list of cleaned entity types from the given comma separated ignore_types string. 
def extract_ignore_types(ignore_types):    
    return list(map(clean_type, ignore_types.split(',')))


# Clean the given entity type by removing all start/end spaces and change all chars to upper case.
def clean_type(type):
    return type.strip().upper()


# Clean the given transcript word by removing the 's or ' at the end, if any.
# This is needed when comparing a word from transcript with text in a named entity, 
# as the former could contain "'s" or "'" in the end, while the latter tends to  have those removed. 
def clean_word(word):
    return word.rstrip("'s").rstrip("'")

 