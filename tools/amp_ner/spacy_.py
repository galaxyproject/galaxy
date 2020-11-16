#!/usr/bin/env python3

import os
import os.path
import json
import shutil
import spacy
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.abspath('../../../../../tools/amp_schema'))
from entity_extraction import EntityExtraction, EntityExtractionMedia, EntityExtractionEntity
from speech_to_text import SpeechToText, SpeechToTextMedia, SpeechToTextResult, SpeechToTextScore, SpeechToTextWord


def main():
    (input_file, json_file, csv_file) = sys.argv[1:4]
    # Read a list of categories to ignore when outputting entity list
    ignore_cats_list = list()
    if len(sys.argv) > 4:
        print("Categories to ignore:" + sys.argv[4])
        ignore_cats_list = split_ignore_list(sys.argv[4])

    # Load English tokenizer, tagger, parser, NER and word vectors
    nlp = spacy.load("en_core_web_lg")

    # Create the ner object
    ner = EntityExtraction()

    with open(input_file, 'r') as file:
        stt = SpeechToText().from_json(json.load(file))

    # If we have a blank file, don't error.  Create another blank json file to pass to the next process
    if(stt is None or stt.results is None):
        ner.media = EntityExtractionMedia(len(stt.results.transcript), input_file)
        # Write the json file
        write_json_file(ner, json_file)
        ner.toCsv(csv_file)
        exit(0)

    doc = nlp(stt.results.transcript)

    # Add the media information
    ner.media = EntityExtractionMedia(len(stt.results.transcript), input_file)

    # Variables for filling time offsets based on speech to text
    lastPos = 0  # Iterator to keep track of location in STT word
    sttWords = len(stt.results.words) # Number of STT words

    # Find named entities, phrases and concepts - Add them to the ner
    for entity in doc.ents:
        # Start and end time offsets
        start = None
        end = None
        text = entity.text

        # Split the entity into an array of words based on whitespace
        entityParts = text.split()

        # For each word in the entity, find the corresponding word in the STT word list
        for entityPart in entityParts:
            for wordPos in range(lastPos, sttWords):
                word = stt.results.words[wordPos]
                # If it matches, set the time offset.
                if word.text == entityPart:
                    # Keep track of last position to save iterations
                    lastPos = wordPos
                    # Set start if we haven't set it yet
                    if start == None:
                        start = word.start
                    end = word.end
                    break
        # Ignore certain categories
        if clean_text(entity.label_) not in ignore_cats_list:
            ner.addEntity(entity.label_, text, None, None, None, None, start, None)   #AMP-636 removed startOffset=endOffset=end=None

    # Write the json file
    write_json_file(ner, json_file)
    # Write the csv file
    ner.toCsv(csv_file)

# Standardize ignore list text
def clean_text(text):
    return text.lower().strip()

# Split a comma separated string, standardize input, and return list
def split_ignore_list(ignore_list_string):
    to_return = list()
    ignore_cats_list = ignore_list_string.split(',')
    for cat in ignore_cats_list:
        to_return.append(clean_text(cat))
    return to_return

# Read a list of categories to ignore
def read_ignore_list(ignore_list_filename):
    print("Reading list")
    ignore_cats_list = list()
    f = open(ignore_list_filename, "r")
    # For each value in the comma separated list.  Standardize text
    for val in f.read().split(","):
        ignore_cats_list.append(clean_text(val))
    print(ignore_cats_list)
    return ignore_cats_list

# Serialize obj and write it to output file
def write_json_file(obj, output_file):
    # Serialize the object
    with open(output_file, 'w') as outfile:
        json.dump(obj, outfile, default=lambda x: x.__dict__)



if __name__ == "__main__":
    main()
