import { takeWhile, share } from "rxjs/operators";
import { content$, dscContent$ } from "./observables";
import { wipeDatabase } from "./wipeDatabase";
import {
    bulkCacheContent,
    cacheContent,
    getCachedContent,
    bulkCacheDscContent,
    getCachedCollectionContent,
    cacheCollectionContent,
} from "./promises";
import { changes } from "./changes";

// test data
import historyContent from "../../test/json/historyContent.json";
import collectionContent from "../../test/json/collectionContent.json";

// https://github.com/hirezio/observer-spy/blob/master/README.md
import { ObserverSpy } from "@hirez_io/observer-spy";

beforeEach(wipeDatabase);
afterEach(wipeDatabase);

describe("changes operator", () => {
    describe("history content (content$)", () => {
        test("hears updates when we add stuff to the history content cache", async () => {
            // listen to changes until dumb fake prop appears
            const update$ = content$.pipe(
                changes(),
                takeWhile((change) => change.doc.floobar == undefined, true),
                share()
            );

            // spy on emissions
            const spy = new ObserverSpy();
            update$.subscribe(spy);

            // put some stuff in th cache
            const cacheResults = await bulkCacheContent(historyContent);
            expect(cacheResults.length).toEqual(historyContent.length);

            // pull out one item, modify it
            const testItem = await getCachedContent(cacheResults[0].id);
            expect(testItem._id).toEqual(cacheResults[0].id);
            testItem.floobar = Math.random();
            const updateResult = await cacheContent(testItem);
            expect(updateResult.updated).toBeTruthy();

            // wait for updates to complete, which should happen since we added "floobar"
            await spy.onComplete();

            // last update should be the testItem we saved
            const emits = spy.getValues();
            const lastEmit = spy.getLastValue();
            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);
            expect(lastEmit.id).toEqual(testItem._id);
            expect(lastEmit.doc.floobar).toEqual(testItem.floobar);
            expect(emits.length).toEqual(historyContent.length + 1);

            // original insert + later update
            const updates = emits.filter((update) => update.doc._id == testItem._id);
            expect(updates.length).toEqual(2);

            // only one should have the "floobar" field
            const floobars = emits.filter((update) => update.doc.floobar !== undefined);
            expect(floobars.length).toEqual(1);
        });
    });

    describe("collection content (dscContent$)", () => {
        test("hears updates when we add stuff to the collection content cache", async () => {
            // listen to changes until dumb fake prop appears
            const update$ = dscContent$.pipe(
                changes(),
                takeWhile((change) => change.doc.floobar == undefined, true),
                share()
            );

            // spy on emissions
            const spy = new ObserverSpy();
            update$.subscribe(spy);

            // preprocess collection content to add parent_url
            const fakeParent = "/api/123/blah";
            const processedCollection = collectionContent.map((doc) => {
                doc.parent_url = fakeParent;
                return doc;
            });

            // put some stuff in the cache
            const cacheResults = await bulkCacheDscContent(processedCollection);
            expect(cacheResults.length).toEqual(processedCollection.length);

            // pull out one item, modify it
            const testItem = await getCachedCollectionContent(cacheResults[0].id);
            expect(testItem._id).toEqual(cacheResults[0].id);
            testItem.floobar = Math.random();
            const updateResult = await cacheCollectionContent(testItem);
            expect(updateResult.updated).toBeTruthy();

            // wait for updates to complete, which should happen since we added "floobar"
            await spy.onComplete();

            // last update should be the testItem we saved
            const emits = spy.getValues();
            const lastEmit = spy.getLastValue();
            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);
            expect(lastEmit.id).toEqual(testItem._id);
            expect(lastEmit.doc.floobar).toEqual(testItem.floobar);
            expect(emits.length).toEqual(collectionContent.length + 1);

            // original insert + later update
            const updates = emits.filter((update) => update.doc._id == testItem._id);
            expect(updates.length).toEqual(2);

            // only one should have the "floobar" field
            const floobars = emits.filter((update) => update.doc.floobar !== undefined);
            expect(floobars.length).toEqual(1);
        });
    });
});
