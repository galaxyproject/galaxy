import { of, isObservable, timer } from "rxjs";
import { take, takeUntil } from "rxjs/operators";
import { ObserverSpy } from "@hirez_io/observer-spy";
// import { wait } from "jest/helpers";

import { SearchParams } from "../../model/SearchParams";
import { buildContentId } from "../../caching/db/observables";
import { watchHistoryContents } from "./watchHistoryContents";
import { cacheContent, getCachedContent, bulkCacheContent, wipeDatabase } from "../../caching";

import historyContent from "../../test/json/historyContent.json";

// need to mock monitorHistoryContent which is instantiated inside the worker,
// but we can't actually fire up threads.js in a unit test because you can't
// call expose() on the main thread, so we mock the adapter functions which
// generate observables from the worker.
jest.mock("../../caching");

beforeEach(wipeDatabase);
afterEach(wipeDatabase);

// We're testing observables and we're assuming they complete,
// but we add a takeUntil() to each one in the event that something
// is wrong to avoid making the tests take forever
const safetyTimeout = 600;

describe("watchHistoryContents", () => {
    const firstDoc = historyContent[0];

    beforeEach(async () => await bulkCacheContent(historyContent));

    describe("simple loading scenario", () => {
        const hid$ = of(firstDoc.hid);
        const fakeHistory = { id: firstDoc.history_id };
        const input$ = of([fakeHistory, new SearchParams()]);

        test("should observe pre-inserted content on the initial emission", async () => {
            const watcher$ = input$.pipe(
                watchHistoryContents({
                    hid$,
                    pageSize: 5,
                }),
                take(1),
                takeUntil(timer(safetyTimeout))
            );

            expect(isObservable(watcher$)).toBe(true);

            // spy on output of observable, wait for it to end
            const spy = new ObserverSpy();
            watcher$.subscribe(spy);
            await spy.onComplete();

            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);

            const { startKey, contents } = spy.getFirstValue();
            expect(startKey).toEqual(firstDoc.hid); // we know there should be an exactd match
            expect(Array.isArray(contents)).toEqual(true);
            expect(contents.length).toEqual(6); // we're at the top, should get 5 rows down + the match
        });

        test("should observe subsequently updated data", async () => {
            const watcher$ = input$.pipe(
                watchHistoryContents({
                    hid$,
                    pageSize: 5,
                }),
                // safeguard, sometimes the debouncing merges both results into one
                // event, sometimes they come in as 2 separate ones, either way
                // should be done in 2 secs.
                take(2),
                takeUntil(timer(1000))
            );

            expect(isObservable(watcher$)).toBe(true);

            // spy on output of observable, wait for it to end
            const spy = new ObserverSpy();
            watcher$.subscribe(spy);

            // give the initial load time to emit
            // await wait(250);

            // update one of the items
            const docId = buildContentId(firstDoc);
            const lookup = await getCachedContent(docId);
            expect(lookup.hid).toEqual(firstDoc.hid);
            expect(lookup._id).toEqual(docId);

            lookup.foo = "abc";
            const update = await cacheContent(lookup);
            expect(update.updated).toEqual(true);
            expect(update.id).toEqual(lookup._id);
            expect(update.id).toEqual(docId);

            // wait for last event
            await spy.onComplete();

            // Should see 2 sets of content, the last of which should have the
            // foo field in one of its entries
            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);

            const { contents: lastContents } = spy.getLastValue();
            expect(lastContents.some((doc) => doc.foo == "abc")).toBe(true);
        });
    });

    describe("should respect filter inputs", () => {
        const hid$ = of(firstDoc.hid);
        const fakeHistory = { id: firstDoc.history_id };

        test("deleted flag", async () => {
            const filters = new SearchParams();
            filters.showDeleted = true;

            const input$ = of([fakeHistory, filters]);

            const watcher$ = input$.pipe(
                watchHistoryContents({
                    hid$,
                    pageSize: 5,
                }),
                take(1),
                takeUntil(timer(safetyTimeout))
            );
            expect(isObservable(watcher$)).toBe(true);

            // spy on output of observable, wait for it to end
            const spy = new ObserverSpy();
            watcher$.subscribe(spy);
            await spy.onComplete();

            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);

            const { contents } = spy.getFirstValue();
            expect(Array.isArray(contents)).toEqual(true);
            expect(contents.every((doc) => doc.isDeleted == true)).toBe(true);
        });

        test("hidden flag", async () => {
            const filters = new SearchParams();
            filters.showHidden = true;

            const input$ = of([fakeHistory, filters]);

            const watcher$ = input$.pipe(
                watchHistoryContents({
                    hid$,
                    pageSize: 5,
                }),
                take(1),
                takeUntil(timer(safetyTimeout))
            );
            expect(isObservable(watcher$)).toBe(true);

            // spy on output of observable, wait for it to end
            const spy = new ObserverSpy();
            watcher$.subscribe(spy);
            await spy.onComplete();

            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);

            const { contents } = spy.getFirstValue();
            expect(Array.isArray(contents)).toEqual(true);
            expect(contents.every((doc) => doc.visible == false)).toBe(true);
        });

        test("deleted and hidden flag", async () => {
            const filters = new SearchParams();
            filters.showDeleted = true;
            filters.showHidden = true;

            const input$ = of([fakeHistory, filters]);

            const watcher$ = input$.pipe(
                watchHistoryContents({
                    hid$,
                    pageSize: 5,
                }),
                take(1),
                takeUntil(timer(safetyTimeout))
            );
            expect(isObservable(watcher$)).toBe(true);

            // spy on output of observable, wait for it to end
            const spy = new ObserverSpy();
            watcher$.subscribe(spy);
            await spy.onComplete();

            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);

            const { contents } = spy.getFirstValue();
            expect(Array.isArray(contents)).toEqual(true);
            expect(contents.every((doc) => doc.visible == false)).toBe(true);
            expect(contents.every((doc) => doc.isDeleted == true)).toBe(true);
        });
    });
});
