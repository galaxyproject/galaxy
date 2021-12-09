import isPromise from "is-promise";
import { isObservable } from "rxjs";
import { wipeDatabase } from "./wipeDatabase";
import { content$, dscContent$, buildContentId, buildCollectionId, prepContent, prepDscContent } from "./observables";
import { firstValueFrom } from "utils/observable/firstValueFrom";

import {
    cacheContent,
    getCachedContent,
    uncacheContent,
    bulkCacheContent,
    getContentByTypeId,
    bulkCacheDscContent,
} from "./promises";

// test data
import historyContent from "components/History/test/json/historyContent.json";
import collectionContent from "components/providers/History/test/json/collectionContent.json";

beforeEach(wipeDatabase);
afterEach(wipeDatabase);

describe("database observables", () => {
    describe("content$", () => {
        it("should be an observable", () => {
            expect(content$).toBeDefined;
            expect(isObservable(content$)).toBeTruthy;
        });

        it("should yield a pouchdb instance", async () => {
            const dbPromise = firstValueFrom(content$);
            expect(isPromise(dbPromise)).toBeTrue;
            const db = await dbPromise;
            expect(db).toBeDefined;
            expect(db.constructor.name).toEqual("PouchDB");
        });

        it("should only build once", async () => {
            const stuff = await firstValueFrom(content$);
            const stuff2 = await firstValueFrom(content$);
            const stuff3 = await firstValueFrom(content$);
            expect(stuff).toStrictEqual(stuff2);
            expect(stuff).toStrictEqual(stuff3);
        });
    });

    describe("dscContent$", () => {
        it("should be an observable", () => {
            expect(dscContent$).toBeDefined;
            expect(isObservable(dscContent$)).toBeTruthy;
        });

        it("should yield a pouchdb instance", async () => {
            const dbPromise = firstValueFrom(dscContent$);
            expect(isPromise(dbPromise)).toBeTrue;
            const db = await dbPromise;
            expect(db).toBeDefined;
            expect(db.constructor.name).toEqual("PouchDB");
        });

        it("should only build once", async () => {
            const stuff = await firstValueFrom(dscContent$);
            const stuff2 = await firstValueFrom(dscContent$);
            const stuff3 = await firstValueFrom(dscContent$);
            expect(stuff).toStrictEqual(stuff2);
            expect(stuff).toStrictEqual(stuff3);
        });
    });
});

describe("history content operators and functions", () => {
    const testDoc = historyContent[0];
    const testId = buildContentId(testDoc);

    describe("buildContentId", () => {
        it("should add the history and hid together", () => {
            const id = buildContentId(testDoc);
            expect(id).toContain(String(testDoc.history_id));
            expect(id).toContain(String(testDoc.hid));
        });
    });

    describe("prepContent", () => {
        const doc = prepContent(testDoc);

        it("should generate an _id for the content", () => {
            expect(doc._id).toContain(String(testDoc.history_id));
            expect(doc._id).toContain(String(testDoc.hid));
        });

        it("should rename the deleted field because pouchdb reserves that prop", () => {
            expect(doc.deleted).toBeUndefined;
            expect(doc.isDeleted).toBeDefined;
            expect(doc.isDeleted).toEqual(testDoc.deleted);
        });
    });

    describe("cacheContent", () => {
        it("should cache a single document", async () => {
            const cacheSummary = await cacheContent(testDoc);
            expect(cacheSummary).toBeDefined;
            expect(cacheSummary.id).toEqual(testId);
        });
    });

    describe("getCachedContent", () => {
        it("should lookup cached content", async () => {
            const cacheSummary = await cacheContent(testDoc);
            expect(cacheSummary).toBeDefined;
            expect(cacheSummary.id).toEqual(testId);

            const lookup = await getCachedContent(testId);
            expect(lookup).toBeDefined;
            expect(lookup._id).toEqual(testId);
        });
    });

    describe("uncacheContent", () => {
        it("should erase a previously cached item", async () => {
            await cacheContent(testDoc);
            const cachedDoc = await getCachedContent(testId);
            const deleteResult = await uncacheContent(cachedDoc);
            expect(deleteResult.ok).toBeTruthy;
            const lookup = await getCachedContent(testId);
            expect(lookup).toEqual(null);
        });
    });

    describe("getContentByTypeId", () => {
        it("should retrieve cached content using the type_id", async () => {
            // cache some content
            const { id } = await cacheContent(testDoc);

            // look it up using _id
            const { history_id, type_id } = await getCachedContent(id);

            // lookup by type_id
            const docByType = await getContentByTypeId(history_id, type_id);
            expect(docByType.type_id).toBe(type_id);
        });
    });

    describe("cacheContent and return doc", () => {
        it("should cache raw props and return with an _id and a cached_at time", async () => {
            const doc = await cacheContent(testDoc, true);
            expect(doc._id).toEqual(buildContentId(testDoc));
            expect(doc.cached_at).toExist;
            expect(typeof doc.cached_at).toEqual("number");
            expect(doc.cached_at).toBeGreaterThan(0);
        });
    });

    describe("bulkCacheContent", () => {
        it("should put a whole line of stuff into the cache", async () => {
            const bulkResult = await bulkCacheContent(historyContent);
            expect(bulkResult.length).toEqual(historyContent.length);
            const cachedIds = bulkResult.map((item) => item.id);
            const inputIds = historyContent.map((doc) => buildContentId(doc));
            expect(cachedIds).toEqual(inputIds);
        });
    });
});

describe("collection content operators and functions", () => {
    describe("prepDscContent", () => {
        it("should process a raw doc (insert from ajax)", () => {
            const raw = collectionContent[0];
            raw.parent_url = "foo"; // required step
            const dsc = prepDscContent(raw);
            expect(dsc).toExist;
            expect(dsc._id).toContain(raw.parent_url);
            expect(dsc._id).toContain(String(raw.element_index));
        });

        // Warrants more testing because we have to untwist the api response format as
        // well as working on existing (already converted) objects

        test("should return valid results for pre-processed cache results (on update)", () => {
            // simulate a collection that has already been cached

            const updateMe = {
                id: "fb85969571388350",
                type_id: "dataset_collection-fb85969571388350",
                model_class: "DatasetCollection",
                history_content_type: "dataset_collection",
                name: "ABC",
                element_identifier: "ABC",
                element_index: 10000,
                element_type: "dataset_collection",
                parent_url: "/abc/def/ghi",
                contents_url: "/api/dataset_collections/5a1cff6882ddb5b2/contents/fb85969571388350",
                collection_type: "paired",
                cached_at: 1602265731626,
                _id: "/abc/def/ghi-000000010000",
                _rev: "6-377d7786587cd5e9e4524a736c228a90",
            };

            const processed = prepDscContent(updateMe);
            expect(processed._id).toEqual(buildCollectionId(updateMe));
            expect(processed.history_content_type).toBe("dataset_collection");
            expect(processed.id).toEqual(updateMe.id);
            expect(processed.type_id).toEqual(updateMe.type_id);
        });
    });

    describe("bulkCacheDscContent", () => {
        // we need to add parent_url to every item in the collection contents cache
        // becahse the contents_url for the collection the contents came from is
        // going to be the parent_url and part of the _id
        const parent_url = "fakecollection";
        const collectionData = collectionContent.map((doc) => {
            doc.parent_url = parent_url;
            return doc;
        });

        it("should put a whole line of stuff into the cache", async () => {
            const bulkSummary = await bulkCacheDscContent(collectionData);
            expect(bulkSummary.length).toEqual(collectionContent.length);
            const cachedIds = bulkSummary.map((item) => item.id);
            const inputIds = collectionData.map((doc) => buildCollectionId(doc));
            expect(cachedIds).toEqual(inputIds);
        });

        it("should retrieve that stuff later", async () => {
            const bulkSummary = await bulkCacheDscContent(collectionData);
            expect(bulkSummary.length).toEqual(collectionContent.length);
        });
    });
});

describe("wipeDatabase", () => {
    const testDoc = historyContent[0];
    const testId = buildContentId(testDoc);

    it("should clear out stuff so each test is clean", async () => {
        const cacheSummary = await cacheContent(testDoc);
        expect(cacheSummary.id).toEqual(testId);

        // retrieve the cached doc to make sure it's in there
        const retrievedDoc = await getCachedContent(testId);
        expect(retrievedDoc).toExist;
        expect(retrievedDoc._id).toEqual(testId);

        // wipe
        await wipeDatabase();

        // try to retrieve again
        const lookupAgain = await getCachedContent(testId);
        expect(lookupAgain).toEqual(null);
    });
});
