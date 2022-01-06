import { of, timer } from "rxjs";
import { takeUntil, share } from "rxjs/operators";
import { ObserverSpy } from "@hirez_io/observer-spy";
import { watchCollection } from "./watchCollection";
import { cacheCollectionContent, bulkCacheDscContent, wipeDatabase } from "components/providers/History/caching";
import { testCollectionContent, testCollection } from "components/providers/History/test/testCollection";
import { untilNthEmission } from "jest/helpers";

// need to mock monitorHistoryContent which is instantiated inside the worker,
// but we can't actually fire up threads.js in a unit test because you can't
// call expose() on the main thread, so we mock the adapter functions which
// generate observables from the worker.
jest.mock("app");
jest.mock("components/providers/History/caching");

const debouncePeriod = 250;
const safetyTimeout = 1000;
const pageSize = 5;
const pluckAll = (arr, prop) => arr.map((o) => o[prop]);

let cachedCollectionContent;

beforeEach(async () => {
    await wipeDatabase();
    cachedCollectionContent = await bulkCacheDscContent(testCollectionContent, true);
    // const cachedIds = pluckAll(cachedCollectionContent, "_id");
    // console.log(cachedIds);
});

afterEach(async () => {
    await wipeDatabase();
});

describe("watchCollection", () => {
    test("should observe pre-inserted content on the initial emission", async () => {
        // the srource stream for the operator is an element_index
        const watcher$ = of(0).pipe(
            watchCollection({
                dsc: testCollection,
                pageSize,
                debouncePeriod,
                debug: false,
            }),
            takeUntil(timer(safetyTimeout))
        );

        // spy on output of observable, wait for it to end
        const spy = new ObserverSpy();
        watcher$.subscribe(spy);
        await spy.onComplete();

        expect(spy.receivedNext()).toBe(true);
        expect(spy.receivedComplete()).toBe(true);
        expect(spy.getValuesLength()).toBe(1);

        const payload = spy.getFirstValue();
        {
            const { startKey, startKeyIndex, targetKey, contents } = payload;

            // at the top of the list, should get the match (element_index = 0) + 2 pages
            expect(startKey).toEqual(0);
            expect(startKeyIndex).toEqual(0);
            expect(targetKey).toEqual(0);
            expect(Array.isArray(contents)).toBe(true);

            // should get back the exact match (element_index = 0, the following page, + 1
            // additional page of buffer-room after the current page
            const returnedIndexes = pluckAll(contents, "element_index");
            // console.log(returnedIndexes);

            expect(contents.length).toBeGreaterThanOrEqual(2 * pageSize);
            expect(returnedIndexes).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
        }
    });

    test("should observe subsequent updates", async () => {
        // the srource stream for the operator is an element_index
        const watcher$ = of(0).pipe(
            watchCollection({
                dsc: testCollection,
                debouncePeriod,
                pageSize,
            }),
            takeUntil(timer(safetyTimeout)),
            share()
        );

        const spy = new ObserverSpy();
        watcher$.subscribe(spy);

        // After the first event, change some stuff on the first row
        // need to delay a little to wait for first emissions to run through
        // otherwise the debouncing will think the 2nd update is the same as the
        await untilNthEmission(watcher$, 1);
        const testChild = cachedCollectionContent[0];
        testChild.foobar = 123;
        const updateResult = await cacheCollectionContent(testChild, true);
        // console.log("after update", updateResult);
        expect(updateResult.foobar).toEqual(123);
        expect(updateResult._rev).not.toEqual(testCollection._rev);

        await spy.onComplete();
        expect(spy.receivedNext()).toBe(true);
        expect(spy.receivedComplete()).toBe(true);
        expect(spy.getValuesLength()).toEqual(2);

        const firstPayload = spy.getFirstValue();
        {
            const { contents } = firstPayload;
            expect(Array.isArray(contents)).toBe(true);
            // no foobar because this happened before the update
            const foobars = pluckAll(contents, "foobar");
            expect(foobars.every((val) => val === undefined)).toBe(true);
        }

        const lastPayload = spy.getLastValue();
        {
            const { contents } = lastPayload;
            expect(Array.isArray(contents)).toBe(true);
            // should have a foobar
            const foobars = pluckAll(contents, "foobar");
            expect(foobars.every((val) => val === undefined)).toBe(false);
        }
    });
});
