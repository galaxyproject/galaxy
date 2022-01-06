/**
 * Observable api for caching the galaxy history contents and collection contents
 */

import config from "config";
import { pipe } from "rxjs";
import { map } from "rxjs/operators";
import { collection, cacheItem, uncacheItem, getItemByKey, bulkCache } from "./pouch";
import { contentIndices, dscIndices } from "./cacheIndices";

// helper operator that applies function to each element of sourced array
// prettier-ignore
const applyEach = (fn) => pipe(
    map((list) => list.map(fn))
);

// pad zeros so ids sort properly
const zeroPad = (num, places) => String(num).padStart(places, "0");

/**
 * History Content & associated operators
 */

export const content$ = collection(
    {
        name: "galaxy-content",
        indexes: contentIndices,
    },
    config
);

// prettier-ignore
export const getCachedContent = (key = "_id") => pipe(
    getItemByKey(content$, key)
);

// prettier-ignore
export const cacheContent = (returnDoc = false) => pipe(
    map(prepContent),
    cacheItem(content$, returnDoc),
    map((result) => (returnDoc ? result.doc : result))
);

// prettier-ignore
export const uncacheContent = () => pipe(
    uncacheItem(content$)
);

// prettier-ignore
export const bulkCacheContent = (returnDocs = false) => pipe(
    applyEach(prepContent),
    bulkCache(content$, returnDocs),
    map((list) => (returnDocs ? list.map((result) => result.doc) : list))
);

export const buildContentId = ({ history_id, hid }) => {
    const paddedHid = zeroPad(hid, 12);
    return `${history_id}-${paddedHid}`;
};

export const prepContent = (props) => {
    const { history_content_type, id, type_id: origTypeId, ...theRest } = props;
    const type_id = origTypeId ? origTypeId : `${history_content_type}-${id}`;
    const _id = buildContentId(props);

    const doc = {
        _id,
        history_content_type,
        id,
        type_id,
        ...theRest,
    };

    return fixDeleted(doc);
};

/**
 * Collection content (drill down into a collection). Since we don't really
 * update dsc content, all I think we need is the bulk operator which gets run
 * when the scroller loads new data
 */

export const dscContent$ = collection(
    {
        name: "galaxy-collection-content",
        indexes: dscIndices,
    },
    config
);

// prettier-ignore
export const getCachedCollectionContent = (key = "_id") => pipe(
    getItemByKey(dscContent$, key)
);

// prettier-ignore
export const cacheCollectionContent = (returnDoc) => pipe(
    map(prepDscContent),
    cacheItem(dscContent$, returnDoc),
    map((result) => (returnDoc ? result.doc : result))
);

// prettier-ignore
export const bulkCacheDscContent = (returnDocs = false) => pipe(
    applyEach(prepDscContent),
    bulkCache(dscContent$, returnDocs),
    map((list) => (returnDocs ? list.map((result) => result.doc) : list))
);

// need to deal with both the bent api format that comes in from the ajax call
// as well as re-processing an existing collection item on a subsequent update
// cache operation.
export const prepDscContent = (rawProps) => {
    // console.log("prepDscContent", rawProps);

    const { object = {}, ...rootProps } = rawProps;
    const props = { ...rootProps, ...object };
    const { id, model_class, element_identifier, ...otherObjectFields } = props;

    // Validation
    if (id === undefined) {
        throw new Error("missing id");
    }
    if (model_class === undefined) {
        throw new Error("missing model_class");
    }

    const history_content_type = model_class == "HistoryDatasetAssociation" ? "dataset" : "dataset_collection";
    const type_id = `${history_content_type}-${id}`;

    const newProps = {
        // parent content url + counter as that is the most likely query
        _id: buildCollectionId(props),

        // make a type_id so we can re-use all our functions which depend on it
        id,
        type_id,
        model_class,
        history_content_type,

        // need to rename for cache indexing
        name: element_identifier,
        element_identifier,

        // move stuff out of "object" and into root of cached packet
        ...otherObjectFields,
    };

    const clean = fixDeleted(newProps);

    return clean;
};

export const buildCollectionId = (props) => {
    const { parent_url, element_index } = props;

    // this is not part of the returned api data, we need to provide it after the
    // ajax call from the contents_url we got this from
    if (undefined == parent_url) {
        throw new Error("missing required parent_url");
    }
    if (undefined == element_index) {
        throw new Error("missing rquired element_index");
    }
    const paddedIndex = zeroPad(element_index, 12);
    return `${parent_url}-${paddedIndex}`;
};

/**
 * We need to rename the deleted property because pouchDB uses that field,
 * which is unfortunate
 * @param {Object} props Raw document props
 */
const fixDeleted = (props) => {
    // console.log(props);
    if (Object.prototype.hasOwnProperty.call(props, "deleted")) {
        const { deleted: isDeleted, ...theRest } = props;
        return { isDeleted, ...theRest };
    }
    return props;
};
