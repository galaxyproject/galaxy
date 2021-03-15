import { of, from, BehaviorSubject, timer } from "rxjs";
import { map, takeUntil, concatMap, delay } from "rxjs/operators";
import { ObserverSpy } from "@hirez_io/observer-spy";

import { History, SearchParams, ScrollPos } from "../../model";
import { bulkCacheContent, wipeDatabase } from "../../caching";
import { getPropRange } from "../../caching/loadHistoryContents";
import { contentPayload } from "./processHistoryStreams";

//#region Test Data

import rawHistory from "../../test/json/History.json";
import rawHistoryContent from "../../test/json/historyContent.json";

const historyContent = rawHistoryContent.map((item) => {
    item.history_id = rawHistory.id;
    return item;
});

const testHistory = new History({
    ...rawHistory,
    hid_counter: historyContent[0].hid + 1,
});

//#endregion

//#region Mocking

import { loadContents } from "./loadContents";
jest.mock("app");
jest.mock("../../caching");
jest.mock("./loadContents");

let loaderMock;
beforeEach(() => {
    // replaces loadContents operator with one that returns test content load summary
    loaderMock = loadContents.mockImplementation((config) => {
        const { min: minHid, max: maxHid } = getPropRange(historyContent, "hid");

        return map((pagination) => {
            return {
                summary: {},
                matches: SearchParams.pageSize,
                totalMatches: historyContent.length,
                minHid: minHid,
                maxHid: maxHid,
                minContentHid: minHid,
                maxContentHid: maxHid,
                limit: 0,
                offset: 0,
            };
        });
    });
});

afterEach(() => {
    loaderMock.mockReset();
});

// set up load contents response

//#endregion

// debugging output
// const payloadHids = (payload) => payload.contents.map((o) => o.hid);

// Create a history and a set of filters then wire up a scrollPos to
// the contentPayload operator, check the payloads that come out

describe("contentPayload operator", () => {
    let sub;
    const safetyTimeout = 2000;
    const disablePoll = true;
    const debouncePeriod = 100;

    beforeEach(async () => {
        await wipeDatabase();
        await bulkCacheContent(historyContent);
    });

    afterEach(async () => {
        if (sub) sub.unsubscribe();
        await wipeDatabase();
    });

    test("single emission, no scrolling, top of list", async () => {
        const spy = new ObserverSpy();
        const start = new ScrollPos();
        const input$ = new BehaviorSubject(start);
        const pageSize = 5;

        // prettier-ignore
        input$.pipe(
            contentPayload({ 
                history: testHistory, 
                pageSize,
                disablePoll,
                debouncePeriod
            }), 
            takeUntil(timer(safetyTimeout))
        ).subscribe(spy);

        await spy.onComplete();

        // should finish
        expect(spy.receivedComplete()).toBe(true);

        // should call the loader once
        expect(loaderMock.mock.calls.length).toEqual(1);

        // should only emit one result
        expect(spy.receivedNext()).toBe(true);
        expect(spy.getValues().length).toEqual(1);

        // expect a payload with results from the top of the list (cursor = 0)
        const payload = spy.getFirstValue();
        expect(payload.contents).toBeDefined();
        expect(payload.contents).toBeInstanceOf(Array);
        expect(payload.contents.length).toEqual(1 + pageSize);
        const payloadHids = payload.contents.map((c) => c.hid);
        expect(payloadHids[0]).toEqual(historyContent[0].hid);
    });

    test("single emission, half way down the list", async () => {
        const spy = new ObserverSpy();
        const start = new ScrollPos({ cursor: 0.5 });
        const input$ = new BehaviorSubject(start);
        const pageSize = 5;

        // prettier-ignore
        input$.pipe(
            contentPayload({ 
                history: testHistory, 
                pageSize,
                disablePoll
            }), 
            takeUntil(timer(safetyTimeout))
        ).subscribe(spy);

        await spy.onComplete();

        // should finish
        expect(spy.receivedComplete()).toBe(true);

        // should call the loader once
        expect(loaderMock.mock.calls.length).toEqual(1);

        // should only emit one result
        expect(spy.receivedNext()).toBe(true);
        expect(spy.getValues().length).toEqual(1);

        // expect a payload with results from the top of the list (cursor = 0)
        const payload = spy.getFirstValue();
        const { contents, startKey, topRows, bottomRows, totalMatches } = payload;

        expect(contents).toBeDefined();
        expect(contents).toBeInstanceOf(Array);
        expect(contents.length).toEqual(1 + 2 * pageSize);
        const payloadHids = contents.map((c) => c.hid);

        // should be down the list a bit
        expect(payloadHids[0]).toBeLessThan(historyContent[0].hid);

        // sartKey should be somewhere in the middle of the returned results
        expect(payloadHids).toContain(startKey);
        expect(payloadHids.indexOf(startKey)).toBeGreaterThan(0);

        // should all add up
        expect(topRows + bottomRows + contents.length).toEqual(totalMatches);
    });

    // prettier-ignore
    test("should emit once for each scroll position input", async () => {
        const spy = new ObserverSpy();
        const pageSize = 5;
        const debouncePeriod = 100;

        // 2 scroll events
        const scrollEvents = [
            ScrollPos.create(),
            ScrollPos.create({ cursor: 0.7 }),
        ];
        const pos$ = from(scrollEvents).pipe(
            concatMap((evt) => of(evt).pipe(delay(4 * debouncePeriod)))
        );

        // listen and emit content near those scroll points
        sub = pos$.pipe(
            contentPayload({
                history: testHistory,
                pageSize,
                disablePoll,
                debouncePeriod,
            }),
            takeUntil(timer(safetyTimeout)),
        ).subscribe(spy);

        // expect 2 outputs
        await spy.onComplete();
        expect(spy.receivedComplete()).toBe(true);
        expect(spy.receivedNext()).toBe(true);

        expect(spy.getValuesLength()).toBe(2);
        expect(spy.getFirstValue().topRows).toEqual(0);
        expect(spy.getLastValue().topRows).toBeGreaterThan(0);
    });
});
