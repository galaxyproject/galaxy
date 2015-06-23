# -*- coding: utf-8 -*-
import sys
import argparse
import requests
import json
# SearchVariantsResponse /variants/search
variantSets = {
"cervix": 3,
"stomach": 15,
"liver": 10,
"bone": 9,
"bladder": 7,
"brain": 2,
"head and neck": 6,
"lung": 11,
"blood": 0,
"colorectal": 4,
"skin": 17,
"uterus": 16,
"esophagus": 5,
"pancreas": 13,
"prostate": 14,
"ovary": 12,
"kidney": 8,
"breast": 1
}

def variants_search(url, output, request):
  f = open(output, "w")
  r = requests.post(url + "/variants/search", data=request, headers={'content-type':'application/json'})
  f.write(r.text)
  f.close()

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Variant DB GA4GH Communicator')
  parser.add_argument('url', nargs='?', default=None,
  help='Path to variant database.')
  parser.add_argument('out', nargs='?', default=None,
  help='File to save output.')
  parser.add_argument('-vs', '--variantSetIds', dest='variantSetIds', nargs='+', type=str, required=True, default=None,
  help='The IDs of the variant sets to search over.')
  parser.add_argument('-vn', '--variantName', type=str, required=False, default=None,
  help='Only return variants which have exactly this name.')
  parser.add_argument('-c', '--callSetIds', nargs='+', type=str, required=False, default=None,
  help='Only return variant calls which belong to call sets with these IDs. Leaving this blank returns all variant calls.')
  parser.add_argument('-r', '--referenceName', type=str, required=True, default=None,
  help='Only return variants on this reference.')
  parser.add_argument('-st', '--start', type=long, required=False, default=None,
  help='Required. The end of the window (0-based, exclusive) for which overlapping variants should be returned.')
  parser.add_argument('-e', '--end', type=long, required=True, default=None,
  help='The beginning of the window (0-based, inclusive) for which overlapping variants should be returned. Genomic positions are non-negative integers less than reference length. Requests spanning the join of circular genomes are represented as two requests one on each side of the join (position 0).')
  parser.add_argument('-s', '--pageSize', type=int, required=False, default=None,
  help='Specifies the maximum number of results to return in a single page. If unspecified, a system default will be used.')
  parser.add_argument('-t', '--pageToken', type=int, required=False, default=None,
  help='The continuation token, which is used to page through large result sets. To get the next page of results, set this parameter to the value of nextPageToken from the previous response.')
  args = parser.parse_args()
  in_url = vars(args).pop('url')
  out = vars(args).pop('out')
  vs = vars(args).pop('variantSetIds')
  tile_vs = []
  for v in vs:
    tile_vs.append(variantSets[v])
  vars(args)['variantSetIds'] = tile_vs
  # SearchVariantsRequest
  j = json.dumps(vars(args))
  variants_search(in_url, out, j)
