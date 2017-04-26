#!/usr/bin/env python
"""
Given a history name and a collection integer id in that history, this script will split the collection into the failed/pending/empty
datasets "(not ok)" and the successfully finished datasets "(ok)".

Sample call:
python filter_failed_datasets_from_collection.py <GalaxyUrl> <ApiKey> MySpecialHistory 1234
"""
from __future__ import print_function

import sys

from bioblend.galaxy import (
    dataset_collections as collections,
    GalaxyInstance
)

if len(sys.argv) < 5:
    print("Usage: %s <GalaxyUrl> <ApiKey> <HistoryName (must be unique)> <CollectionHistoryId (i.e. the simple integer id)>" % sys.argv[0])
    exit(0)

galaxyUrl = sys.argv[1]
galaxyApiKey = sys.argv[2]
historyName = sys.argv[3]
collectionHistoryId = int(sys.argv[4])

gi = GalaxyInstance(url=galaxyUrl, key=galaxyApiKey)

historyMatches = gi.histories.get_histories(name=historyName)
if (len(historyMatches) > 1):
    print("Error: more than one history matches that name.")
    exit(1)

historyId = historyMatches[0]['id']
historyContents = gi.histories.show_history(historyId, contents=True, deleted=False, visible=True, details=False)
matchingCollections = [x for x in historyContents if x['hid'] == collectionHistoryId]

if len(matchingCollections) == 0:
    print("Error: no collections matching that id found.")
    exit(1)

if len(matchingCollections) > 1:
    print("Error: more than one collection matching that id found (WTF?)")
    exit(1)

collectionId = matchingCollections[0]['id']
failedCollection = gi.histories.show_dataset_collection(historyId, collectionId)
okDatasets = [d for d in failedCollection['elements'] if d['object']['state'] == 'ok' and d['object']['file_size'] > 0]
notOkDatasets = [d for d in failedCollection['elements'] if d['object']['state'] != 'ok' or d['object']['file_size'] == 0]
okCollectionName = failedCollection['name'] + " (ok)"
notOkCollectionName = failedCollection['name'] + " (not ok)"

gi.histories.create_dataset_collection(
    history_id=historyId,
    collection_description=collections.CollectionDescription(
        name=okCollectionName,
        elements=[collections.HistoryDatasetElement(d['object']['name'], d['object']['id']) for d in okDatasets]))

gi.histories.create_dataset_collection(
    history_id=historyId,
    collection_description=collections.CollectionDescription(
        name=notOkCollectionName,
        elements=[collections.HistoryDatasetElement(d['object']['name'], d['object']['id']) for d in notOkDatasets]))
