import { timer } from "rxjs";
import { takeWhile, share, takeUntil } from "rxjs/operators";
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
import { changes, feeds } from "./changes";
import { wait } from "jest/helpers";

// test data
import historyContent from "components/History/test/json/historyContent.json";
import collectionContent from "components/providers/History/test/json/collectionContent.json";

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

    describe("change feed should be shared", () => {
        const lifeTime = 300;
        const spinUpTime = 100;

        test("subscriging should show 1 feed, unsubscribing should show 0", async () => {
            // subscribe to changes once
            const feed$ = content$.pipe(changes(), takeUntil(timer(lifeTime)));
            const spy = new ObserverSpy();
            feed$.subscribe(spy);

            // give it a little time to put itself together
            await wait(spinUpTime);
            expect(feeds.size).toEqual(1);

            // complete, share() should now remove instance
            await spy.onComplete();
            expect(feeds.size).toEqual(0);
        });

        test("subscribing 2 times should result in one feed if it's the same DB", async () => {
            // subscribe to changes onece
            const feed$ = content$.pipe(changes(), takeUntil(timer(2 * lifeTime)));
            const spy = new ObserverSpy();
            feed$.subscribe(spy);

            // give it a little time to put itself together
            await wait(spinUpTime);
            expect(feeds.size).toEqual(1);

            // subscribe again
            const feed2$ = content$.pipe(changes(), takeUntil(timer(lifeTime)));
            const spy2 = new ObserverSpy();
            feed2$.subscribe(spy2);

            await wait(spinUpTime);
            expect(feeds.size).toEqual(1);

            // unsub from 2nd feed
            await spy2.onComplete();
            expect(feeds.size).toEqual(1);

            // unsub from 1st feed
            await spy.onComplete();
            expect(feeds.size).toEqual(0);
        });
    });
});
