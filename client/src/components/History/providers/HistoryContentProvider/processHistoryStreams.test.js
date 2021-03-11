import { BehaviorSubject, timer } from "rxjs";
import { map, take, takeUntil } from "rxjs/operators";
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

const loadContentsResults = historyContent;
const { min: minHid, max: maxHid } = getPropRange(loadContentsResults, "hid");

loadContents.mockImplementation((config) => {
    return map(() => {
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

//#endregion

// Create a history and a set of filters then wire up a scrollPos to
// the contentPayload operator, check the payloads that come out

describe("contentPayload operator", () => {
    beforeEach(async () => {
        await wipeDatabase();
        await bulkCacheContent(historyContent);
    });

    afterEach(async () => {
        await wipeDatabase();
    });

    test("initial emission", async () => {
        const spy = new ObserverSpy();
        const start = new ScrollPos({ cursor: 0.5 });
        const input$ = new BehaviorSubject(start);

        // prettier-ignore
        input$.pipe(
            contentPayload({ history: testHistory, pageSize: 5 }), 
            take(1), 
            takeUntil(timer(1000))
        ).subscribe(spy);

        await spy.onComplete();

        expect(spy.receivedNext()).toBe(true);
        expect(spy.receivedComplete()).toBe(true);

        const thing = spy.getFirstValue();
        const { contents, ...result } = thing;

        console.log(
            "hids",
            contents.map((o) => o.hid)
        );
        console.log("contents", contents.length);
        console.log("result", result);
    });
});
