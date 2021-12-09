import { BehaviorSubject, timer } from "rxjs";
import { takeUntil, share } from "rxjs/operators";
import { ObserverSpy } from "@hirez_io/observer-spy";
import { ScrollPos } from "components/History/model/ScrollPos";
import { bulkCacheContent, wipeDatabase } from "components/providers/History/caching";
import { contentPayload } from "./contentPayload";
import { loadContents } from "./loadContents";
import { serverContent, testHistory, testHistoryContent } from "components/providers/History/test/testHistory";
import { untilNthEmission } from "jest/helpers";

jest.mock("app");
jest.mock("components/providers/History/caching");
jest.mock("./loadContents");

// Create a history and a set of filters then wire up a scrollPos to
// the contentPayload operator, check the payloads that come out

describe("contentPayload operator", () => {
    let sub;
    const safetyTimeout = 2000;
    const disablePoll = true;
    const debouncePeriod = 250;

    beforeEach(async () => {
        await wipeDatabase();
        await bulkCacheContent(testHistoryContent, true);
    });

    afterEach(async () => {
        if (sub) {
            sub.unsubscribe();
        }
        await wipeDatabase();
    });

    // The first emission any time we subscribe to the payload should
    // be the top of the history, this is because we do not yet have any
    // way to gauge how big the history is, so our first emission is always
    // from the top of the list, which is where we reset the scroller when
    // the inputs change anyway

    test("single emission, no scrolling, top of list", async () => {
        const spy = new ObserverSpy();
        const start = new ScrollPos();
        const input$ = new BehaviorSubject(start);
        const pageSize = 10;

        // prettier-ignore
        sub = input$.pipe(
            contentPayload({ 
                parent: testHistory, 
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
        expect(loadContents.mock.calls.length).toEqual(1);

        // should only emit one result
        expect(spy.receivedNext()).toBe(true);
        expect(spy.getValues().length).toEqual(1);

        // expect a payload with results from the top of the list (cursor = 0)
        const { contents } = spy.getFirstValue();

        expect(contents).toBeDefined();
        expect(contents).toBeInstanceOf(Array);
        expect(contents.length).toBeGreaterThanOrEqual(2 * pageSize);

        const payloadHids = contents.map((c) => c.hid);
        expect(payloadHids[0]).toEqual(testHistoryContent[0].hid);
    });

    // The first emission must be from the top of the list, but then
    // the user moves the scroller down half-way. Should get results
    // from the middle of the sample contents

    test("move half way down the list", async () => {
        const pageSize = 5;

        // scroll position (cursor/key)
        const pos$ = new BehaviorSubject(ScrollPos.create());

        // subscribe to payload emitter
        // first emission needs to be at top of list
        const payload$ = pos$.pipe(
            contentPayload({
                parent: testHistory,
                pageSize,
                disablePoll,
            }),
            takeUntil(timer(safetyTimeout)),
            share()
        );

        const spy = new ObserverSpy();
        sub = payload$.subscribe(spy);

        // wait until first emission, then move scroller
        await untilNthEmission(payload$, 1);
        pos$.next(ScrollPos.create({ cursor: 0.5 }));

        await spy.onComplete();
        expect(spy.receivedComplete()).toBe(true);
        expect(spy.receivedNext()).toBe(true);
        // spy.getValues().forEach(reportPayload);

        // should call the loader once
        expect(loadContents.mock.calls.length).toBeGreaterThan(0);

        const serverResults = serverContent();
        const serverResultHids = serverResults.map((o) => o.hid);

        const initialPayload = spy.getFirstValue();
        {
            const { contents, startKey, startKeyIndex, topRows, bottomRows, totalMatches } = initialPayload;
            const listLength = 2 * pageSize;
            const payloadHids = contents.map((o) => o.hid);
            const historyHids = serverResultHids.slice(startKeyIndex, contents.length);

            expect(contents).toBeDefined();
            expect(contents).toBeInstanceOf(Array);
            expect(contents.length).toBeGreaterThanOrEqual(listLength);
            expect(startKey).toEqual(serverResultHids[0]);
            expect(startKeyIndex).toEqual(0);
            expect(topRows).toEqual(0);
            expect(totalMatches).toEqual(serverResults.length);
            expect(payloadHids).toEqual(historyHids);
            expect(topRows + bottomRows + contents.length).toEqual(totalMatches);
        }

        const secondPayload = spy.getLastValue();
        {
            const { contents, startKey, startKeyIndex, topRows, bottomRows, totalMatches } = secondPayload;
            const payloadHids = contents.map((o) => o.hid);

            expect(contents).toBeDefined();
            expect(contents).toBeInstanceOf(Array);
            expect(topRows).toBeGreaterThan(0);
            expect(totalMatches).toEqual(serverResults.length);
            expect(startKeyIndex).toBeGreaterThan(0);
            expect(payloadHids).toContain(startKey);
            expect(topRows + bottomRows + contents.length).toEqual(totalMatches);
        }
    });
});
