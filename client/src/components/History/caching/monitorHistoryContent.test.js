import { timer, of } from "rxjs";
import { takeUntil } from "rxjs/operators";
import { firstValueFrom } from "utils/observable/firstValueFrom";
import { wipeDatabase } from "./db/wipeDatabase";
import { wait } from "jest/helpers";
import { ObserverSpy } from "@hirez_io/observer-spy";

import { SearchParams } from "../model/SearchParams";
import { content$ } from "../caching/db/observables";
import { bulkCacheContent, cacheContent } from "../caching/db/promises";
import { find } from "../caching/db/find";
import { buildContentPouchRequest, monitorHistoryContent } from "./monitorHistoryContent";

// test data
import historyContent from "../test/json/historyContent.json";
// import collectionContent from "../../test/json/collectionContent.json";

jest.mock("app");
jest.mock("../caching");

beforeEach(wipeDatabase);
afterEach(wipeDatabase);

const monitorSpinUp = 400;
const monitorSafetyTimeout = 1000;
const selectorHasField = (selector, field) => selector.$and.some((row) => row[field] !== undefined);

describe("buildContentPouchRequest", () => {
    test("should turn inputs into a pouch request suitable for find", () => {
        const fn = buildContentPouchRequest();
        expect(fn).toBeInstanceOf(Function);

        const { history_id, hid } = historyContent[0];
        const inputs = [history_id, new SearchParams(), hid];
        const request = fn(inputs);

        expect(request).toBeDefined();
        expect(request.selector).toBeDefined();
        expect(request.selector.$and).toBeDefined();
        expect(selectorHasField(request.selector, "_id")).toBeTruthy();
        expect(selectorHasField(request.selector, "history_id")).toBeTruthy();
    });
});

describe("monitorHistoryContent", () => {
    let cachedContentMap;

    // cache sample content, store in a map for later, keyed by HID
    beforeEach(async () => {
        const cachedContent = await bulkCacheContent(historyContent, true);
        const cachedContentEntries = cachedContent.map((o) => [o.hid, o]);
        cachedContentMap = new Map(cachedContentEntries);
    });

    afterEach(() => (cachedContentMap = null));

    test("sanity check all the data is in there", async () => {
        const { history_id } = historyContent[0];
        const request = { selector: { history_id } };
        const obs$ = of(request).pipe(find(content$));
        const result = await firstValueFrom(obs$);
        expect(result.length).toEqual(historyContent.length);
    });

    test("should see the pre-inserted content if params match", async () => {
        const { history_id, hid } = historyContent[0];
        const monitor$ = of([history_id, new SearchParams(), hid]).pipe(
            monitorHistoryContent({
                inputDebounce: 50,
                pageSize: 10, // get everything without pagination for now
            }),
            takeUntil(timer(monitorSafetyTimeout)) // safety
        );

        const spy = new ObserverSpy();
        monitor$.subscribe(spy);
        await spy.onComplete();
        expect(spy.getValuesLength()).toBeGreaterThan(0);

        spy.getValues().forEach((evt) => {
            const { key, match, doc } = evt;
            expect(match).toBe(true);
            expect(doc.hid).toEqual(key);
            expect(cachedContentMap.has(key)).toBe(true);
            // we had default params
            expect(doc.isDeleted).toBe(false);
            expect(doc.visible).toBe(true);
        });
    });

    test("should see subsequent updates", async () => {
        const firstDoc = historyContent[0];
        const { history_id, hid } = firstDoc;
        const inputs = [history_id, new SearchParams(), hid];

        const monitor$ = of(inputs).pipe(
            monitorHistoryContent({ inputDebounce: 50 }),
            takeUntil(timer(monitorSafetyTimeout)) // safety
        );

        // monitor observable
        const spy = new ObserverSpy();
        monitor$.subscribe(spy);

        // wait for first emission before updating, this lets all
        // the initial matches emit
        await wait(monitorSpinUp);

        // update one doc
        const firstHid = historyContent[0].hid;
        const updateMe = cachedContentMap.get(firstHid);
        const fakeVal = 123;
        updateMe.foobar = fakeVal;
        const updatedContent = await cacheContent(updateMe, true);
        expect(updatedContent.foobar).toEqual(fakeVal);

        // wait until monitor completes
        await spy.onComplete();

        const lastEmit = spy.getLastValue();
        expect(lastEmit.doc.foobar).toEqual(fakeVal);
    });
});
