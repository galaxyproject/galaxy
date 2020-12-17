import { timer, of } from "rxjs";
import { take, pluck, takeUntil } from "rxjs/operators";
import { firstValueFrom } from "utils/observable/firstValueFrom";
import { wipeDatabase } from "../caching/db/pouch";
import { wait } from "jest/helpers";
import { ObserverSpy } from "@hirez_io/observer-spy";

import { SearchParams } from "../model/SearchParams";
import { content$, buildContentId } from "../caching/db/observables";
import { bulkCacheContent, getCachedContent, cacheContent } from "../caching/db/promises";
import { find } from "../caching/db/find";
import { buildContentPouchRequest, monitorHistoryContent } from "./monitorHistoryContent";
import { ACTIONS } from "../caching/db/monitorQuery";

// test data
import historyContent from "../test/json/historyContent.json";
// import collectionContent from "../../test/json/collectionContent.json";

beforeEach(wipeDatabase);
afterEach(wipeDatabase);

describe("buildContentPouchRequest", () => {
    test("should turn inputs into a pouch request suitable for find", () => {
        const fn = buildContentPouchRequest();
        expect(fn).toBeInstanceOf(Function);

        const { history_id, hid } = historyContent[0];
        const inputs = [history_id, new SearchParams(), hid];
        const request = fn(inputs);

        expect(request).toBeDefined();
        expect(request.selector._id).toBeDefined();
        expect(request.selector.history_id).toBeDefined();
    });
});

describe("monitorHistoryContent", () => {
    beforeEach(async () => await bulkCacheContent(historyContent));

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
                pageSize: 100000000, // get everything without pagination for now
            }),
            pluck("initialMatches"),
            take(1),
            takeUntil(timer(2000)) // safety
        );

        const spy = new ObserverSpy();
        monitor$.subscribe(spy);

        await spy.onComplete();

        // monitorHistoryContent has 2 seeks, one up, one down, so two emits
        // with initialMatches, some of the test rows have been doctored so they
        // don't match the initial filters
        const evts = spy.getValues();
        const matches = evts.reduce((acc, matches) => acc + matches.length, 0);

        // show only visible, undeleted rows, there are a couple that don't match
        const expectedRows = historyContent.filter((row) => row.deleted == false && row.visible == true);
        expect(expectedRows.length).not.toEqual(historyContent.length);
        expect(matches).toEqual(expectedRows.length);
    });

    test("should see subsequent updates", async () => {
        const firstDoc = historyContent[0];
        const { history_id, hid } = firstDoc;
        const inputs = [history_id, new SearchParams(), hid];

        const monitor$ = of(inputs).pipe(
            monitorHistoryContent({ inputDebounce: 50 }),
            take(2),
            takeUntil(timer(2000)) // safety, ends stream if test fails
        );

        // monitor observable
        const spy = new ObserverSpy();
        monitor$.subscribe(spy);

        // wait for first emission before updating
        await wait(500);

        // update doc
        const lookup = await getCachedContent(buildContentId(firstDoc));
        lookup.foobar = 123;
        const cached = await cacheContent(lookup);
        expect(cached.updated).toBeTruthy();

        // wait until monitor completes
        await spy.onComplete();
        expect(spy.getValuesLength()).toEqual(2);
        expect(spy.receivedError()).toBe(false);
        expect(spy.receivedNext()).toBe(true);
        expect(spy.receivedComplete()).toBe(true);

        // first emission should have been the initial load
        const firstUpdate = spy.getFirstValue();
        expect(firstUpdate.action).toEqual(ACTIONS.INITIAL);

        const lastUpdate = spy.getLastValue();
        expect(lastUpdate.action).toEqual(ACTIONS.UPDATE);
        expect(lastUpdate.doc._id).toEqual(lookup._id);
        expect(lastUpdate.doc.foobar).toEqual(123);
    });
});
