/**
 * Functions for aggregating incoming cache updates for presentation to the
 * scroller. As cache changes roll in, the updates are summarized and sorted in
 * a SkipList for fast retrieval.
 */

import SkipList from "proper-skip-list";
import { pipe, take, filter } from "iter-tools/es2018";
import { ACTIONS } from "../caching/db/monitorQuery";

// utils for buildContentResult
const firstEntryKey = (entries) => (entries.length ? entries[0][0] : undefined);
const distance = (a, b) => Math.abs(+a - +b);

export const buildContentResult = (cfg = {}) => {
    const { keyDirection = "asc", pageSize = 50, getKey } = cfg;

    if (keyDirection != "asc" && keyDirection != "desc") {
        throw new Error(`buildContentResult: invalid sort direction: ${keyDirection}`);
    }

    return ([updateMap, targetKey]) => {
        if (isNaN(targetKey)) {
            console.warn("Target key should be numeric", updateMap, targetKey);
            throw new Error("buildContentResult: targetKey must be a numeric value", targetKey);
        }

        const { matchingValue, desc, asc } = updateMap.findEntries(targetKey);

        // iterator transformations to find some up/down from target
        const up = pipe(
            filter(([k]) => k > targetKey),
            take(pageSize)
        );
        const down = pipe(
            filter(([k]) => k < targetKey),
            take(pageSize)
        );

        // make iterators into concrete arrays
        const top = Array.from(up(asc));
        const bottom = Array.from(down(desc));

        // startKey is the closest key in the result set to the requested targetKey
        let startKey;
        if (matchingValue !== undefined) {
            startKey = getKey(matchingValue);
        } else {
            const topKey = firstEntryKey(top);
            const bottomKey = firstEntryKey(bottom);
            startKey = findClosestKey(targetKey, topKey, bottomKey);
        }

        // assemble contents array by combining the results
        const match = matchingValue ? [[targetKey, matchingValue]] : [];
        const contentEntries = [...top.reverse(), ...match, ...bottom];
        const contentList = contentEntries.map(([k, v]) => v);

        // reverse order for ascending content
        const contents = keyDirection == "desc" ? contentList : contentList.reverse();

        return { contents, startKey, targetKey };
    };
};

/**
 * Finds closest of keys by measuring numeric distance from targetKey
 *
 * @param   {String|Number}  targetKey  Key to match
 * @param   {String|Number}  keys       Keys to check
 *
 * @return  {String|Number} Member of keys closest to targetKey numerially
 */
const findClosestKey = (targetKey, ...keys) => {
    return keys
        .filter((val) => val !== undefined)
        .reduce((result, key) => {
            if (result !== undefined) {
                const keyCloser = distance(targetKey, key) < distance(targetKey, result);
                return keyCloser ? key : result;
            }
            return key;
        }, undefined);
};

/**
 * Fresh update map, gets built when inputs change
 */
export const newUpdateMap = () => {
    return new SkipList();
};

/**
 * Generates a can function for consuming updates from the pouchdb-live-find.
 * Update variable will either be a big initial chunk of results matching the
 * query or a follow-up incremental change.
 * @param {*} cfg
 */
export const processContentUpdate = (cfg = {}) => {
    const {
        // function to extract a key from the doc.
        // this should return a hid or an element_index
        getKey = (doc) => doc._id,
    } = cfg;

    return (resultMap, update) => {
        const { initialMatches = [], action, doc } = update;

        // initial load
        if (action == ACTIONS.INITIAL && initialMatches.length) {
            initialMatches.forEach((match) => {
                resultMap.upsert(getKey(match), match);
            });
        }

        // incremental updates
        if (action && doc) {
            const key = getKey(doc);
            switch (action) {
                case ACTIONS.IGNORE:
                    console.log("ignored update", doc);
                    break;

                case ACTIONS.UPDATE:
                case ACTIONS.ADD:
                    resultMap.upsert(key, doc);
                    break;

                case ACTIONS.REMOVE:
                    resultMap.delete(key);
                    break;
            }
        }

        return resultMap;
    };
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
