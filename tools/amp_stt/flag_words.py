#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path
import json
import logging
import sys
import os
sys.path.insert(0, os.path.abspath('../../../../../tools/amp_schema'))
from speech_to_text import SpeechToText
def main():
    amp_transcript =  sys.argv[1] 
    words_to_flag_file =  sys.argv[2] 
    output_csv =  sys.argv[3] 
    words_to_flag = get_words(words_to_flag_file) 

    print("Words to Flag:")
    for w in words_to_flag:
        print(w)
    print("")

    matching_words = list()
    with open(amp_transcript, 'r') as f:
        transcript_dict = json.load(f)
        # Check to see if we have a valid transcript.  If so, find the matches. 
        if "results" in transcript_dict.keys() and "words" in transcript_dict["results"].keys():
            transcript_words = transcript_dict["results"]["words"]
            matching_words = match_words(words_to_flag, transcript_words)

    # Print the output
    print(matching_words)
    write_csv(output_csv, matching_words)
    exit(0)

def match_words(words_to_flag, transcript_words):
    matching_words = list()
    # Iterate through the transcript
    for word in transcript_words:
        cleaned_word = clean_word(word["text"])
        # Iterate through all the words to flag
        for flag_word in words_to_flag:
            if flag_word["whole_phrase"] == cleaned_word:
                matching_words.append({'start': word["start"], 'text': flag_word["whole_phrase"]})
                break
            elif flag_word["whole_phrase"].startswith(cleaned_word) and len(flag_word["parts"])>1:
                # For multiple word phrases, find the starting index and iterate through the list
                index = transcript_words.index(word)
                found_match = True
                index_part = 0
                phrase_matches = list()
                # Iterate through the word list
                for i in range(index, index + len(flag_word["parts"])):
                    next_word = transcript_words[i]
                    print("Phrase: "  + next_word["text"] + " : " + flag_word["parts"][index_part])
                    # If the word doesn't match, neither does the phrase.  Break here
                    if clean_word(next_word["text"]) != flag_word["parts"][index_part]:
                        found_match = False
                        break
                    index_part +=1
                    phrase_matches.append(next_word)
                # If we found a complete match, store the value
                if found_match:
                    match = {'start': word["start"], 'text': flag_word["whole_phrase"]}
                    matching_words.append(match)
    return matching_words

# Write the CSV.  Sorted by text then start time
def write_csv(output_file, matching_words):
    with open(output_file, 'w') as csvfile:  
        # creating a csv writer object  
        csvwriter = csv.writer(csvfile)  
            
        # writing the fields  
        csvwriter.writerow(["Word", "Start"])
        
        # Print each row, sorted by text/start
        for word in sorted(matching_words, key = lambda i: (i['text'], i['start'])):
            csvwriter.writerow([word["text"], word["start"]])

# Simple word cleaning function for comparison
def clean_word(word):
    return word.strip().lower()

# Parse the list of words.  Store the whole phrase as well as the parts
def get_words(words_to_flag):
    word_file = open(words_to_flag, 'r')
    word_lines = word_file.readlines()

    to_return = list()
    if(len(word_lines)==0):
        return to_return

    for line in word_lines:
        flag_word = dict()

        flag_word["parts"] = list()
        flag_word["whole_phrase"] = clean_word(line)

        if(len(flag_word["whole_phrase"])==0):
            continue

        for w in flag_word["whole_phrase"].split(' '):
            flag_word["parts"].append(clean_word(w))

        if len(flag_word["parts"]) > 0:
            to_return.append(flag_word)
    return to_return

class FlagWord:
    parts = list()
    whole_phrase = ""
    def __int__(self):
        self.whole_phrase = ""
        self.parts = list()
    
if __name__ == "__main__":
    main()