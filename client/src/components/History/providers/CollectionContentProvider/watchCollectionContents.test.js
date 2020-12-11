import { of, isObservable, timer } from "rxjs";
import { take, takeUntil } from "rxjs/operators";
import { ObserverSpy } from "@hirez_io/observer-spy";
import { wait } from "jest/helpers";
import { SearchParams } from "../../model/SearchParams";
import { watchCollectionCache } from "./watchCollectionCache";

import { cacheCollectionContent, bulkCacheDscContent, wipeDatabase } from "../../caching";

import rawCollection from "../../test/json/collectionContent.json";

// need to mock monitorHistoryContent which is instantiated inside the worker,
// but we can't actually fire up threads.js in a unit test because you can't
// call expose() on the main thread, so we mock the adapter functions which
// generate observables from the worker.
jest.mock("../../caching");

describe("watchCollectionContents", () => {
    beforeEach(wipeDatabase);

    afterEach(wipeDatabase);

    describe("single layer collection", () => {
        let children;

        const testTimeout = 2000;
        const parent_url = "/foo";

        const cursor$ = of(0);
        const fakeDscParent = { contents_url: parent_url };
        const input$ = of([fakeDscParent, new SearchParams()]);

        // insert a list of collection contents
        beforeEach(async () => {
            const rawChildren = rawCollection.map((props) => ({ ...props, parent_url }));
            children = await bulkCacheDscContent(rawChildren, true);
        });

        test("sanity check inputs", () => {
            expect(children).toBeDefined();
            expect(Array.isArray(children)).toBe(true);
            expect(children.length).toEqual(rawCollection.length);
            expect(children.every((doc) => doc.parent_url == parent_url)).toBe(true);
        });

        test("should observe pre-inserted collection content", async () => {
            // prettier-ignore
            const watcher$ = input$.pipe(
                watchCollectionCache({ cursor$, pageSize: 5 }),
                take(1),
                takeUntil(timer(testTimeout))
            );
            expect(isObservable(watcher$)).toBe(true);

            // spy on output of observable, wait for it to end
            const spy = new ObserverSpy();
            watcher$.subscribe(spy);
            await spy.onComplete();

            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);

            const { startKey, contents } = spy.getFirstValue();
            expect(startKey).toEqual(0);
            expect(Array.isArray(contents)).toEqual(true);
            expect(contents.length).toEqual(rawCollection.length);
            // show(contents);
        });

        test("should observe subsequent updates", async () => {
            // prettier-ignore
            const watcher$ = input$.pipe(
                watchCollectionCache({
                    cursor$,
                    pageSize: 100,
                    inputDebounce: 0,
                    outputDebounce: 100,
                }),
                take(2),
                takeUntil(timer(2000))
            );
            expect(isObservable(watcher$)).toBe(true);

            // spy on output of observable, wait for it to end
            const spy = new ObserverSpy();
            watcher$.subscribe(spy);

            // let the initial event fire
            await wait(200);

            // Update one of the rows
            const testCollection = children[0];
            testCollection.foobar = 123;
            const updateResult = await cacheCollectionContent(testCollection, true);
            expect(updateResult.foobar).toEqual(123);
            expect(updateResult._rev).not.toEqual(testCollection._rev);

            await spy.onComplete();

            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);
            expect(spy.getValuesLength()).toEqual(2);

            const { contents } = spy.getLastValue();
            expect(Array.isArray(contents)).toBe(true);
            expect(contents.length).toEqual(children.length);
            expect(contents[0].foobar).toEqual(123);
        });
    });
});
