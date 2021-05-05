#!/usr/bin/env python3

import os
import os.path
import sys
import json
import xml.etree.ElementTree as ET
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath('../../../../../tools/amp_util'))
import mgm_utils

def main():
    input_file = sys.argv[1]
    context_json = sys.argv[2]
    output_xml = sys.argv[3]
    print(context_json)
    context = json.loads(context_json)
    item_name = context["itemName"]
    primary_file_name = context["primaryfileName"]
    
    with open(input_file,'r') as json_file:
        applause_segments = json.load(json_file)
        segment_start = None
        segment_count = 1
        item = ET.Element('Item')
        item.set('label', item_name)
        primary_file = ET.SubElement(item, 'Div')
        primary_file.set('label', primary_file_name)

        for segment in applause_segments["segments"]:
            # This should start a segment
            if segment["label"] == "applause":
                # If this is the first segment, set the start time
                if segment_start is None:
                    segment_start = segment["start"]
                #  Applause item, create the element
                create_work_item(primary_file, segment_start, segment["end"], 'Work')
                segment_start = None
            elif segment["label"] == "non-applause":
                # Non applause should be added to the next applause segment
                segment_start = segment["start"]
                # If this is the last segment, output it
                if segment_count == len(applause_segments["segments"]):
                    create_work_item(primary_file, segment_start, segment["end"], 'Other')
                    segment_start = None
            segment_count+=1
        mydata = ET.tostring(element=item, method="xml")
        myfile = open(output_xml, "wb")
        myfile.write(mydata)
    
    exit(0)

def create_work_item(xml_parent, begin, end, label):
    work_item = ET.SubElement(xml_parent, 'Span')
    work_item.set('begin', to_time_string(begin))
    work_item.set('end', to_time_string(end))
    work_item.set('label', label + str(len(xml_parent.getchildren())))

def to_time_string(seconds):
    dt = datetime.utcfromtimestamp(seconds)
    return dt.strftime("%H:%M:%S.%f")[:-3]

if __name__ == "__main__":
    main()
