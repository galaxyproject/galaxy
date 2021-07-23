#!/usr/bin/env python3


import spacy
import sys

import mgm_utils
import ner_helper


def main():
    (amp_transcript, spacy_entities, amp_entities, ignore_types) = sys.argv[1:5]

    # preprocess NER inputs and initialize AMP entities output
    [amp_transcript_obj, amp_entities_obj, ignore_types_list] = ner_helper.preprocess_amp_entities(amp_transcript, amp_entities, ignore_types)

    # if we reach here, further processing is needed, continue with Spacy   
     
    # load English tokenizer, tagger, parser, NER and word vectors
    nlp = spacy.load("en_core_web_lg")
    
    # run Spacy with input transcript
    spacy_entities_obj = nlp(amp_transcript_obj.results.transcript)

    # write the output Spacy entities object to JSON file
    mgm_utils.write_json_file(spacy_entities_obj.to_json(), spacy_entities)
    
    # populate AMP Entities list based on input AMP transcript words list and output AWS Entities list  
    ner_helper.populate_amp_entities(amp_transcript_obj, spacy_entities_obj.ents, amp_entities_obj, ignore_types_list)

    # write the output AMP entities object to JSON file
    mgm_utils.write_json_file(amp_entities_obj, amp_entities)
    

if __name__ == "__main__":
    main()
