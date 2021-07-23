#!/usr/bin/env python3

import sys
import json

from entity_extraction import EntityExtraction

def main():
    (amp_entities, amp_entities_csv) = sys.argv[1:3]

    # Open the file and create the ner object
    with open(amp_entities, 'r') as file:
        ner = EntityExtraction.from_json(json.load(file))

    # Write the csv file
    ner.toCsv(amp_entities_csv)


if __name__ == "__main__":
    main()
