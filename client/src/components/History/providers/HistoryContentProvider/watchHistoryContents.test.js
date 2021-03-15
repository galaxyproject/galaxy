import { of, isObservable, timer } from "rxjs";
import { take, takeUntil } from "rxjs/operators";
import { ObserverSpy } from "@hirez_io/observer-spy";

import { SearchParams } from "../../model/SearchParams";
import { buildContentId } from "../../caching/db/observables";
import { watchHistoryContents } from "./watchHistoryContents";
import { cacheContent, getCachedContent, bulkCacheContent, wipeDatabase } from "../../caching";

import historyContent from "../../test/json/historyContent.json";

// need to mock monitorHistoryContent which is instantiated inside the worker,
// but we can't actually fire up threads.js in a unit test because you can't
// call expose() on the main thread, so we mock the adapter functions which
// generate observables from the worker.
jest.mock("app");
jest.mock("../../caching");

beforeEach(async () => {
    await wipeDatabase();
    await bulkCacheContent(historyContent);
});

afterEach(async () => {
    await wipeDatabase();
});

// We're testing observables and we're assuming they complete,
// but we add a takeUntil() to each one in the event that something
// is wrong to avoid making the tests take forever
const safetyTimeout = 600;

describe("watchHistoryContents", () => {
    const firstDoc = historyContent[0];

    describe("simple loading scenario", () => {
        const hid$ = of(firstDoc.hid);
        const history = { id: firstDoc.history_id };
        const filters = new SearchParams();

        test("should observe pre-inserted content on the initial emission", async () => {
            const watcher$ = hid$.pipe(
                watchHistoryContents({
                    history,
                    filters,
                    pageSize: 5,
                }),
                takeUntil(timer(safetyTimeout))
            );

            expect(isObservable(watcher$)).toBe(true);

            // spy on output of observable, wait for it to end
            const spy = new ObserverSpy();
            watcher$.subscribe(spy);
            await spy.onComplete();

            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);
            expect(spy.getValuesLength()).toBe(1);

            const { startKey, contents } = spy.getFirstValue();
            expect(startKey).toEqual(firstDoc.hid); // we know there should be an exactd match
            expect(Array.isArray(contents)).toEqual(true);
            expect(contents.length).toEqual(6); // we're at the top, should get 5 rows down + the match
        });

        test("should observe subsequently updated data", async () => {
            const watcher$ = hid$.pipe(
                watchHistoryContents({
                    history,
                    filters,
                    pageSize: 5,
                }),
                takeUntil(timer(safetyTimeout))
            );

            // spy on output of observable, wait for it to end
            const spy = new ObserverSpy();
            watcher$.subscribe(spy);

            // wait for the first event
            const firstWatcherEvent$ = watcher$.pipe(take(1));

            // then update the first doc
            firstWatcherEvent$.subscribe(async () => {
                const docId = buildContentId(firstDoc);
                const lookup = await getCachedContent(docId);
                expect(lookup.hid).toEqual(firstDoc.hid);
                expect(lookup._id).toEqual(docId);

                lookup.foo = "abc";
                const update = await cacheContent(lookup);
                expect(update.updated).toEqual(true);
                expect(update.id).toEqual(lookup._id);
                expect(update.id).toEqual(docId);
            });

            // Should see 2 sets of content, the last of which should have the
            // foo field in one of its entries
            await spy.onComplete();
            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);
            expect(spy.getValuesLength()).toBe(2);

            const { contents: lastContents } = spy.getLastValue();
            expect(lastContents.some((doc) => doc.foo == "abc")).toBe(true);
        });
    });

    describe("should respect filter inputs", () => {
        const hid$ = of(firstDoc.hid);
        const history = { id: firstDoc.history_id };
        let filters;

        beforeEach(() => {
            filters = new SearchParams();
        });

        test("deleted flag", async () => {
            filters.showDeleted = true;

            const watcher$ = hid$.pipe(
                watchHistoryContents({
                    history,
                    filters,
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
            filters.showHidden = true;

            const watcher$ = hid$.pipe(
                watchHistoryContents({
                    history,
                    filters,
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
            filters.showDeleted = true;
            filters.showHidden = true;

            const watcher$ = hid$.pipe(
                watchHistoryContents({
                    history,
                    filters,
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
