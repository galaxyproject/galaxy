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

sys.path.insert(0, os.path.abspath('../../../../../tools/amp_json_schema'))

from entity_extraction_schema import EntityExtraction, EntityExtractionMedia, EntityExtractionEntity
from speech_to_text_schema import SpeechToText, SpeechToTextMedia, SpeechToTextResult, SpeechToTextScore, SpeechToTextWord


def main():
    (input_file, json_file) = sys.argv[1:3]

    # Load English tokenizer, tagger, parser, NER and word vectors
    nlp = spacy.load("en_core_web_lg")

    with open(input_file, 'r') as file:
        stt = SpeechToText().from_json(json.load(file))

    doc = nlp(stt.result.transcript)

    # Create the result object
    result = EntityExtraction()

    # Add the media information
    result.media = EntityExtractionMedia(len(stt.result.transcript), input_file)
    
    # Variables for filling time offsets based on speech to text
    lastPos = 0  # Iterator to keep track of location in STT word
    sttWords = len(stt.result.words) # Number of STT words

    # Find named entities, phrases and concepts - Add them to the result
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
                word = stt.result.words[wordPos]
                # If it matches, set the time offset.
                if word.text == entityPart:
                    # Keep track of last position to save iterations
                    lastPos = wordPos
                    # Set start if we haven't set it yet
                    if start == None:
                        start = word.start
                    end = word.end
                    break
        result.addEntity(entity.label_, text, entity.start_char, entity.end_char, None, None, start, end)
    
    # Write the json file
    write_json_file(result, json_file)

# Serialize obj and write it to output file
def write_json_file(obj, output_file):
    # Serialize the object
    with open(output_file, 'w') as outfile:
        json.dump(obj, outfile, default=lambda x: x.__dict__)


        
if __name__ == "__main__":
    main()
