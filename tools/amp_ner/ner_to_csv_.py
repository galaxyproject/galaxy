#!/usr/bin/env python3

import os.path
import sys
import json

sys.path.insert(0, os.path.abspath('../../../../../tools/amp_schema'))
from entity_extraction import EntityExtraction

def main():
    (input_file, csv_file) = sys.argv[1:3]

    # Open the file and create the ner object
    with open(input_file, 'r') as file:
        ner = EntityExtraction.from_json(json.load(file))

    # Write the csv file
    ner.toCsv(csv_file)


if __name__ == "__main__":
    main()
