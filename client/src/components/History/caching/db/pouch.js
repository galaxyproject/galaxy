/**
 * Generic pouch db operators, These are low-level pouchdb access operators
 * intended to be used to create more specific operators.
 */

import moment from "moment";
import deepEqual from "deep-equal";
import { defer, pipe, from } from "rxjs";
import { tap, filter, mergeMap, reduce, shareReplay } from "rxjs/operators";
import { needs } from "utils/observable";
import { dasherize } from "underscore.string";

import PouchDB from "pouchdb";
import PouchAdapterMemory from "pouchdb-adapter-memory";
import PouchUpsert from "pouchdb-upsert";
import PouchFind from "pouchdb-find";
import PouchErase from "pouchdb-erase";
// import PouchDebug from "pouchdb-debug";

PouchDB.plugin(PouchAdapterMemory);
PouchDB.plugin(PouchUpsert);
PouchDB.plugin(PouchFind);
PouchDB.plugin(PouchErase);
// PouchDB.plugin(PouchDebug);

// debugging stuff
// PouchDB.debug.enable('pouchdb:find');
// const show = (obj) => console.log(JSON.stringify(obj, null, 4));

// Instance storage map, keyed by database name
export const dbs = new Map();

/**
 * Generate an observable that initializes and shares a pouchdb instance.
 *
 * @param {object} options pouchdb initialization configs
 * @return {Observable} observable that emits the pouch instance
 */
export const collection = (opts, appConfig) => {
    return defer(() => {
        const coll = buildCollection(opts, appConfig);
        const name = collectionName(opts, appConfig);
        return from(coll).pipe(tap((db) => dbs.set(name, db)));
    }).pipe(
        filter((db) => db instanceof PouchDB),
        shareReplay(1)
    );
};

async function buildCollection(opts, appConfig) {
    if (!opts) {
        throw new Error("collection: Missing database config");
    }
    if (!appConfig) {
        throw new Error("collection: Missing application config");
    }

    const name = collectionName(opts, appConfig);
    // eslint-disable-next-line no-unused-vars
    const { indexes = [], ...otherOpts } = opts;
    const dbConfig = { ...appConfig.caching, ...otherOpts, name };

    // make instance
    const db = await new PouchDB(dbConfig);

    // pre-install common indexes
    await installCollectionIndexes(db, indexes);

    return db;
}

function collectionName(opts, appConfig) {
    const { name: dbName } = opts;
    const { name: envName } = appConfig;
    return dasherize(`${dbName} ${envName}`);
}

async function installCollectionIndexes(db, indexes = []) {
    const promises = indexes.map((idx) => db.createIndex(idx));
    if (promises.length) {
        await Promise.all(promises);
    }
    return db;
}

/**
 * Retrieves an object from the cache
 *
 * @param {Observable} db$ Observable of a pouchdb instance
 * @param {string} keyName Field to lookup object by
 * @returns {Function} Observable operator
 */
// prettier-ignore
export const getItemByKey = (db$, keyName = "_id") => pipe(
    needs(db$),
    mergeMap(async ([keyValue, db]) => {
        let doc = null;
        if (keyName == "_id") {
            doc = await getDocByDocId(db, keyValue);
        } else {
            doc = await getDocByKeyValue(db, keyName, keyValue);
        }
        return doc;
    })
);

async function getDocByDocId(db, docId) {
    let doc = null;
    try {
        doc = await db.get(docId);
    } catch (err) {
        // pouch throws a 404 when a .get doesn't find anything,
        // which in my mind is a perfectly legitimate result, so
        // we're returning a null here, otherwise rethrow
        const { status } = err;
        if (status !== 404) {
            throw err;
        }
    }
    return doc;
}

async function getDocByKeyValue(db, keyName, keyValue) {
    let doc = null;

    // otherwise do a find by keyname
    const searchConfig = {
        selector: { [keyName]: keyValue },
        limit: 1,
    };

    const response = await db.find(searchConfig);
    if (response.warning) {
        console.warn(response.warning, searchConfig);
    }

    const { docs } = response;
    if (docs && docs.length > 0) {
        doc = docs[0];
    }

    return doc;
}

/**
 * Operator that caches all source documents in the indicated collection.
 * Upserts new fields into the old document, so the props need not be complete,
 * just needs to have the _id.
 *
 * Adds a cached_at timestamp and fixes pouchdb specific field names like
 * "deleted"
 *
 * @source Observable stream of docs to cache
 * @param {Observable} db$ Observable pouchdb instance
 * @returns {Function} Observable operator
 */
// prettier-ignore
export const cacheItem = (db$, returnDoc = false) => pipe(
    needs(db$),
    mergeMap(async ([item, db]) => {

        const result = await db.upsert(item._id, (existing) => {
            // eslint-disable-next-line no-unused-vars
            const { _rev, cached_at, ...existingFields } = existing;

            // ignore if what we're caching is the same as what's in there
            const same = deepEqual(item, existingFields);
            if (same) {return false;}

            return {
                ...existing,
                ...item,
                cached_at: moment().valueOf(),
            };
        });

        if (returnDoc) {
            result.doc = await getDocByDocId(db, result.id);
        }

        return result;
    })
);

/**
 * Doing it the dumb way for now, will try a true bulkDocs call later.
 *
 * @source Observable of docs to cache
 * @param {Observable} db$ Observable of a PouchDB instance
 * @returns {Function} Observable operator
 */
// prettier-ignore
export const bulkCache = (db$, returnDocs = false) => pipe(
    mergeMap((list) =>
        from(list).pipe(
            cacheItem(db$, returnDocs),
            reduce((result, item) => {
                result.push(item);
                return result;
            }, [])
        )
    )
);

/**
 * Creates an operator that will delete the source document from the configured
 * database observable. In pouchdb, deleting just means setting _deleted to
 * true.
 *
 * @source Observable stream of documents to uncache
 * @param {Observable} db$ Observable of the pouchdb instance
 * @returns {Function} Observable operator
 */
// prettier-ignore
export const uncacheItem = (db$) => pipe(
    needs(db$),
    mergeMap(([doomedDoc, db]) => {
        return db.remove(doomedDoc);
    })
);

/**
 * Delete existing indexes in a pouchdb database.
 *
 * @param {PouchDB} db pouch db instance
 * @returns {Promise}
 */
export async function deleteIndexes(db) {
    const response = await db.getIndexes();
    const doomedIndexes = response.indexes.filter((idx) => idx.ddoc !== null);
    const promises = doomedIndexes.map((idx) => db.deleteIndex(idx));
    return await Promise.all(promises);
}
