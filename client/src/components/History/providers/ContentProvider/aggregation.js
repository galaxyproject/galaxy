/**
 * Functions for aggregating incoming cache updates for presentation to the
 * scroller. As cache changes roll in, the updates are summarized and sorted in
 * a SkipList for fast, ordered retrieval.
 *
 * TODO: PouchDB has similar aggregation capabilities but when last I looked they
 * were too difficult to get working properly with dynamically changing queries.
 * I feel like this is the duty of the caching layer, however, and we should
 * investigate again.
 */

import SkipList from "proper-skip-list";
import { pipe, take, filter } from "iter-tools";
import { SEEK } from "components/providers/History/caching/enums";
import { SearchParams } from "../../model";

// utils for buildContentResult
const distance = (a, b) => Math.abs(+a - +b);

export const buildContentResult = (cfg = {}) => {
    const { keyDirection = SEEK.ASC, pageSize = SearchParams.pageSize } = cfg;

    if (!SEEK.isValid(keyDirection)) {
        throw new Error(`buildContentResult: invalid sort direction: ${keyDirection}`);
    }

    return ([updateMap, targetKey]) => {
        // console.log("buildContentResult", updateMap, rawTargetKey, typeof targetKey);

        if (updateMap === undefined) {
            throw new Error("missing skiplist");
        }
        if (targetKey === undefined) {
            throw new Error("missing target key");
        }
        // make sure key is an int
        if (!Number.isFinite(targetKey)) {
            console.warn("Target key should be numeric", updateMap, targetKey);
            throw new Error("buildContentResult: targetKey must be a numeric value", targetKey);
        }

        const { matchingValue, desc, asc } = updateMap.findEntries(targetKey);

        // We want 3 whole pages, 1 behind us, the one we're on, and 1 ahead of us, this means
        // we have to figure out what "behind" and "in front" mean based on the key direction

        // if the keys are ascending, "down" the list is the asc iterator
        // if the keys are ascending, "up" the list is the desc iterator

        const isAscending = keyDirection == SEEK.ASC;
        const topIterator = isAscending ? desc : asc;
        const bottomIterator = isAscending ? asc : desc;

        const topFilter = pipe(
            filter(([k]) => (isAscending ? k < targetKey : k > targetKey)),
            take(pageSize)
        );

        const bottomFilter = pipe(
            filter(([k]) => (isAscending ? k > targetKey : k < targetKey)),
            take(2 * pageSize)
        );

        const top = Array.from(topFilter(topIterator));
        const bottom = Array.from(bottomFilter(bottomIterator));

        // assemble contents array by combining the results
        const match = matchingValue ? [[targetKey, matchingValue]] : [];
        const contentEntries = [...top.reverse(), ...match, ...bottom];

        // startKey is the closest key in the result set to the requested targetKey
        const { startKey, startKeyIndex } = findClosestEntry(targetKey, contentEntries);

        const contents = contentEntries.map(([k, v]) => v);

        return {
            // list of contents from the skiplist around the targetKey
            contents,

            // original value used to query the skiplist, should be in
            // the middle of the contents list
            targetKey,

            // closest key to the targetKey that actually exists in the slice
            startKey,

            // index of the closest row matching the targetKey, also should
            // be in the middle of the contents
            startKeyIndex,
        };
    };
};

/**
 * Finds closest of keys by measuring numeric distance from targetKey
 *
 * @param   {String|Number}  targetKey  Key to match
 * @param   {String|Number}  entries    content entries from the map i.e. list of [key,val]
 *
 * @return  {Object}                    startKey, startKeyIndex
 */
const findClosestEntry = (targetKey, entries = []) => {
    const startingVal = { startKey: null, startKeyIndex: -1, distance: Infinity };
    return entries
        .filter((entry) => Array.isArray(entry))
        .reduce((result, entry, idx) => {
            const [key] = entry;
            const myDistance = distance(targetKey, key);
            return myDistance < result.distance ? { startKey: key, startKeyIndex: idx, distance: myDistance } : result;
        }, startingVal);
};

/**
 * Fresh update map, gets built when inputs change
 */
export const newUpdateMap = () => {
    return new SkipList();
};

/**
 * Generates a scan function for consuming updates from the pouchdb-live-find.
 * Adds or removes incoming docs from the skiplist
 */
export const processContentUpdate = (resultMap, update) => {
    const { doc, key, match } = update;

    // make sure key is an int
    const storageKey = parseInt(key);

    if (match) {
        resultMap.upsert(storageKey, doc);
    } else if (resultMap.has(storageKey)) {
        resultMap.delete(storageKey);
    }

    return resultMap;
};

// Configurable function returns a key for the updateMap from a doc during upate operations
// aggregate results in a map for each set of id + params
export const getKeyForUpdateMap = (keyField) => (doc) => {
    let rawKey;
    if (keyField in doc) {
        rawKey = doc[keyField];
    } else {
        // won't have a full doc on a delete, but it's embeedded in the id
        const parts = doc._id.split("-");
        rawKey = parseInt(parts[1]);
    }

    const result = parseInt(rawKey);
    if (isNaN(result)) {
        console.warn("Non integer key for document", doc);
        throw new Error("Key for update map should be an integer");
    }

    return result;
};
